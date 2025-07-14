import math

from odoo.exceptions import UserError
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime, date 
from collections import defaultdict
import hashlib
import json

import logging

_logger = logging.getLogger(__name__)

class ProjectProgress(models.Model):
    _name = 'project.progress.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin'] 

    name = fields.Many2one('project.project', string='Project', track_visibility='onchange')
    seq = fields.Char(string='No', compute='_compute_seq', store=True)
    revision_date = fields.Date("Revision Date", readonly=True)
    show_experience_note = fields.Boolean(string="Show Experience Note", default=False)

    project_manager = fields.Many2one('hr.employee', string='Project Manager', compute='_compute_project_manager', store=True)
    
    project_plan_curve_line = fields.One2many(
    'project.plan.curve', 'plan_plan_curve_id', string='Project Plan Curve', track_visibility='onchange'
    )
    project_plan_cashout_line = fields.One2many(
        'project.plan.cashout', 'plan_plan_cashout_id', string='Project Plan Cash Out', store=True, track_visibility='onchange'
    )
    project_plan_cashin_line = fields.One2many(
        'project.plan.cashin', 'plan_plan_cashin_id', string='Project Plan Cash In', track_visibility='onchange'
    )
    project_plan_invoice_line = fields.One2many(
        'project.plan.invoice', 'plan_plan_invoice_id', string='Project Plan Invoice', track_visibility='onchange'
    )
    project_plan_manhour_line = fields.One2many(
        'project.plan.manhour', 'plan_plan_manhour_id', string='Project Plan Manhour', track_visibility='onchange'
    )
    project_actual_curve_line = fields.One2many(
        'project.actual.curve', 'plan_actual_curve_id', string='Project Actual Curve', track_visibility='onchange'
    )
    project_actual_cashout_line = fields.One2many(
        'project.actual.cashout', 'actual_cashout_line_id', string='Project Actual Cashout', track_visibility='onchange'
    )
    project_estimated_cashout_line = fields.One2many(
        'project.estimated.cashout', 'estimated_cashout_line_id', string='Project Estimated Cashout', track_visibility='onchange'
    )
    project_actual_cost_line = fields.One2many(
        'project.actual.cost', 'actual_cost_line_id', string='Project Actual Cost', track_visibility='onchange'
    )
    project_actual_invoice_line = fields.One2many(
        'project.actual.invoice', 'actual_invoice_line_id', string='Project Actual Invoice', track_visibility='onchange'
    )
    project_actual_cashin_line = fields.One2many(
        'project.actual.cashin', 'actual_cashin_line_id', string='Project Actual Cash In', track_visibility='onchange'
    )
    project_actual_manhour_line = fields.One2many(
        'project.actual.manhour', 'actual_manhour_line_id', string='Project Actual Manhour In', track_visibility='onchange'
    )
    refresh_onchange_actual_value = fields.Datetime(
        string="Update Actual Value??", track_visibility='onchange'
    )
    project_actual_plan_curve_line = fields.One2many(
        'project.actual.plan.curve', 'actual_curve_plan_line_id', string='Project Actual Curve', track_visibility='onchange'
    )
    project_actual_plan_cashout_line = fields.One2many(
        'project.actual.plan.cashout', 'actual_cashout_plan_line_id', string='Project Actual Cashout', track_visibility='onchange'
    )
    project_actual_plan_cashin_line = fields.One2many(
        'project.actual.plan.cashin', 'actual_cashin_plan_line_id', string='Project Actual Cashin', track_visibility='onchange'
    )
    project_actual_plan_invoice_line = fields.One2many(
        'project.actual.plan.invoice', 'actual_invoice_plan_line_id', string='Project Actual Invoice', track_visibility='onchange'
    )
    project_actual_plan_manhour_line = fields.One2many(
        'project.actual.plan.manhour', 'actual_manhour_plan_line_id', string='Project Actual Manhour', track_visibility='onchange'
    )

    # expense_sheet_amount = fields.Integer(compute='_get_expense_sheet_amount', track_visibility='onchange')
    # expense_advance_count = fields.Integer(compute='_get_expense_advance_count', track_visibility='onchange')
    # expense_advance_amount = fields.Integer(compute='_get_expense_advance_amount', track_visibility='onchange')
    # purchase_order_amount = fields.Integer(compute='_get_purchase_order_amount', track_visibility='onchange')

    project_execution_experience_line = fields.One2many(
        'project.execution.experience', 'project_execution_experience_id', string='Project Execution Experience', track_visibility='onchange'
    )
    lesson_learned_line = fields.One2many(
        'project.lesson.learned', 'lesson_learned_id', string='Lesson Learned', track_visibility='onchange'
    )
    subcon_performance_service_line = fields.One2many(
        'project.subcon.performance.service', 'subcon_performance_service_id', string='Subcon Performance Service', track_visibility='onchange'
    )
    procurement_recommendation_line = fields.One2many(
        'project.procurement.recommendation', 'procurement_recommendation_id',
        string='Procurement/Logistic Recommendation', track_visibility='onchange'
    )

    project_pm = fields.Many2one(
        related='name.project_manager', string="Project Manager", store=True, track_visibility='onchange'
    )
    location = fields.Many2one(
        related='name.location', string="Project Location", store=True, track_visibility='onchange'
    )
    order_date = fields.Date(
        related='name.order_date', string="Order Date", store=True, track_visibility='onchange'
    )

    current_accum_plan_progress = fields.Float(
        string="Plan Prog. (%)", compute='_compute_current_accum_values', store=True, digits=(16, 2), track_visibility='onchange'
    )
    current_accum_actual_progress = fields.Float(
        string="Actual Prog. (%)", compute='_compute_current_accum_values', store=True, digits=(16, 2), track_visibility='onchange'
    )
    current_accum_plan_invoice = fields.Float(
        string="Plan Inv.", compute='_compute_current_accum_values', store=True, digits=(16, 2), track_visibility='onchange'
    )
    current_accum_actual_invoice = fields.Float(
        string="Actual Inv.", compute='_compute_current_accum_values', store=True, digits=(16, 2), track_visibility='onchange'
    )
    current_accum_plan_cash_out = fields.Float(
        string="Plan Cash Out", compute='_compute_current_accum_values', store=True, digits=(16, 2), track_visibility='onchange'
    )
    current_accum_actual_cash_out = fields.Float(
        string="Actual Cash Out", compute='_compute_current_accum_values', store=True, digits=(16, 2), track_visibility='onchange'
    )
    current_accum_plan_cash_in = fields.Float(
        string="Plan Cash In", compute='_compute_current_accum_values', store=True, digits=(16, 2), track_visibility='onchange'
    )
    current_accum_actual_cash_in = fields.Float(
        string="Actual Cash In", compute='_compute_current_accum_values', store=True, digits=(16, 2), track_visibility='onchange'
    )
    current_accum_plan_manhour = fields.Float(
        string="Plan MH", compute='_compute_current_accum_values', store=True, digits=(16, 0), track_visibility='onchange'
    )
    current_accum_actual_manhour = fields.Float(
        string="Actual MH", compute='_compute_current_accum_values', store=True, digits=(16, 0), track_visibility='onchange'
    )

    last_report_data_signature = fields.Char(string="Last Report Data Signature", readonly=True, copy=False)

    def toggle_notebook(self):
        for record in self:
            record.show_experience_note = not record.show_experience_note

    @api.depends('name')
    def _compute_seq(self):
        for record in self:
            record.seq = record.name.seq if record.name else ''

    @api.depends('name')
    def _compute_project_manager(self):
        for record in self:
            record.project_manager = record.name.project_manager if record.name else None
    
    # trigger untuk onchange update actual value
    def action_update_actual_value(self):
        _logger.info("action_update_actual_value: Starting for PP IDs: %s", self.ids)
        for record in self: # Process record by record, self is usually one record from button context
            _logger.info("  Processing action_update_actual_value for PP ID: %s (Project: %s)", 
                         record.id, record.name.name if record.name else "N/A")
            self.ensure_one() # Add this at the top of action_update_actual_value
            # Trigger onchange methods by writing to 'refresh_onchange_actual_value'
            # This is the mechanism your original code used to make the onchange methods fire.
            # The onchange methods themselves will modify the record's O2M actual lines.
            record.write({'refresh_onchange_actual_value': fields.Datetime.now()})
            
            # The write above should have triggered the @api.depends('refresh_onchange_actual_value')
            # on your onchange_... methods.
            # If your onchange methods are NOT standard Odoo onchanges but regular methods
            # that you intend to call sequentially, then call them directly:

            _logger.info("  PP ID %s: Calling onchange methods to update direct actual and actual_plan lines...", record.id)
            
            # Methods to update direct 'project_actual_...' lines
            if hasattr(record, 'onchange_estimated_cash_out'):
                _logger.debug("    Calling onchange_estimated_cash_out for PP ID %s", record.id)
                record.onchange_estimated_cash_out()
            if hasattr(record, 'onchange_actual_cashout'):
                _logger.debug("    Calling onchange_actual_cashout for PP ID %s", record.id)
                record.onchange_actual_cashout()
            if hasattr(record, 'onchange_actual_cost'):
                _logger.debug("    Calling onchange_actual_cost for PP ID %s", record.id)
                record.onchange_actual_cost()
            if hasattr(record, 'onchange_actual_invoice'):
                _logger.debug("    Calling onchange_actual_invoice for PP ID %s", record.id)
                record.onchange_actual_invoice()
            if hasattr(record, 'onchange_actual_cashin'):
                _logger.debug("    Calling onchange_actual_cashin for PP ID %s", record.id)
                record.onchange_actual_cashin()
            if hasattr(record, 'onchange_actual_manhour'):
                _logger.debug("    Calling onchange_actual_manhour for PP ID %s", record.id)
                record.onchange_actual_manhour()
            
            # Methods to update chart-specific 'project_actual_plan_...' lines
            # These lines combine actuals (just fetched) and plans for chart displays.
            # If these project_actual_plan_... lines are also inputs to your
            # _get_current_report_data_signature, ensure they are up-to-date here.
            if hasattr(record, 'onchange_actual_plan_curve'): # Assuming this one exists too, based on pattern
                _logger.debug("    Calling onchange_actual_plan_curve for PP ID %s", record.id)
                record.onchange_actual_plan_curve() # You might have this for S-curve chart
            if hasattr(record, 'onchange_actual_plan_cashout'):
                _logger.debug("    Calling onchange_actual_plan_cashout for PP ID %s", record.id)
                record.onchange_actual_plan_cashout()
            if hasattr(record, 'onchange_actual_plan_invoice'):
                _logger.debug("    Calling onchange_actual_plan_invoice for PP ID %s", record.id)
                record.onchange_actual_plan_invoice()
            if hasattr(record, 'onchange_actual_plan_cashin'):
                _logger.debug("    Calling onchange_actual_plan_cashin for PP ID %s", record.id)
                record.onchange_actual_plan_cashin()
            if hasattr(record, 'onchange_actual_plan_manhour'):
                _logger.debug("    Calling onchange_actual_plan_manhour for PP ID %s", record.id)
                record.onchange_actual_plan_manhour()

            _logger.info("  PP ID %s: Onchange methods completed. Calling generate_report_data...", record.id)
            if hasattr(record, 'generate_report_data'):
                record.generate_report_data() 
            else:
                _logger.warning("  Method 'generate_report_data' not found for PP ID %s. Intermediary reports and stored tree view fields may be stale.", record.id)
        
        _logger.info("action_update_actual_value: Completed for PP IDs: %s", self.ids)
        return True
    
    # get value Estimated Cost
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_estimated_cash_out(self):
        for rec in self:
            project_estimated_cashout_line = self.get_actual_estimated_lines()
            actual_estimated_lines = rec.project_estimated_cashout_line.browse([])
            for r in project_estimated_cashout_line:
                actual_estimated_lines += actual_estimated_lines.new(r)
            rec.project_estimated_cashout_line = actual_estimated_lines

            return

    # get list Estimated Cashout form  Purchase Order
    @api.model
    def get_actual_estimated_lines(self):
        res = [] 
        # for rec in self:
        #     # compute list BAR
        #     for expense in self.env['hr.expense.advance'].search(['&',('project_id', '=', rec.name.id),('state', 'in', ['partial','paid']),]):
        #         expenses = {
        #                 'code': 'BAR',
        #                 'name': expense.name,
        #                 'created_date': expense.requested_date,
        #                 'amount': expense.amount_total,
        #                 'project': expense.project_id,
        #             }
        #         res.append(expenses)
        #
        # #------DISABLE------
        #     # compute list PR
        #     # for pr in self.env['material.purchase.requisition'].search([
        #     #     ('project', '=', rec.name.id),
        #     #     ('state', 'in', ['approve','partial_process']),
        #     #     ('purchase_count', '=', 0)
        #     # ]):
        #     #     requisitions = {
        #     #             'code': 'PR',
        #     #             'created_date': pr.request_date,
        #     #             'name': pr.name,
        #     #             'amount': pr.total_est_price,
        #     #             'project': pr.project,
        #     #             }
        #     #     res.append(requisitions)
        #
        #     # compute list Purchase
        #     for purchase in self.env['purchase.order'].search(['&',('project', '=', rec.name.id),('state', 'in', ['purchase']),]):
        #         date_new = purchase.date_planned.date()
        #         purchases = {
        #                 'code': 'PO',
        #                 'created_date': date_new,
        #                 'name': purchase.name,
        #                 'amount': purchase.amount_untaxed,
        #                 'project': purchase.project,
        #                 }
        #         res.append(purchases)

        return res   

