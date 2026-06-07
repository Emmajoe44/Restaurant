from odoo import fields, models, _,api
from odoo.exceptions import AccessError


class SalesDetailsWizard(models.TransientModel):
    _name = 'sales.details.wizard'
    _description = 'Sales Details Wizard'

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True)
    from_date = fields.Date(string='From Date', required=True)
    to_date = fields.Date(string='To Date', required=True)
    state = fields.Selection(
        string='Status',
        selection=[('draft', 'Quotation  Draft'),
                   ('sent', 'Quotation Sent'),
                   ('sale', 'Sales Order'),
                   ('done', 'Locked'),
                   ('cancel', 'Canceled'),
                   ],
        required=True, )
    get_state_value = fields.Char(string='Get_st_value', required=False, compute='_get_state_value_function')

    @api.depends('state')
    def _get_state_value_function(self):
        self.get_state_value = dict(self._fields['state'].selection).get(self.state)

    def print_sales_details(self):
        data = {'model': self._name, 'ids': self.ids, 'form': self.read()[0]}
        return self.env.ref('custom_sales.sales_details_report').report_action(self, data=data)


class ReportSalesDetailsWizard(models.AbstractModel):
    _name = 'report.custom_sales.sales_details_report_view'

    def _get_report_values(self, docids, data=None):
        selected_currency = data['form']['currency_id'][0]
        selected_form_date = data['form']['from_date']
        selected_to_date = data['form']['to_date']
        selected_state = data['form']['state']
        status_value = data['form']['get_state_value']

        sales_details_data = self.env['sale.order'].search(
            [('create_date', '>=', selected_form_date), ('create_date', '<=', selected_to_date),
             ('currency_id_to_get_rate', '=', selected_currency),('state', '=', selected_state)])
        if selected_form_date >= selected_to_date:
            raise AccessError(_("From Date Must Be Grater Than To Date"))
        sales_total_amount = 0
        sales_details_list = []
        if sales_details_data:
            for sale_order in sales_details_data:
                vals = {'sale_order_number': sale_order.name, 'create_date': sale_order.create_date,
                        'customer': sale_order.partner_id.name, 'sales_person': sale_order.user_id.name,
                        'amount': sale_order.amount_total, 'status': sale_order.state}
                sales_total_amount += sale_order.amount_total
                sales_details_list.append(vals)
        else:
            raise AccessError(_("No Data To Display !"))
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'from_date': selected_form_date,
            'to_date': selected_to_date,
            'currency_name': data['form']['currency_id'][1],
            'total_amount': sales_total_amount,
            'state': status_value,
            'docs': sales_details_list,
        }

