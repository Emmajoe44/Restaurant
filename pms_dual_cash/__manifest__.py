# -*- coding: utf-8 -*-
{
    'name': 'PMS Dual Currency Cash (SSP + USD)',
    'version': '14.0.1.0.7',
    'category': 'Accounting',
    'summary': 'Auto-configure Cash SSP and Cash USD journals on every database',
    'description': """
        Installs automatically with Accounting and provisions:
        - Cash SSP journal (CSH1) on account 101501
        - Cash USD journal (CSH2) on account 101504
        - Multi-currency enabled
        - POS payment methods when Point of Sale is installed
    """,
    'author': 'PMS',
    'license': 'LGPL-3',
    'depends': ['account', 'point_of_sale', 'pos_multi_pricelist_app'],
    'data': [
        'security/security.xml',
        'views/pos_order_views.xml',
        'views/assets.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': ['account'],
}
