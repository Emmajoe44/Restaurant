# -*- coding: utf-8 -*-
from odoo import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.depends('company_id', 'company_id.currency_id')
    def _compute_currency(self):
        """Session uses company currency; each order uses its pricelist currency (SSP/USD)."""
        for config in self:
            config.currency_id = config.company_id.currency_id
