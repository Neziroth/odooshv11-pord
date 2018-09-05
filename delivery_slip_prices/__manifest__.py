# -*- coding: utf-8 -*-
{
    'name': "Delivery Slip prices",

    'summary': "Adding prices and totals to delivery slips",

    'description': "Adding prices and totals to delivery slips",

    'author': "Odoo",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['stock'],

    # always loaded
    'data': [
        'reports/delivery_slip.xml',
    ],
}