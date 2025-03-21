# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ExpenseAdvanceRefuseWizard(models.TransientModel):

    _name = "hr.expense.advance.refuse.wizard"
    _description = "Expense Advance Refuse Reason Wizard"

    reason = fields.Char(string='Reason', required=True)

    @api.multi
    def expense_advance_refuse_reason(self):
        req = self.env['hr.expense.advance'].browse(self.env.context.get('active_ids'))
        return req.action_reject(reason=self.reason)
        # return {'type': 'ir.actions.act_window_close'}
