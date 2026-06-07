# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['pos.config'].search([]).write({
        'manage_orders': True,
        'module_account': True,
    })
