from odoo import models, fields, api


class HrExpenseReportLineWizard(models.Model):
    _name = 'hr.expense.report.line.wizard'

    expense_report_id = fields.Many2one('hr.expense.sheet','Expense Report Id',)