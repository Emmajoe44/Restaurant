# -*- coding: utf-8 -*-
{
 'name': 'Restaurant Logo',
 'version': '14.0.1.0',
 'category': 'Point of Sale',
 'summary': 'Restaurant icon on Point of Sale',
 'description': 'Displays a restaurant icon in the POS header instead of the default Odoo logo.',
 'author': 'PMS Development Team',
 'depends': ['point_of_sale', 'pos_restaurant'],
 'data': [
 'views/pos_restaurant_logo_templates.xml',
 ],
 'qweb': [
 'static/src/xml/Chrome.xml',
 ],
 'images': ['static/description/icon.png'],
 'installable': True,
 'auto_install': False,
 'application': False,
 'license': 'LGPL-3',
}