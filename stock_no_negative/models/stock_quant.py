# ?? 2015-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError
from odoo.tools import config, float_compare

class StockMoveUpdate(models.Model):
    _inherit = "stock.move"
    
    def _compute_cost(self):
        for rec in self:
            rec.computed_cost = rec.quantity_done * rec.product_id.standard_price
            
    computed_cost = fields.Float("Cost",compute="_compute_cost")
    
class StockMoveUpdate(models.Model):
    _inherit = "stock.move.line"
    
    def _compute_cost(self):
        for rec in self:
            rec.computed_cost = rec.qty_done * rec.product_id.standard_price
            
    computed_cost = fields.Float("Cost",compute="_compute_cost")    
class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _compute_cost(self):
        for rec in self:
            rec.cost_value = rec.quantity * rec.product_id.standard_price
            rec.active = rec.product_id.active
            rec.is_expireed = False
            if rec.product_id.x_expiry:
                if rec.product_id.x_expiry >= fields.Date.today():
                    rec.is_expireed = False
                else:
                    rec.is_expireed = True
    cost_value = fields.Float("Cost Value",compute='_compute_cost')
    active = fields.Boolean('Is Active',default=True)
    reorder_level = fields.Integer(related="product_tmpl_id.x_reorder")
    exp_date = fields.Date(related="product_id.x_expiry",store=True)
    
    
    is_expireed = fields.Boolean('Is Expired')
    
    def _compute_sales(self):
        for rec in self:
            rec.sales_value = rec.quantity * rec.product_id.lst_price
    sales_value = fields.Float("Sales Value",compute='_compute_sales')
    @api.constrains("product_id", "quantity")
    def check_negative_qty(self):
        p = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        check_negative_qty = (
            config["test_enable"] and self.env.context.get("test_stock_no_negative")
        ) or not config["test_enable"]
        if not check_negative_qty:
            return

        for quant in self:
            disallowed_by_product = (
                not quant.product_id.allow_negative_stock
                and not quant.product_id.categ_id.allow_negative_stock
            )
            disallowed_by_location = not quant.location_id.allow_negative_stock
            if (
                float_compare(quant.quantity, 0, precision_digits=p) == -1
                and quant.product_id.type == "product"
                and quant.location_id.usage in ["internal", "transit"]
                and disallowed_by_product
                and disallowed_by_location
            ):
                msg_add = ""
                if quant.lot_id:
                    msg_add = _(" lot '%s'") % quant.lot_id.name_get()[0][1]
                raise ValidationError(
                    _(
                        "You cannot validate this stock operation because the "
                        "stock level of the product '%s'%s would become negative "
                        "(%s) on the stock location '%s' and negative stock is "
                        "not allowed for this product and/or location."
                    )
                    % (
                        quant.product_id.display_name,
                        msg_add,
                        quant.quantity,
                        quant.location_id.complete_name,
                    )
                )
