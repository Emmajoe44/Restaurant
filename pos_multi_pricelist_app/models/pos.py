# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, timedelta
from functools import partial

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT


class currency(models.Model):
	_inherit = 'res.currency'

	company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
	converted_currency = fields.Float('Currency', compute="_onchange_currency")

	@api.depends('company_id')
	def _onchange_currency(self):
		res_currency = self.env['res.currency'].search([])
		company_currency = self.env.user.company_id.currency_id
		for i in self:
			if i.id == company_currency.id:
				i.converted_currency = 1
			else:
				rate = (round(i.rate,6) / company_currency.rate)
				i.converted_currency = rate


class ProductPricelist(models.Model):

	_inherit = 'product.pricelist'
	converted_currency = fields.Float('Currency',related='currency_id.converted_currency')


class PosPayment(models.Model):

	_inherit = "pos.payment"

	amount_currency = fields.Float(string="Currency Amount")
	currency = fields.Many2one("res.currency", string="Currency")

class PosPaymentMethod(models.Model):

	_inherit = "pos.payment.method"

	def _compute_currency(self):
		for pm in self:
			pm.currency_id = pm.company_id.currency_id.id
			if pm.cash_journal_id and pm.cash_journal_id.currency_id:
				pm.currency_id = pm.cash_journal_id.currency_id.id
	currency_id = fields.Many2one("res.currency", 'Currency',compute='_compute_currency')
	separate_invoice = fields.Boolean("Separate Invoice")
	stock_movement = fields.Boolean("Stock Movement",default=True)
	generate_revenue = fields.Boolean("Generate Revenue",default=True)
	journal_id = fields.Many2one('account.journal', string='Journal',
		ondelete='restrict',
		help='The payment method is of type cash. A cash statement will be automatically generated.')


