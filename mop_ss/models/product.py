# ?? 2015-2016 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api,_
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_repr
from odoo.exceptions import ValidationError
from datetime import datetime

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

            if rec.from_account_id.currency_id.name == 'SSP' and rec.to_account_id.currency_id.name != 'SSP':
                if rec.exchange_rate == 0:
                    raise UserError(_('Exchange rate should be greater than zero.'))
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
                            'amount_currency': rec.amount,
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



    # @api.onchange('to_account_id')
    # def to_account_changed(self):
    #     for rec in self:
    #         if rec.to_account_id.currency_id.name == 'SSP':
    #             for group in self.env['account.move.line'].read_group(domain=[('account_id', '=', rec.to_account_id.id),('move_id.state','=','posted')], fields=['account_id', 'amount_currency','balance'],groupby=['account_id']):
    #
    #                 if group['balance'] > 0:
    #                     rec.existing_exchange_rate = group['amount_currency'] / group['balance']
    #                 else:
    #                     rec.existing_exchange_rate = 1

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


class CompoundPayment(models.Model):
    _name = "compound.payment"


    @api.onchange("compound_payment_detail_ids")
    def line_changed(self):
        for rec in self:
            total = 0
            for line in rec.compound_payment_detail_ids:
                rec.remark = line.desc
                break
            for line in rec.compound_payment_detail_ids:
                total += line.amount
            rec.total_amount = total

    def validate_payment(self):
        for rec in self:


            lst = []
            for x in rec.compound_payment_detail_ids:
                if x.account_id.user_type_id.type in ('receivable', 'payable'):
                    if not x.partner_id:
                        raise UserError(_("For Payable and Receivable Accounts vendor/customer name is mandatory."))
            if rec.payment_method_id.currency_id.id == self.env.company.currency_id.id:
                total_cash_out = 0
                total_cash_out_curr = 0
                debited_amt = 0
                for x in rec.compound_payment_detail_ids:
                    debited_amt = round(x.amount / rec.exchange_rate, 2)
                    total_cash_out += debited_amt
                    total_cash_out_curr += x.amount
                    lst.append((0, 0, {'account_id': x.account_id.id, 'name': x.desc, 'debit': debited_amt,
                                       'amount_currency': x.amount, 'partner_id': x.partner_id.id,
                                       'currency_id': rec.payment_method_id.currency_id.id,
                                       'analytic_account_id': x.analytic_account_id.id, 'credit': 0.0, }))
                lst.append((0, 0, {'account_id': rec.payment_method_id.default_account_id.id, 'debit': 0.0,
                                   'name': rec.remark, 'amount_currency': -1 * total_cash_out_curr,
                                   'credit': total_cash_out, 'currency_id': rec.payment_method_id.currency_id.id, }))
                move = self.env['account.move'].create(
                    {'move_type': 'entry', 'ref': rec.remark, 'journal_id': rec.payment_method_id.id,
                        'currency_id': rec.payment_method_id.currency_id.id, 'date': rec.payment_date,
                        'line_ids': lst, })
                move.action_post()
                rec.account_move_id = move.id
                rec.name = move.name
                rec.state = move.state
            else:
                existing_exchange_rate = 1
                total_cash_out = 0
                for group in self.env['account.move.line'].read_group(
                        domain=[('account_id', '=', rec.payment_method_id.default_account_id.id),
                                ('move_id.state', '=', 'posted')], fields=['account_id', 'amount_currency', 'balance'],
                        groupby=['account_id']):

                    if group['balance'] > 0:
                        existing_exchange_rate = group['amount_currency'] / group['balance']
                    else:
                        raise UserError(_("You don't have balance to pay this using this payment method."))
                    old_value = rec.total_amount / existing_exchange_rate
                    new_value = rec.total_amount / rec.exchange_rate
                    exchange_gain_loss = round((new_value - old_value), 2)

                    gain_account_id = self.env['account.account'].search([('name', '=', 'Foreign Exchange Gain')],
                        limit=1)
                    exc_gain = 0.00
                    exc_loss = 0.00
                    if exchange_gain_loss > 0:
                        exc_gain = round(exchange_gain_loss, 2)
                    else:
                        exc_loss = round((exchange_gain_loss * -1), 2)
                    debited = 0.00
                    credited = 0.00
                    for x in rec.compound_payment_detail_ids:
                        total_cash_out += round(x.amount, 2)
                        debited += round((x.amount / rec.exchange_rate), 2)
                        lst.append((0, 0, {'account_id': x.account_id.id, 'name': x.desc,
                                           'debit': round((x.amount / rec.exchange_rate), 2),
                                           'amount_currency': x.amount, 'partner_id': x.partner_id.id,
                                           'currency_id': rec.payment_method_id.currency_id.id,
                                           'analytic_account_id': x.analytic_account_id.id, 'credit': 0.0, }))
                    debited += exc_loss
                    credited = round(((total_cash_out / existing_exchange_rate) + exc_gain), 2)
                    lst.append((0, 0, {'account_id': rec.payment_method_id.default_account_id.id, 'debit': 0.0,
                                       'name': rec.remark, 'amount_currency': -1 * total_cash_out,
                                       'credit': round((total_cash_out / existing_exchange_rate), 2),
                                       'currency_id': rec.payment_method_id.currency_id.id, }))
                    lst.append((0, 0, {'account_id': gain_account_id.id, 'currency_id': gain_account_id.currency_id.id,
                        'debit': exc_loss, 'credit': exc_gain, }))
                    if debited - credited >= 0.01:
                        lst.append((0, 0,
                                    {'account_id': gain_account_id.id, 'currency_id': gain_account_id.currency_id.id,
                                     'debit': 0, 'credit': debited - credited, }))
                    elif credited - debited >= 0.01:
                        lst.append((0, 0,
                                    {'account_id': gain_account_id.id, 'currency_id': gain_account_id.currency_id.id,
                                     'debit': credited - debited, 'credit': 0, }))

                move = self.env['account.move'].create(
                    {'move_type': 'entry', 'ref': rec.remark, 'journal_id': rec.payment_method_id.id,
                        'currency_id': rec.payment_method_id.currency_id.id, 'date': rec.payment_date,
                        'line_ids': lst, })
                move.action_post()
                rec.account_move_id = move.id
                rec.name = move.name
                rec.state = move.state

    @api.onchange("payment_method_id")
    def payment_method_changed(self):
        for rec in self:
            if rec.payment_method_id.currency_id.id == self.env.company.currency_id.id:
                rec.exchange_rate = 1
            else:
                rst = self.env['res.currency.rate'].search([('name', '<=', rec.payment_date)], order='name DESC')
                rec.exchange_rate = rec.payment_method_id.currency_id.rate
                for r in rst:
                    rec.exchange_rate = r.rate
                    break

    def _compute_state(self):
        for r in self:
            if r.account_move_id:
                r.state = r.account_move_id.state
            else:
                r.state = 'draft'

    name = fields.Char("Ref")
    source_pv = fields.Char("PV")
    account_move_id = fields.Many2one("account.move")
    payment_date = fields.Date("Payment Date")
    remark = fields.Char("Memo", required=True)
    exchange_rate = fields.Integer("Exchange Rate", required=True)
    state = fields.Selection(selection=[('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled'), ],
        string='Status', compute="_compute_state", required=True, tracking=True, default='draft')
    payment_type = fields.Selection(selection=[('Payment', 'Payment'), ('Receipt', 'Receipt'), ], string='Payment Type',
        default='Payment')
    total_amount = fields.Float("Total Amount")
    payment_method_id = fields.Many2one('account.journal', domain="[('type', 'in', ['cash', 'bank'])]",
        string='Payment Method', required=True)
    compound_payment_detail_ids = fields.One2many("compound.payment.detail", "compound_payment_id")


