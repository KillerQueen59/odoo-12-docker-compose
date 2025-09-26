# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class ApprovalBanner(http.Controller):
    """
    Controller to fetch and render the approval banner for the
    Project Management tree view.
    """

    def _get_approval_counts(self):
        """
        Fetches the counts for all relevant approval types for the current user
        using hardcoded domains.
        """
        uid = request.uid
        env = request.env
        # counts = {
        #     'cvr': env['hr.expense.sheet'].search_count([
        #         ('state', 'in', ['submit']),
        #         '|', ('project_manager_id.user_id', '=', uid),
        #         ('site_manager_id.user_id', '=', uid)
        #     ]),
        #     'bar': env['hr.expense.advance'].search_count([
        #         ('state', 'in', ['submitted']),
        #         '|', ('project_manager.user_id', '=', uid),
        #         ('site_manager.user_id', '=', uid)
        #     ]),
        #     'po': env['purchase.order'].search_count([
        #         ('state', 'in', ['pm_approval']),
        #         ('project.project_manager.user_id', '=', uid)
        #     ]),
        #     'pr': env['material.purchase.requisition'].search_count([
        #         ('state', 'in', ['dept_confirm']),
        #         ('requisiton_responsible_id.user_id', '=', uid)
        #     ]),
        #     'receipt_asset': env['stock.picking'].search_count([
        #         ('picking_type_id.name', 'like', 'Receipt%'),
        #         ('state', 'in', ['waiting']),
        #         ('show_asset_menu', '=', True),
        #         '|', ('gut_approved_by.user_id', '=', uid),
        #         ('project.project_manager.user_id', 'in', [uid])
        #     ]),
        #     'receipt_inventory': env['stock.picking'].search_count([
        #         ('picking_type_id.name', 'like', 'Receipt%'),
        #         ('state', 'in', ['waiting']),
        #         ('show_asset_menu', '=', False),
        #         '|', ('gut_approved_by.user_id', '=', uid),
        #         ('project.project_manager.user_id', 'in', [uid])
        #     ]),
        #      'takeout_asset': env['stock.picking'].search_count([
        #         ('picking_type_id.name', 'like', 'Take Out%'),
        #         ('state', 'in', ['waiting']),
        #         ('show_asset_menu', '=', True),
        #         '|', ('gut_approved_by.user_id', '=', uid),
        #         ('project.project_manager.user_id', 'in', [uid])
        #     ]),
        #     'takeout_inventory': env['stock.picking'].search_count([
        #         ('picking_type_id.name', 'like', 'Take Out%'),
        #         ('state', 'in', ['waiting']),
        #         ('show_asset_menu', '=', False),
        #         '|', ('gut_approved_by.user_id', '=', uid),
        #         ('project.project_manager.user_id', 'in', [uid])
        #     ]),
        # }
        counts = []
        _logger.info("Approval counts for user %s: %s", uid, counts)
        return counts
        
    @http.route('/project_management/approval_banner', type='json', auth='user')
    def approval_banner(self):
        return {}
        # """
        # Endpoint for the banner_route.
        # """
        # approval_counts = self._get_approval_counts()
        #
        # if not any(approval_counts.values()):
        #     return {}
        #
        # return {
        #     'html': request.env.ref('rnet_project_management.approval_banner_template').render({
        #         'approval_counts': approval_counts,
        #     })
        # }
