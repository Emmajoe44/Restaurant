# -*- coding: utf-8 -*-
{
    'name': 'Restaurant Management',
    'summary': 'Restaurant branding and POS customization for PMS',
    'description': """
        Restaurant management module for Point of Sale.
        Adds restaurant icon, menu labels, and inventory wording.
    """,
    'author': 'PMS Development Team',
    'website': 'http://www.yourcompany.com',
    'category': 'Sales/Point of Sale',
    'version': '14.0.1.0.2',
    'depends': ['base', 'point_of_sale', 'pos_restaurant', 'stock', 'account', 'contacts'],
    'data': [
        'security/security.xml',
        'data/menu_icon.xml',
        'views/assets.xml',
        'views/views.xml',
        'views/pos.xml',
        'views/inventory.xml',
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/order_management_buttons.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'demo': [
        'demo/demo.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}