# get value Cost
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_cost(self):
        for rec in self:
            project_actual_cost_line = self.get_actual_cost_lines()
            actual_cost_lines = rec.project_actual_cost_line.browse([])
            for r in project_actual_cost_line:
                actual_cost_lines += actual_cost_lines.new(r)
            rec.project_actual_cost_line = actual_cost_lines

            return

    # get list Cost form CVR & Purchase Order
    @api.model
    def get_actual_cost_lines(self):
        res = [] 
        # for rec in self:
        #
        #     # --- compute list CVR Costs (Searching hr.expense.sheet, summing lines) ---
        #     current_project = rec.name
        #     if not current_project:
        #         _logger.warning("No project linked to current record 'rec' (ID: %s). Skipping CVR cost calculation.", rec.id)
        #         # continue # Or handle differently
        #     else:
        #         # 1. Search Expense Sheets that contain lines for the specific project
        #         #    and are in an approved/posted/done state.
        #         expense_sheets_domain = [
        #             ('expense_line_ids.project', '=', current_project.id), # Project on Expense Line
        #             ('state', 'in', ['approve', 'post', 'done']) # Adjust states based on your workflow when cost is considered "actual"
        #         ]
        #
        #         try:
        #             # Search the sheets matching the criteria
        #             expense_sheets = self.env['hr.expense.sheet'].search(expense_sheets_domain)
        #         except Exception as e:
        #             _logger.error("Error searching hr.expense.sheet for project %s: %s", current_project.id, e)
        #             expense_sheets = self.env['hr.expense.sheet'] # Ensure empty recordset
        #
        #
        #         # 2. Iterate through found sheets and sum costs from relevant lines FOR THIS PROJECT
        #         for sheet in expense_sheets:
        #             project_cost_from_sheet = 0.0
        #
        #             # Filter expense lines WITHIN this sheet for the CURRENT project
        #             relevant_lines = sheet.expense_line_ids.filtered(
        #                 lambda line: line.project == current_project and line.total_amount
        #             )
        #
        #             # Sum the total_amount from the filtered lines
        #             project_cost_from_sheet = sum(line.total_amount or 0.0 for line in relevant_lines)
        #
        #             # 3. Append data to results list only if cost > 0 for this project in this sheet
        #             if project_cost_from_sheet > 0:
        #                 description = "\n".join({line.name for line in sheet.expense_line_ids if line.name})
        #                 # Retrieve attachments linked to the expense sheet
        #                 attachments = self.env['ir.attachment'].search([
        #                     ('res_model', '=', 'hr.expense.sheet'),
        #                     ('res_id', '=', sheet.id)
        #                 ])
        #
        #                 # Store only attachment IDs or names (adjust based on need)
        #                 attachment_list = [att.id for att in attachments]
        #                 cvr_data = {
        #                         'code': 'CVR', # Cash Voucher Report
        #                         'name': sheet.name, # Use Sheet Name/Number
        #                         'created_date': sheet.created_date,
        #                         'amount': project_cost_from_sheet, # <<< Use calculated sum from lines
        #                         'amount_company_signed': project_cost_from_sheet, # Cost is positive debit nature
        #                         'currency_id': sheet.currency_id, # <<< Use currency from the sheet header
        #                         'project': current_project.id, # Pass project ID
        #                         'expense_sheet_id': sheet.id, # Add sheet ID for reference
        #                         'move_id': sheet.account_move_id.id if sheet.account_move_id else None, # Add move ID if available
        #                         'description': description,
        #                         'attachments': attachment_list,
        #
        #                     }
        #                 # Ensure 'res' list exists and append
        #                 if 'res' in locals() and isinstance(res, list): res.append(cvr_data)
        #                 elif 'res' in globals() and isinstance(res, list): res.append(cvr_data)
        #                 else: _logger.error("'res' list not found. Cannot append CVR data %s.", sheet.id)
        #                 _logger.debug("--> Appended CVR Data: %s", cvr_data)
        #
        #     # --- Compute list Project Costs from Goods Receipt Journal Entries (Per Move) ---
        #     current_project = rec.name
        #     if not current_project:
        #         _logger.warning("No project linked to current record 'rec' (ID: %s). Skipping Picking cost calculation.", rec.id)
        #         # continue # Or handle differently
        #     else:
        #         # 1. Find Account Moves linked to a Picking AND the Project
        #         picking_moves_domain = [
        #             ('project', '=', current_project.id), # Filter by Project on Move Header
        #             ('picking_id', '!=', False),         # Must be linked to a Picking
        #             ('state', '=', 'posted')             # Must be posted
        #             # Optional: ('is_cost_project', '=', True) # If you want to combine flags
        #         ]
        #         try:
        #             picking_moves = self.env['account.move'].search(picking_moves_domain)
        #             _logger.info("Found %s Account Moves linked to Pickings for project %s: %s",
        #                          len(picking_moves), current_project.id, picking_moves.ids)
        #         except Exception as e:
        #             _logger.error("Error searching account.move for picking JEs (Project %s): %s", current_project.id, e)
        #             picking_moves = self.env['account.move'] # Ensure empty recordset
        #
        #         # 2. Get Expense/Cost Account Type IDs
        #         expense_type_ids = []
        #         try:
        #             expense_type_ids_model = self.env['account.move.line'] # Or account.move
        #             if hasattr(expense_type_ids_model, '_get_expense_account_type_ids'):
        #                 expense_type_ids = expense_type_ids_model._get_expense_account_type_ids()
        #             if not expense_type_ids: _logger.warning("Expense types list empty.")
        #         except Exception as e: _logger.error("Error getting expense types: %s", e); expense_type_ids = []
        #
        #         # 3. Iterate through EACH found Picking Move and sum ITS relevant debit lines
        #         for move in picking_moves:
        #             move_project_cost_amount = 0.0 # Cost for *this* move for *this* project
        #             if expense_type_ids:
        #                 # Filter lines within THIS move by expense type AND matching THIS project
        #                 cost_lines = move.line_ids.filtered(
        #                     lambda line: line.project == current_project and \
        #                                  line.debit > 0 and \
        #                                  line.account_id.user_type_id.id in expense_type_ids
        #                 )
        #                 move_project_cost_amount = sum(line.debit or 0.0 for line in cost_lines)
        #             else:
        #                  _logger.warning("Cannot calculate cost for Picking Move ID: %s because expense types are unknown.", move.id)
        #
        #             # 4. Append data to results list FOR EACH MOVE if calculated cost > 0
        #             if move_project_cost_amount > 0:
        #                 cost_data = {
        #                     'code': 'Journal GR', # Code for Goods Receipt Note JE
        #                     'name': move.name,
        #                     'created_date': move.date,
        #                     'amount': move_project_cost_amount, # Cost specific to THIS move & THIS project
        #                     'amount_company_signed': move_project_cost_amount,
        #                     'currency_id': move.company_id.currency_id,
        #                     'project': current_project.id, # Pass Project ID
        #                     'move_id': move.id,
        #                     'picking_id': move.picking_id.id if move.picking_id else None, # Pass Picking ID
        #                 }
        #                 # Append to res list safely
        #                 if 'res' in locals() and isinstance(res, list): res.append(cost_data)
        #                 elif 'res' in globals() and isinstance(res, list): res.append(cost_data)
        #                 else: _logger.error("'res' list not found...")
        #
        #
        #     # --- compute list Project Cost Journal Entries (Exclude Docs, Based on Move Flag, Sum SPECIFIC Project Lines) ---
        #     current_project = rec.name
        #     if not current_project:
        #         _logger.warning("No project linked to current record 'rec' (ID: %s). Skipping cost calculation.", rec.id)
        #         # continue # Or handle differently
        #     else:
        #         # 1. Find IDs of relevant MOVES first (based on flag, state, exclusions, but NOT header project)
        #         relevant_move_ids = []
        #         try:
        #             move_domain = [
        #                 # ('project', '=', current_project.id), # <<< REMOVED HEADER PROJECT FILTER
        #                 ('is_cost_project', '=', True),         # Flag on move header IS required
        #                 ('state', '=', 'posted'),
        #                 ('invoice_id', '=', False),
        #                 ('picking_id', '=', False),
        #                 ('purchase_id', '=', False),
        #             ]
        #             relevant_moves = self.env['account.move'].search(move_domain)
        #             relevant_move_ids = relevant_moves.ids
        #         except Exception as e:
        #             _logger.error("Error searching account.move: %s", e)
        #
        #         # Proceed only if potentially relevant moves were found
        #         if relevant_move_ids:
        #             # 2. Get Expense Account Type IDs
        #             # ... (Get expense_type_ids as before) ...
        #             expense_type_ids = []
        #             try:
        #                 expense_type_ids_model = self.env['account.move.line']
        #                 if hasattr(expense_type_ids_model, '_get_expense_account_type_ids'):
        #                     expense_type_ids = expense_type_ids_model._get_expense_account_type_ids()
        #                 if not expense_type_ids: _logger.warning("Expense types list empty.")
        #             except Exception as e: _logger.error("Error getting expense types: %s", e); expense_type_ids = []
        #
        #
        #             # 3. Search account.move.line, filtering by the found move IDs AND line criteria (including project)
        #             cost_lines = self.env['account.move.line'] # Initialize empty
        #             if expense_type_ids:
        #                 line_domain = [
        #                     ('move_id', 'in', relevant_move_ids), # <<< Lines must belong to the flagged moves
        #                     ('project', '=', current_project.id), # <<< Filter lines for THIS project
        #                     ('debit', '>', 0),
        #                     ('account_id.user_type_id', 'in', expense_type_ids)
        #                 ]
        #                 _logger.info("Searching account.move.line for project %s within relevant moves - domain: %s", current_project.id, line_domain)
        #                 try:
        #                     cost_lines = self.env['account.move.line'].search(line_domain)
        #                 except Exception as e:
        #                     _logger.error("Error searching account.move.line: %s", e)
        #                     cost_lines = self.env['account.move.line']
        #             else:
        #                  _logger.warning("Skipping line search for project %s as expense types are unknown.", current_project.id)
        #
        #             # 4. Iterate through EACH found cost line and append its details
        #             for line in cost_lines:
        #                 line_cost_amount = line.debit or 0.0
        #                 cost_data = {
        #                     'code': 'Project Cost Journal Entries',
        #                     'name': line.name or line.move_id.name or line.move_id.ref,
        #                     'created_date': line.date,
        #                     'amount': line_cost_amount,
        #                     'amount_company_signed': line_cost_amount,
        #                     'currency_id': line.company_currency_id,
        #                     'project': current_project.id, # Project ID
        #                 }
        #                 # ... (Append to res list safely) ...
        #                 if 'res' in locals() and isinstance(res, list): res.append(cost_data)
        #                 elif 'res' in globals() and isinstance(res, list): res.append(cost_data)
        #                 else: _logger.error("'res' list not found...")
        #
        #         else: # No moves matched the header criteria (is_cost_project=True, posted, no doc links)
        #              _logger.info("No account moves found matching header criteria (is_cost_project=True, etc.).")

        return res   
    
    # get value actual cashout
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_cashout(self):
        for rec in self:
            project_actual_cashout_line = self.get_actual_cashout_lines()
            actual_cashout_lines = rec.project_actual_cashout_line.browse([])
            for r in project_actual_cashout_line:
                actual_cashout_lines += actual_cashout_lines.new(r)
            rec.project_actual_cashout_line = actual_cashout_lines

        return
        
    # get list actual cashout form CVR & Purchase Invoice & BAR Payment
    @api.model
    def get_actual_cashout_lines(self):
        res = [] 
        for rec in self:

            # compute list Purchase paid/ account payment
            for payment in self.env['account.payment'].search(['&','&',('project', '=', rec.name.id),('state','not in', ['cancelled','draft']),('payment_type', '=', 'outbound'),]):
                payments = {
                        'code': 'Purchase Invoice payment',
                        'payment_date': payment.payment_date,
                        'name': payment.name,
                        'amount': payment.amount_untaxed_signed,
                        'project': payment.project,
                    }
                res.append(payments)

            # compute list BAR paid
            for payment in self.env['account.payment'].search(['&','&',('project', '=', rec.name.id),('state','not in', ['cancelled','draft']),('payment_type', '=', 'transfer'),]):
                payments = {
                        'code': 'BAR - ' + payment.communication,
                        'payment_date': payment.payment_date,
                        'name': payment.name,
                        'amount': payment.amount_idr_curr,
                        'project': payment.project,
                    }
                res.append(payments)

        return res   

    # get value actual Invoice
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_invoice(self):
        for rec in self:
            project_actual_invoice_line = self.get_actual_invoice_lines()
            actual_invoice_lines = rec.project_actual_invoice_line.browse([])
            for r in project_actual_invoice_line:
                actual_invoice_lines += actual_invoice_lines.new(r)
            rec.project_actual_invoice_line = actual_invoice_lines

        return
        
    # get list actual invoice form Account Invoice
    @api.model
    def get_actual_invoice_lines(self):
        res = [] 
        for rec in self:
            # compute list Invoice
            for inv in self.env['account.invoice'].search(['&','&',('project', '=', rec.name.id),('type', '=', 'out_invoice'),('state', 'in', ['open']),]):
                invoices = {
                        'name': inv.number,
                        'created_date': inv.date_invoice,
                        'amount': inv.amount_untaxed_signed,
                        'amount_company_signed' : inv.amount_untaxed_signed,
                        'currency_id': inv.currency_id,
                        'project': inv.project
                    }
                res.append(invoices)

        return res  


    # get value actual Actual Cash In
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_cashin(self):
        for rec in self:
            project_actual_cashin_line = self.get_actual_cashin_lines()
            actual_cashin_lines = rec.project_actual_cashin_line.browse([])
            for r in project_actual_cashin_line:
                actual_cashin_lines += actual_cashin_lines.new(r)
            rec.project_actual_cashin_line = actual_cashin_lines

        return
        
    # get list actual Cash In form account payment
    @api.model
    def get_actual_cashin_lines(self):
        res = [] 
        for rec in self:
            # compute list Invoice
            for pay in self.env['account.payment'].search(['&','&',('invoice_ids.project', '=', rec.name.id),('payment_type', '=', 'inbound'),('state', '=', 'posted'),]):
                invoices = {
                        'name': pay.name,
                        'payment_date': pay.payment_date,
                        'amount': pay.amount_untaxed_signed,
                        'project': pay.invoice_ids.project,
                    }
                res.append(invoices)

        return res 


    # get value actual Manhour
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_manhour(self):
        for rec in self:
            project_actual_manhour_lines = rec.get_actual_manhour_lines()
            actual_manhour_lines = self.env['project.actual.manhour'].browse()

            for project, months in project_actual_manhour_lines.items():
                for year_month, values in months.items():
                    actual_manhour_lines |= actual_manhour_lines.new({
                        'name': values.get('name'),
                        'date_from': values.get('date_from'),
                        'date_to': values.get('date_to'),
                        'total': values.get('total'),
                        'project': project,
                        'month': year_month,
                    })

            rec.project_actual_manhour_line = actual_manhour_lines
        return


    @api.model
    def get_actual_manhour_lines(self):
        result = {}
        for rec in self:
            # Compute list of manhour lines grouped by project and month
            timesheets = self.env['hr_timesheet.sheet'].search([('attendances_ids.project', '=', rec.name.id)])
            for ts in timesheets:
                for att in ts.attendances_ids:
                    if att.project and att.project.id == rec.name.id:  # Ensure correct project
                        # Extract year and month from check_in date
                        check_in_date = fields.Date.from_string(att.check_in)
                        year_month = "{}-{:02d}".format(check_in_date.year, check_in_date.month)

                        total_hours = att.gut_normal_hours + att.gut_class1 + att.gut_class2 + att.gut_class3 + att.gut_class4

                        if att.project.id not in result:
                            result[att.project.id] = {}

                        if year_month not in result[att.project.id]:
                            result[att.project.id][year_month] = {
                                'name': ts.name,
                                'date_from': ts.date_start,
                                'date_to': ts.date_end,
                                'total': 0.0,
                                'project': att.project.id,
                                'month': year_month,
                            }

                        # Aggregate hours by project and month
                        result[att.project.id][year_month]['total'] += total_hours
        return result


   # get value actual and plan cash out
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_plan_cashout(self):
        for rec in self:
            project_actual_plan_cashout_line = self.get_actual_plan_cashout_lines()
            actual_plan_cashout_lines = rec.project_actual_plan_cashout_line.browse([])
            for r in project_actual_plan_cashout_line:
                actual_plan_cashout_lines += actual_plan_cashout_lines.new(r)
            rec.project_actual_plan_cashout_line = actual_plan_cashout_lines

        return
        
    @api.model
    def get_actual_plan_curve_lines(self):
        res = []
        for rec in self:

            # compute list actual curve
            for actual in self.env['project.actual.curve'].search([('plan_actual_curve_id', '=', rec.id)]):
                actuals = {
                    'code': 'Actual',
                    'name': actual.seq,
                    'payment_date': actual.date,
                    'amount': actual.name,
                    'project': actual.plan_actual_curve_id.name,
                }
                res.append(actuals)

            # compute list plan curve
            for plan in self.env['project.plan.curve'].search([('plan_plan_curve_id', '=', rec.id)]):
                plans = {
                    'code': 'Plan',
                    'name': plan.seq,
                    'payment_date': plan.date,
                    'amount': plan.name,
                    'project': plan.plan_plan_curve_id.name,
                }
                res.append(plans)
        return res

    # get list actual and plan cashout
    @api.model
    def get_actual_plan_cashout_lines(self):
        res = [] 
        for rec in self:

            # compute list actual cashout
            for actual in self.env['project.actual.cashout'].search([('actual_cashout_line_id', '=', rec.id)]):
                actuals = {
                        'code': 'Actual',
                        'name': actual.name,
                        'payment_date': actual.payment_date,
                        'amount': actual.amount,
                        'project': actual.project,
                    }
                res.append(actuals)


            # compute list plan cashout
            for plan in self.env['project.plan.cashout'].search([('plan_plan_cashout_id', '=', rec.id)]):
                plans = {
                        'code': 'Plan',
                        'name': plan.seq,
                        'payment_date': plan.date,
                        'amount': plan.name,
                        'project': plan.plan_plan_cashout_id.name,
                    }
                res.append(plans)
        return res   

    @api.multi
    def open_actual_plan_cashout_chart(self):
            for rec in self:
                return {
                    'name': _('Actual and Plan Cashout'),
                    'view_type': 'form',
                    'view_mode': 'graph,pivot',
                    'res_model': 'project.actual.plan.cashout',
                    'view_id':  False,
                    'type': 'ir.actions.act_window',
                    'option': {'no_create_edit': True},
                    'domain': [('project.id', '=', rec.name.id)],
                }

    @api.multi
    def open_actual_plan_curve_chart(self):
        for rec in self:
            project_actual_plan_curve_line = self.get_actual_plan_curve_lines()
            actual_plan_curve_lines = rec.project_actual_plan_curve_line.browse([])
            for r in project_actual_plan_curve_line:
                actual_plan_curve_lines += actual_plan_curve_lines.new(r)
            rec.project_actual_plan_curve_line = actual_plan_curve_lines
            return {
                'name': _('Actual and Plan Curve'),
                'view_type': 'form',
                'view_mode': 'graph,pivot',
                'res_model': 'project.actual.plan.curve',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'option': {'no_create_edit': True},
                'domain': [('project.id', '=', rec.name.id)],
            }

   # get value actual and plan cash in
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_plan_cashin(self):
        for rec in self:
            project_actual_plan_cashin_line = self.get_actual_plan_cashin_lines()
            actual_plan_cashin_lines = rec.project_actual_plan_cashin_line.browse([])
            for r in project_actual_plan_cashin_line:
                actual_plan_cashin_lines += actual_plan_cashin_lines.new(r)
            rec.project_actual_plan_cashin_line = actual_plan_cashin_lines

        return

    # get list actual and plan cashin 
    @api.model
    def get_actual_plan_cashin_lines(self):
        res = [] 
        for rec in self:

            # compute list actual cashin
            for actual in self.env['project.actual.cashin'].search([('actual_cashin_line_id', '=', rec.id)]):
                actuals = {
                        'code': 'Actual',
                        'name': actual.name,
                        'payment_date': actual.payment_date,
                        'amount': actual.amount,
                        'project': actual.project,
                    }
                res.append(actuals)


            # compute list plan cashin
            for plan in self.env['project.plan.cashin'].search([('plan_plan_cashin_id', '=', rec.id)]):
                plans = {
                        'code': 'Plan',
                        'name': plan.seq,
                        'payment_date': plan.date,
                        'amount': plan.name,
                        'project': plan.plan_plan_cashin_id.name,
                    }
                res.append(plans)
        return res   

    @api.multi
    def open_actual_plan_cashin_chart(self):
            for rec in self:
                return {
                    'name': _('Actual and Plan cashin'),
                    'view_type': 'form',
                    'view_mode': 'graph,pivot',
                    'res_model': 'project.actual.plan.cashin',
                    'view_id':  False,
                    'type': 'ir.actions.act_window',
                    'option': {'no_create_edit': True},
                    'domain': [('project.id', '=', rec.name.id)],
                }           


   # get value actual and plan Invoice
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_plan_invoice(self):
        for rec in self:
            project_actual_plan_invoice_line = self.get_actual_plan_invoice_lines()
            actual_plan_invoice_lines = rec.project_actual_plan_invoice_line.browse([])
            for r in project_actual_plan_invoice_line:
                actual_plan_invoice_lines += actual_plan_invoice_lines.new(r)
            rec.project_actual_plan_invoice_line = actual_plan_invoice_lines

        return

   # get list actual and plan invoice 
    @api.model
    def get_actual_plan_invoice_lines(self):
        res = [] 
        for rec in self:

            # compute list actual invoice
            for actual in self.env['project.actual.invoice'].search([('actual_invoice_line_id', '=', rec.id)]):
                actuals = {
                        'code': 'Actual',
                        'name': actual.name,
                        'payment_date': actual.created_date,
                        'amount': actual.amount,
                        'project': actual.project,
                    }
                res.append(actuals)


            # compute list plan invoice
            for plan in self.env['project.plan.invoice'].search([('plan_plan_invoice_id', '=', rec.id)]):
                plans = {
                        'code': 'Plan',
                        'name': plan.seq,
                        'payment_date': plan.date,
                        'amount': plan.name,
                        'project': plan.plan_plan_invoice_id.name,
                    }
                res.append(plans)
        return res   

    @api.multi
    def open_actual_plan_invoice_chart(self):
            for rec in self:
                return {
                    'name': _('Actual and Plan invoice'),
                    'view_type': 'form',
                    'view_mode': 'graph,pivot',
                    'res_model': 'project.actual.plan.invoice',
                    'view_id':  False,
                    'type': 'ir.actions.act_window',
                    'option': {'no_create_edit': True},
                    'domain': [('project.id', '=', rec.name.id)],
                }


   # get value actual and plan manhour
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_plan_manhour(self):
        for rec in self:
            project_actual_plan_manhour_line = self.get_actual_plan_manhour_lines()
            actual_plan_manhour_lines = rec.project_actual_plan_manhour_line.browse([])
            for r in project_actual_plan_manhour_line:
                actual_plan_manhour_lines += actual_plan_manhour_lines.new(r)
            rec.project_actual_plan_manhour_line = actual_plan_manhour_lines

        return

    # get list actual and plan manhour 
    @api.model
    def get_actual_plan_manhour_lines(self):
        res = [] 
        for rec in self:
            for actual in self.env['project.actual.manhour'].search([('actual_manhour_line_id', '=', rec.id)], limit=1):
                    act = self.env['project.actual.manhour'].search([('actual_manhour_line_id', '=', rec.id)])
                    actuals = {
                            'code': 'Actual',
                            'name': actual.name,
                            'date': actual.date_from,
                            'total': sum(line.total for line in act),
                            'project': actual.project,
                        }
                    res.append(actuals)

            # compute list plan manhour
            for plan in self.env['project.plan.manhour'].search([('plan_plan_manhour_id', '=', rec.id)], limit=1):
                pln = self.env['project.plan.manhour'].search([('plan_plan_manhour_id', '=', rec.id)])
                plans = {
                        'code': 'Plan',
                        'name': plan.seq,
                        'date': plan.date,
                        'total': sum(line.name for line in pln),
                        'project': plan.plan_plan_manhour_id.name,
                    }
                res.append(plans)
        return res   

    @api.multi
    def open_actual_plan_manhour_chart(self):
            for rec in self:
                return {
                    'name': _('Actual and Plan manhour'),
                    'view_type': 'form',
                    'view_mode': 'graph,pivot',
                    'res_model': 'project.actual.plan.manhour',
                    'view_id':  False,
                    'type': 'ir.actions.act_window',
                    'option': {'no_create_edit': True},
                    'domain': [('project.id', '=', rec.name.id)],
                }

    @api.model
    def get_details(self):
        query = '''SELECT  COALESCE(SUM(out.name),0) as cashout, count(plan_plan_cashout_id)
                        FROM project_plan_cashout out
						LEFT JOIN project_progress_plan pp ON pp.id = out.plan_plan_cashout_id
                        WHERE plan_plan_cashout_id  = %s AND pp.active = 't' """ % (data.id)'''
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        cashout = []
        for record in data:
            cashout.append(record.get('cashout'))

        return {
            'cashout': cashout,
        }
         

    def _get_cashout(self):
        for task in self:
            if len(task.project_plan_cashout_line) > 0:
                for detail in self.get_details():
                    task.total_cashout = detail['cashout']
            task.total_cashout = 0.0

    # @api.multi
    # def onchange_actual_cashout(self):
    #     res = {
    #             'value': {
    #                 #delete old input lines
    #                 'project_actual_cashout_line': map(lambda x: (2, x,), self.project_actual_cashout_line.ids),
    #                 }
    #         }
    #     project_actual_cashout_line = self.get_actual_cashout_lines()
    #             # rec.update({
    #             # 'project_actual_cashout_line': project_actual_cashout_line
    #             # })
    #     res['value'].update({
    #                 'worked_days_line_ids': project_actual_cashout_line,
    #         })
    #     return res



