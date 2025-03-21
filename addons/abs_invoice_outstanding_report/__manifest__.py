# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2019-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

{
    'name': "Outstanding Invoice Report",
    'author': 'Ascetic Business Solution',
    'category': 'account_invoicing',
    'summary': """Report for customer's outstanding invoice amount within the particular date period""",
    'website': 'http://www.asceticbs.com',
    'license': 'AGPL-3',
    'description': """
""",
    'version': '12.0.0.1',
    'depends': ['base','account'],
    'data': ['wizard/invoice_outstanding.xml','views/invoice_outstanding_report_view.xml','report/invoice_outstanding_template.xml','report/invoice_outstanding_report.xml'],
    'installable': True,
    'images': ['static/description/banner.png'],
    'application': True,
    'auto_install': False,
}
