from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



import logging

_logger = logging.getLogger(__name__)

class ProductTemplateInherit(models.Model):
    _inherit = 'res.partner'

    industry_id = fields.Many2one('res.partner.industry')
    

class VendorCategory(models.Model):
    _inherit = 'res.partner.industry'

    vendor_count = fields.Integer(string='Vendor Count', compute='_get_vendor_count')

    @api.multi
    def open_vendor_category(self):
        for group in self:
            return {
                    'name': 'Vendors',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'res.partner',
                    'type': 'ir.actions.act_window',
                    'domain': [('industry_id', '=', group.id)],
                }
        pass

    @api.multi
    def _get_vendor_count(self):
            res = self.env['res.partner'].search_count([('industry_id', '=', self.id)])
            self.vendor_count = res or 0
