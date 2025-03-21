from odoo import _, api, fields, models, SUPERUSER_ID


class Users(models.Model):
    _inherit = 'res.users'

    picking_type_ids = fields.Many2many(string='Allowed Operation Types',
                                        comodel_name='stock.picking.type',)


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    user_ids = fields.Many2many(string='User Ids', comodel_name='res.users',)
