# -*- coding: utf-8 -*-
{
    'name': "Project Management Dashboard",
   'summary': """
        A comprehensive, interactive dashboard for project managers to track 
        approvals, KPIs, employee reviews, and project progress.""",
    'version': '12.0.2.5', 
    'category': 'Project Management',
    'author': "RNET",
    'website': "https://www.rekonsnetwork.com",
    'depends': [
        'web',
        'mail',
        'hr',
        'stock',
        'project',
        'purchase', 
        'hr_timesheet',
        'hr_timesheet_sheet',
        'hr_expense',          
        'purchase_requisition',
        'hr_expense_request_advance',
        'purchase_tripple_approval',
        'rnet_project_management',
        'rnet_hr',
        'rnet_project',
        'rnet_project_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/dashboard_templates_view.xml',
        'views/dashboard_views.xml',
    ],
    'qweb': [
        "static/src/xml/dashboard_templates.xml",
    ],
}