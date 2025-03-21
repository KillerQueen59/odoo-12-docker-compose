from odoo import models, fields, api

ALOKASIBIAYA = [
    ('overhead_proyek', 'Overhead Proyek'),
    ('sipil', 'Sipil'),
    ('mekanikal', 'Mekanikal'),
    ('elektrikal', 'Elektrikal'),
    ('instrumen', 'Instrumen'),
    ('engineering', 'Engineering'),
    ('donation', 'Donation'),
]

class ExpenseForm(models.Model):
    _inherit = 'hr.expense'

    alokasi_biaya = fields.Many2one('expense.alokasi.biaya', string='Alokasi Biaya',)

class AlokasiBiaya(models.Model):
    _name = 'expense.alokasi.biaya'

    name = fields.Char('Name')
    description = fields.Char( string="Description",)
    expense_alokasi_biaya_count = fields.Integer(string='Alokasi Biaya Count', compute='_get_alokasi_biaya_count')    

    @api.multi
    def open_expense_alokasi_biaya(self):
        for group in self:
            return {
                    'name': 'Expense',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'hr.expense',
                    'type': 'ir.actions.act_window',
                    'domain': [('alokasi_biaya', '=', group.id)],
                }
        pass

    @api.multi
    def _get_alokasi_biaya_count(self):
            res = self.env['hr.expense'].search_count([('alokasi_biaya', '=', self.id)])
            self.expense_alokasi_biaya_count = res or 0
