{
    'name': "RNET - Invoice",
    'author': "RNET",
    'version': '0.1',

    'depends': ['account', 'project'],

    'data': [
        'security/ir.model.access.csv',
        'views/invoice.xml',
        'views/invoice_supplier.xml',
        'views/faktur_pajak_view.xml',
        'report/report.xml',
        'report/invoice_gut.xml',
        'report/invoice_hyundai.xml',
        'report/invoice_rapp.xml',
        'report/invoice_donghwa.xml',
        'report/debit_note_vat.xml',
        'report/debit_note_no_vat.xml',
        'report/debit_note_shinbo.xml',
        'report/proforma_invoice.xml',
        'data/sequence.xml',
    ],

    "installable": True,
    "auto_install": False,
    "application": True,
}