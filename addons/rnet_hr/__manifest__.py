{
    'name': "RNET - HR",
    'author': "RNET",
    'version': '0.1',

    'depends': ['hr', 'hr_payroll','rnet_project', 'project'],

    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/employee.xml',
        'views/attendance.xml',
        'views/employee_grade.xml',
        'views/timesheet.xml',
        'views/payslip.xml',
        'views/contract.xml',
        'views/cv.xml',
        'views/cuti.xml',
        'views/appraisal.xml',
        'views/employee_certificate.xml',
        'views/employee_penilaian_kinerja.xml',
        'report/report.xml',
        'report/payslip_report_template.xml',
        'report/payslip_report_detail_template.xml',
        'report/cuti_report_template.xml',
        'report/cv_report_template.xml',
        'report/overtime_order_report_template.xml',
        'report/allowance_claim_report_template.xml',
        'report/timesheet_report_template.xml',
        'report/timesheet_report_template_form_c.xml',
        'report/appraisal_report_template.xml',
        'data/salary_rule.xml',

    ],

    "installable": True,
    "auto_install": False,
    "application": True,
}