# ?? 2015-2016 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api,_
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_repr
from odoo.exceptions import ValidationError

class AccountingExchange(models.Model):
    _name = 'company.exchange'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _description = 'Currency Exchange'
    _order = "id desc"
    _check_company_auto = True

    def validate(self):
        for rec in self:
            gain_account_id = self.env['account.account'].search([('name', '=', 'Foreign Exchange Gain')], limit=1)

            exc_gain = 0
            exc_loss = 0
            if rec.amount > rec.available_amount:
                raise UserError(_('You dont have enough balance.'))
            if rec.exchange_gain_loss >0:
                exc_gain = rec.exchange_gain_loss
            else:
                exc_loss = rec.exchange_gain_loss * -1
                gain_account_id = self.env['account.account'].search([('name', '=', 'Foreign Exchange Gain')], limit=1)

            if rec.from_account_id.currency_id.name == 'SSP' and rec.from_account_id.currency_id.name != 'SSP':

                move = self.env['account.move'].create({
                    'move_type': 'entry',
                    'date': rec.date,
                    'line_ids': [
                        (0, 0, {
                            'account_id': rec.from_account_id.id,
                            'currency_id': rec.from_account_id.currency_id.id,
                            'debit': 0.0,
                            'credit': rec.amount / rec.existing_exchange_rate,
                            'amount_currency': 0 - rec.amount,
                        }),
                        (0, 0, {
                            'account_id': rec.to_account_id.id,
                            'currency_id': rec.to_account_id.currency_id.id,
                            'debit': rec.expected_amount,
                            'credit': 0.0,
                        }),
                        (0, 0, {
                            'account_id': gain_account_id.id,
                            'currency_id': gain_account_id.currency_id.id,
                            'debit': exc_loss,
                            'credit': exc_gain,
                        }),
                    ],
                })
            elif rec.from_account_id.currency_id.name == 'SSP' and rec.from_account_id.currency_id.name == 'SSP':

                move = self.env['account.move'].create({
                    'move_type': 'entry',
                    'date': rec.date,
                    'line_ids': [
                        (0, 0, {
                            'account_id': rec.from_account_id.id,
                            'currency_id': rec.from_account_id.currency_id.id,
                            'debit': 0.0,
                            'credit': rec.amount / rec.existing_exchange_rate,
                            'amount_currency': 0 - rec.amount,
                        }),
                        (0, 0, {
                            'account_id': rec.to_account_id.id,
                            'currency_id': rec.to_account_id.currency_id.id,
                            'debit': rec.amount / rec.existing_exchange_rate,
                            'credit': 0.0,
                        }),
                    ],
                })
            else:

                move = self.env['account.move'].create({
                    'move_type': 'entry', 'date': rec.date, 'line_ids': [(0, 0, {
                    'account_id': rec.from_account_id.id,
                    'debit': 0.0, 'credit': rec.amount,
                     }),
                                                                         (0, 0, {'account_id': rec.to_account_id.id,
                                                                                 'amount_currency': rec.expected_amount,
                    'currency_id': rec.to_account_id.currency_id.id, 'debit': rec.amount, 'credit': 0.0, }), ], })


            move.action_post()
            rec.account_move_id = move.id
            rec.state = "validate"
    date = fields.Date("Date",default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validate', 'Validated'),
    ],default='draft', string='Status')

    @api.onchange('from_account_id')
    def from_account_changed(self):
        for rec in self:
            for group in self.env['account.move.line'].read_group(domain=[('account_id', '=', rec.from_account_id.id),('move_id.state','=','posted')],
                    fields=['account_id', 'amount_currency', 'balance'], groupby=['account_id']):
                rec.available_amount = group['amount_currency']
                rec.available_amount_usd = group['balance']
                if rec.from_account_id.currency_id.name == 'SSP':
                    if group['balance'] > 0:
                        rec.existing_exchange_rate = group['amount_currency'] / group['balance']
                    else:
                        rec.existing_exchange_rate = 1



    @api.onchange('to_account_id')
    def to_account_changed(self):
        for rec in self:
            if rec.to_account_id.currency_id.name == 'SSP':
                for group in self.env['account.move.line'].read_group(domain=[('account_id', '=', rec.to_account_id.id),('move_id.state','=','posted')], fields=['account_id', 'amount_currency','balance'],groupby=['account_id']):

                    if group['balance'] > 0:
                        rec.existing_exchange_rate = group['amount_currency'] / group['balance']
                    else:
                        rec.existing_exchange_rate = 1

    @api.onchange('amount', 'exchange_rate')
    def on_amount_change(self):
        for rec in self:
            if rec.from_account_id.currency_id.name == 'SSP':
                if rec.exchange_rate:
                    if rec.exchange_rate > 0:
                        rec.expected_amount = rec.amount / rec.exchange_rate
                        old_value = rec.amount / rec.existing_exchange_rate
                        new_value = rec.amount / rec.exchange_rate
                        change_currency = rec.existing_exchange_rate - rec.exchange_rate
                        rec.exchange_gain_loss = new_value - old_value
            else:
                if rec.exchange_rate:
                    if rec.exchange_rate > 0:
                        rec.expected_amount = rec.amount * rec.exchange_rate
                        old_value = rec.amount / rec.existing_exchange_rate
                        new_value = rec.amount / rec.exchange_rate
                        change_currency = rec.existing_exchange_rate - rec.exchange_rate
                        rec.exchange_gain_loss = 0

    from_account_id = fields.Many2one('account.account',"From",domain=[('user_type_id.name', '=', 'Bank and Cash')])
    to_account_id = fields.Many2one('account.account',"To",domain=[('user_type_id.name', '=', 'Bank and Cash')])
    account_move_id = fields.Many2one('account.move', string='Journal Entry', ondelete='restrict', copy=False,
    readonly=True)
    name = fields.Char("Ref")
    ref = fields.Char("Ref")
    available_amount = fields.Float("Amount Available")
    available_amount_usd = fields.Float("Amount amount in USD")
    existing_exchange_rate = fields.Float("Existing rate")

    amount = fields.Float("Amount to Change")
    exchange_rate = fields.Float("Exchange Rate")
    expected_amount = fields.Float("Expected Amount")
    exchange_gain_loss = fields.Float("Exchange Gain/Loss")