class CompoundPaymentDetail(models.Model):
    _name = "compound.payment.detail"

    @api.onchange('partner_id', 'account_id')
    def partner_changed(self):
        for rec in self:

            if rec.partner_id:

                if rec.desc == "":
                    rec.desc = rec.partner_id.name
                if rec.partner_id.property_account_payable_id:
                    rec.account_id = rec.partner_id.property_account_payable_id.id

            if rec.account_id and rec.partner_id:
                domain = [('account_id', '=', rec.account_id.id), ('partner_id', '=', rec.partner_id.id),
                          ('move_id.state', '=', 'posted')]
                revenues = self.env['account.move.line'].read_group(domain, ['account_id', 'currency_id', 'balance', ],
                    ['account_id', 'currency_id'], offset=0, limit=None, orderby=False, lazy=False)
                for rev in revenues:
                    rec.balance = rev['balance']

    compound_payment_id = fields.Many2one("compound.payment")
    product_id = fields.Many2one("product.product", "Service")
    partner_id = fields.Many2one("res.partner", "Vendor")
    desc = fields.Char("Description")
    account_id = fields.Many2one("account.account", "Account")
    amount = fields.Float("Amount")
    balance = fields.Float("Balance")
    company_amount = fields.Float("Company Amount")
    analytic_account_id = fields.Many2one("account.analytic.account")

class RequestDirectorate(models.Model):
    _name = "request.directorate"

    name = fields.Char("Directorate")
