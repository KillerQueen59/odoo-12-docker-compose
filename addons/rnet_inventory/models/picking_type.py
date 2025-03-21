# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from itertools import groupby
from odoo import api, fields, models, _

class PickingType(models.Model):
    _inherit = "stock.picking.type"

    count_picking_confirmed = fields.Integer(compute='_compute_picking_count')

    @api.multi
    def _compute_picking_count(self):
        # TDE TODO count picking can be done using previous two
        domains = {
            'count_picking_draft': [('state', '=', 'draft')],
            'count_picking_waiting': [('state', '=', 'waiting')],
            'count_picking_confirmed': [('state', '=', 'confirmed')],
            'count_picking_ready': [('state', 'in', ('assigned', 'partially_available'))],
            'count_picking': [('state', 'in', ('draft','assigned', 'waiting', 'confirmed', 'partially_available'))],
            'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting', 'partially_available'))],
        }
        for field in domains:
            data = self.env['stock.picking'].read_group(domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['picking_type_id'])
            count = {
                x['picking_type_id'][0]: x['picking_type_id_count']
                for x in data if x['picking_type_id']
            }
            for record in self:
                record[field] = count.get(record.id, 0)
        for record in self:
            record.rate_picking_late = record.count_picking and record.count_picking_late * 100 / record.count_picking or 0
            record.rate_picking_backorders = record.count_picking and record.count_picking_backorders * 100 / record.count_picking or 0

   
    @api.multi
    def _get_action(self, action_xmlid):
        # TDE TODO check to have one view + custo in methods
        action = self.env.ref(action_xmlid).read()[0]
        if self:
            action['display_name'] = self.display_name
        return action


    @api.multi
    def get_action_picking_tree_late(self):
        return self._get_action('rnet_inventory.action_picking_tree_late')

    @api.multi
    def get_action_picking_tree_backorder(self):
        return self._get_action('stock.action_picking_tree_backorder')

    @api.multi
    def get_action_picking_tree_waiting(self):
        return self._get_action('rnet_inventory.action_picking_tree_waiting')

    @api.multi
    def get_action_picking_tree_ready(self):
        return self._get_action('rnet_inventory.action_picking_tree_ready')
    
    @api.multi
    def get_action_picking_tree_draft(self):
        return self._get_action('rnet_inventory.action_picking_tree_draft')

    @api.multi
    def get_action_picking_tree_confirmed(self):
        return self._get_action('rnet_inventory.action_picking_tree_confirmed')

    @api.multi
    def get_stock_picking_action_picking_type(self):
        return self._get_action('rnet_inventory.stock_picking_action_picking_type')



