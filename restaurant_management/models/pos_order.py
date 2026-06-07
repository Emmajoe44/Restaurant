# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_open_pos_session(self):
        self.ensure_one()
        session = self.config_id.current_session_id
        if not session:
            raise UserError(_(
                'Open a POS session on %s before refunding or exchanging orders.',
                self.config_id.display_name,
            ))
        return session

    @api.model
    def refund_to_pos_session(self, order_id):
        """Create a refund order in the open session and return POS UI payload."""
        order = self.browse(order_id)
        order.ensure_one()
        if order.state not in ('paid', 'done', 'invoiced'):
            raise UserError(_('Only paid orders can be refunded.'))
        session = order._get_open_pos_session()
        refund_order = order.copy(order._prepare_refund_values(session))
        PosOrderLineLot = self.env['pos.pack.operation.lot']
        for line in order.lines:
            for pack_lot in line.pack_lot_ids:
                PosOrderLineLot += pack_lot.copy()
            line.copy(line._prepare_refund_data(refund_order, PosOrderLineLot))
        return refund_order.export_for_ui()

    @api.model
    def exchange_to_pos_session(self, order_id):
        """Start a new order in the open session with the same items (exchange)."""
        order = self.browse(order_id)
        order.ensure_one()
        if order.state not in ('paid', 'done', 'invoiced'):
            raise UserError(_('Only paid orders can be exchanged.'))
        session = order._get_open_pos_session()
        exchange_order = self.create({
            'name': order.pos_reference + _(' EXCHANGE'),
            'session_id': session.id,
            'date_order': fields.Datetime.now(),
            'partner_id': order.partner_id.id,
            'pricelist_id': order.pricelist_id.id,
            'fiscal_position_id': order.fiscal_position_id.id,
        })
        for line in order.lines:
            line.copy({
                'order_id': exchange_order.id,
                'qty': line.qty,
                'price_unit': line.price_unit,
                'discount': line.discount,
            })
        return exchange_order.export_for_ui()
