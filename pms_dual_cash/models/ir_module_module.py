# -*- coding: utf-8 -*-
from odoo import models


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def button_immediate_install(self):
        res = super().button_immediate_install()
        if self.name == 'point_of_sale':
            self.env['dual.cash.setup'].setup_all_companies()
        return res
