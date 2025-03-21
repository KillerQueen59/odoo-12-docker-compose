from odoo import models, api, fields


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    product_group = fields.Many2one('product.group', string='Product Group')


class ProductGroup(models.Model):
    _name = "product.group"

    _sql_constraints = [('code_uniq', 'unique (code)', "Product group code must be unique!"), ]

    code = fields.Char('Code', required=True)
    name = fields.Char('Name')
    description = fields.Char('Description')

    product_count = fields.Integer(string='Product Count', compute='_get_product_count')

    @api.multi
    def open_products(self):
        for group in self:
            return {
                'name': 'Products',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'domain': [('product_group', '=', group.id)],
            }
        pass

    @api.multi
    def _get_product_count(self):
        res = self.env['product.template'].search_count([('product_group', '=', self.id)])
        self.product_count = res or 0
