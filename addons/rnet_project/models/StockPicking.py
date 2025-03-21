from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    project = fields.Many2one('project.project', string='Project')

    @api.model
    def create(self, vals):
        picking = super(StockPicking, self).create(vals)
        origin = vals.get('origin')
        purchase_list = self.env['purchase.order'].search([('name', '=', origin)], limit=1)
        for purchase in purchase_list:
            picking.write({'project': purchase.project.id})
        return picking
