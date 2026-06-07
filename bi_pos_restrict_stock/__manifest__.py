# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Restrict Out of Stock Product on POS',
    'version': '14.0.0.0',
    'category': 'Point of Sale',
    'summary': 'Out of stock product restriction on point of sales order restriction for out of stock product restriction for POS Restrict Out Stock Product POS stop out of stock product for POS available products only out of stock product alerts out of stock products POS',
    'description': """

        Restrict Out of Stock Product on POS in odoo,
        Display Product Stock in odoo,
        Stock Configuration on POS in odoo,
        Restrict Product Out of Stock in POS in odoo,
        Raise Warning Popup in odoo,
        Total On Hand Quantity of Product in odoo,

    """,
    'author': 'BrowseInfo',
    "price": 12,
    "currency": 'EUR',
    'website': 'https://www.browseinfo.in',
    'depends': ['base', 'point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_assets_common.xml',
    ],
    'qweb': [
        'static/src/xml/Screens/ProductItem.xml',
        'static/src/xml/Popups/BiWarningPopup.xml',
    ],
    'auto_install': False,
    'installable': True,
    'live_test_url': 'https://youtu.be/h56RBaFf5Ww',
    'images': ["static/description/Banner.png"],
}
