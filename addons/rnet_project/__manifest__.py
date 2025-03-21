{
    'name': "RNET - Project",
    'author': "RNET",
    'version': '0.1',

    'depends': ['project','hr'],

    'data': [
        'security/ir.model.access.csv',
        'data/project.xml',
        'views/project_views.xml',
        # 'views/project_task.xml',
        # 'views/stock_picking_views.xml',
        'report/report.xml',
        'report/jo_registration_template.xml',
    ],

    "installable": True,
    "auto_install": False,
    "application": True,
}