# ?? 2015-2016 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import UserError


class ExchangeUpdater(models.Model):
    _name = "exchange.updater"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def exchange_approved(self):
        for r in self.exchange_updater_line_ids:
            products = self.env["product.product"].search(
                [("id", "=", r.product_id.id)]
            )
            for pr in products:
                pr.write({"list_price": r.rounded_change})
        self.state = "confirm"
    def analyze(self):

        products = self.env['product.product'].search([('available_in_pos', '=', True)])
        lst_products = []
        lst_products.append((5,0,0))
        for x in products:
            percentage_float = 0.0
            percentage_float = self.percentage/100
            increased_value = 0
            increased_value = x.list_price + (x.list_price * percentage_float)
            increased_in_les = increased_value % 500
            increased_in_fifties = (increased_value-increased_in_les)/500


            if(increased_in_les>150):
                increased_in_fifties += 1

            new_value = increased_in_fifties * 500
            obj_given = {'exchange_updater_id': self.id,
                         'product_id': x.id,
                         'exact_increase':increased_value,
                         'rounded_change':new_value}

            lst_products.append([0, 0, obj_given])

        self.exchange_updater_line_ids = lst_products

    @api.onchange('last_rate','current_rate')
    def changed_rate(self):
        if self.last_rate>0:
            self.percentage =((self.current_rate - self.last_rate)/ self.last_rate)*100
    state = fields.Selection(
        [("draft", "Draft"), ("confirm", "Confirmed")],
        default="draft",
        required=True,
        tracking=True,
    )
    date = fields.Date("Date")
    last_rate = fields.Float("Last Rate")
    current_rate = fields.Float("Current Rate")
    percentage = fields.Float("Percentage")
    exchange_updater_line_ids = fields.One2many("exchange.updater.line","exchange_updater_id")

class ExchangeUpdaterLine(models.Model):
    _name = "exchange.updater.line"
    exchange_updater_id = fields.Many2one("exchange.updater", ondelete='cascade')
    date = fields.Date("Date",related='exchange_updater_id.date')
    product_id = fields.Many2one("product.product")
    current_price = fields.Float(related="product_id.list_price")
    exact_increase = fields.Float("Exact Change")
    rounded_change = fields.Float("Rounded Change")

class ProductCategory(models.Model):
    _inherit = "product.category"

    allow_negative_stock = fields.Boolean(
        string="Allow Negative Stock",
        help="Allow negative stock levels for the stockable products "
        "attached to this category. The options doesn't apply to products "
        "attached to sub-categories of this category.",
    )



class ProductProductUpdate(models.Model):
    _inherit = "product.product"


    def _compute_sales(self):
        for rec in self:
            rec.sales_value = rec.qty_available * rec.product_tmpl_id.lst_price
    def _compute_costs(self):
        for rec in self:
            rec.cost_value = rec.qty_available * rec.product_tmpl_id.standard_price

    sales_value = fields.Float("Sales Value",compute='_compute_sales')
    cost_value = fields.Float("Sales Value", compute='_compute_costs')

class ProductTemplate(models.Model):
    _inherit = "product.template"
    x_reorder =fields.Integer("Reorder level")
    x_expiry = fields.Date("Date")
    def write(self, vals):
        if 'uom_id' in vals:
            new_uom = self.env['uom.uom'].browse(vals['uom_id'])
            updated = self.filtered(lambda template: template.uom_id != new_uom)
            done_moves = self.env['stock.move'].search([('product_id', 'in', updated.with_context(active_test=False).mapped('product_variant_ids').ids)], limit=1)
            #if done_moves:
            #    raise UserError(_("You cannot change the unit of measure as there are already stock moves for this product. If you want to change the unit of measure, you should rather archive this product and create a new one."))
        if 'type' in vals and vals['type'] != 'product' and sum(self.mapped('nbr_reordering_rules')) != 0:
            raise UserError(_('You still have some active reordering rules on this product. Please archive or delete them first.'))
        if any('type' in vals and vals['type'] != prod_tmpl.type for prod_tmpl in self):
            existing_move_lines = self.env['stock.move.line'].search([
                ('product_id', 'in', self.mapped('product_variant_ids').ids),
                ('state', 'in', ['partially_available', 'assigned']),
            ])
            if existing_move_lines:
                raise UserError(_("You can not change the type of a product that is currently reserved on a stock move. If you need to change the type, you should first unreserve the stock move."))
        return super(ProductTemplate, self).write(vals)

    @api.onchange('x_reorder','qty_available')
    def _compute_is_low_level(self):
        for rec in self:

            if rec.x_reorder >= rec.qty_available:
                rec.is_low = True
            else:
                rec.is_low = False


    @api.onchange('x_reorder','qty_available')
    def _compute_is_expired(self):
        for rec in self:
            rec.is_expireed = False
            if rec.x_expiry:
                if rec.x_expiry >= fields.Date.today():
                    rec.is_expireed = False
                else:
                    rec.is_expireed = True



    is_low = fields.Boolean('Is low',compute='_compute_is_low_level')
    is_expireed = fields.Boolean('Is Expired', compute='_compute_is_expired')
    allow_negative_stock = fields.Boolean(
        string="Allow Negative Stock",
        help="If this option is not active on this product nor on its "
        "product category and that this product is a stockable product, "
        "then the validation of the related stock moves will be blocked if "
        "the stock level becomes negative with the stock move.",
    )
