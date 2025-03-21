from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
import logging
_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = 'product.product'

    # categ_id
    is_generate_multiple_asset = fields.Boolean(compute='_is_generate_multiple_asset', string='Is Generate Multiple Asset')

    @api.one
    def _is_generate_multiple_asset(self):
        self.is_generate_multiple_asset = self.categ_id.po_generate_multiple_asset

    @api.multi
    def name_get(self):
        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        self.browse(self.ids).read(['name', 'brand'])
        return [(template.id, '%s%s' % (template.brand.name and '[%s] ' % template.brand.name or '', template.name))
                for template in self]

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand = fields.Many2one('gut.brand', 'Brand')
    brand_type = fields.Char('Brand Type')
    display_as_delivery_cost = fields.Boolean(default=False)
    category_name = fields.Char('Category Name', compute="_compute_category_name", store=True)

    def create(self, vals_list):
        template = super(ProductTemplate, self).create(vals_list)
        ir = template.default_code
        if not ir:
            template.default_code = self._get_product_prefix(template.categ_id.id)
        return template

    def _get_product_prefix(self, categ_id):
        categ = self.env['product.category'].search([
            ('id', '=', categ_id)
        ])
        prefix = categ.product_prefix
        if not prefix:
            return None
        seq = self.env['ir.sequence'].next_by_code('product.seq') or None
        if not seq:
            raise UserError(_("Sequence is null or not found"))
        return prefix + str(seq)

    @api.one
    def _compute_category_name(self):
        for rec in self:
            cat = rec.categ_id.parent_id.name
            self.category_name = cat if cat else None


class ProductCategory(models.Model):
    _inherit = 'product.category'

    po_generate_multiple_asset = fields.Boolean('PO Generate Multiple Asset')
    product_prefix = fields.Char("Product Prefix")

