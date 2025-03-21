{
    'name': "RNET - Purchase Requisition",
    'author': "RNET",
    'version': '0.1',

    'depends': ['material_purchase_requisitions'],

    'data': [
        'views/purchase_requisition_view.xml',
        'views/purchase_requisition_history_view.xml',
        'report/purchase_requisition_template.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/mail_template.xml',
    ],

    "installable": True,
    "auto_install": False,
    "application": True,
}