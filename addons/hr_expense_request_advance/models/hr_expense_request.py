# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import ValidationError

class HRExpenseRequest(models.Model):
    _name = 'hr.expense.request'
    _description = 'HR Expense Request'
    _inherit = ['expense.request.abstract']


    @api.multi
    def action_submit(self):
        super(HRExpenseRequest, self).action_submit()
        self.activity_update()

    @api.multi
    def action_approve(self):
        super(HRExpenseRequest, self).action_approve()
        sequence_code = 'hr.expense.request.sequence'
        self.seq_num = self.env['ir.sequence'].with_context(ir_sequence_date=self.requested_date).next_by_code(sequence_code)
        responsible_id = self.user_id.id or self.env.user.id
        self.write({'user_id': responsible_id})
        self.activity_update()

    @api.multi
    def action_reject(self, reason):
        self.write({'state': 'rejected'})
        for req in self:
            req.message_post_with_view('hr_expense_request_advance.expense_request_template_refuse_reason',  values={'reason': reason, 'name': req.name})
        self.activity_update()


    @api.multi
    def unlink(self):
        for request in self:
            if request.state in ['approved', 'submitted', 'reported']:
                raise ValidationError(_('You cannot delete reported, approved or submitted Expense Request.'))
        return super(HRExpenseRequest, self).unlink()


    # Mail Thread
    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'approved':
            return 'hr_expense_request_advance.mt_expense_request_approved'
        elif 'state' in init_values and self.state == 'rejected':
            return 'hr_expense_request_advance.mt_expense_request_rejected'
        return super(HRExpenseRequest, self)._track_subtype(init_values)

    def _get_responsible_for_approval(self):
        if self.user_id:
            return self.user_id
        elif self.employee_id.parent_id.user_id:
            return self.employee_id.parent_id.user_id
        elif self.employee_id.department_id.manager_id.user_id:
            return self.employee_id.department_id.manager_id.user_id
        return self.env['res.users']

    def activity_update(self):
        for expense_request in self.filtered(lambda req: req.state == 'submitted'):
            self.activity_schedule(
                'hr_expense_request_advance.mail_act_expense_request_approval',
                user_id=expense_request.sudo()._get_responsible_for_approval().id or self.env.user.id)

        self.filtered(lambda req: req.state == 'approved').activity_feedback(
                ['hr_expense_request_advance.mail_act_expense_request_approval'])

        self.filtered(lambda req: req.state == 'rejected').activity_unlink(
                ['hr_expense_request_advance.mail_act_expense_request_approval'])



