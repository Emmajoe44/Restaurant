# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    confirm_rate = fields.Float(
        string='Confirm rate',
        required=False)

    def _action_confirm(self):
        """ Implementation of additionnal mecanism of Sales Order confirmation.
            This method should be extended when the confirmation should generated
            other documents. In this method, the SO are in 'sale' state (not yet 'done').
        """
        # create an analytic account if at least an expense product
        for order in self:
            if any(expense_policy not in [False, 'no'] for expense_policy in
                   order.order_line.mapped('product_id.expense_policy')):
                if not order.analytic_account_id:
                    order._create_analytic_account()

        if self.pricelist_id.currency_id.name == 'USD':
            self.confirm_rate = self.pricelist_id.currency_id.rate
            for prod in self.order_line:
                prod.price_unit = prod.price_unit
                prod.price_unit = prod.price_unit * self.pricelist_id.currency_id.rate

        return True

    def action_cancel(self):
        cancel_warning = self._show_cancel_wizard()
        if cancel_warning:
            return {
                'name': _('Cancel Sales Order'),
                'view_mode': 'form',
                'res_model': 'sale.order.cancel',
                'view_id': self.env.ref('sale.sale_order_cancel_view_form').id,
                'type': 'ir.actions.act_window',
                'context': {'default_order_id': self.id},
                'target': 'new'
            }
        inv = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        inv.button_cancel()

        if self.pricelist_id.currency_id.name == 'USD':
            for prod in self.order_line:
                prod.write({'price_unit': prod.price_unit / self.confirm_rate})
            self.confirm_rate = 0

        return self.write({'state': 'cancel'})
