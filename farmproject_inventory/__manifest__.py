# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "The Farm Project: Purchase Inventory Customizations",
    'summary': "Web",
    'description': """
The Farm Project: Purchase Inventory Customizations
===================================================
- Quantities in purchase unit of measures on incoming shipments.
""",
    "author": "Odoo Inc",
    'website': "https://www.odoo.com",
    'category': 'Custom Development',
    'version': '0.1',
    'depends': ['stock', 'purchase'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'license': 'OEEL-1',
}