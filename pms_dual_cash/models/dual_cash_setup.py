# -*- coding: utf-8 -*-
from odoo import api, models


class DualCashSetup(models.AbstractModel):
    _name = 'dual.cash.setup'
    _description = 'Provision SSP and USD cash journals for Accounting and POS'

    @api.model
    def setup_all_companies(self):
        for company in self.env['res.company'].search([]):
            self.with_company(company).setup_dual_cash()

    @api.model
    def setup_dual_cash(self, configure_pos=True):
        """Idempotent dual-currency cash setup for the current company.

        :param configure_pos: link POS payment methods (skip during chart of accounts load).
        """
        company = self.env.company
        Currency = self.env['res.currency']
        ssp = Currency.search([('name', '=', 'SSP')], limit=1)
        usd = Currency.search([('name', '=', 'USD')], limit=1)
        if not ssp or not usd:
            return False

        ssp.active = True
        usd.active = True

        multi_currency_group = self.env.ref('base.group_multi_currency', raise_if_not_found=False)
        internal_user = self.env.ref('base.group_user', raise_if_not_found=False)
        if multi_currency_group and internal_user and multi_currency_group not in internal_user.implied_ids:
            internal_user.write({'implied_ids': [(4, multi_currency_group.id)]})

        cash_ssp_journal = self.env['account.journal'].search([
            ('type', '=', 'cash'),
            ('code', '=', 'CSH1'),
            ('company_id', '=', company.id),
        ], limit=1)
        if not cash_ssp_journal:
            cash_ssp_journal = self.env['account.journal'].search([
                ('type', '=', 'cash'),
                ('company_id', '=', company.id),
            ], limit=1)
        if not cash_ssp_journal:
            return False

        cash_ssp_account = cash_ssp_journal.default_account_id
        cash_ssp_journal.write({'name': 'Cash SSP', 'code': 'CSH1'})
        if cash_ssp_account:
            cash_ssp_account.write({'name': 'Cash SSP'})
            self.env.cr.execute(
                'UPDATE account_account SET currency_id = %s WHERE id = %s',
                (ssp.id, cash_ssp_account.id),
            )
        self.env.cr.execute(
            'UPDATE account_journal SET currency_id = %s WHERE id = %s',
            (ssp.id, cash_ssp_journal.id),
        )
        cash_ssp_journal.invalidate_cache()

        cash_usd_account = self.env['account.account'].search([
            ('code', '=', '101504'),
            ('company_id', '=', company.id),
        ], limit=1)
        if not cash_usd_account:
            liquidity_type = self.env.ref('account.data_account_type_liquidity')
            cash_usd_account = self.env['account.account'].create({
                'code': '101504',
                'name': 'Cash USD',
                'user_type_id': liquidity_type.id,
                'currency_id': usd.id,
                'company_id': company.id,
                'reconcile': False,
            })
        else:
            cash_usd_account.write({'name': 'Cash USD', 'currency_id': usd.id})

        journal_vals = {
            'name': 'Cash USD',
            'type': 'cash',
            'code': 'CSH2',
            'currency_id': usd.id,
            'default_account_id': cash_usd_account.id,
            'company_id': company.id,
            'profit_account_id': cash_ssp_journal.profit_account_id.id,
            'loss_account_id': cash_ssp_journal.loss_account_id.id,
        }
        cash_usd_journal = self.env['account.journal'].search([
            ('type', '=', 'cash'),
            ('code', '=', 'CSH2'),
            ('company_id', '=', company.id),
        ], limit=1)
        if cash_usd_journal:
            cash_usd_journal.write(journal_vals)
        else:
            cash_usd_journal = self.env['account.journal'].create(journal_vals)

        if not configure_pos or 'pos.payment.method' not in self.env:
            return True

        pos_receivable = company.account_default_pos_receivable_account_id
        if not pos_receivable:
            return True

        cash_pm = self.env['pos.payment.method'].search([
            ('name', 'in', ['Cash', 'Cash SSP']),
            ('company_id', '=', company.id),
            ('is_cash_count', '=', True),
        ], limit=1)
        if not cash_pm:
            cash_pm = self.env['pos.payment.method'].search([
                ('is_cash_count', '=', True),
                ('cash_journal_id', '=', cash_ssp_journal.id),
                ('company_id', '=', company.id),
            ], limit=1)
        if cash_pm:
            cash_pm.write({
                'name': 'Cash SSP',
                'is_cash_count': True,
                'cash_journal_id': cash_ssp_journal.id,
            })
        else:
            cash_pm = self.env['pos.payment.method'].create({
                'name': 'Cash SSP',
                'is_cash_count': True,
                'cash_journal_id': cash_ssp_journal.id,
                'receivable_account_id': pos_receivable.id,
                'company_id': company.id,
            })

        cash_usd_pm = self.env['pos.payment.method'].search([
            ('name', '=', 'Cash USD'),
            ('company_id', '=', company.id),
        ], limit=1)
        if not cash_usd_pm:
            cash_usd_pm = self.env['pos.payment.method'].create({
                'name': 'Cash USD',
                'is_cash_count': True,
                'cash_journal_id': cash_usd_journal.id,
                'receivable_account_id': pos_receivable.id,
                'company_id': company.id,
            })
        else:
            cash_usd_pm.write({
                'cash_journal_id': cash_usd_journal.id,
                'is_cash_count': True,
            })

        bank_pm = self.env['pos.payment.method'].search([
            ('name', '=', 'Bank'),
            ('company_id', '=', company.id),
        ], limit=1)
        pm_ids = [cash_pm.id, cash_usd_pm.id]
        if bank_pm:
            pm_ids.append(bank_pm.id)

        pricelists = self.env['product.pricelist'].search([
            ('currency_id', 'in', [ssp.id, usd.id]),
            '|', ('company_id', '=', company.id), ('company_id', '=', False),
        ])
        ssp_pl = pricelists.filtered(lambda pl: pl.currency_id == ssp)[:1]
        for config in self.env['pos.config'].search([('company_id', '=', company.id)]):
            if config.has_active_session:
                continue
            vals = {
                'payment_method_ids': [(6, 0, pm_ids)],
                'manage_orders': True,
                'module_account': True,
            }
            if config.use_pricelist and pricelists:
                vals['available_pricelist_ids'] = [(6, 0, pricelists.ids)]
                # Default SSP pricelist so product prices and Cash SSP match local currency.
                if ssp_pl:
                    vals['pricelist_id'] = ssp_pl.id
            config.write(vals)
            if hasattr(config, '_compute_currency'):
                config._compute_currency()

        return True
