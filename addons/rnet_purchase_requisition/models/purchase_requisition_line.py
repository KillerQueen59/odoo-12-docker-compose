from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, UserError

import logging

_logger = logging.getLogger(__name__)


class PurchaseRequisitionLine(models.Model):
    _inherit = 'material.purchase.requisition.line'

    brand = fields.Many2one('gut.brand', 'Brand')
    brand_note = fields.Char('Brand Note')
    remark = fields.Char('Remark')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.name
            rec.uom = rec.product_id.uom_id.id
            rec.brand = rec.product_id.brand.id
            rec.brand_note = rec.product_id.brand_type
