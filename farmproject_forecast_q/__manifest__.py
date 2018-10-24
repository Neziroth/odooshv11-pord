# -*- coding: utf-8 -*-
{
    'name': "farmproject_forecast_q",

    'summary': "Add forecast queue",

    'description': "Add forecast queue",

    'author': "odoo, inc",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['stock','product'],

    # always loaded
    'data': [
        'views/views.xml',
        'wizard/stock_by_location_wizard.xml',
    ],
}