class PaymentRequest(models.Model):
    _name = "payment.request"


    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        vals["name"] = (
            self.env["ir.sequence"].next_by_code("payment.request") or "New"
        )
        return super(PaymentRequest, self).create(vals)

    def validate_payment(self):
        lst = []
        for rec in self:

            if rec.payment_method_id.currency_id.id == self.env.company.currency_id.id:
                lst.append((0, 0, {'account_id': rec.payment_method_id.default_account_id.id, 'debit': 0.0,
                                   'name': rec.remark, 'amount_currency': -1 * rec.paid_amount,
                                   'credit': rec.paid_amount, 'currency_id': rec.payment_method_id.currency_id.id, }))
                lst.append((0, 0, {'account_id':rec.expense_account_id.id, 'name': rec.remark, 'debit': rec.paid_amount,
                                   'amount_currency': rec.paid_amount,
                                   'currency_id': rec.payment_method_id.currency_id.id,
                                   'credit': 0.0, }))
                move = self.env['account.move'].create(
                    {'move_type': 'entry', 'ref': rec.remark, 'journal_id': rec.payment_method_id.id,
                        'currency_id': rec.payment_method_id.currency_id.id, 'date': rec.payment_date,
                        'line_ids': lst, })
                move.action_post()
                rec.account_move_id = move.id
            else:
                existing_exchange_rate = 1
                available_amount = 0
                available_in_usd = 0
                rtt = self.env['account.move.line'].read_group(
                    domain=[('account_id', '=', rec.payment_method_id.default_account_id.id),
                            ('move_id.state', '=', 'posted')],
                    fields=['account_id', 'debit', 'credit', 'amount_currency'],
                    groupby=[ 'account_id'])
                for r in rtt:
                    available_amount = r['amount_currency']
                    available_in_usd = r['debit'] - r['credit']
                    if available_in_usd > 0:
                        existing_exchange_rate = available_amount / available_in_usd
                lst.append((0, 0, {'account_id': rec.payment_method_id.default_account_id.id, 'debit': 0.0,
                                   'name': rec.remark, 'amount_currency': -1 * rec.paid_amount,
                                   'credit': rec.paid_amount/existing_exchange_rate, 'currency_id': rec.payment_method_id.currency_id.id, }))
                lst.append((0, 0, {'account_id':rec.expense_account_id.id, 'name': rec.remark, 'debit': rec.paid_amount/existing_exchange_rate,
                                   'amount_currency': rec.paid_amount,
                                   'currency_id': rec.payment_method_id.currency_id.id,
                                   'credit': 0.0, }))
                move = self.env['account.move'].create(
                    {'move_type': 'entry', 'ref': rec.remark, 'journal_id': rec.payment_method_id.id,
                        'currency_id': rec.payment_method_id.currency_id.id, 'date': rec.payment_date,
                        'line_ids': lst, })
                move.action_post()
                rec.account_move_id = move.id
            return self.write({"state": "paid", "registered_by": self.env.uid})

    def request_approval(self):

        return self.write({"state": "requested","registered_by":self.env.uid})


    def approved(self):
        return self.write({"state": "approved","approved_by":self.env.uid,"payment_date":  datetime.today().date()})




    name = fields.Char("Serial No")
    request_date = fields.Date("Date", required=True)
    payment_date = fields.Date("Payment Date")
    directorate_id = fields.Many2one("request.directorate","Directorate", required=True)
    requested_by = fields.Char("Requested By", required=True)
    paid_to = fields.Char("Paid To")
    remark = fields.Char("Desc.", required=True)
    expense_account_id = fields.Many2one('account.account', "Expenditure Code", domain=[('user_type_id.name', '=', 'Expenses')])
    @api.onchange("requested_amount")
    def requested_amount_change(self):
        for rec in self:
            rec.paid_amount = rec.requested_amount

    @api.onchange("payment_method_id")
    def payment_method_changed(self):
        for rec in self:
            rec.available_amount = 0
            if rec.payment_method_id:
                rst = self.env['account.move.line'].read_group(domain=[('account_id', '=', rec.payment_method_id.default_account_id.id),('move_id.state','=','posted')],
                        fields=['currency_id','account_id', 'debit', 'credit','amount_currency'], groupby=['currency_id','account_id'])
                for r in rst:
                    if r['currency_id'][0] == 2:
                        rec.available_amount = r['debit'] - r['credit']
                    else:
                        rec.available_amount = r['amount_currency']

    source_pv = fields.Char("PV")
    account_move_id = fields.Many2one("account.move")
    requested_amount = fields.Float("Amount Requested",tracking=True)
    payment_method_id = fields.Many2one('account.journal', domain="[('type', 'in', ['cash', 'bank'])]",
        string='Payment Method', required=True)
    available_amount = fields.Float("Available Amount")
    paid_amount = fields.Float("Paid Amount", tracking=True)
    exchange_rate = fields.Integer("Exchange Rate")
    state = fields.Selection(selection=[('draft', 'Draft'), ('requested', 'App. Req'), ('approved', 'Approved'),('paid', 'Paid'), ('cancel', 'Cancelled'), ],
        string='Status',required=True, tracking=True, default='draft')
    payment_type = fields.Selection(selection=[('Payment', 'Payment'), ('Receipt', 'Receipt'), ], string='Payment Type',
        default='Payment')

    registered_by = fields.Many2one("res.users","Registered By")
    approved_by = fields.Many2one("res.users","Approved By")

