from odoo import models, fields, api


class ExpenseForm(models.Model):
    _inherit = 'hr.expense'

    expense_direct = fields.Many2one('expense.direct.indirect', string='Direct',)

class AlokasiBiaya(models.Model):
    _name = 'expense.direct.indirect'

    name = fields.Char('Name')
    description = fields.Char( string="Description",)
    expense_direct_indirect_count = fields.Integer(string='Direct Count', compute='_get_direct_count')    

    @api.multi
    def open_expense_direct(self):
        for group in self:
            return {
                    'name': 'Expense',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'hr.expense',
                    'type': 'ir.actions.act_window',
                    'domain': [('expense_direct', '=', group.id)],
                }
        pass

    @api.multi
    def _get_direct_count(self):
            res = self.env['hr.expense'].search_count([('expense_direct', '=', self.id)])
            self.expense_direct_indirect_count = res or 0
