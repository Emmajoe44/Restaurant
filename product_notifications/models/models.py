# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from datetime import datetime
from dateutil import parser

from odoo.exceptions import ValidationError


class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    expiration_date_notification = fields.Date(
        string='Expiration Date',
        required=True)
    notification_date = fields.Date(
        string='Notification Date',required=True)
    responsible_user = fields.Many2one(
        comodel_name='res.users',
        string='Responsible User',
        required=True)

    # Constrains To Check Expiration Date And Send Notification Date
    @api.constrains('expiration_date_notification', 'notification_date')
    def _check_date(self):
        if self.expiration_date_notification <= self.notification_date:
            raise ValidationError(
                _('The Expiration Date must be greater than the Notification Date'))
    # Send Notification To Specific User By Product Status
    def send_product_notification(self):
        odoobot = self.env.ref('base.partner_root')
        products_list = self.env['product.template'].search([])
        for product_id in products_list:
            if product_id.expiration_date_notification and product_id.notification_date and product_id.responsible_user:
                if product_id.notification_date == fields.Date.today():
                    self.env['mail.message'].create({
                        'message_type': "notification",
                        'subject': 'Product Will Be Expired',
                        'body': '<p> <b>{}</b> Product Will Be Expired At {}'
                                '<p style="margin-top:18px; margin-bottom:16px">'
                                '<a style="background-color:#875A7B;'
                                ' padding:10px; text-decoration:none; color:#fff; border-radius:5px"'
                                'href="/mail/view?model={}&res_id={}">'
                                'View Product</a></p>'.format(product_id.name, product_id.expiration_date_notification,
                                                              self._name, product_id.id),
                        'model': self._name,
                        'res_id': product_id.id,
                        'author_id': odoobot.id,
                        'partner_ids': [product_id.responsible_user.partner_id.id],
                        'notification_ids': [((0, 0, {'res_partner_id': product_id.responsible_user.partner_id.id,
                                                      'notification_type': 'inbox'}))]
                    })
                if product_id.expiration_date_notification == fields.Date.today():
                    self.env['mail.message'].create({
                        'message_type': "notification",
                        'subject': 'Expired Product',
                        'body': '<p> Expired Product <b>{}</b>'
                                '<p style="margin-top:18px; margin-bottom:16px">'
                                '<a style="background-color:#875A7B;'
                                ' padding:10px; text-decoration:none; color:#fff; border-radius:5px"'
                                'href="/mail/view?model={}&res_id={}">'
                                'View Product</a></p>'.format(product_id.name, self._name, product_id.id),
                        'model': self._name,
                        'res_id': product_id.id,
                        'author_id': odoobot.id,
                        'partner_ids': [product_id.responsible_user.partner_id.id],
                        'notification_ids': [((0, 0, {'res_partner_id': product_id.responsible_user.partner_id.id,
                                                      'notification_type': 'inbox'}))]
                    })
