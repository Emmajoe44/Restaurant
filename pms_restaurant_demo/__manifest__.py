# -*- coding: utf-8 -*-
{
    'name': 'PMS Restaurant Demo Data',
    'version': '14.0.1.0.2',
    'category': 'Point of Sale',
    'summary': 'Reset accounting and load restaurant demo products',
    'description': """
        Provides demo restaurant products (USD + SSP prices) and a tool to
        clear POS/accounting transactions for a fresh start.
    """,
    'author': 'PMS',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'point_of_sale',
        'stock',
        'pms_dual_cash',
        'pos_multi_pricelist_app',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/demo_categories.xml',
        'data/demo_products.xml',
        'views/demo_setup_views.xml',
    ],
    'installable': True,
}
