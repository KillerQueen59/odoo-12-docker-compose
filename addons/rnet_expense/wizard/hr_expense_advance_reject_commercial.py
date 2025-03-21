from odoo import fields, models, api, _
from odoo.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)


class ExpenseAdvanceCommercialRejectWizard(models.TransientModel):
    _name = 'hr.expense.advance.reject.wizard'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    reject_reason = fields.Text(string="Reject Reason", required=True)

    @api.one
    def action_reject(self):
    
        pr = self.env['hr.expense.advance'].browse(self._context['expense_advance_id'])
        pr.write({
            'state': 'rejected_commercial',
            'reject_employee_id': self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1).id,
            'userreject_date': fields.Date.today(),
            'reject_reason': self.reject_reason,
        })
                                                                                            
        employee_mail_template = self.env.ref('rnet_expense.email_expense_advance_rejected_commercial')
        if employee_mail_template:
            employee_mail_template.send_mail(pr.id)