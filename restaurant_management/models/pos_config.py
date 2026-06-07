# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    manage_orders = fields.Boolean(string='Manage Orders', default=True)
    module_account = fields.Boolean(default=True)
