# -*- coding: utf-8 -*-


def post_init_hook(cr, registry):
    """Apply dual-cash setup on all companies when the module is installed."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    env['dual.cash.setup'].setup_all_companies()
