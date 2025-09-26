
{
    'name': 'RNET - Project Management',
    'version': '1.0',
    'category': 'Project',
    'author':'',
    'description': """
    Use Project module for Progress project Management.
    """,
    'data': [
        'security/ir.model.access.csv',
        # 'views/project_progress.xml',
        'views/approval_banner.xml',
        'views/project_cashflow.xml',
        'views/assets.xml',
        'views/project_task_views.xml',
        'data/data.xml',
        'security/security.xml',
        'report/plan_analysis.xml',
        'report/actual_analysis.xml',
        'report/actual_plan_analysis.xml',
        'reports/report.xml',
        'reports/cashflow_report.xml',

    ],
    'depends': ['mail','account','project','hr_timesheet_sheet','purchase','web_project_gantt_view'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 105,
    'license': 'AGPL-3',
}
