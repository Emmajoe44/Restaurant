from odoo import fields, models, api, _
from odoo.exceptions import AccessError
from datetime import datetime, date


class ProductDetailsWizard(models.TransientModel):
    _name = 'product.details.wizard'
    _description = 'product Details Wizard'

    def print_product_details(self):
        data = {'model': self._name, 'ids': self.ids, 'form': self.read()[0]}
        return self.env.ref('custom_product.product_details_report').report_action(self, data=data)


class ReportProductDetailsWizard(models.AbstractModel):
    _name = 'report.custom_product.product_details_report_view'

    def _get_report_values(self, docids, data=None):
        product_ids = self.env['product.template'].search([])
        product_total_amount = 0
        product_details_list = []
        if product_ids:
            for product in product_ids:
                vals = {'product_name': product.name, 'category_id': product.categ_id.name,
                        'list_price': product.list_price, 'qty_available': product.qty_available,
                        'amount': (product.qty_available * product.list_price), }
                product_total_amount += (product.qty_available * product.list_price)
                product_details_list.append(vals)
        else:
            raise AccessError(_("No Data To Display !"))
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'total_amount': product_total_amount,
            'docs': product_details_list,
        }
