# -*- coding: utf-8 -*-
from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        # Accounting only during chart load; POS is configured when POS modules install.
        self.env['dual.cash.setup'].with_company(company).setup_dual_cash(configure_pos=False)
        return res
