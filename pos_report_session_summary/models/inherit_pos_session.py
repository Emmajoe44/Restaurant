from odoo import fields, models, api, _
from odoo.exceptions import UserError


class InheritPosSession(models.Model):
    _inherit = 'pos.session'

    pos_session_order_line_ids = fields.One2many(
        comodel_name='pos.session.order.line',
        inverse_name='pos_session_id',
        string='Pos Order Line', )

    def action_pos_session_closing_control(self):
        self._check_pos_session_balance()
        for session in self:
            if any(order.state == 'draft' for order in session.order_ids):
                raise UserError(_("You cannot close the POS when orders are still in draft"))
            if session.state == 'closed':
                raise UserError(_('This session is already closed.'))
            session.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
            if not session.config_id.cash_control:
                session.action_pos_session_close()
        self.write({'pos_session_order_line_ids': [(
            5, 0, 0,)]})
        order_line_list = []
        order_line_dict = {}
        for order in self.order_ids:
            for line in order.lines:
                line_id = self.pos_session_order_line_ids.browse(line.product_id.id)
                if line_id.id not in order_line_dict:

                    order_line_dict[line_id.id] = (0, 0, {'product_name': line.full_product_name, 'quantity': line.qty,
                                                          'price_unit': line.price_unit,
                                                          'total_amount': line.qty * line.price_unit})
                else:
                    order_line_dict[line_id.id] = (
                        0, 0, {'product_name': line.full_product_name,
                               'quantity': order_line_dict[line_id.id][2]['quantity'] + line.qty,
                               'price_unit': line.price_unit,
                               'total_amount': (order_line_dict[line_id.id][2]['quantity'] + line.qty) * line.price_unit})

        for item in order_line_dict.values():
            order_line_list.append(item)
        self.write({'pos_session_order_line_ids': order_line_list})


class PosSessionOrderLine(models.Model):
    _name = 'pos.session.order.line'
    _description = 'Pos Session Order Line'

    pos_session_id = fields.Many2one(
        comodel_name='pos.session',
        string='Pos Session',
        required=False)
    product_name = fields.Char('Product')
    price_unit = fields.Float(tring='Price', required=False)
    quantity = fields.Integer(string='Quantity', required=False)
    total_amount = fields.Float(string='Total Amount', required=False)
