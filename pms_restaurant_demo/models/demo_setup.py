# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# USD list price; SSP = USD * 6500 (demo rate)
RESTAURANT_DEMO_PRODUCTS = [
  {'name': 'Margherita Pizza', 'usd': 8.0, 'pos_categ': 'Food', 'barcode': 'DEMO-PIZZA-01'},
  {'name': 'Beef Burger', 'usd': 6.0, 'pos_categ': 'Food', 'barcode': 'DEMO-BURGER-01'},
  {'name': 'Chicken Wings', 'usd': 7.0, 'pos_categ': 'Food', 'barcode': 'DEMO-WINGS-01'},
  {'name': 'French Fries', 'usd': 3.0, 'pos_categ': 'Food', 'barcode': 'DEMO-FRIES-01'},
  {'name': 'Garden Salad', 'usd': 4.5, 'pos_categ': 'Food', 'barcode': 'DEMO-SALAD-01'},
  {'name': 'Tea', 'usd': 1.0, 'pos_categ': 'Drinks', 'barcode': 'DEMO-TEA-01'},
  {'name': 'Coffee', 'usd': 2.0, 'pos_categ': 'Drinks', 'barcode': 'DEMO-COFFEE-01'},
  {'name': 'Water (Small)', 'usd': 1.0, 'pos_categ': 'Drinks', 'barcode': 'DEMO-WATER-S'},
  {'name': 'Water (Large)', 'usd': 1.5, 'pos_categ': 'Drinks', 'barcode': 'DEMO-WATER-L'},
  {'name': 'Fresh Juice', 'usd': 2.5, 'pos_categ': 'Drinks', 'barcode': 'DEMO-JUICE-01'},
  {'name': 'Ice Cream', 'usd': 4.0, 'pos_categ': 'Desserts', 'barcode': 'DEMO-ICE-01'},
  {'name': 'Chocolate Cake', 'usd': 5.0, 'pos_categ': 'Desserts', 'barcode': 'DEMO-CAKE-01'},
]

SSP_RATE = 6500.0