class PosSessionUpdate(models.Model):
	_inherit = 'pos.session'

	@api.depends('order_ids.payment_ids.amount')
	def _compute_total_payments_amount(self):
		result = self.env['pos.payment'].read_group([('session_id', 'in', self.ids)], ['amount'], ['session_id'])
		session_amount_map = dict((data['session_id'][0], data['amount']) for data in result)
		for session in self:
			session.total_payments_amount = session_amount_map.get(session.id) or 0

	def _create_picking_at_end_of_session(self):
		self.ensure_one()
		lines_grouped_by_dest_location = {}
		picking_type = self.config_id.picking_type_id

		if not picking_type or not picking_type.default_location_dest_id:
			session_destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
		else:
			session_destination_id = picking_type.default_location_dest_id.id

		for order in self.order_ids:
			if order.company_id.anglo_saxon_accounting and order.is_invoiced:
				continue
			destination_id = order.partner_id.property_stock_customer.id or session_destination_id

			stock_movement = True
			for payment in order.payment_ids:
				if not payment.payment_method_id.stock_movement:
					stock_movement = False

			if stock_movement:
				if destination_id in lines_grouped_by_dest_location:
					lines_grouped_by_dest_location[destination_id] |= order.lines
				else:
					lines_grouped_by_dest_location[destination_id] = order.lines

		for location_dest_id, lines in lines_grouped_by_dest_location.items():
			pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(location_dest_id, lines,
				picking_type)
			pickings.write({'pos_session_id': self.id, 'origin': self.name})

	def _accumulate_amounts(self, data):
		# Accumulate the amounts for each accounting lines group
		# Each dict maps `key` -> `amounts`, where `key` is the group key.
		# E.g. `combine_receivables` is derived from pos.payment records
		# in the self.order_ids with group key of the `payment_method_id`
		# field of the pos.payment record.
		amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
		tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
		split_receivables = defaultdict(amounts)
		split_receivables_cash = defaultdict(amounts)
		combine_receivables = defaultdict(amounts)
		combine_receivables_cash = defaultdict(amounts)
		invoice_receivables = defaultdict(amounts)
		sales = defaultdict(amounts)
		taxes = defaultdict(tax_amounts)
		stock_expense = defaultdict(amounts)
		stock_return = defaultdict(amounts)
		stock_output = defaultdict(amounts)
		rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
		# Track the receivable lines of the invoiced orders' account moves for reconciliation
		# These receivable lines are reconciled to the corresponding invoice receivable lines
		# of this session's move_id.
		order_account_move_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
		rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally'
		for order in self.order_ids:
			# Combine pos receivable lines
			# Separate cash payments for cash reconciliation later.

			for payment in order.payment_ids:
				amount, date = payment.amount, payment.payment_date
				if payment.payment_method_id.is_cash_count:
					journal_currency = (
						payment.payment_method_id.cash_journal_id.currency_id
						or order.pricelist_id.currency_id
						or self.company_id.currency_id
					)
					company_currency = self.company_id.currency_id
					if journal_currency == company_currency:
						amount_converted = amount
					else:
						amount_converted = journal_currency._convert(
							amount, company_currency, self.company_id, date)
					if payment.payment_method_id.split_transactions:
						prev = split_receivables_cash[payment]
						split_receivables_cash[payment] = {
							'amount': prev['amount'] + amount,
							'amount_converted': prev['amount_converted'] + amount_converted,
						}
					else:
						key = payment.payment_method_id
						prev = combine_receivables_cash[key]
						combine_receivables_cash[key] = {
							'amount': prev['amount'] + amount,
							'amount_converted': prev['amount_converted'] + amount_converted,
						}
					continue
				if payment.payment_method_id.split_transactions:
					if payment.payment_method_id.separate_invoice and payment.payment_method_id.generate_revenue and not order.is_invoiced:
							product = self.env['product.product'].search([('name', '=', 'Credit Sales')], limit=1)
							installment_label = "Order " + order.name + " Credit Sales."
							move_line_temp = {'name': installment_label, 'price_unit': amount, 'quantity': 1.0,
											  'discount': 0.0, 'product_uom_id': product.uom_id.id,
											  'product_id': product.id, }
							invoice_type = 'out_invoice'
							journ_id = payment.payment_method_id.journal_id.id
							invoice = self.env['account.move'].create(
								{'journal_id': journ_id, 'move_type': invoice_type, 'partner_id': order.partner_id.id,
								 'invoice_date': datetime.today().date(), 'invoice_date_due': datetime.today().date(),
								 'invoice_line_ids': [(0, 0, move_line_temp)]

								 })
							invoice.action_post()
						#else:
						#	split_receivables[payment] = self._update_amounts(split_receivables[payment],{'amount': amount}, date)

				else:
					key = payment.payment_method_id
					combine_receivables[key] = self._update_amounts(
						combine_receivables[key], {'amount': amount}, date)

			if order.is_invoiced:
				# Combine invoice receivable lines
				key = order.partner_id

			else:
				order_taxes = defaultdict(tax_amounts)
				for order_line in order.lines:
					line = self._prepare_line(order_line)
					# Combine sales/refund lines
					sale_key = (# account
						line['income_account_id'], # sign
						-1 if line['amount'] < 0 else 1, # for taxes
						tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in line['taxes']),
						line['base_tags'],)
					register_sales = True
					for payment in order.payment_ids:
						if payment.payment_method_id.separate_invoice or not payment.payment_method_id.generate_revenue:
							register_sales = False
					if register_sales: 
						sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']}, line['date_order'])

						for tax in line['taxes']:
							tax_key = (tax['account_id'] or line['income_account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
							order_taxes[tax_key] = self._update_amounts(order_taxes[tax_key],{'amount': tax['amount'], 'base_amount': tax['base']},tax['date_order'],round=not rounded_globally)                    
				for tax_key, amounts in order_taxes.items():
					if rounded_globally:
						amounts = self._round_amounts(amounts)
					for amount_key, amount in amounts.items():
						taxes[tax_key][amount_key] += amount

				if self.company_id.anglo_saxon_accounting and order.picking_ids.ids:
					# Combine stock lines
					stock_moves = self.env['stock.move'].sudo().search(
						[('picking_id', 'in', order.picking_ids.ids), ('company_id.anglo_saxon_accounting', '=', True),
							('product_id.categ_id.property_valuation', '=', 'real_time')])
					for move in stock_moves:
						exp_key = move.product_id._get_product_accounts()['expense']
						out_key = move.product_id.categ_id.property_stock_account_output_categ_id
						amount = -sum(move.sudo().stock_valuation_layer_ids.mapped('value'))
						stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount},
							move.picking_id.date, force_company_currency=True)
						if move.location_id.usage == 'customer':
							stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount},
								move.picking_id.date, force_company_currency=True)
						else:
							stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount},
								move.picking_id.date, force_company_currency=True)

				if self.config_id.cash_rounding:
					diff = order.amount_paid - order.amount_total
					rounding_difference = self._update_amounts(rounding_difference, {'amount': diff}, order.date_order)

				# Increasing current partner's customer_rank
				partners = (order.partner_id | order.partner_id.commercial_partner_id)
				partners._increase_rank('customer_rank')

		if self.company_id.anglo_saxon_accounting:
			global_session_pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
			if global_session_pickings:
				stock_moves = self.env['stock.move'].sudo().search([('picking_id', 'in', global_session_pickings.ids),
					('company_id.anglo_saxon_accounting', '=', True),
					('product_id.categ_id.property_valuation', '=', 'real_time'), ])
				for move in stock_moves:
					exp_key = move.product_id._get_product_accounts()['expense']
					out_key = move.product_id.categ_id.property_stock_account_output_categ_id
					amount = -sum(move.stock_valuation_layer_ids.mapped('value'))
					stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount},
						move.picking_id.date, force_company_currency=True)
					if move.location_id.usage == 'customer':
						stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount},
							move.picking_id.date, force_company_currency=True)
					else:
						stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount},
							move.picking_id.date, force_company_currency=True)
		MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

		data.update(
			{'taxes': taxes, 'sales': sales, 'stock_expense': stock_expense, 'split_receivables': split_receivables,
				'combine_receivables': combine_receivables, 'split_receivables_cash': split_receivables_cash,
				'combine_receivables_cash': combine_receivables_cash, 'invoice_receivables': invoice_receivables,
				'stock_return': stock_return, 'stock_output': stock_output,
				'order_account_move_receivable_lines': order_account_move_receivable_lines,
				'rounding_difference': rounding_difference, 'MoveLine': MoveLine})
		return data