# Revisi Project Plan
    @api.depends('current_revision_id', 'old_revision_ids')
    def _compute_has_old_revisions(self):
        for plan in self:
            if plan.old_revision_ids:
                plan.has_old_revisions = True

    @api.one
    @api.depends('old_revision_ids')
    def _compute_revision_count(self):
        self.revision_count = len(self.old_revision_ids)

    current_revision_id = fields.Many2one(
        comodel_name='project.progress.plan',
        string='Current revision',
        readonly=True,
        copy=True
    )
    old_revision_ids = fields.One2many(
        comodel_name='project.progress.plan',
        inverse_name='current_revision_id',
        string='Old revisions',
        readonly=True,
        context={'active_test': False}
    )
    revision_number = fields.Integer(
        string='Revision',
        copy=False,
        default=0
    )
    unrevisioned_seq = fields.Char(
        string='Original Plan Reference',
        copy=True,
        readonly=True,
    )
    active = fields.Boolean(
        default=True
    )
    has_old_revisions = fields.Boolean(
        compute='_compute_has_old_revisions')

    revision_count = fields.Integer(compute='_compute_revision_count')

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}

        return super(ProjectProgress, self).copy(default=default)

    def copy_revision_with_context(self):
        default_data = self.default_get([])
        new_rev_number = self.revision_number + 1
        default_data.update({
            'revision_number': new_rev_number,
            'unrevisioned_seq': self.seq,
            'seq': '%s(REV-%02d)' % (self.seq, new_rev_number),
            'revision_date' : date.today(),
            'old_revision_ids': [(4, self.id, False)],
        })

        actual_curve_line =  []
        for line in self.project_actual_curve_line:
                actual_curve_line.append([0, False,
                                    {   'seq' : line.seq,
                                        'name' : line.name,
                                        'date' : line.date,
                                    }])

        actual_cashin_line =  []
        for line in self.project_actual_cashin_line:
                actual_cashin_line.append([0, False, 
                                    {   'name' : line.name,
                                        'amount' : line.amount,
                                        'payment_date' : line.payment_date,
                                    }])
                                    
        actual_invoice_line =  []
        for line in self.project_actual_invoice_line:
                actual_invoice_line.append([0, False, 
                                    {   'name' : line.name,
                                        'amount' : line.amount,
                                        'amount_company_signed': line.amount_company_signed,
                                        'created_date' : line.created_date,
                                    }])

        actual_cashout_line =  []
        for line in self.project_actual_cashout_line:
                actual_cashout_line.append([0, False, 
                                    {   'name' : line.name,
                                        'code' : line.code,
                                        'amount' : line.amount,
                                        'payment_date' : line.payment_date,
                                        'project' : line.project.id,
                                    }])

        actual_manhour_line =  []
        for line in self.project_actual_manhour_line:
                actual_manhour_line.append([0, False,
                                    {   'name' : line.name,
                                        'total' : line.total,
                                        'date_from' : line.date_from,
                                        'date_to' : line.date_to,
                                        'month' : line.month,

                                    }])

        plan_curve_line =  []
        for line in self.project_plan_curve_line:
                plan_curve_line.append([0, False,
                                    {   'seq' : line.seq,
                                        'name' : line.name,
                                        'date' : line.date,
                                    }])
        plan_cashin_line =  []
        for line in self.project_plan_cashin_line:
                plan_cashin_line.append([0, False,
                                    {   'seq' : line.seq,
                                        'name' : line.name,
                                        'date' : line.date,
                                    }])

        plan_cashout_line =  []
        for line in self.project_plan_cashout_line:
                plan_cashout_line.append([0, False,
                                    {   'seq' : line.seq,
                                        'name' : line.name,
                                        'date' : line.date,
                                    }])
        plan_invoice_line =  []
        for line in self.project_plan_invoice_line:
                plan_invoice_line.append([0, False,
                                    {   'seq' : line.seq,
                                        'name' : line.name,
                                        'date' : line.date,
                                    }])

        plan_manhour_line =  []
        for line in self.project_plan_manhour_line:
                plan_manhour_line.append([0, False,
                                    {   'seq' : line.seq,
                                        'name' : line.name,
                                        'date' : line.date,
                                    }])

        estimated_cashout_line =  []
        for line in self.project_estimated_cashout_line:
                estimated_cashout_line.append([0, False, 
                                    {   'name' : line.name,
                                        'code' : line.code,
                                        'amount' : line.amount,
                                        'created_date' : line.created_date,
                                        'project' : line.project.id,
                                    }])
                
        actual_cost_line =  []
        for line in self.project_actual_cost_line:
                actual_cost_line.append([0, False, 
                                    {   'name' : line.name,
                                        'code' : line.code,
                                        'amount' : line.amount,
                                        'created_date' : line.created_date,
                                        'project' : line.project.id,
                                    }])

        default_data['project_actual_curve_line'] = actual_curve_line
        default_data['project_actual_cashin_line'] = actual_cashin_line
        default_data['project_actual_invoice_line'] = actual_invoice_line
        default_data['project_actual_cashout_line'] = actual_cashout_line
        default_data['project_actual_manhour_line'] = actual_manhour_line
        default_data['project_estimated_cashout_line'] = estimated_cashout_line
        default_data['project_actual_cost_line'] = actual_cost_line
        
        default_data['project_plan_curve_line'] = plan_curve_line
        default_data['project_plan_cashin_line'] = plan_cashin_line
        default_data['project_plan_cashout_line'] = plan_cashout_line
        default_data['project_plan_invoice_line'] = plan_invoice_line
        default_data['project_plan_manhour_line'] = plan_manhour_line

        new_revision = self.copy(default_data)
        self.old_revision_ids.write({
            'current_revision_id': new_revision.id,
        })
        self.write({'active': False,
            'current_revision_id': new_revision.id,
        })

        return new_revision

    @api.multi
    def create_revision(self):
        revision_ids = []
        # Looping over Project Progress records
        for project_progress_rec in self:
            # Calling  Copy method
            copied_progress_rec = project_progress_rec.copy_revision_with_context()

            msg = _('New revision created: %s') % copied_progress_rec.seq
            copied_progress_rec.message_post(body=msg)
            project_progress_rec.message_post(body=msg)

            revision_ids.append(copied_progress_rec.id)

        res = {
            'type': 'ir.actions.act_window',
            'name': _('Revisions'),
            'res_model': 'project.progress.plan',
            'domain': "[('id', 'in', %s)]" % revision_ids,
            'auto_search': True,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'target': 'current',
            'nodestroy': True,
        }

        # Returning the new Project Progress Plan view with new record.
        return res

    @api.multi
    def open_revision_list(self):
        if self.old_revision_ids:
            for rec in self:
                return {
                    'name': _('Revision History'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'project.progress.plan',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': ['&', ['current_revision_id', '=', rec.id], ['active', '=', False]],
                    'option': {'no_create_edit': True},
                }

    # statinfo  BAR & CVR di Project management
    # @api.multi
    # def _get_expense_sheet_count(self):
    #         res = self.env['hr.expense.sheet'].search_count(['&', ('project', '=', self.name.id), ('state', 'not in', ['draft', 'cancel', 'reject_control', 'reject_technical', 'reject_finance'])])
    #         self.expense_sheet_count = res or 0

    # @api.multi
    # @api.depends('expense_sheet_count')
    # def _get_expense_sheet_amount(self):
    #     data_obj = self.env['hr.expense.sheet'].search(['&', ('project', '=', self.name.id), ('state', 'not in', ['draft', 'cancel', 'reject_control', 'reject_technical', 'reject_finance'])])
    #     total_amount = sum(data_obj.mapped('total_amount'))
    #     for record in self:
    #         record.expense_sheet_amount = total_amount or False

    # @api.multi
    # def _get_expense_advance_count(self):
    #         res = self.env['hr.expense.advance'].search_count(['&', ('project_id', '=', self.name.id), ('state', 'not in', ['draft', 'rejected'])])
    #         self.expense_advance_count = res or 0
            
    # @api.multi
    # @api.depends('expense_advance_count')
    # def _get_expense_advance_amount(self):
    #     data_obj = self.env['hr.expense.advance'].search(['&', ('project_id', '=', self.name.id), ('state', 'not in', ['draft', 'rejected'])])
    #     total_amount = sum(data_obj.mapped('amount_total'))
    #     for record in self:
    #         record.expense_advance_amount = total_amount or False

# statinfo PO di Project management
    @api.multi
    def _get_purchase_order_amount(self):
        data_obj = self.env['purchase.order'].search(['&', ('project', '=', self.name.id), ('state', 'not in', ['draft', 'cancel', 'refuse'])])
        total_amount = sum(data_obj.mapped('amount_total'))
        for record in self:
            record.purchase_order_amount = total_amount or False


# open CVR
    @api.multi
    def open_expense_sheet_project(self):
        for group in self:
            return {
                    'name': 'CVR',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'hr.expense.sheet',
                    'type': 'ir.actions.act_window',
                    'domain': ['&', ('project', '=', group.name.id), ('state', 'not in', ['draft', 'cancel', 'reject_control', 'reject_technical', 'reject_finance']),],
                }
        pass

# open BAR
    @api.multi
    def open_expense_advance_project(self):
        # for group in self:
        #     return {
        #             'name': 'BAR',
        #             'view_type': 'form',
        #             'view_mode': 'tree,form',
        #             'res_model': 'hr.expense.advance',
        #             'type': 'ir.actions.act_window',
        #             'domain': ['&', ('project_id', '=', group.name.id), ('state', 'not in', ['draft', 'rejected']),],
        #         }
        pass

# open PUrchase order
    @api.multi
    def open_purchase_order_project(self):
        for group in self:
            return {
                    'name': 'Purchase Order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'purchase.order',
                    'type': 'ir.actions.act_window',
                    'domain': ['&', ('project', '=', group.name.id), ('state', 'not in', ['draft', 'cancel', 'refuse']),],
                }
        pass




    @api.depends(
        'project_actual_plan_curve_report', 
        'project_actual_plan_curve_report.accumulative_plan', 
        'project_actual_plan_curve_report.accumulative_actual',
        'project_actual_plan_curve_report.year', 'project_actual_plan_curve_report.weeks',

        'project_invoice_report', 
        'project_invoice_report.accumulative_plan_invoice', 
        'project_invoice_report.accumulative_actual_invoice',
        'project_invoice_report.year', 'project_invoice_report.weeks',

        'project_cash_out_report', # For weekly sum of Cash Out
        'project_cash_out_report.plan_cash_out',    
        'project_cash_out_report.actual_cash_out',
        
        'project_cash_in_report', 
        'project_cash_in_report.accumulative_plan_cash_in', 
        'project_cash_in_report.accumulative_actual_cash_in',
        'project_cash_in_report.year', 'project_cash_in_report.weeks',

        'project_manhour_report', 
        'project_manhour_report.accumulative_plan_manhour', 
        'project_manhour_report.accumulative_actual_manhour',
        'project_manhour_report.year', 'project_manhour_report.weeks'
    )
    def _compute_current_accum_values(self):
        _logger.info("--- _compute_current_accum_values (store=True) TRIGGERED for PP IDs: %s ---", self.ids)
        for record in self:
            _logger.info("  Processing PP ID: %s for stored tree view values", record.id)
            
            # Initialize (values will be overwritten if data found)
            plan_progress, actual_progress = 0.0, 0.0
            plan_invoice, actual_invoice = 0.0, 0.0
            plan_cash_out, actual_cash_out = 0.0, 0.0 # These will be summed
            plan_cash_in, actual_cash_in = 0.0, 0.0
            plan_manhour, actual_manhour = 0.0, 0.0

            # % Progress - Reads from project_actual_plan_curve_report
            if record.project_actual_plan_curve_report:
                latest_progress_line = record.project_actual_plan_curve_report.sorted(
                    key=lambda r: (r.year, r.weeks), reverse=True
                )[:1]
                if latest_progress_line:
                    plan_progress = latest_progress_line.accumulative_plan
                    actual_progress = latest_progress_line.accumulative_actual
            
            # Invoice - Reads from project_invoice_report
            if record.project_invoice_report:
                latest_invoice_line = record.project_invoice_report.sorted(
                    key=lambda r: (r.year, r.weeks), reverse=True
                )[:1]
                if latest_invoice_line:
                    plan_invoice = latest_invoice_line.accumulative_plan_invoice
                    actual_invoice = latest_invoice_line.accumulative_actual_invoice

            # Cash Out - Sums from project_cash_out_report (which contains weekly values)
            if record.project_cash_out_report:
                for line_co in record.project_cash_out_report:
                    plan_cash_out += line_co.plan_cash_out
                    actual_cash_out += line_co.actual_cash_out
            
            # Cash In - Reads from project_cash_in_report
            if record.project_cash_in_report:
                latest_cashin_line = record.project_cash_in_report.sorted(
                    key=lambda r: (r.year, r.weeks), reverse=True
                )[:1]
                if latest_cashin_line:
                    plan_cash_in = latest_cashin_line.accumulative_plan_cash_in
                    actual_cash_in = latest_cashin_line.accumulative_actual_cash_in

            # Manhour - Reads from project_manhour_report
            if record.project_manhour_report:
                latest_manhour_line = record.project_manhour_report.sorted(
                    key=lambda r: (r.year, r.weeks), reverse=True
                )[:1]
                if latest_manhour_line:
                    plan_manhour = latest_manhour_line.accumulative_plan_manhour
                    actual_manhour = latest_manhour_line.accumulative_actual_manhour
            
            record.current_accum_plan_progress = plan_progress
            record.current_accum_actual_progress = actual_progress
            record.current_accum_plan_invoice = plan_invoice
            record.current_accum_actual_invoice = actual_invoice
            record.current_accum_plan_cash_out = plan_cash_out
            record.current_accum_actual_cash_out = actual_cash_out
            record.current_accum_plan_cash_in = plan_cash_in
            record.current_accum_actual_cash_in = actual_cash_in
            record.current_accum_plan_manhour = plan_manhour
            record.current_accum_actual_manhour = actual_manhour
            
            _logger.info(
                "    PP ID %s: SETTING Stored Tree Values - PlanProg=%s, ActualProg=%s, PlanInv=%s, ActualInv=%s, PlanCO=%s, ActualCO=%s, PlanCI=%s, ActualCI=%s, PlanMH=%s, ActualMH=%s",
                record.id, plan_progress, actual_progress, plan_invoice, actual_invoice,
                plan_cash_out, actual_cash_out, plan_cash_in, actual_cash_in, plan_manhour, actual_manhour
            )

    
    def generate_report_data(self):
        self.ensure_one()
        _logger.info(">>>> generate_report_data (Tier 2 - Signature Check): START for PP ID: %s", self.id)

        current_signature = self._get_current_report_data_signature()

        if self.last_report_data_signature == current_signature:
            _logger.info("  PP ID %s: Data signature matches last run (%s). SKIPPING intermediary report regeneration.", 
                         self.id, current_signature)
            # Even if reports are skipped, if tree view fields are store=False, they'd recompute.
            # If store=True, they won't recompute if their dependencies (intermediary reports) didn't change.
            return True 

        _logger.info("  PP ID %s: Data signature changed. Old: [%s], New: [%s]. Regenerating intermediary reports.",
                     self.id, self.last_report_data_signature, current_signature)

        if hasattr(self, '_compute_start_finish_dates'): # If you have this method to set start/finish
             self._compute_start_finish_dates()
        _logger.info("  PP ID %s: Start Date=%s, Finish Date=%s (for report period)", self.id, self.start_date, self.finish_date)

        # 1. Get all data for new INTERMEDIARY report lines
        s_curve_data_list = self.get_actual_plan_curve_lines_report() if hasattr(self, 'get_actual_plan_curve_lines_report') else []
        invoice_data_list = self.get_invoice_report() if hasattr(self, 'get_invoice_report') else []
        cash_out_weekly_data_list = self.get_cash_out_report_weekly() if hasattr(self, 'get_cash_out_report_weekly') else []
        cash_in_data_list = self.get_cash_in_report() if hasattr(self, 'get_cash_in_report') else []
        manhour_data_list = self.get_manhour_report() if hasattr(self, 'get_manhour_report') else []
        _logger.info("  PP ID %s: Fetched data for intermediary report lines.", self.id)

        # 2. Unlink old intermediary report lines
        _logger.info("  PP ID %s: Unlinking old intermediary report lines...", self.id)
        self.project_actual_plan_curve_report.unlink()
        self.project_invoice_report.unlink()
        self.project_cash_out_report.unlink() # weekly ones for cash out sum
        self.project_cash_in_report.unlink()
        self.project_manhour_report.unlink()
        # If project_cash_flow_report is used for cash out accumulatives by other parts, unlink it too.
        # if hasattr(self, 'project_cash_flow_report'): self.project_cash_flow_report.unlink()
        _logger.info("  PP ID %s: Old intermediary report lines unlinked.", self.id)

        # 3. Create new intermediary report lines
        # This will trigger _compute_current_accum_values due to @api.depends
        _logger.info("  PP ID %s: Creating new intermediary report lines...", self.id)
        if s_curve_data_list:
            for d in s_curve_data_list: d['actual_curve_plan_report_id'] = self.id
            self.env['project.actual.plan.curve.report'].create(s_curve_data_list)
        if invoice_data_list:
            for d in invoice_data_list: d['invoice_report_id'] = self.id
            self.env['project.invoice.report'].create(invoice_data_list)
        if cash_out_weekly_data_list: 
            for d in cash_out_weekly_data_list: d['cash_out_report_id'] = self.id
            self.env['project.cash.out.report'].create(cash_out_weekly_data_list)
        if cash_in_data_list:
            for d in cash_in_data_list: d['cash_in_report_id'] = self.id
            self.env['project.cash.in.report'].create(cash_in_data_list)
        if manhour_data_list:
            for d in manhour_data_list: d['manhour_report_id'] = self.id
            self.env['project.manhour.report'].create(manhour_data_list)
        _logger.info("  PP ID %s: New intermediary report lines created.", self.id)

        # 4. Update the last_report_data_signature
        _logger.info("  PP ID %s: Updating last_report_data_signature to %s", self.id, current_signature)
        self.sudo().write({'last_report_data_signature': current_signature})

        # The store=True fields (current_accum_...) will be recomputed and saved by Odoo
        # because their dependencies (the intermediary report lines) changed.
        # An explicit self.recompute() is usually not needed here for this purpose if @api.depends is correct.

        _logger.info("<<<< generate_report_data: FINISH for PP ID: %s", self.id)
        return True

    @api.model
    def run_project_progress_update_cron(self):
        _logger.info("CRON (Combined Approach): Starting job.")
        
        all_active_projects = self.env['project.progress.plan'].search([('active', '=', True)])
        records_to_process_tier1 = []
        _logger.info("CRON: Tier 1 Filter - Checking %s active projects for actual data (amount > 0).", len(all_active_projects))

        for project in all_active_projects:
            has_positive_actuals = False
            if any(line.name > 0 for line in project.project_actual_curve_line): has_positive_actuals = True
            elif any(line.amount > 0 for line in project.project_actual_invoice_line): has_positive_actuals = True
            elif any(line.amount > 0 for line in project.project_actual_cashout_line): has_positive_actuals = True
            elif any(line.amount > 0 for line in project.project_actual_cashin_line): has_positive_actuals = True
            elif any(line.total > 0 for line in project.project_actual_manhour_line): has_positive_actuals = True
            elif any(line.amount > 0 for line in project.project_actual_cost_line): has_positive_actuals = True
            
            if has_positive_actuals:
                records_to_process_tier1.append(project)
        
        total_to_process = len(records_to_process_tier1)
        _logger.info("CRON: Tier 1 Filter - Found %s projects with positive actuals to process further.", total_to_process)

        if not records_to_process_tier1:
            _logger.info("CRON: No records with positive actuals need updating at this time.")
            return True

        processed_count = 0
        commit_batch_size = 20 

        for record in records_to_process_tier1:
            processed_count += 1
            project_name = record.name.name if record.name else "N/A"
            _logger.info("CRON: Processing record %s/%s (ID: %s, Name: %s)", 
                         processed_count, total_to_process, record.id, project_name)
            try:
                # action_update_actual_value will fetch latest actuals into source O2M lines,
                # then call generate_report_data which has the signature check (Tier 2).
                if hasattr(record, 'action_update_actual_value'):
                    record.action_update_actual_value()
                else:
                    _logger.warning("CRON: Method 'action_update_actual_value' not found for PP ID: %s", record.id)
                
                if processed_count % commit_batch_size == 0:
                    self.env.cr.commit()
                    _logger.info("CRON: Committed after processing %s records.", processed_count)
            except Exception as e:
                _logger.error("CRON: Error processing project.progress.plan ID %s (Name: %s): %s.", 
                              record.id, project_name, e)
                self.env.cr.rollback()
                self.env.cr.commit() 
            
        if total_to_process > 0 and processed_count > 0 and processed_count % commit_batch_size != 0 :
             self.env.cr.commit()
             _logger.info("CRON: Final commit made.")

        _logger.info("CRON: Finished processing %s targeted records.", processed_count)
        return True

    # You still need the _compute_current_accum_values method defined (likely in an inheriting class
    # like ProjectProgressPlanTreeValues from project_progress_export.py, or here if you combine files).
    # Ensure its @api.depends is correct and it reads from the intermediary report lines.


    def _get_current_report_data_signature(self):
        self.ensure_one()
        _logger.debug("PP ID %s - Signature: Calculating current data signature...", self.id)
        data_to_sign = []
        def date_to_str(val):
            if not val: return None
            return val.strftime('%Y-%m-%d') if hasattr(val, 'strftime') else str(val)
        def round_val(val, digits=2):
            return round(val or 0.0, digits)

        # Plan Data (sorted by ID for consistency)
        for line in self.project_plan_curve_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('plan_curve', date_to_str(line.date), line.name))
        for line in self.project_plan_invoice_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('plan_invoice', date_to_str(line.date), round_val(line.name)))
        for line in self.project_plan_cashout_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('plan_cashout', date_to_str(line.date), round_val(line.name)))
        for line in self.project_plan_cashin_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('plan_cashin', date_to_str(line.date), round_val(line.name)))
        for line in self.project_plan_manhour_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('plan_manhour', date_to_str(line.date), round_val(line.name)))

        # Actual Data (sorted by ID for consistency)
        for line in self.project_actual_curve_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('actual_curve', date_to_str(line.date), line.name))
        for line in self.project_actual_invoice_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('actual_invoice', date_to_str(line.created_date), round_val(line.amount)))
        for line in self.project_actual_cashout_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('actual_cashout', date_to_str(line.payment_date), round_val(line.amount), line.code))
        for line in self.project_actual_cashin_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('actual_cashin', date_to_str(line.payment_date), round_val(line.amount)))
        for line in self.project_actual_manhour_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('actual_manhour', date_to_str(line.date_from), date_to_str(line.date_to), line.total))
        for line in self.project_actual_cost_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('actual_cost', date_to_str(line.created_date), round_val(line.amount), line.code))
        for line in self.project_estimated_cashout_line.sorted(key=lambda r: r.id):
            data_to_sign.append(('estimated_cashout', date_to_str(line.created_date), round_val(line.amount), line.code))
        
        # Add direct fields from self if they influence reports
        # data_to_sign.append(('self_project_name', self.name.name if self.name else None))

        consistent_string_data = json.dumps(data_to_sign, sort_keys=True, default=str)
        # _logger.debug("PP ID %s - SIGNATURE_INPUT_STRING:\n%s", self.id, consistent_string_data) # For deep debugging
        signature = hashlib.sha256(consistent_string_data.encode('utf-8')).hexdigest()
        _logger.debug("PP ID %s - Calculated signature: %s", self.id, signature)
        return signature