class PmsRestaurantDemoSetup(models.TransientModel):
    _name = 'pms.restaurant.demo.setup'
    _description = 'Reset accounting and load restaurant demo data'

    confirm = fields.Boolean(
        string='I understand this deletes POS and accounting entries',
        default=False,
    )
    can_reset_accounting = fields.Boolean(compute='_compute_access_flags')
    is_cashier_only = fields.Boolean(compute='_compute_access_flags')

    @api.depends()
    def _compute_access_flags(self):
        for rec in self:
            user = rec.env.user
            can_reset = (
                user.has_group('pms_dual_cash.group_pms_accountant')
                or user.has_group('pms_dual_cash.group_pms_admin')
            )
            rec.can_reset_accounting = can_reset
            rec.is_cashier_only = (
                user.has_group('pms_dual_cash.group_pms_cashier') and not can_reset
            )

    def _notify_demo_ready(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Restaurant demo ready'),
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_load_demo_only(self):
        """Cashiers and POS staff: refresh demo products without touching accounting."""
        self.ensure_one()
        self.env['pms.restaurant.demo.service'].load_restaurant_demo_products()
        return self._notify_demo_ready(
            _('Demo restaurant products were loaded or updated (accounting was not changed).'),
        )

    def action_reset_and_load_demo(self):
        """Accountants and administrators: clear books and load demo data."""
        self.ensure_one()
        user = self.env.user
        if not (
            user.has_group('pms_dual_cash.group_pms_accountant')
            or user.has_group('pms_dual_cash.group_pms_admin')
        ):
            raise UserError(_(
                'Only users with the Restaurant Accountant or Administrator role '
                'can reset accounting. Cashiers can use "Load demo products only".',
            ))
        if not self.confirm:
            raise UserError(_('Please confirm that you want to reset accounting and load demo data.'))
        self.env['pms.restaurant.demo.service'].reset_accounting()
        self.env['pms.restaurant.demo.service'].load_restaurant_demo_products()
        return self._notify_demo_ready(
            _('Accounting was cleared and demo restaurant products were loaded.'),
        )


class PmsRestaurantDemoService(models.AbstractModel):
    _name = 'pms.restaurant.demo.service'
    _description = 'Restaurant demo data and accounting reset'

    @api.model
    def reset_accounting(self):
        """Remove POS orders/sessions and all journal entries (fresh books)."""
        company = self.env.company

        # POS orders (cancel paid orders before unlink)
        orders = self.env['pos.order'].with_context(active_test=False).search([
            ('company_id', '=', company.id),
        ])
        if orders:
            orders.filtered(lambda o: o.state not in ('cancel', 'draft')).action_pos_order_cancel()
            self.env['pos.payment'].search([('pos_order_id', 'in', orders.ids)]).unlink()
            orders.mapped('lines').unlink()
            orders.unlink()

        sessions = self.env['pos.session'].search([('company_id', '=', company.id)])

        # Custom cash payments (mop_ss)
        if 'compound.payment' in self.env:
            cp = self.env['compound.payment'].search([])
            for rec in cp:
                try:
                    if hasattr(rec, 'action_cancel'):
                        rec.action_cancel()
                except Exception:
                    pass
            cp.unlink()

        # Standard payments
        payments = self.env['account.payment'].search([('company_id', '=', company.id)])
        for pay in payments:
            try:
                if pay.state == 'posted':
                    pay.action_draft()
                pay.action_cancel()
            except Exception:
                pass
        payments.unlink()

        # Unreconcile all entries for this company
        reconciled_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('account_id.reconcile', '=', True),
            '|', ('matched_debit_ids', '!=', False), ('matched_credit_ids', '!=', False),
        ])
        if reconciled_lines:
            reconciled_lines.remove_move_reconcile()
        self.env['account.partial.reconcile'].search([]).unlink()

        # Bank statements and their journal entries
        statements = self.env['account.bank.statement'].search([
            ('company_id', '=', company.id),
        ])
        statements.write({'pos_session_id': False})
        for statement in statements:
            for line in list(statement.line_ids):
                line.unlink()
            try:
                if statement.state != 'open':
                    statement.button_reopen()
            except Exception:
                pass
        try:
            statements.unlink()
        except Exception as exc:
            _logger.warning('Could not delete bank statements: %s', exc)

        # Remaining journal entries
        moves = self.env['account.move'].search([('company_id', '=', company.id)])
        for move in moves:
            if move.state == 'posted':
                move.button_draft()
            elif move.state == 'cancel':
                move.button_draft()
        moves.with_context(force_delete=True).unlink()

        # Currency exchange records if installed
        if 'currency.exchange' in self.env:
            self.env['currency.exchange'].search([]).unlink()

        for session in sessions:
            try:
                if session.state != 'closed':
                    session.action_pos_session_closing_control()
            except Exception as exc:
                _logger.warning('Could not close session %s: %s', session.name, exc)
        try:
            sessions.unlink()
        except Exception as exc:
            _logger.warning('Some POS sessions could not be deleted: %s', exc)

        self.env.cr.commit()
        _logger.info('Accounting reset completed for company %s', company.name)
        return True

    @api.model
    def _get_or_create_pos_category(self, name):
        PosCategory = self.env['pos.category']
        cat = PosCategory.search([('name', '=', name)], limit=1)
        if not cat:
            cat = PosCategory.create({'name': name})
        return cat

    @api.model
    def _get_pricelists(self):
        usd = self.env['product.pricelist'].search([
            ('currency_id.name', '=', 'USD'),
            '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id),
        ], limit=1)
        ssp = self.env['product.pricelist'].search([
            ('currency_id.name', '=', 'SSP'),
            '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id),
        ], limit=1)
        return usd, ssp

    @api.model
    def _set_pricelist_item(self, pricelist, product, price):
        if not pricelist:
            return
        Item = self.env['product.pricelist.item']
        item = Item.search([
            ('pricelist_id', '=', pricelist.id),
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
        ], limit=1)
        vals = {
            'pricelist_id': pricelist.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'applied_on': '1_product',
            'compute_price': 'fixed',
            'fixed_price': price,
        }
        if item:
            item.write(vals)
        else:
            Item.create(vals)

    @api.model
    def load_restaurant_demo_products(self):
        """Archive old POS products and create demo menu with USD/SSP prices."""
        Product = self.env['product.product']
        company = self.env.company

        # Archive previous sale products (keep stock items)
        old_products = Product.search([
            ('sale_ok', '=', True),
            ('default_code', 'not like', 'DEMO-%'),
        ])
        if old_products:
            old_products.write({'active': False, 'available_in_pos': False})

        product_categ = self.env.ref(
            'pms_restaurant_demo.product_categ_restaurant',
            raise_if_not_found=False,
        )
        if not product_categ:
            product_categ = self.env['product.category'].search([
                ('name', '=', 'Restaurant'),
            ], limit=1)

        usd_pl, ssp_pl = self._get_pricelists()
        pos_categ_map = {}

        for row in RESTAURANT_DEMO_PRODUCTS:
            pos_categ_name = row['pos_categ']
            if pos_categ_name not in pos_categ_map:
                pos_categ_map[pos_categ_name] = self._get_or_create_pos_category(pos_categ_name)

            product = Product.search([('default_code', '=', row['barcode'])], limit=1)
            vals = {
                'name': row['name'],
                'default_code': row['barcode'],
                'barcode': row['barcode'],
                'list_price': row['usd'],
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': False,
                'available_in_pos': True,
                'categ_id': product_categ.id if product_categ else False,
                'pos_categ_id': pos_categ_map[pos_categ_name].id,
                'active': True,
            }
            if product:
                product.write(vals)
            else:
                product = Product.create(vals)

            ssp_price = row['usd'] * SSP_RATE
            self._set_pricelist_item(usd_pl, product, row['usd'])
            self._set_pricelist_item(ssp_pl, product, ssp_price)

        # POS config: dual cash + both pricelists
        if 'dual.cash.setup' in self.env:
            self.env['dual.cash.setup'].setup_dual_cash(configure_pos=True)

        for config in self.env['pos.config'].search([('company_id', '=', company.id)]):
            if usd_pl and ssp_pl and config.use_pricelist:
                config.write({
                    'available_pricelist_ids': [(6, 0, [usd_pl.id, ssp_pl.id])],
                    'pricelist_id': ssp_pl.id,
                })
                if hasattr(config, '_compute_currency'):
                    config._compute_currency()

        self.env.cr.commit()
        _logger.info('Loaded %s restaurant demo products', len(RESTAURANT_DEMO_PRODUCTS))
        return True

    @api.model
    def reset_and_load_all(self):
        self.reset_accounting()
        self.load_restaurant_demo_products()
        return True