class POSOrder(models.Model):
	_inherit = "pos.order"

	amount_total = fields.Float(string='Total', digits=0, required=True)
	amount_paid = fields.Float(string='Paid', digits=0, required=True)

	def _is_pos_order_paid(self):
		if (abs(self.amount_total - self.amount_paid) < 0.02):
			self.write({'amount_total': self.amount_paid})
			return True
		else:
			return False

	@api.model
	def _payment_fields(self, order, ui_paymentline):
		payment_date = ui_paymentline['name']
		payment_date = fields.Date.context_today(self, fields.Datetime.from_string(payment_date))
		pl_currency = order.pricelist_id.currency_id
		company_currency = order.company_id.currency_id
		amount = ui_paymentline['amount'] or 0.0
		price_unit_foreign_curr = 0.0
		currency_id = False

		if pl_currency and company_currency and pl_currency != company_currency:
			price_unit_foreign_curr = amount
			currency_id = pl_currency.id

		return {'amount_currency': price_unit_foreign_curr, 'currency': currency_id,
			'amount': amount, 'payment_date': ui_paymentline['name'],
			'payment_method_id': ui_paymentline['payment_method_id'], 'card_type': ui_paymentline.get('card_type'),
			'cardholder_name': ui_paymentline.get('cardholder_name'),
			'transaction_id': ui_paymentline.get('transaction_id'),
			'payment_status': ui_paymentline.get('payment_status'), 'pos_order_id': order.id, }

	@api.model
	def _order_fields(self, ui_order):
		# Keep amounts in the order pricelist currency (SSP or USD). Do not convert to
		# session currency so mixed SSP/USD orders in one session stay correct.
		process_line = partial(self.env['pos.order.line']._order_line_fields, session_id=ui_order['pos_session_id'])
		return {'user_id': ui_order['user_id'] or False, 'session_id': ui_order['pos_session_id'],
			'lines': [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False,
			'pos_reference': ui_order['name'], 'sequence_number': ui_order['sequence_number'],
			'partner_id': ui_order['partner_id'] or False,
			'date_order': ui_order['creation_date'].replace('T', ' ')[:19],
			'fiscal_position_id': ui_order['fiscal_position_id'], 'pricelist_id': ui_order['pricelist_id'],
			'amount_paid': ui_order['amount_paid'], 'amount_total': ui_order['amount_total'],
			'amount_tax': ui_order['amount_tax'],
			'amount_return': ui_order['amount_return'],
			'company_id': self.env['pos.session'].browse(ui_order['pos_session_id']).company_id.id,
			'to_invoice': ui_order['to_invoice'] if "to_invoice" in ui_order else False,
			'is_tipped': ui_order.get('is_tipped', False), 'tip_amount': ui_order.get('tip_amount', 0), }

	def _process_payment_lines(self, pos_order, order, pos_session, draft):
		"""Create account.bank.statement.lines from the dictionary given to the parent function.

		If the payment_line is an updated version of an existing one, the existing payment_line will first be
		removed before making a new one.
		:param pos_order: dictionary representing the order.
		:type pos_order: dict.
		:param order: Order object the payment lines should belong to.
		:type order: pos.order
		:param pos_session: PoS session the order was created in.
		:type pos_session: pos.session
		:param draft: Indicate that the pos_order is not validated yet.
		:type draft: bool.
		"""
		prec_acc = order.pricelist_id.currency_id.decimal_places
		pricelist_id = self.env['product.pricelist'].browse(pos_order.get('pricelist_id'))
		order_bank_statement_lines = self.env['pos.payment'].search([('pos_order_id', '=', order.id)])
		order_bank_statement_lines.unlink()
		payment_date = fields.Date.today()
		for payments in pos_order['statement_ids']:
			if not float_is_zero(payments[2]['amount'], precision_digits=prec_acc):
				order.add_payment(self._payment_fields(order, payments[2]))

		order.amount_paid = sum(order.payment_ids.mapped('amount'))

		currency_id = False
		amt_currncy = 0.0
		price_subtotal_comp_curr = pos_order['amount_return']
		pl_currency = pricelist_id.currency_id
		company_currency = pos_session.company_id.currency_id
		if pl_currency and company_currency and pl_currency != company_currency:
			price_subtotal_comp_curr = pl_currency._convert(
				pos_order['amount_return'], company_currency, pos_session.company_id, payment_date)
			currency_id = pl_currency.id
			amt_currncy = -pos_order['amount_return']
		elif pl_currency:
			currency_id = pl_currency.id
			amt_currncy = -pos_order['amount_return']
		if not draft and not float_is_zero(pos_order['amount_return'], prec_acc):
			pl_currency = order.pricelist_id.currency_id
			cash_payment_method = pos_session.payment_method_ids.filtered(
				lambda pm: pm.is_cash_count and pm.cash_journal_id.currency_id == pl_currency
			)[:1]
			if not cash_payment_method:
				cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
			if not cash_payment_method:
				raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
			return_payment_vals = {'name': _('return'), 'pos_order_id': order.id, 'amount_currency': amt_currncy,
				'currency': currency_id, 'amount': -price_subtotal_comp_curr, 'payment_date': fields.Datetime.now(),
				'payment_method_id': cash_payment_method.id, 'is_change': True, }
			order.add_payment(return_payment_vals)


class POSConfig(models.Model):
	_inherit = 'pos.config'

	@api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id',
		'payment_method_ids')
	def _check_currencies(self):
		for config in self:
			if config.use_pricelist and config.pricelist_id not in config.available_pricelist_ids:
				raise ValidationError(_("The default pricelist must be included in the available pricelists."))

			# Dual cash (SSP + USD): company + POS/pricelist currency, plus each cash
			# drawer journal (e.g. Cash SSP + Cash USD on one POS during chart install).
			cash_pms = config.payment_method_ids.filtered(
				lambda pm: pm.is_cash_count and pm.cash_journal_id
			)
			allowed_currencies = (
				config.company_id.currency_id
				| config.currency_id
				| cash_pms.mapped('cash_journal_id.currency_id')
			)
			# Standard dual-currency cash setup (SSP + USD)
			for code in ('SSP', 'USD'):
				cur = self.env['res.currency'].search([('name', '=', code)], limit=1)
				if cur:
					allowed_currencies |= cur
			allowed_names = ', '.join(allowed_currencies.mapped('name'))

			if any(config.available_pricelist_ids.mapped(
				lambda pl: pl.currency_id not in allowed_currencies
			)):
				raise ValidationError(_(
					"Available pricelists must use one of: %s."
				) % allowed_names)

			if config.invoice_journal_id.currency_id and config.invoice_journal_id.currency_id not in allowed_currencies:
				raise ValidationError(_(
					"The invoice journal currency must be one of: %s."
				) % allowed_names)

			invalid_cash = cash_pms.filtered(
				lambda pm: pm.cash_journal_id.currency_id not in allowed_currencies
			)
			if invalid_cash:
				raise ValidationError(_(
					"Cash payment method \"%s\" uses %s; allowed currencies are: %s."
				) % (
					invalid_cash[0].name,
					invalid_cash[0].cash_journal_id.currency_id.name,
					allowed_names,
				))
