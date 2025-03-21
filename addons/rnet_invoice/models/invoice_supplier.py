from odoo import models, fields, api

_STATES = [
    ('manager_approved', 'Manager Approved'),

]

class InvoiceSupplier(models.Model):
    _inherit = 'account.invoice'

state = fields.Selection([

('manager_approved', 'Manager Approved'),
])

