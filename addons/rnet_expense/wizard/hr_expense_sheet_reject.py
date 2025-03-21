from odoo import fields, models, api, _
from odoo.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)

class HrExpenseRefuseWizard(models.TransientModel):
    _inherit = "hr.expense.refuse.wizard"


    @api.model
    def default_get(self, fields):
        res = super(HrExpenseRefuseWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])
        refuse_model = self.env.context.get('hr_expense_refuse_model')
        if refuse_model == 'hr.expense':
            res.update({
                'hr_expense_ids': active_ids,
                'hr_expense_sheet_id': False,
            })
        elif refuse_model == 'hr.expense.sheet':
            res.update({
                'hr_expense_sheet_id': active_ids[0] if active_ids else False,
                'hr_expense_ids': [],
                
            })
        return res

    @api.multi
    def expense_refuse_reason(self):
        self.ensure_one()
        if self.hr_expense_ids:
            self.hr_expense_ids.refuse_expense(self.reason)
        if self.hr_expense_sheet_id:
            self.hr_expense_sheet_id.refuse_sheet(self.reason)

        template = self.env.ref('rnet_expense.email_refuse_project_manager_cvr')
        if template:
            template.send_mail(self.hr_expense_sheet_id.id)

        return {'type': 'ir.actions.act_window_close'}

class ExpenseSheetControlRejectWizard(models.TransientModel):
    _name = 'hr.expense.sheet.control.reject.wizard'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    reject_control_reason = fields.Text(string="Reject Reason", required=True)

    @api.one
    def action_reject_control(self):
    
        pr = self.env['hr.expense.sheet'].browse(self._context['expense_sheet_control_id'])
        pr.write({
            'state': 'reject_control',
            'reject_employee_id': self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1).id,
            'userreject_date': fields.Date.today(),
            'reject_control_reason': self.reject_control_reason,
        })
                                                                                            
        employee_mail_template = self.env.ref('rnet_expense.email_reject_cost_control_cvr')
        if employee_mail_template:
            employee_mail_template.send_mail(pr.id)

class ExpenseSheetTechnicalRejectWizard(models.TransientModel):
    _name = 'hr.expense.sheet.technical.reject.wizard'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    reject_technical_reason = fields.Text(string="Reject Reason", required=True)

    @api.one
    def action_reject_technical(self):
    
        pr = self.env['hr.expense.sheet'].browse(self._context['expense_sheet_technical_id'])
        pr.write({
            'state': 'reject_technical',
            'reject_employee_id': self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1).id,
            'userreject_date': fields.Date.today(),
            'reject_technical_reason': self.reject_technical_reason,
        })
                                                                                            
        employee_mail_template = self.env.ref('rnet_expense.email_reject_technical_director_cvr')
        if employee_mail_template:
            employee_mail_template.send_mail(pr.id)

class ExpenseSheetFinanceRejectWizard(models.TransientModel):
    _name = 'hr.expense.sheet.finance.reject.wizard'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    reject_finance_reason = fields.Text(string="Reject Reason", required=True)

    @api.one
    def action_reject_finance(self):
    
        pr = self.env['hr.expense.sheet'].browse(self._context['expense_sheet_finance_id'])
        pr.write({
            'state': 'reject_finance',
            'reject_employee_id': self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1).id,
            'userreject_date': fields.Date.today(),
            'reject_finance_reason': self.reject_finance_reason,
        })
                                                                                            
        employee_mail_template = self.env.ref('rnet_expense.email_reject_finance_director_cvr')
        if employee_mail_template:
            employee_mail_template.send_mail(pr.id)