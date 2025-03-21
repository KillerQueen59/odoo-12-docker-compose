# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Assets Management',
    'depends': ['account'],
    'category': 'Accounting',
    'sequence': 32,
    'description': """
        Assets management
        =================
        Manage assets owned by a company or a person.
        Keeps track of depreciations, and creates corresponding journal entries.
    
    Asset Types
    Assets
asset
account asset
asset account
account depreciations
depreciation
asset depreciations
depreciations
assets management
asset management
asset app
asset module
asset report

    """,
    'license': 'Other proprietary',
    'price': 99.0,
    'currency': 'EUR',
    'version': '1.4.1',
    'website': 'www.probuse.com',
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'support': 'contact@probuse.com',
    'images': ['static/description/img1.jpg'],
    'live_test_url': 'https://youtu.be/XHjsj5KDHYc',
    'data': [
        'security/account_asset_security.xml',
        'security/ir.model.access.csv',
        'wizard/asset_depreciation_confirmation_wizard_views.xml',
        'wizard/asset_modify_views.xml',
        'views/account_asset_views.xml',
        'views/account_invoice_views.xml',
#         'views/account_asset_templates.xml',
        'views/product_views.xml',
#         'views/res_config_settings_views.xml',
        'report/account_asset_report_views.xml',
        'data/account_asset_data.xml',
    ],
    'installable': True,
    'application': True,
}
