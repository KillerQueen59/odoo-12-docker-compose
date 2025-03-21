{
    'name': "RNET - Expenses",
    'author': "RNET",
    'version': '0.1',

    'depends': ['hr_expense', 'hr_expense_request_advance',],

    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/report_paperformat.xml',
        'views/expense.xml',
        'views/partner_view.xml',
        'views/sequence.xml',
        'views/account_bankbook.xml',
        'views/alokasi_biaya.xml',
        'views/direct_indirect.xml',
        'views/assets.xml',
        # 'report/expense.xml',
        'report/report.xml',
        'report/expense_advance_report_template.xml',
        'report/expense_sheet_report_template.xml',
        'report/expense_sheet_report_pcr_template.xml',
        'report/expense_sheet_journal_cvr_template.xml',
        'wizard/hr_expense_advance_register_payment.xml',
        'wizard/hr_expense_sheet_receive_payment.xml',
        'wizard/hr_expense_advance_reject_commercial.xml',
        'wizard/hr_expense_sheet_reject.xml',
        #
    ],

    "installable": True,
    "auto_install": False,
    "application": True,
}
