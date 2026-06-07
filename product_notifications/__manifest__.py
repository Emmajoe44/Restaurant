# -*- coding: utf-8 -*-
{
    'name': "Product Notifications",

    'summary': """
        Send notifications when the product expires or its quantity decreases """,

    'description': """
        Sending notifications to the user when the product expires 
        or the quantity decreases to the required limit
    """,

    'author': "Ghanem Ibrahim",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'data/notification_cron.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',

    ],
}
