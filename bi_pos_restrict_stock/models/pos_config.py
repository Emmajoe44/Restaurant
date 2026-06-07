# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
import json


class PosConfig(models.Model):
    _inherit = "pos.config"

    pos_display_stock = fields.Boolean(string='Display Stock in POS')
    pos_restrict_product = fields.Boolean(string='Restrict Product Out of Stock in POS')
    pos_stock_type = fields.Selection(
        [('onhand', 'Qty on Hand'), ('virtual', 'Virtual Qty'), ('both', 'Both')], string='Stock Type',default='onhand')


class Product(models.Model):
    _inherit = 'product.product'

    quant_ids = fields.One2many("stock.quant", "product_id", string="Quants",
                                domain=[('location_id.usage', '=', 'internal')])

    quant_text = fields.Text('Quant Qty', compute='_compute_avail_locations', store=True)

    @api.depends('stock_quant_ids', 'stock_quant_ids.product_id', 'stock_quant_ids.location_id',
                 'stock_quant_ids.quantity')
    def _compute_avail_locations(self):
        for rec in self:
            final_data = {}
            rec.quant_text = json.dumps(final_data)
            if rec.type == 'product':
                quants = self.env['stock.quant'].sudo().search(
                    [('product_id', 'in', rec.ids), ('location_id.usage', '=', 'internal')])
                for quant in quants:
                    loc = quant.location_id.id
                    if loc in final_data:
                        last_qty = final_data[loc][0]
                        final_data[loc][0] = last_qty + quant.quantity
                    else:
                        final_data[loc] = [quant.quantity, 0, 0]

                rec.quant_text = json.dumps(final_data)
        return True


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def create(self, vals):
        res = super(StockQuant, self).create(vals)

        notifications = []
        for rec in res:
            prod_data = rec.product_id.read(['id', 'qty_available', 'virtual_available', 'quant_text'])[0]
            prod_data = json.dumps(prod_data)
            notifications.append(((self._cr.dbname, 'pos.sync.stock', self.env.user.id), {
                'id': rec.product_id.ids, 'prod_data': prod_data}))

        if len(notifications) > 0:
            self.env['bus.bus'].sendmany(notifications)

        return res

    def write(self, vals):
        res = super(StockQuant, self).write(vals)
        notifications = []
        for rec in self:
            prod_data = rec.product_id.read(['id', 'qty_available', 'virtual_available', 'quant_text'])[0]
            prod_data = json.dumps(prod_data)
            notifications.append(((self._cr.dbname, 'pos.sync.stock', self.env.user.id), {
                'id': rec.product_id.ids, 'prod_data': prod_data}))

        if len(notifications) > 0:
            self.env['bus.bus'].sendmany(notifications)

        return res
