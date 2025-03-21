# -*- coding: utf-8 -*-
{
    'name': "Expense Request/Cash Advance",

    'summary': """
        Manage Employee Expense Request and Cash Advance.
        """,

    'description': """
        Employee can raise expense request or cash advance and get approval before spending it.
        """,

    'author': "odookz",
    "price": 30.82,
    "currency": 'USD',
    'license': 'LGPL-3',

    'category': 'Human Resources',
    'version': '12.0.0.0.9',

    # any module necessary for this one to work correctly
    'depends': ['hr','hr_expense','account'],

    'data': [
        'security/hr_expense_request_rule.xml',
        'security/hr_expense_advance_rule.xml',
        'security/ir.model.access.csv',
        'data/hr_expense_sequence.xml',
        'data/email_notification_data.xml',
        'wizard/hr_expense_request_refuse_reason_views.xml',
        'wizard/hr_expense_advance_refuse_reason_views.xml',
        'wizard/hr_expense_advance_register_payment.xml',
        'views/hr_expense_request_views.xml',
        'views/hr_expense_advance_views.xml',
        'views/hr_expense_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