class ProjectPlanCurve(models.Model):
    _name = 'project.plan.curve'

    name = fields.Float(string='Progress %')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_plan_curve_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')

    @api.depends('plan_plan_curve_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_curve_id'):
            seq = 1
            for line in order.project_plan_curve_line:
                line.seq = seq
                seq += 1

class ProjectActualCurve(models.Model):
    _name = 'project.actual.curve'

    name = fields.Float(string='Progress %')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_actual_curve_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')


    @api.depends('plan_actual_curve_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_actual_curve_id'):
            seq = 1
            for line in order.project_actual_curve_line:
                line.seq = seq
                seq += 1


class ProjectPlanCashout(models.Model):
    _name = 'project.plan.cashout'

    name = fields.Float(string='Cash Out')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal',store=True)
    plan_plan_cashout_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')

    @api.depends('plan_plan_cashout_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_cashout_id'):
            seq = 1
            for line in order.project_plan_cashout_line:
                line.seq = seq
                seq += 1

class ProjectActualCashout(models.Model):
    _name = 'project.actual.cashout'
    _description = 'Actual cashout '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Payment Date')
    actual_cashout_line_id = fields.Many2one('project.progress.plan', string='Actual Cashout', ondelete='cascade')
    code = fields.Char('Source',help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total PO & CVR")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')

class ProjectActualCashout(models.Model):
    _name = 'project.actual.cost'
    _description = 'Actual Cost '

    name = fields.Char(string='Number')
    created_date = fields.Date(string='Created Date')
    actual_cost_line_id = fields.Many2one('project.progress.plan', string='Actual Cost', ondelete='cascade')
    code = fields.Char('Source',help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total PI & CVR")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')
    description = fields.Char('Description', help="Keterangan")
    attachments = fields.Many2many('ir.attachment', string='Attachments')


class ProjectPlanCashin(models.Model):
    _name = 'project.plan.cashin'

    name = fields.Float(string='Cash In')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_plan_cashin_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')

    @api.depends('plan_plan_cashin_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_cashin_id'):
            seq = 1
            for line in order.project_plan_cashin_line:
                line.seq = seq
                seq += 1

class ProjectActualCashin(models.Model):
    _name = 'project.actual.cashin'
    _description = 'Actual Cash In '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Payment Date')
    actual_cashin_line_id = fields.Many2one('project.progress.plan', string='Actual Cash In ', ondelete='cascade', index=True)
    amount = fields.Float(string="Total", help="Amount of Total Cash In")
    currency_id = fields.Many2one('res.currency')
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectPlanInvoice(models.Model):
    _name = 'project.plan.invoice'

    name = fields.Float(string='Invoice')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_plan_invoice_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')


    @api.depends('plan_plan_invoice_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_invoice_id'):
            seq = 1
            for line in order.project_plan_invoice_line:
                line.seq = seq
                seq += 1

class ProjectActualInvoice(models.Model):
    _name = 'project.actual.invoice'
    _description = 'Actual Invoice '

    name = fields.Char(string='Number')
    created_date = fields.Date(string='Invoice Date')
    actual_invoice_line_id = fields.Many2one('project.progress.plan', string='Actual Invoice', ondelete='cascade', index=True)
    amount = fields.Float(string="Total", help="Amount of Total Invoice")
    amount_company_signed = fields.Float(string="Total Company Signed", help="Amount of Total Invoice")
    currency_id = fields.Many2one('res.currency')
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')

class ProjectPlanManhour(models.Model):
    _name = 'project.plan.manhour'

    name = fields.Float(string='Manhour')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_plan_manhour_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')


    @api.depends('plan_plan_manhour_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_manhour_id'):
            seq = 1
            for line in order.project_plan_manhour_line:
                line.seq = seq
                seq += 1

class ProjectActualManhour(models.Model):
    _name = 'project.actual.manhour'
    _description = 'Actual Manhour '

    name = fields.Char(string='Name')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    actual_manhour_line_id = fields.Many2one('project.progress.plan', string='Actual Manhour', ondelete='cascade', index=True)
    total = fields.Integer(string="Total Hours", help="Amount of Total Manhour")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')
    month = fields.Char(string='Month',)

class ProjectEstimatedCashout(models.Model):
    _name = 'project.estimated.cashout'
    _description = 'Estimated cashout '

    name = fields.Char(string='Number')
    created_date = fields.Date(string='Created Date')
    estimated_cashout_line_id = fields.Many2one('project.progress.plan', string='Actual Cashout', ondelete='cascade', index=True)
    code = fields.Char('Source',help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total PO&CVR")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectActualPlanCashout(models.Model):
    _name = 'project.actual.plan.cashout'
    _description = 'Actual and Plan cashout '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Date')
    actual_cashout_plan_line_id = fields.Many2one('project.progress.plan', string='Actual Cashout', ondelete='cascade')
    code = fields.Char('Source',help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total PO & CVR")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectActualPlanCurve(models.Model):
    _name = 'project.actual.plan.curve'
    _description = 'Actual and Plan Curve '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Date')
    actual_curve_plan_line_id = fields.Many2one('project.progress.plan', string='Actual Curve', ondelete='cascade')
    code = fields.Char('Source', help="Testing")
    amount = fields.Float(string="Total", help="Testing")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')

class ProjectActualPlanCashin(models.Model):
    _name = 'project.actual.plan.cashin'
    _description = 'Actual and Plan Cashin '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Date')
    actual_cashin_plan_line_id = fields.Many2one('project.progress.plan', string='Actual Cashin', ondelete='cascade')
    code = fields.Char('Source',help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')

class ProjectActualPlanInvoice(models.Model):
    _name = 'project.actual.plan.invoice'
    _description = 'Actual and Plan invoice '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Date')
    actual_invoice_plan_line_id = fields.Many2one('project.progress.plan', string='Actual Invoice', ondelete='cascade')
    code = fields.Char('Source',help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')

class ProjectActualPlanManhour(models.Model):
    _name = 'project.actual.plan.manhour'
    _description = 'Actual and Plan Manhour '

    name = fields.Char(string='Number')
    date = fields.Date(string='Date')
    actual_manhour_plan_line_id = fields.Many2one('project.progress.plan', string='Actual manhour', ondelete='cascade')
    code = fields.Char('Source',help="The code that can be used")
    total = fields.Float(string="Total", help="Amount of Total")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectExecutionExperienceLine(models.Model):
    _name = 'project.execution.experience'
    _description = 'Project Execution Experience Line'

    project_execution_experience_id = fields.Many2one('project.progress.plan', string='Parent', ondelete='cascade')
    value = fields.Text(string='Project Execution Experience Value')

class LessonLearnedLine(models.Model):
    _name = 'project.lesson.learned'
    _description = 'Lesson Learned Line'

    lesson_learned_id = fields.Many2one('project.progress.plan', string='Parent', ondelete='cascade')
    value = fields.Text(string='Lesson Value')

class SubconPerformanceServiceLine(models.Model):
    _name = 'project.subcon.performance.service'
    _description = 'Subcon Performance Service Line'

    subcon_performance_service_id = fields.Many2one('project.progress.plan', string='Parent', ondelete='cascade')
    value = fields.Text(string='Subcon Value')

class ProcurementRecommendationLine(models.Model):
    _name = 'project.procurement.recommendation'
    _description = 'Procurement Recommendation Line'

    procurement_recommendation_id = fields.Many2one('project.progress.plan', string='Parent', ondelete='cascade')
    value = fields.Text(string='Procurement Value')