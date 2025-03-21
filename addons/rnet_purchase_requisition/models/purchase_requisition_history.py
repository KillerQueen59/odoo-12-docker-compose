from odoo import models, fields, api, _


class PurchaseRequisitionHistory(models.Model):
    _name = 'purchase.requisition.history'
    _inherit = 'material.purchase.requisition'

    original_id = fields.Integer(required=True)
    revision = fields.Integer(default=0)
    revision_date = fields.Datetime()

    requisition_line_ids = fields.One2many('purchase.requisition.line.history', 'requisition_id',
                                           string='Purchase Requisitions Line', copy=True,)

