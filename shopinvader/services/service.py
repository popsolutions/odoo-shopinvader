# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

from odoo import _
from odoo.addons.component.core import AbstractComponent
from odoo.exceptions import MissingError, UserError
from odoo.osv import expression

from .. import shopinvader_response

_logger = logging.getLogger(__name__)


class BaseShopinvaderService(AbstractComponent):
    _inherit = "base.rest.service"
    _name = "base.shopinvader.service"
    _collection = "shopinvader.backend"
    _expose_model = None

    @property
    def partner(self):
        # partner that matches the real profile on client side
        # or its main contact which in any case is used for all
        # account information.
        return self.work.partner

    @property
    def partner_user(self):
        # partner that matches the real user on client side.
        # The standard `self.partner` will match `partner_user`
        # only when the main customer account is logged in.
        # In this way we can support multiple actors for the same profile.
        # TODO: check if there are place wher it's better to use
        # `partner_user` instead of `partner`.
        return getattr(self.work, "partner_user", self.partner)

    @property
    def shopinvader_session(self):
        return self.work.shopinvader_session

    @property
    def shopinvader_backend(self):
        return self.work.shopinvader_backend

    @property
    def client_header(self):
        return self.work.client_header

    def _scope_to_domain(self, scope):
        # Convert the liquid scope syntax to the odoo domain
        try:
            OPERATORS = {
                "gt": ">",
                "gte": ">=",
                "lt": "<",
                "lte": "<=",
                "ne": "!=",
            }
            domain = []
            for key, value in scope.items():
                if "." in key:
                    key, op = key.split(".")
                    op = OPERATORS[op]
                else:
                    op = "="
                domain.append((key, op, value))
            return expression.normalize_domain(domain)
        except Exception as e:
            raise UserError(_("Invalid scope %s, error : %s"), scope, e)

    def _paginate_search(self, default_page=1, default_per_page=5, **params):
        """
        Build a domain and search on it.
        As we use expression (from Odoo), manuals domains get from "scope" and
        "domain" keys are normalized to avoid issues.
        :param default_page: int
        :param default_per_page: int
        :param params: dict
        :return: dict
        """
        domain = self._get_base_search_domain()
        if params.get("scope"):
            scope_domain = self._scope_to_domain(params.get("scope"))
            scope_domain = expression.normalize_domain(scope_domain)
            domain = expression.AND([domain, scope_domain])
        if params.get("domain"):
            custom_domain = expression.normalize_domain(params.get("domain"))
            domain = expression.AND([domain, custom_domain])
        model_obj = self.env[self._expose_model]
        total_count = model_obj.search_count(domain)
        page = params.get("page", default_page)
        per_page = params.get("per_page", default_per_page)
        records = model_obj.search(
            domain, limit=per_page, offset=per_page * (page - 1)
        )
        return {"size": total_count, "data": self._to_json(records)}

    def _get(self, _id):
        domain = expression.normalize_domain(self._get_base_search_domain())
        domain = expression.AND([domain, [("id", "=", _id)]])
        record = self.env[self._expose_model].search(domain)
        if not record:
            raise MissingError(
                _("The record %s %s does not exist")
                % (self._expose_model, _id)
            )
        else:
            return record

    def _get_base_search_domain(self):
        return []

    def _get_openapi_default_parameters(self):
        defaults = super(
            BaseShopinvaderService, self
        )._get_openapi_default_parameters()
        defaults.append(
            {
                "name": "API-KEY",
                "in": "header",
                "description": "Ath API key",
                "required": True,
                "schema": {"type": "string"},
                "style": "simple",
            }
        )
        defaults.append(
            {
                "name": "PARTNER-EMAIL",
                "in": "header",
                "description": "Logged partner email",
                "required": False,
                "schema": {"type": "string"},
                "style": "simple",
            }
        )
        return defaults

    def _is_logged_in(self):
        """
        Check if the current partner is a real partner (not the anonymous one
        and not empty)
        :return: bool
        """
        logged = False
        if (
            self.partner
            and self.partner != self.shopinvader_backend.anonymous_partner_id
        ):
            logged = True
        return logged

    def _is_logged(self):
        _logger.warning("DEPRECATED: You should use `self._is_logged_in()`")
        return self._is_logged_in()

    @property
    def shopinvader_response(self):
        """
        An instance of
        ``odoo.addons.shopinvader.shopinvader_response.ShopinvaderResponse``.
        """
        return shopinvader_response.get()

    def dispatch(self, method_name, _id=None, params=None):
        res = super().dispatch(method_name, _id=_id, params=params)
        store_cache = self.shopinvader_response.store_cache
        if store_cache:
            values = res.get("store_cache", {})
            values.update(store_cache)
            res["store_cache"] = values
        session = self.shopinvader_response.session
        if session:
            values = res.get("set_session", {})
            values.update(session)
            res["set_session"] = values
        return res
