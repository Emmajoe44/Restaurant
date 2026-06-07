# -*- coding: utf-8 -*-
from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_journal_bank_account_balance(self, domain=None):
        """Show cash balance in the journal currency (e.g. SSP on Cash SSP)."""
        self.ensure_one()
        company_currency = self.company_id.currency_id
        journal_currency = self.currency_id
        if (
            journal_currency
            and journal_currency != company_currency
            and self.default_account_id
        ):
            base_domain = (domain or []) + [
                ('account_id', '=', self.default_account_id.id),
                ('display_type', 'not in', ('line_section', 'line_note')),
                ('parent_state', '!=', 'cancel'),
            ]
            groups = self.env['account.move.line'].read_group(
                base_domain + [('currency_id', '=', journal_currency.id)],
                ['amount_currency:sum'],
                [],
            )
            amount = 0.0
            if groups:
                amount = groups[0].get('amount_currency') or 0.0
            nb_lines = self.env['account.move.line'].search_count(base_domain)
            return float(amount), nb_lines
        return super()._get_journal_bank_account_balance(domain=domain)
