{
    'name': 'RNET - Project Management',
    'version': '1.0',
    'category': 'Project',
    'author': '',
    'description': """
    Use Project module for Progress project Management.
    """,
    'data': [
        'security/ir.model.access.csv',
        'views/project_progress.xml',
        'views/project_cashflow.xml',
        'data/data.xml',
        'security/security.xml',
        'report/plan_analysis.xml',
        'report/actual_analysis.xml',
        'report/actual_plan_analysis.xml',
        # 'views/project_dashboard.xml',
        # 'views/project_dashboard_detail.xml',
        'reports/report.xml',
        'reports/cashflow_report.xml'
    ],
    'depends': ['mail','account','project','hr_timesheet_sheet','purchase'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 105,
    'license': 'AGPL-3',
}
