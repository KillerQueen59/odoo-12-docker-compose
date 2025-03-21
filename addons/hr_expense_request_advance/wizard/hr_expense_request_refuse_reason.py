# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ExpenseRequestRefuseWizard(models.TransientModel):

    _name = "hr.expense.request.refuse.wizard"
    _description = "Expense Request Refuse Reason Wizard"

    reason = fields.Char(string='Reason', required=True)

    @api.multi
    def expense_request_refuse_reason(self):
        req = self.env['hr.expense.request'].browse(self.env.context.get('active_ids'))
        return req.action_reject(reason=self.reason)
        # return {'type': 'ir.actions.act_window_close'}
