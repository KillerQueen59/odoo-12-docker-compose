from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class Brand(models.Model):
    _name = 'gut.brand'
    _description = 'Product Brand'

    _sql_constraints = [('brand_name_unique', 'unique(name)', "Brand name must be unique!"), ]

    code = fields.Char('Brand Code',)
    name = fields.Char('Brand Name', required=True)
    alias = fields.Char('Alias')

    product_count = fields.Integer(string='Product Count', compute='_get_product_count')

    @api.multi
    def open_products(self):
        for brand in self:
            return {
                'name': 'Products',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'domain': [('brand', '=', brand.id)],
            }
        pass

    @api.multi
    def _get_product_count(self):
        res = self.env['product.template'].search_count([('brand', '=', self.id)])
        self.product_count = res or 0

    #https://www.odoo.com/forum/help-1/odoo-14-unique-values-but-how-to-prevent-with-spelling-mistakes-182159
    @api.constrains('name')
    def _check_unique_brand(self):
        brand_ids = self.search([]) - self

        value = [x.name.lower() for x in brand_ids]

        if self.name and self.name.lower() in value:
            raise ValidationError(_('The Brand Name is already Exist'))

        return True
