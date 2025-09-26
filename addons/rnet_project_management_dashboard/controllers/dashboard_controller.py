# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class ApprovalBannerController(http.Controller):

    def _get_approval_count(self, model_name, domain):
        """ Helper to safely count records for the current user. """
        if model_name not in request.env:
            _logger.warning("Approval Banner: Model '%s' not found. Is the module installed?", model_name)
            return 0
        
        Model = request.env[model_name]
        if not Model.check_access_rights('read', raise_exception=False):
             _logger.warning("User %s does not have read access for model '%s'. Skipping count.", request.env.user.name, model_name)
             return 0
        
        try:
            return Model.search_count(domain)
        except Exception as e:
            _logger.error("Error counting approvals for model %s: %s", model_name, e)
            return 0

    @http.route('/pm_dashboard/approval_banner', type='json', auth='user')
    def get_approval_banner_data(self):
        """
        Provides the data for the approval banner using the specified domains.
        """
        uid = request.env.user.id
        
        # --- FIX: Using the exact domains you provided ---
        cvr_domain = [
            ('state', 'in', ['submit']),
            '|', ('project_manager_id.user_id', '=', uid),
            ('site_manager_id.user_id', '=', uid)
        ]
        bar_domain = [
            ('state', 'in', ['submitted']),
            '|', ('project_manager.user_id', '=', uid),
            ('site_manager.user_id', '=', uid)
        ]
        po_domain = [
            ('state', 'in', ['pm_approval']),
            ('project.project_manager.user_id', '=', uid)
        ]
        pr_domain = [
            ('state', 'in', ['dept_confirm']),
            ('requisiton_responsible_id.user_id', '=', uid)
        ]
        receipt_asset_domain = [
            ('picking_type_id.name', 'like', 'Receipt%'),
            ('state', 'in', ['waiting']),
            ('show_asset_menu', '=', True),
            '|', ('gut_approved_by.user_id', '=', uid),
            ('project.project_manager.user_id', 'in', [uid])
        ]
        receipt_inventory_domain = [
            ('picking_type_id.name', 'like', 'Receipt%'),
            ('state', 'in', ['waiting']),
            ('show_asset_menu', '=', False),
            '|', ('gut_approved_by.user_id', '=', uid),
            ('project.project_manager.user_id', 'in', [uid])
        ]

        approval_counts = {
            'cvr': self._get_approval_count('hr.expense.sheet', cvr_domain),
            'bar': self._get_approval_count('hr.expense.advance', bar_domain),
            'po': self._get_approval_count('purchase.order', po_domain),
            'pr': self._get_approval_count('material.purchase.requisition', pr_domain),
            'receipt_asset': self._get_approval_count('stock.picking', receipt_asset_domain),
            'receipt_inventory': self._get_approval_count('stock.picking', receipt_inventory_domain),
        }

        html = request.env.ref('rnet_project_management_dashboard.approval_banner_template').render({
            'approval_counts': approval_counts
        })

        return {'html': html}