# -*- coding: utf-8 -*-
# Copyright 2016 Akretion (http://www.akretion.com)
# Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from openerp.http import request

def rjson(result):
    return request.make_response(
        json.dumps(result),
        headers={'Content-Type': 'application/json'})
