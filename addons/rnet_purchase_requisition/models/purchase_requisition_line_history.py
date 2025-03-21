from odoo import models, fields, api, _


class PurchaseRequisitionLineHistory(models.Model):
    _name = 'purchase.requisition.line.history'
    _inherit = 'material.purchase.requisition.line'

    requisition_id = fields.Many2one('purchase.requisition.history', string='Requisitions',)