class PaymentReceipts(models.Model):
    _name = "payment.receipts"


    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        vals["name"] = (
            self.env["ir.sequence"].next_by_code("payment.receipts") or "New"
        )
        return super(PaymentReceipts, self).create(vals)

    def validate_payment(self):
        lst = []
        for rec in self:

            if rec.payment_method_id.currency_id.id == self.env.company.currency_id.id:
                lst.append((0, 0, {'account_id': rec.income_account_id.id, 'debit': 0.0,
                                   'name': rec.remark, 'amount_currency': -1 * rec.amount,
                                   'credit': rec.amount, 'currency_id': rec.payment_method_id.currency_id.id, }))
                lst.append((0, 0, {'account_id':rec.payment_method_id.default_account_id.id, 'name': rec.remark, 'debit': rec.amount,
                                   'amount_currency': rec.amount,
                                   'currency_id': rec.payment_method_id.currency_id.id,
                                   'credit': 0.0, }))
                move = self.env['account.move'].create(
                    {'move_type': 'entry', 'ref': rec.remark, 'journal_id': rec.payment_method_id.id,
                        'currency_id': rec.payment_method_id.currency_id.id, 'date': rec.payment_date,
                        'line_ids': lst, })
                move.action_post()
                rec.account_move_id = move.id
            else:
                lst.append((0, 0, {'account_id': rec.income_account_id.id, 'debit': 0.0,
                                   'name': rec.remark, 'amount_currency': -1 * rec.amount,
                                   'credit': rec.amount/rec.exchange_rate, 'currency_id': rec.payment_method_id.currency_id.id, }))
                lst.append((0, 0, {'account_id':rec.payment_method_id.default_account_id.id, 'name': rec.remark, 'debit': rec.amount/rec.exchange_rate,
                                   'amount_currency': rec.amount,
                                   'currency_id': rec.payment_method_id.currency_id.id,
                                   'credit': 0.0, }))
                move = self.env['account.move'].create(
                    {'move_type': 'entry', 'ref': rec.remark, 'journal_id': rec.payment_method_id.id,
                        'currency_id': rec.payment_method_id.currency_id.id, 'date': rec.payment_date,
                        'line_ids': lst, })
                move.action_post()
                rec.account_move_id = move.id
            return self.write({"state": "received"})

    def request_approval(self):

        return self.write({"state": "requested","registered_by":self.env.uid})


    def approved(self):
        return self.write({"state": "approved","approved_by":self.env.uid,"payment_date":  datetime.today().date()})




    name = fields.Char("Serial No")
    payment_date = fields.Date("Payment Date")
    remark = fields.Char("Desc.", required=True)
    income_account_id = fields.Many2one('account.account', "Received From", domain=[('user_type_id.name', '=', 'Income')])
    account_move_id = fields.Many2one("account.move")
    amount = fields.Float("Amount",tracking=True)
    payment_method_id = fields.Many2one('account.journal', domain="[('type', 'in', ['cash', 'bank'])]",
        string='Deposited To', required=True)
    available_amount = fields.Float("Current Balance")
    exchange_rate = fields.Integer("Exchange Rate")
    state = fields.Selection(selection=[('draft', 'Draft'),('received', 'Received'), ('cancel', 'Cancelled'), ],
        string='Status',required=True, tracking=True, default='draft')

    received_by = fields.Many2one("res.users","Received By")
    approved_by = fields.Many2one("res.users","Approved By")

    @api.onchange("payment_method_id")
    def payment_method_changed(self):
        for rec in self:
            rec.available_amount = 0
            if rec.payment_method_id:
                rst = self.env['account.move.line'].read_group(domain=[('account_id', '=', rec.payment_method_id.default_account_id.id),('move_id.state','=','posted')],
                        fields=['currency_id','account_id', 'debit', 'credit','amount_currency'], groupby=['currency_id','account_id'])
                for r in rst:
                    if r['currency_id'][0] == 2:
                        rec.available_amount = r['debit'] - r['credit']
                    else:
                        rec.available_amount = r['amount_currency']



