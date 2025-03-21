

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# select multiple product
class SelectMultiProductStockInventory(models.TransientModel):
    _name = 'sr.multi.product.stock.inventory'

    product_ids = fields.Many2many('product.product', string="Product")

    @api.multi
    def add_product(self):
        context = dict(self._context or {})
        picking = self.env['stock.inventory'].browse(context.get('active_ids'))
        for line in self.product_ids:
            self.env['stock.inventory.line'].create({
                    'product_id': line.id,
                    'location_id' : picking.location_id.id,
                    'product_uom_id' : line.uom_id.id,
                    'inventory_id': self._context.get('active_id'),
                })
        return


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    @api.constrains('product_id')
    def _check_product_id(self):
        """ As no quants are created for consumable products, it should not be possible do adjust
        their quantity.
        """
        for line in self:
            if line.product_id.type not in ['product','consu']:
                raise ValidationError(_("You can only adjust storable products.") + '\n\n%s -> %s' % (line.product_id.display_name, line.product_id.type))
