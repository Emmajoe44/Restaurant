# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_order_currency_id',
        store=True,
        readonly=True,
    )
    amount_total_usd = fields.Float(
        string='Total (USD)',
        compute='_compute_dual_currency_totals',
        digits=(16, 2),
        readonly=True,
    )
    amount_total_ssp = fields.Float(
        string='Total (SSP)',
        compute='_compute_dual_currency_totals',
        digits=(16, 2),
        readonly=True,
    )

    @api.depends('pricelist_id', 'pricelist_id.currency_id', 'config_id.currency_id')
    def _compute_order_currency_id(self):
        for order in self:
            order.currency_id = (
                order.pricelist_id.currency_id or order.config_id.currency_id
            )

    @api.model
    def _get_usd_ssp_currencies(self):
        Currency = self.env['res.currency']
        usd = Currency.search([('name', '=', 'USD')], limit=1)
        ssp = Currency.search([('name', '=', 'SSP')], limit=1)
        return usd, ssp

    @api.depends(
        'amount_total',
        'currency_id',
        'pricelist_id',
        'pricelist_id.currency_id',
        'date_order',
        'company_id',
    )
    def _compute_dual_currency_totals(self):
        usd, ssp = self._get_usd_ssp_currencies()
        for order in self:
            company = order.company_id or self.env.company
            order_date = order.date_order or fields.Datetime.now()
            src = (
                order.currency_id
                or order.pricelist_id.currency_id
                or company.currency_id
            )
            amount = order.amount_total
            if not src or not amount:
                order.amount_total_usd = 0.0
                order.amount_total_ssp = 0.0
                continue
            if usd and src == usd:
                order.amount_total_usd = amount
                order.amount_total_ssp = (
                    usd._convert(amount, ssp, company, order_date) if ssp else 0.0
                )
            elif ssp and src == ssp:
                order.amount_total_ssp = amount
                order.amount_total_usd = (
                    ssp._convert(amount, usd, company, order_date) if usd else 0.0
                )
            else:
                order.amount_total_usd = (
                    src._convert(amount, usd, company, order_date) if usd else amount
                )
                order.amount_total_ssp = (
                    src._convert(amount, ssp, company, order_date) if ssp else amount
                )

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._compute_order_currency_id()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if 'pricelist_id' in vals:
            self._compute_order_currency_id()
        return res

    def _get_cash_payment_method_for_pricelist(self, payment_method):
        """Use Cash SSP or Cash USD based on the order pricelist currency."""
        self.ensure_one()
        if not payment_method.is_cash_count:
            return payment_method
        currency = self.pricelist_id.currency_id
        if not currency:
            return payment_method
        match = self.session_id.payment_method_ids.filtered(
            lambda pm: pm.is_cash_count
            and pm.cash_journal_id
            and pm.cash_journal_id.currency_id == currency
        )
        return match[:1] or payment_method

    def add_payment(self, data):
        if data.get('payment_method_id'):
            pm = self.env['pos.payment.method'].browse(data['payment_method_id'])
            data = dict(data)
            data['payment_method_id'] = self._get_cash_payment_method_for_pricelist(pm).id
        return super().add_payment(data)


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            pm_id = vals.get('payment_method_id')
            order_id = vals.get('pos_order_id')
            if pm_id and order_id:
                order = self.env['pos.order'].browse(order_id)
                pm = self.env['pos.payment.method'].browse(pm_id)
                vals['payment_method_id'] = order._get_cash_payment_method_for_pricelist(pm).id
        return super().create(vals_list)
