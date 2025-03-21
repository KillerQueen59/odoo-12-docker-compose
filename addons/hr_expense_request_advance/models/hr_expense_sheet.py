# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model
    def _get_approved_my_expense_request_domain(self):
        res = [('id', '=', 0)]  # Nothing by default
        if self.env.user.employee_ids:
            user = self.env.user
            res = [('state', '=', 'approved'), ('employee_id.user_id.id', '=', user.id)]
        return res

    @api.model
    def _get_approved_my_expense_advance_domain(self):
        # res = [('id', '=', 0)]  # Nothing by default
        # if self.env.user.employee_ids:
        #     user = self.env.user
        #     res = [('state', '=', 'paid'),('employee_id.user_id.id', '=', user.id)]
        res = [('state', '=', 'paid'),]
        return res

    expense_request_id = fields.Many2one('hr.expense.request', string="Expense Request", readonly=True, states={'draft': [('readonly', False)]}, domain= lambda self: self._get_approved_my_expense_request_domain())
    request_currency_id = fields.Many2one('res.currency', string='Request Currency', related='expense_request_id.currency_id')
    request_amount = fields.Monetary(string="Request Amount", related='expense_request_id.requested_amount', currency_field='request_currency_id')
    expense_advance_id = fields.Many2one('hr.expense.advance', string="Expense Advance", readonly=True, states={'draft': [('readonly', False)]}, domain=lambda self: self._get_approved_my_expense_advance_domain())
    advance_currency_id = fields.Many2one('res.currency', string='Advance Currency', related='expense_advance_id.currency_id')
    advance_amount = fields.Monetary(string="Advance Amount", related='expense_advance_id.paid_amount', currency_field='advance_currency_id')
    return_amount = fields.Monetary(string="Return Amount", currency_field='currency_id', compute='cal_return_amount')
    return_to_employee = fields.Boolean('Return to Employee?', compute='cal_return_amount')
    notes = fields.Text('Remarks')


    @api.depends('advance_amount', 'total_amount', 'expense_line_ids.total_amount_company')
    def cal_return_amount(self):
        for sheet in self:
            if sheet.expense_advance_id and sheet.advance_currency_id and sheet.advance_amount > 0:
                advance_company_amount = sheet.advance_amount
                if sheet.currency_id.id != sheet.advance_currency_id.id:
                    advance_company_amount = sheet.advance_currency_id._convert(
                        sheet.expense_advance_id.paid_amount, sheet.currency_id,
                        sheet.company_id, fields.Date.today())

                diff = sheet.total_amount - advance_company_amount
            else:
                diff = sheet.total_amount
            sheet.return_to_employee = True if diff > 0 else False
            sheet.return_amount = abs(diff)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.address_id = self.employee_id.sudo().address_home_id
        self.department_id = self.employee_id.department_id
        self.user_id = self.employee_id.sudo().expense_manager_id or self.employee_id.sudo().parent_id.user_id

    @api.multi
    def approve_expense_sheets(self):
        super(HrExpenseSheet, self).approve_expense_sheets()
        if self.expense_request_id:
            self.expense_request_id.write({'state': 'reported'})
        if self.expense_advance_id:
            self.expense_advance_id.write({'state': 'reported'})

    @api.multi
    def refuse_sheet(self, reason):
        super(HrExpenseSheet, self).refuse_sheet(reason)
        if self.expense_request_id:
            self.expense_request_id.write({'state': 'approved'})
            self.expense_request_id = None
        if self.expense_advance_id:
            self.expense_advance_id.write({'state': 'paid'})
            self.expense_advance_id = None

