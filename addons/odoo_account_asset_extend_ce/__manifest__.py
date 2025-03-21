# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Account Asset Extension',
    'currency': 'EUR',
    'version' : '1.1',
    'category': 'Accounting',
    'price' : 49.0,
    'summary' : 'This module will add some more fields on Account Asset.',
    'description': """
Odoo Account Asset Extend
Asset Employee
Asset User
Asset Manager
Warranty Information for Asset
Asset Warranty Information
Asset Warranty Details
Asset Pivot Report
account asset
            """,
    'author' : 'Probuse Consulting Service Pvt. Ltd.',
    'website' : 'www.probuse.com',
    'support': 'contact@probuse.com',
#     'live_test_url': 'https://youtu.be/cFrlw7ccpuU',
    'live_test_url': 'https://youtu.be/WkxKaTwlGC4',
    'images': ['static/description/img1.jpg'],
    'depends' : [
            'hr',
            'account',
            'purchase',
            'maintenance',
            'odoo_account_asset',
            'asset_print_report',
                ],
    'data' : [
            'data/asset_sequence.xml',
            'views/asset_view.xml',
            'security/res_group.xml',
            'views/asset_menu_view.xml',
            'views/account_asset_report_views.xml',
            'security/ir.model.access.csv',
            'report/asset_print_report.xml',
              ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
