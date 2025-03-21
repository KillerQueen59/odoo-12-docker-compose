# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError


class HrExpenseAdvance(models.Model):
    _name = "hr.expense.advance"
    _description = "HR Expense Advance"
    _inherit = ['expense.request.abstract']

    @api.model
    def _default_bank_journal_id(self):
        return self.env['account.journal'].search([('type', 'in', ('bank', 'cash')), ('company_id', '=', self.env.user.company_id.id)], limit=1)

    journal_id = fields.Many2one('account.journal', string='Payment Method', domain=[('type', 'in', ('bank', 'cash'))], default=_default_bank_journal_id)
    payment_date = fields.Date(string='Paid Date', default=fields.Date.context_today)
    paid_amount = fields.Monetary(string='Paid Amount', currency_field='currency_id', digits=dp.get_precision('Account'))
    payment_id = fields.Many2one('account.payment', string='Payment', ondelete='restrict', copy=False)
    state = fields.Selection(selection_add=[('paid', 'Paid')])
    address_id = fields.Many2one('res.partner', string="Employee Home Address")

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.address_id = self.employee_id.sudo().address_home_id
        super(HrExpenseAdvance, self).onchange_employee_id()

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        if self.journal_id.company_id.id != self.company_id.id:
            raise ValidationError(_("Can not create payment journal entry for different company!"))


    @api.onchange('residual_amount')
    def onchnage_residual_amount(self):
        self.paid_amount = self.total_paid

    # @api.multi
    # @api.constrains('requested_amount', 'paid_amount')
    # def check_requested_amount(self):
    #     if self.requested_amount <= 0.00 or self.paid_amount <= 0.00:
    #         raise ValidationError(_("The amount should be greater than 0.0!"))

    @api.multi
    def action_submit(self):
        super(HrExpenseAdvance, self).action_submit()
        self.activity_update()

    @api.multi
    def action_approve(self):
        super(HrExpenseAdvance, self).action_approve()
        sequence_code = 'hr.expense.advance.sequence'
        self.seq_num = self.env['ir.sequence'].with_context(ir_sequence_date=self.requested_date).next_by_code(sequence_code)
        responsible_id = self.user_id.id or self.env.user.id
        self.write({'user_id': responsible_id})
        self.activity_update()

    @api.multi
    def action_reject(self, reason):
        self.write({'state': 'rejected'})
        for advance in self:
            advance.message_post_with_view('hr_expense_request_advance.expense_advance_template_refuse_reason', values={'reason': reason, 'name': advance.name})
        self.activity_update()

    @api.multi
    def unlink(self):
        for request in self:
            if request.state in ['approved', 'submitted', 'paid', 'reported']:
                raise ValidationError(_('You cannot delete reported, paid ,approved or submitted Expense Advance.'))
        return super(HrExpenseAdvance, self).unlink()


    # Mail Thread
    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'approved':
            return 'hr_expense_request_advance.mt_expense_advance_approved'
        elif 'state' in init_values and self.state == 'rejected':
            return 'hr_expense_request_advance.mt_expense_advance_rejected'
        elif 'state' in init_values and self.state == 'paid':
            return 'hr_expense_request_advance.mt_expense_advance_paid'
        return super(HrExpenseAdvance, self)._track_subtype(init_values)


    def _get_responsible_for_approval(self):
        if self.user_id:
            return self.user_id
        elif self.employee_id.parent_id.user_id:
            return self.employee_id.parent_id.user_id
        elif self.employee_id.department_id.manager_id.user_id:
            return self.employee_id.department_id.manager_id.user_id
        return self.env['res.users']

    def activity_update(self):
        for expense_advance in self.filtered(lambda req: req.state == 'submitted'):
            self.activity_schedule(
                'hr_expense_request_advance.mail_act_expense_advance_approval',
                user_id=expense_advance.sudo()._get_responsible_for_approval().id or self.env.user.id)

        self.filtered(lambda req: req.state == 'approved').activity_feedback(
                ['hr_expense_request_advance.mail_act_expense_advance_approval'])

        self.filtered(lambda req: req.state == 'rejected').activity_unlink(
                ['hr_expense_request_advance.mail_act_expense_advance_approval'])
