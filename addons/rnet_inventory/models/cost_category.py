from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

STATEPARENTNAME = [
    ('running_overhead', 'Running Overhead'),
    ('one_time_overhead', 'One Time Overhead'),
    ('local_worker', 'Local Worker'),
    ('operation', 'Operation'),
    ('personal', 'Personal'),
]

import logging

_logger = logging.getLogger(__name__)

class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    product_cost_category = fields.Many2one('product.cost.category', string='Cost Category')
    

class Brand(models.Model):
    _name = 'product.cost.category'
    _description = 'Product cost category expense'

    code = fields.Char('Code', required=True)
    name = fields.Char('Nama', required=True)
    parent_name = fields.Selection(STATEPARENTNAME, 'Cost Category')
    description = fields.Char('Description')

    product_count = fields.Integer(string='Product Count', compute='_get_product_count')
    expense_count = fields.Integer(string='Expense Count', compute='_get_expense_count')

    @api.multi
    def open_product_cost_category(self):
        for group in self:
            return {
                    'name': 'Products',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'product.template',
                    'type': 'ir.actions.act_window',
                    'domain': [('product_cost_category', '=', group.id)],
                }
        pass

    @api.multi
    def open_expense_cost_category(self):
        for group in self:
            return {
                    'name': 'Expenses',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'hr.expense',
                    'type': 'ir.actions.act_window',
                    'domain': [('cost_category', '=', group.id)],
                }
        pass

    @api.multi
    def _get_product_count(self):
            res = self.env['product.template'].search_count([('product_cost_category', '=', self.id)])
            self.product_count = res or 0

    @api.multi
    def _get_expense_count(self):
            res = self.env['hr.expense'].search_count([('cost_category', '=', self.id)])
            self.expense_count = res or 0

    @api.multi
    def name_get(self):
        data = []
        for o in self:
            display_name = '['
            display_name += o.code or ""
            display_name += '] '
            display_name += o.name or ""
            data.append((o.id, display_name))
        return data

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        cost_category_ids = self._search(domain + args, limit=limit)
        return self.browse(cost_category_ids).name_get()
