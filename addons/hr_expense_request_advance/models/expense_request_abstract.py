# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError

class ExpenseRequestAbstract(models.AbstractModel):
    _name = 'expense.request.abstract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Abstract model for expense request and advance"
    _order = "requested_date desc"

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    seq_num = fields.Char(string="Sequence", readonly=True, copy=False)
    name = fields.Char(string="Purpose", required=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(
        [('draft', 'Draft'),
         ('submitted', 'Submitted'),
         ('approved', 'Approved'),
         ('rejected', 'Rejected'),
         ('reported', 'Reported')],
        string='Status', index=True, readonly=True, copy=False, track_visibility='onchange',
        default='draft', required=True, help='Expense Request State')

    employee_id = fields.Many2one('hr.employee', string="Employee Name", required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_employee)
    department_id = fields.Many2one('hr.department', string="Department Name", readonly=True, states={'draft': [('readonly', False)]})
    job_id = fields.Many2one('hr.job', string="Job Title", readonly=True, states={'draft': [('readonly', False)]})
    requested_date = fields.Date(string='Requested Date', default=fields.Date.context_today, readonly=True, states={'draft': [('readonly', False)]})
    requested_user = fields.Many2one('res.users', string="Requested User", default=lambda self: self.env.user.id)
    user_id = fields.Many2one('res.users', 'Approver', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id.currency_id)
    requested_amount = fields.Monetary(string='Requested Amount', readonly=True, states={'draft': [('readonly', False)]}, currency_field='currency_id', digits=dp.get_precision('Account'))
    current_user_is_requester = fields.Boolean(string='Current user is requester?', compute='_compute_current_user_is_requester')
    description = fields.Text('Description')

    @api.multi
    def _compute_current_user_is_requester(self):
        for req in self:
            req.current_user_is_requester = True if req.create_uid == req.env.user else False

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.department_id = self.employee_id.department_id.id
        self.job_id = self.employee_id.job_id.id
        self.user_id = self.employee_id.sudo().expense_manager_id or self.employee_id.sudo().parent_id.user_id

    @api.multi
    def action_submit(self):
        # if self.requested_amount <= 0.00:
        #     raise ValidationError(_('Request amount should be greater than 0.0.'))
        self.write({'state': 'submitted'})

    @api.multi
    def action_draft(self) :
        self.write({'state': 'draft'})

    @api.multi
    def action_approve(self):
        # if self.requested_amount <= 0.00:
        #     raise ValidationError(_('Request amount should be greater than 0.0.'))
        self.write({'state': 'approved'})







