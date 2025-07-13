# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_
import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountFinancialReport(models.Model):
    _name = 'account.financial.report'

    def _get_children_by_order(self):
        res = self
        children = self.search([('parent_id', 'in', self.ids)], order='sequence ASC')
        if children:
            for child in children:
                res += child._get_children_by_order()
        return res

    @api.multi
    @api.depends('parent_id', 'parent_id.level')
    def _get_level(self):
        for report in self:
            level = 0
            if report.parent_id:
                level = report.parent_id.level + 1
            report.level = level

    name = fields.Char('Report Name', required=True, translate=True)
    level = fields.Integer(compute='_get_level', string='Level', store=True)
    sequence = fields.Integer('Sequence')
    parent_id = fields.Many2one('account.financial.report', 'Parent')
    children_ids = fields.One2many('account.financial.report', 'parent_id', 'Account Report')
    type = fields.Selection([
        ('sum', 'View'),
        ('accounts', 'Accounts'),
        ('account_type', 'Account Type'),
        ('account_report', 'Report Value'),
        ('header', 'Header'),
        ('sum_report', 'Sum Report'),
    ], 'Type', default='sum')
    account_ids = fields.Many2many('account.account', 'account_account_financial_report', 'report_line_id',
                                   'account_id', 'Accounts')
    account_report_id = fields.Many2one('account.financial.report', 'Report Value')
    account_type_ids = fields.Many2many('account.account.type', 'account_account_financial_report_type', 'report_id',
                                        'account_type_id', 'Account Types')
    sign = fields.Selection([(-1, 'Reverse balance sign'), (1, 'Preserve balance sign')], 'Sign on Reports',
                            required=True, default=1,
                            help='For accounts that are typically more debited than credited and that you would like to print as negative amounts in your reports, you should reverse the sign of the balance; e.g.: Expense account. The same applies for accounts that are typically more credited than debited and that you would like to print as positive amounts in your reports; e.g.: Income account.')
    display_detail = fields.Selection([
        ('no_detail', 'No detail'),
        ('detail_flat', 'Display children flat'),
        ('detail_with_hierarchy', 'Display children with hierarchy')
    ], 'Display details', default='detail_flat')
    style_overwrite = fields.Selection([
        (0, 'Automatic formatting'),
        (1, 'Main Title 1 (bold, underlined)'),
        (2, 'Title 2 (bold)'),
        (3, 'Title 3 (bold, smaller)'),
        (4, 'Normal Text'),
        (5, 'Italic Text (smaller)'),
        (6, 'Smallest Text'),
    ], 'Financial Report Style', default=0,
        help="You can set up here the format you want this record to be displayed. If you leave the automatic formatting, it will be computed based on the financial reports hierarchy (auto-computed field 'level').")

    active = fields.Boolean(default=True)
    report_line_ids= fields.Many2many('account.financial.report', 'account_financial_report_line','report_line_id','account_report_id')
    report_type = fields.Char('Report Type')

class AccountingReportBi(models.TransientModel):
    _name = "accounting.report.bi"
    _description = "Accounting Report"

    @api.model
    def _get_account_report(self):
        reports = []
        if self._context.get('active_id'):
            menu = self.env['ir.ui.menu'].browse(self._context.get('active_id')).name
            reports = self.env['account.financial.report'].search([('name', 'ilike', menu)])
        return reports and reports[0] or False

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True,
                                   default=lambda self: self.env['account.journal'].search([]))
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date',default=date.today())
    display_account = fields.Selection([('all', 'All'), ('movement', 'With movements'),
                                        ('not_zero', 'With balance is not equal to 0'), ],
                                       string='Display Accounts', required=True, default='movement')
    target_move = fields.Selection([('posted', 'Posted Entries'),
                                    ('draft', 'Unposted Entries'),
                                    ], string='Target Moves', required=False, default=False)
    enable_filter = fields.Boolean(string='Enable Comparison')
    account_report_id = fields.Many2one('account.financial.report', string='Account Reports',
                                        default=_get_account_report)
    label_filter = fields.Char(string='Column Label',
                               help="This label will be displayed on report to show the balance computed for the given comparison filter.")
    filter_cmp = fields.Selection([('filter_no', 'No Filters'), ('filter_date', 'Date')], string='Filter by',
                                  required=True, default='filter_no')
    date_from_cmp = fields.Date(string='Start Date')
    date_to_cmp = fields.Date(string='End Date')
    debit_credit = fields.Boolean(string='Display Debit/Credit Columns',
                                  help="This option allows you to get more details about the way your balances are computed. Because it is space consuming, we do not allow to use it while doing a comparison.")
    initial_balance = fields.Boolean(string='Include Initial Balances',
                                     help='If you selected date, this field allow you to add a row to display the amount of debit/credit/balance that precedes the filter you\'ve set.')
    sortby = fields.Selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')], string='Sort by',
                              required=True, default='sort_date')
    project = fields.Many2one('project.project', 'Project')
    show_account_code = fields.Boolean(string="Show Account Code", default=False)

    report_format = fields.Selection([
        ('standard', 'Standard Period'), # For your existing reports
        ('monthly', 'Monthly Period')
    ], string="Report Format", default='standard', required=True)
    
    year_filter = fields.Integer(string="Year", default=lambda self: fields.Date.today().year)
    hide_zero_balance_lines = fields.Boolean(
        string="Hide Zero-Balance", 
        default=False,
        help="If checked, lines with a final balance of zero will not be displayed on the report (for standard period reports)."
    )

# untuk monthly report

    def _get_monthly_balances_for_report(self, report_lines_config, year):
        _logger.info("Starting _get_monthly_balances_for_report for year %s", year)
        
        monthly_report_data = {}
        for report_line in report_lines_config: # Initialize structure
            monthly_report_data[report_line.id] = {
                'name': report_line.name,
                'level': report_line.style_overwrite or report_line.level,
                'type': report_line.type,
                'sign': report_line.sign,
                'display_detail': report_line.display_detail,
                'account_ids': report_line.account_ids,
                'account_type_ids': report_line.account_type_ids,
                'monthly_balances': {i: 0.0 for i in range(1, 13)},
                'ytd_balance': 0.0,
                'monthly_accounts_data': {i: {} for i in range(1,13)}
            }

        for month in range(1, 13):
            month_start_date_str = "{}-{:02d}-01".format(year, month) 
            
            try:
                month_start_date = fields.Date.to_date(month_start_date_str)
                # Corrected isinstance check:
                if not isinstance(month_start_date, date): # Odoo's fields.Date.to_date() returns datetime.date
                    _logger.error(
                        "Month_start_date is not a datetime.date object for month %s, year %s. String was: %s. Got type: %s",
                        month, year, month_start_date_str, type(month_start_date)
                    )
                    continue 
            except ValueError as e:
                _logger.error(
                    "Invalid date string for month %s, year %s. String was: '%s'. Error: %s",
                    month, year, month_start_date_str, e
                )
                continue 

            try:
                first_day_next_month = month_start_date + relativedelta(months=1)
                month_end_date = first_day_next_month - relativedelta(days=1)
            except TypeError as e_rd:
                _logger.error(
                    "TypeError during relativedelta calculation for month %s, year %s. month_start_date: %s (type %s). Error: %s",
                    month, year, month_start_date, type(month_start_date), e_rd
                )
                continue 
            except Exception as e_other:
                 _logger.error(
                    "Unexpected error during month_end_date calculation for month %s, year %s. Error: %s",
                    month, year, e_other
                )
                 continue

            _logger.info("Calculating for month %s: %s to %s", month, month_start_date, month_end_date)

            journal_ids_for_new = []
            if self.journal_ids:
                journal_ids_for_new = [(6, 0, self.journal_ids.ids)]

            monthly_calc_wizard = self.new({
                'date_from': month_start_date,
                'date_to': month_end_date,
                'project': self.project.id if self.project else False,
                'target_move': self.target_move,
                'journal_ids': journal_ids_for_new,
                'company_id': self.company_id.id,
                'display_account': self.display_account,
                'account_report_id': self.account_report_id.id,
                'report_format': 'standard', 
            })
            
            month_balances = monthly_calc_wizard._compute_report_balance_for_period(report_lines_config)

            for report_line_id, data_val in month_balances.items(): # Renamed 'data' to 'data_val' to avoid conflict
                if report_line_id in monthly_report_data:
                    sign_multiplier = 1
                    try:
                        sign_multiplier = int(monthly_report_data[report_line_id]['sign'])
                    except (ValueError, TypeError):
                        _logger.warning("Invalid sign for report line %s: %s. Defaulting to 1.", 
                                        report_line_id, monthly_report_data[report_line_id]['sign'])
                    
                    balance_for_month = data_val.get('balance', 0.0) * sign_multiplier
                    monthly_report_data[report_line_id]['monthly_balances'][month] = balance_for_month
                    monthly_report_data[report_line_id]['ytd_balance'] += balance_for_month
                    
                    if data_val.get('account'): # Check 'data_val'
                         monthly_report_data[report_line_id]['monthly_accounts_data'][month] = data_val['account']

        _logger.info("Finished _get_monthly_balances_for_report. Data structure for first report line (if any): %s", 
                     monthly_report_data.get(next(iter(monthly_report_data))) if monthly_report_data else "No data")
        return monthly_report_data

    def _compute_report_balance_for_period(self, reports):
        """
        A simplified version of _compute_report_balance that calculates balances
        strictly for the period defined by self.date_from and self.date_to of the
        wizard instance it's called on. It ignores special report_type flags
        like 'CY_RE_PREV_MONTH' etc., treating all P&L calculations as for the given period.
        """
        if not isinstance(reports, models.Model): # Basic input validation
            try:
                if isinstance(reports, (int, list)): reports = self.env['account.financial.report'].browse(reports)
                elif isinstance(reports, models.Model) and len(reports) == 1 : reports = self.env['account.financial.report'].browse(reports.id)
                else: return {}
            except: return {}
        if not reports: return {}

        res = {}
        fields_to_compute = ['credit', 'debit', 'balance']
        _logger.info(
            "--- _compute_report_balance_FOR_PERIOD CALLED for reports: %s. Wizard (%s) dates: FROM %s TO %s ---",
            reports.mapped('name'), self.id, self.date_from, self.date_to
        )

        for report in reports:
            if report.id in res: continue
            res[report.id] = dict.fromkeys(fields_to_compute, 0.0)
            if report.type in ['accounts', 'account_type']:
                 res[report.id]['account'] = {}

            # All calculations use the dates from 'self' (the wizard instance, e.g., monthly_calc_wizard)
            if report.type == 'accounts':
                account_balances = self._compute_account_balance(report.account_ids) # Uses self.date_from/to
                res[report.id]['account'].update(account_balances)
                for value in account_balances.values():
                    for f in fields_to_compute: res[report.id][f] += value.get(f, 0.0)

            elif report.type == 'account_type':
                accounts = self.env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
                if not accounts: continue
                all_account_balances = self._compute_account_balance(accounts) # Uses self.date_from/to
                res[report.id]['account'].update(all_account_balances)
                for value in all_account_balances.values():
                    for f in fields_to_compute: res[report.id][f] += value.get(f, 0.0)
            
            elif report.type == 'sum_report_pl' and report.account_report_id:
                # The source P&L report also needs to be calculated for THIS wizard's period
                res2 = self._compute_report_balance_for_period(report.account_report_id) 
                source_balances = res2.get(report.account_report_id.id, {})
                for f in fields_to_compute: res[report.id][f] += source_balances.get(f, 0.0)

            elif report.type in ('account_report', 'sum', 'sum_report'):
                target_children = None
                if report.type == 'account_report': target_children = report.account_report_id
                elif report.type == 'sum': target_children = report.children_ids
                elif report.type == 'sum_report': target_children = report.report_line_ids
                if target_children:
                    res2 = self._compute_report_balance_for_period(target_children)
                    ids_to_sum = target_children.ids if isinstance(target_children, models.Model) else []
                    if report.type == 'account_report' and report.account_report_id: ids_to_sum = [report.account_report_id.id]
                    for item_id in ids_to_sum:
                        item_bals = res2.get(item_id, {})
                        for f in fields_to_compute: res[report.id][f] += item_bals.get(f, 0.0)
            
            for f in fields_to_compute: # Float conversion
                if not isinstance(res[report.id][f], (int, float)):
                    try: res[report.id][f] = float(res[report.id][f])
                    except: res[report.id][f] = 0.0
            _logger.debug("Report '%s' (ID %s) FOR PERIOD balances: %s", report.name, report.id, res[report.id])
        return res

    def get_monthly_report_lines_data(self):
        self.ensure_one()
        _logger.info("PDF MODULE - MONTHLY: get_monthly_report_lines_data called for wizard ID %s, year %s. Hide zero lines: %s", 
                     self.id, self.year_filter, self.hide_zero_balance_lines)
        
        processed_display_lines = [] # The final list of lines for QWeb
        
        if not self.account_report_id:
            _logger.error("PDF MODULE - MONTHLY: account_report_id is not set.")
            return []
        if not self.year_filter: # Should be caught by check_report, but good to have
            _logger.error("PDF MODULE - MONTHLY: year_filter is not set.")
            return []

        root_report_config = self.account_report_id
        # _get_children_by_order() includes the root report itself
        report_structure_config_lines = root_report_config._get_children_by_order()

        if not report_structure_config_lines:
            _logger.info("PDF MODULE - MONTHLY: No report structure lines found for '%s'.", root_report_config.name)
            return []

        # This fetches all data, including balances for all months and YTD
        # monthly_data_map = {report_line_id: {'name':..., 'monthly_balances':{1:bal,...}, 'ytd_balance':..., ...}}
        monthly_data_map = self._get_monthly_balances_for_report(report_structure_config_lines, self.year_filter)

        for report_config_line in report_structure_config_lines:
            if report_config_line.id not in monthly_data_map:
                _logger.warning("PDF MODULE - MONTHLY: Report line %s (ID %s) not found in monthly_data_map. Skipping.", 
                                report_config_line.name, report_config_line.id)
                continue

            data_for_this_config_line = monthly_data_map[report_config_line.id]
            
            # Apply sign to YTD balance for filtering and display
            # Note: monthly_balances in data_for_this_config_line are already signed from _get_monthly_balances_for_report
            # if that method applies the sign. If not, apply sign to monthly_balances too.
            # Assuming sign was applied in _get_monthly_balances_for_report to individual month balances.
            # YTD balance in monthly_data_map should be the sum of signed monthly balances.
            
            ytd_balance_for_filtering = data_for_this_config_line.get('ytd_balance', 0.0)
            # The sign is usually applied to monthly_balances when summing for YTD in _get_monthly_balances_for_report
            # or it should be applied when displaying. Let's assume ytd_balance is already correctly signed.

            # Filter 1: Hide zero-YTD-balance main lines
            if self.hide_zero_balance_lines and \
               report_config_line.type != 'header' and \
               self.company_id.currency_id.is_zero(ytd_balance_for_filtering):
                _logger.debug("PDF MODULE - MONTHLY: Hiding zero-YTD-balance line: %s (YTD: %s)", 
                             data_for_this_config_line['name'], ytd_balance_for_filtering)
                continue 

            # Prepare the main line for display
            # Monthly balances should be a list of 12 items
            display_monthly_balances = [data_for_this_config_line['monthly_balances'].get(m, 0.0) for m in range(1, 13)]

            vals = {
                'id': report_config_line.id,
                'name': data_for_this_config_line['name'],
                'level': data_for_this_config_line['level'],
                'type': data_for_this_config_line['type'],
                'display_detail': data_for_this_config_line['display_detail'],
                'monthly_balances': display_monthly_balances,
                'ytd_balance': ytd_balance_for_filtering, # Already signed (or should be)
                'show_balance': data_for_this_config_line['type'] not in ['header'],
            }
            processed_display_lines.append(vals)

            # Handle detail lines (accounts) if not 'no_detail'
            if report_config_line.display_detail != 'no_detail' and \
               data_for_this_config_line.get('monthly_accounts_data'):
                
                # Consolidate all unique accounts that have data for this report_config_line across all months
                all_present_account_ids = set()
                for month_num in range(1, 13):
                    for acc_id in data_for_this_config_line['monthly_accounts_data'].get(month_num, {}).keys():
                        all_present_account_ids.add(acc_id)
                
                # --- Logic to prevent duplicating single account detail ---
                skip_details_for_this_line = False
                if report_config_line.type == 'accounts' and len(all_present_account_ids) == 1:
                    account_id_single = list(all_present_account_ids)[0]
                    account_obj_single = self.env['account.account'].browse(account_id_single)
                    if account_obj_single:
                        formatted_account_name = self._format_account_name(account_obj_single)
                        if formatted_account_name.strip().lower() == report_config_line.name.strip().lower():
                            _logger.info("PDF MODULE - MONTHLY: Skipping redundant detail for '%s' (type 'accounts').", report_config_line.name)
                            skip_details_for_this_line = True
                # --- End of duplication prevention logic ---

                if not skip_details_for_this_line:
                    account_detail_lines_for_qweb = []
                    for acc_id in sorted(list(all_present_account_ids)): # Sort by ID or later by name
                        account = self.env['account.account'].browse(acc_id)
                        if not account: continue

                        acc_monthly_balances_list = []
                        acc_ytd_balance = 0.0
                        
                        # Apply sign from the parent report_config_line to account details
                        sign_multiplier_detail = int(data_for_this_config_line.get('sign', 1)) # sign from report_line_config
                        if sign_multiplier_detail not in (1,-1): sign_multiplier_detail = 1

                        has_any_movement_or_balance = False # For display_account filtering

                        for month_num in range(1, 13):
                            acc_month_data = data_for_this_config_line['monthly_accounts_data'].get(month_num, {}).get(acc_id, {})
                            # Balances from _compute_account_balance are typically not pre-signed by report.sign
                            # So, apply the parent report_config_line's sign here.
                            bal_for_month = acc_month_data.get('balance', 0.0) * sign_multiplier_detail
                            acc_monthly_balances_list.append(bal_for_month)
                            acc_ytd_balance += bal_for_month

                            if not self.company_id.currency_id.is_zero(acc_month_data.get('debit', 0.0)) or \
                               not self.company_id.currency_id.is_zero(acc_month_data.get('credit', 0.0)):
                                has_any_movement_or_balance = True


                        # Filter 2a: Hide zero-YTD-balance account details
                        if self.hide_zero_balance_lines and self.company_id.currency_id.is_zero(acc_ytd_balance):
                            _logger.debug("PDF MODULE - MONTHLY: Hiding zero-YTD-balance account detail: %s (YTD: %s)", 
                                         self._format_account_name(account), acc_ytd_balance)
                            continue
                        
                        # Filter 2b: Display Account criteria
                        if not self.company_id.currency_id.is_zero(acc_ytd_balance): # if ytd is not zero, it has a balance
                            has_any_movement_or_balance = True

                        show_this_account_line = False
                        if self.display_account == 'all':
                            show_this_account_line = True
                        elif self.display_account == 'movement' and has_any_movement_or_balance:
                            show_this_account_line = True
                        elif self.display_account == 'not_zero' and not self.company_id.currency_id.is_zero(acc_ytd_balance):
                            show_this_account_line = True
                        
                        if not show_this_account_line:
                            continue

                        sub_vals = {
                            'id': account.id, # Account ID
                            'name': self._format_account_name(account),
                            'level': (data_for_this_config_line['level'] or 0) + 1 if data_for_this_config_line['display_detail'] == 'detail_with_hierarchy' else (data_for_this_config_line['level'] or 0) + 1,
                            'type': 'account_detail_monthly', # Special type for QWeb to identify these
                            'monthly_balances': acc_monthly_balances_list,
                            'ytd_balance': acc_ytd_balance,
                            'show_balance': True, # Detail lines always try to show balances
                        }
                        account_detail_lines_for_qweb.append(sub_vals)
                    
                    # Sort detail lines by name if needed, then extend
                    processed_display_lines.extend(sorted(account_detail_lines_for_qweb, key=lambda x: x['name']))

        _logger.info("PDF MODULE - MONTHLY: Final lines count for QWeb: %s", len(processed_display_lines))
        # _logger.debug("PDF MODULE - MONTHLY: Final lines structure for QWeb: %s", processed_display_lines)
        return processed_display_lines

    @api.multi
    def check_report(self):
        self.ensure_one() 

        if not self.account_report_id:
            raise UserError(_('Misconfiguration. Please select a base Account Report (e.g., Profit and Loss or Balance Sheet).'))

        project_display = self.project.no if self.project and hasattr(self.project, 'no') else (self.project.name if self.project else _("All"))
        target_move_display = self.target_move or 'posted'

        final_dict = {}
        action_xml_id = ''


        if self.report_format == 'standard':
            _logger.info("PDF MODULE - STANDARD: Preparing report for wizard ID %s.", self.id)
            
            if self.date_to and self.date_from and self.date_to < self.date_from: 
                raise UserError(_('Standard Report: End date should be greater than or equal to start date.'))
            
            if self.enable_filter and self.filter_cmp == 'filter_date':
                if not self.date_from_cmp or not self.date_to_cmp:
                    raise UserError(_('Comparison dates are required when date comparison filter is enabled.'))
                if self.date_to_cmp < self.date_from_cmp:
                    raise UserError(_('Comparison end date should be greater than or equal to comparison start date.'))

            report_lines = self.get_account_lines() # Uses current wizard's date_from/to
            final_dict = {
                'report_lines': report_lines,
                'name': self.account_report_id.name,
                'debit_credit': self.debit_credit,
                'enable_filter': self.enable_filter,
                'label_filter': self.label_filter,
                'target_move': target_move_display,
                'date_from': self.date_from, 
                'date_to': self.date_to,     
                'project': project_display,
                'create_date_report': self.create_date, 
                'show_account_code': self.show_account_code,
                'report_format': self.report_format,
            }
            _logger.info("PDF MODULE - STANDARD: Final dictionary (to be nested in action's 'data' key) for wizard ID %s: %s", self.id, final_dict)
            action_xml_id = 'bi_financial_pdf_reports.action_report_balancesheet'

        elif self.report_format == 'monthly':
            _logger.info("PDF MODULE - MONTHLY: Preparing report for wizard ID %s, year %s.", self.id, self.year_filter)
            if not self.year_filter or not (1900 <= self.year_filter <= 2200):
                raise UserError(_("Please specify a valid year for the monthly report."))

            # Temporarily set overall date span on 'self' for layouts if they need docs.date_from/to
            original_date_from = self.date_from 
            original_date_to = self.date_to    
            year_start_date_str = "{}-01-01".format(self.year_filter)
            year_end_date_str = "{}-12-31".format(self.year_filter)
            # These writes to self might not be ideal if 'self' is used elsewhere concurrently,
            # but for a wizard action, it's usually okay for the duration of the method.
            self.write({
                'date_from': fields.Date.to_date(year_start_date_str),
                'date_to': fields.Date.to_date(year_end_date_str)
            })
            _logger.info("PDF MODULE - MONTHLY: Temporarily set self.date_from=%s, self.date_to=%s on wizard ID %s for layout purposes.", 
                         self.date_from, self.date_to, self.id)
            
            # **** CORRECTED LINE: Call the method that prepares monthly structured data ****
            monthly_lines_data = self.get_monthly_report_lines_data() 
            # *****************************************************************************
            
            months_headers = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            report_title = "{} - Monthly Breakdown {}".format(
                self.account_report_id.name if self.account_report_id else _("Monthly Report"), 
                self.year_filter
            )

            final_dict = {
                'report_lines': monthly_lines_data, # This now contains monthly structured lines
                'name': self.account_report_id.name, 
                'report_title': report_title, 
                'year': self.year_filter,
                'months_headers': months_headers,
                'project': project_display,
                'target_move': target_move_display,
                'create_date_report': fields.Datetime.now(),
                'report_format': self.report_format,
                'show_account_code': self.show_account_code,
                'debit_credit': False, 
                'enable_filter': False,
                'display_date_from': self.date_from, # Year start for display
                'display_date_to': self.date_to,     # Year end for display
            }
            _logger.info("PDF MODULE - MONTHLY: Final dictionary (to be nested in action's 'data' key) for wizard ID %s: %s", self.id, final_dict)
            action_xml_id = 'bi_financial_pdf_reports.action_report_monthly_financial' # Make sure this XML ID is correct
            
            # Restore original dates on self if they were modified
            self.write({
                'date_from': original_date_from,
                'date_to': original_date_to
            })
            _logger.info("PDF MODULE - MONTHLY: Restored self.date_from and self.date_to on wizard ID %s.", self.id)

        else:
            raise UserError(_("Unsupported report format: {}").format(self.report_format))

        # Common part to get action reference and call report_action
        try:
            report_action_ref = self.env.ref(action_xml_id)
            _logger.info("PDF MODULE: Resolved report_action_ref for '%s': ID %s, Report Name: %s, Report Type: %s", 
                         action_xml_id, report_action_ref.id if report_action_ref else 'N/A', 
                         report_action_ref.report_name if report_action_ref else 'N/A', 
                         report_action_ref.report_type if report_action_ref else 'N/A')
            _logger.info("PDF MODULE: Wizard's self.company_id that will be used by rendering_context: %s (Type: %s)", 
                         self.company_id, type(self.company_id)) # This company_id is important for layouts
            if not self.company_id or not isinstance(self.company_id, models.BaseModel):
                _logger.error("CRITICAL: self.company_id on the wizard instance (ID %s) is None or not a record!", self.id)

        except ValueError: # More specific for env.ref not found
            _logger.error("Report action XML ID '%s' not found.", action_xml_id)
            raise UserError(_("The report action '{}' is not defined.").format(action_xml_id))
        
        if not report_action_ref: # Should be caught by ValueError if ref fails
             _logger.error("Report action '%s' resolved to None.", action_xml_id)
             raise UserError(_("Failed to resolve the report action '{}'.").format(action_xml_id))

        action_to_return = report_action_ref.report_action(self, data=final_dict)
        _logger.info("PDF MODULE: Action dictionary being returned for '%s': %s", action_xml_id, action_to_return)
        
        if not isinstance(action_to_return.get('data'), dict):
             _logger.error("CRITICAL: 'data' key in returned action_to_return is NOT A DICTIONARY or is missing! Action: %s", action_to_return)
        elif not action_to_return.get('data').get('report_lines') and self.report_format == 'monthly':
             _logger.warning("Warning: 'report_lines' key not found in action_to_return['data'] for monthly report. This might be okay if it was a minimal test. Data: %s", action_to_return.get('data'))
        
        return action_to_return

    # --- Helper method ---
    def _format_account_name(self, account):
        """ Helper to consistently format account name based on show_account_code """
        if not account: # Should not happen if account_id is valid
            return ''
        if self.show_account_code and account.code:
            return "{} {}".format(account.code, account.name)
        return account.name

    def get_account_lines(self): 
        self.ensure_one()
        _logger.info("PDF MODULE - STANDARD: get_account_lines called for wizard ID %s. Hide zero lines: %s", 
                     self.id, self.hide_zero_balance_lines)
        
        if not self.account_report_id:
            _logger.error("PDF MODULE - STANDARD: account_report_id is not set in get_account_lines.")
            return []

        # Ensure account_report is a browse record
        account_report = self.account_report_id
        if isinstance(account_report, int): # Should ideally be an object already
            account_report = self.env['account.financial.report'].browse(account_report)
        
        if not account_report: # Double check after potential browse
            _logger.error("PDF MODULE - STANDARD: account_report_id could not be resolved to a record.")
            return []

        child_reports = account_report._get_children_by_order()
        if not child_reports:
            _logger.info("PDF MODULE - STANDARD: No child reports found for report '%s'.", account_report.name)
            return []

        # Determine date_from for context (respecting wizard input or defaulting)
        old_year = fields.Date.from_string(fields.Date.today().strftime('%Y-%m-%d')) - relativedelta(years=20)
        context_date_from = self.date_from if self.date_from else old_year
        context_date_to = self.date_to # Wizard should have a default (e.g., today())

        if not context_date_to:
            _logger.error("PDF MODULE - STANDARD: date_to is not set on the wizard for get_account_lines.")
            # Defaulting to today for safety, but this indicates a wizard configuration issue
            context_date_to = fields.Date.today() 

        used_context_dict = {
            'state': self.target_move or 'posted',
            'date_from': context_date_from,
            'date_to': context_date_to,
            'journal_ids': [j.id for j in self.journal_ids],
            'strict_range': True, 
            'company_id': self.company_id.id,
        }
        _logger.info("PDF MODULE - STANDARD: Context for _compute_report_balance: %s", used_context_dict)

        # res contains balances for all child_reports
        # Call on self (the wizard instance) but with specific context for date range etc.
        res = self.with_context(used_context_dict)._compute_report_balance(child_reports)
        _logger.debug("PDF MODULE - STANDARD: Raw results from _compute_report_balance: %s", res)

        # Comparison logic (if enabled)
        # This part populates 'comp_bal' in the 'res' dictionary
        if self.enable_filter and self.filter_cmp == 'filter_date':
            _logger.info("PDF MODULE - STANDARD: Calculating comparison balances.")
            comparison_context_dict = {
                'journal_ids': [j.id for j in self.journal_ids],
                'state': self.target_move or 'posted',
                'company_id': self.company_id.id,
            }
            if self.date_from_cmp and self.date_to_cmp:
                 comparison_context_dict.update({
                    'date_from': self.date_from_cmp,
                    'date_to': self.date_to_cmp,
                    'strict_range': True,
                })
                 temp_comp_res = self.with_context(comparison_context_dict)._compute_report_balance(child_reports)
                 for report_id_cmp, value_cmp in temp_comp_res.items():
                    if report_id_cmp in res: 
                        res[report_id_cmp]['comp_bal'] = value_cmp.get('balance', 0.0) # Use .get for safety
                        if res[report_id_cmp].get('account') and value_cmp.get('account'):
                            for acc_id_cmp, acc_val_cmp in value_cmp['account'].items():
                                if acc_id_cmp in res[report_id_cmp]['account']:
                                    res[report_id_cmp]['account'][acc_id_cmp]['comp_bal'] = acc_val_cmp.get('balance', 0.0)
            else:
                _logger.warning("PDF MODULE - STANDARD: Comparison filter by date enabled, but comparison dates are missing.")

        processed_lines = []
        for report in child_reports:
            if report.id not in res:
                _logger.warning("PDF MODULE - STANDARD: Report ID %s (%s) from child_reports not in computed results. Skipping.", report.id, report.name)
                continue

            report_data = res[report.id]
            sign_multiplier = int(report.sign) if report.sign in (1, -1) else 1
            current_balance = report_data.get('balance', 0.0) * sign_multiplier
            
            # Filter 1: Hide zero-balance main lines
            if self.hide_zero_balance_lines and \
               report.type != 'header' and \
               self.company_id.currency_id.is_zero(current_balance): # Use company_id from self for currency
                _logger.debug("PDF MODULE - STANDARD: Hiding zero-balance line: %s (Balance: %s)", report.name, current_balance)
                continue 

            vals = {
                'id': report.id,
                'name': report.name,
                'balance': current_balance,
                'type': report.type,
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': ', '.join(report.account_type_ids.mapped('name')) if report.type == 'account_type' else (report.type or False),
                'display_detail': report.display_detail,
                'debit': report_data.get('debit', 0.0), 
                'credit': report_data.get('credit', 0.0),
                'show_balance': report.type != 'header', # Headers typically don't show balances
            }
            if self.enable_filter and report_data.get('comp_bal') is not None:
                vals['balance_cmp'] = report_data['comp_bal'] * sign_multiplier
            
            processed_lines.append(vals)

            # Handle detail lines (accounts)
            if report.display_detail != 'no_detail' and report_data.get('account'):
                accounts_data_for_report_line = report_data['account']
                
                skip_details_for_this_line = False
                if report.type == 'accounts' and len(accounts_data_for_report_line) == 1:
                    account_id_single = list(accounts_data_for_report_line.keys())[0]
                    account_obj_single = self.env['account.account'].browse(account_id_single)
                    if account_obj_single: # Ensure account object exists
                        formatted_account_name = self._format_account_name(account_obj_single)
                        if formatted_account_name.strip().lower() == report.name.strip().lower(): # Case-insensitive comparison
                            _logger.info("PDF MODULE - STANDARD: Skipping redundant detail for '%s' (type 'accounts').", report.name)
                            skip_details_for_this_line = True
                
                if not skip_details_for_this_line:
                    sub_lines_for_report = []
                    for account_id, acc_value_dict in accounts_data_for_report_line.items():
                        account = self.env['account.account'].browse(account_id)
                        if not account: continue

                        acc_balance_signed = acc_value_dict.get('balance', 0.0) * sign_multiplier
                        
                        # Filter 2a: Hide zero-balance account details
                        hide_this_acc_detail = False
                        if self.hide_zero_balance_lines and self.company_id.currency_id.is_zero(acc_balance_signed):
                            if self.debit_credit: # If debit/credit shown, hide only if all three are zero
                                if self.company_id.currency_id.is_zero(acc_value_dict.get('debit', 0.0)) and \
                                   self.company_id.currency_id.is_zero(acc_value_dict.get('credit', 0.0)):
                                    hide_this_acc_detail = True
                            else: # If only balance shown, hide if balance is zero
                                 hide_this_acc_detail = True
                        if hide_this_acc_detail:
                            _logger.debug("PDF MODULE - STANDARD: Hiding zero-balance account detail: %s", self._format_account_name(account))
                            continue
                        
                        # Filter 2b: Display Account criteria
                        show_this_account_line = False
                        if self.display_account == 'all':
                            show_this_account_line = True
                        elif self.display_account == 'movement' and \
                             (not self.company_id.currency_id.is_zero(acc_value_dict.get('debit', 0.0)) or \
                              not self.company_id.currency_id.is_zero(acc_value_dict.get('credit', 0.0))):
                            show_this_account_line = True
                        elif self.display_account == 'not_zero' and \
                             not self.company_id.currency_id.is_zero(acc_balance_signed):
                            show_this_account_line = True
                        
                        if not show_this_account_line:
                            continue

                        sub_vals = {
                            'id': account.id, # Use account.id for detail lines if needed
                            'name': self._format_account_name(account),
                            'balance': acc_balance_signed,
                            'type': 'account', 
                            'level': (report.level or 0) + 1, 
                            'account_type': account.user_type_id.name or account.internal_type, # Prefer user_type_id.name
                            'debit': acc_value_dict.get('debit', 0.0),
                            'credit': acc_value_dict.get('credit', 0.0),
                            'show_balance': True, # Account details always show balance
                        }
                        if self.enable_filter and acc_value_dict.get('comp_bal') is not None:
                            sub_vals['balance_cmp'] = acc_value_dict['comp_bal'] * sign_multiplier
                        
                        sub_lines_for_report.append(sub_vals)
                    
                    processed_lines.extend(sorted(sub_lines_for_report, key=lambda x: x['name']))
        
        _logger.info("PDF MODULE - STANDARD: Final lines count for QWeb: %s", len(processed_lines))
        # _logger.debug("PDF MODULE - STANDARD: Final lines structure: %s", processed_lines) # Can be very verbose
        return processed_lines  
    
    # _get_current_fiscal_year_start_date() helper:
    def _get_current_fiscal_year_start_date(self): # Based on self.date_to of the instance it's called on
        if not self.date_to:
            # This wizard instance (self) might be a temporary one.
            # Its date_to should be set correctly by the calling logic.
            _logger.warning("Wizard %s: self.date_to is not set for _get_current_fiscal_year_start_date.", self.id or "NewId")
            # Fallback is tricky here if self.date_to is genuinely None from a temp wizard.
            # The calling code should ensure date_to is valid on the wizard passed to this.
            return fields.Date.today().replace(month=1, day=1) 
        return self.date_to.replace(month=1, day=1) # Simplified: Assumes Jan 1st for the year of self.date_to

    # _get_previous_fiscal_year_end_date() helper:
    def _get_previous_fiscal_year_end_date(self): # Based on self.date_to of the instance it's called on
        if not self.date_to:
            _logger.warning("Wizard %s: self.date_to is not set for _get_previous_fiscal_year_end_date.", self.id or "NewId")
            return None 
        current_fiscal_year_start = self._get_current_fiscal_year_start_date() # This uses self.date_to
        if not current_fiscal_year_start: return None # Should not happen if self.date_to is valid
        previous_fiscal_year_end = current_fiscal_year_start - relativedelta(days=1)
        _logger.info("Determined previous fiscal year end for date_to %s (wizard %s) as: %s",
                     self.date_to, self.id or "NewId", previous_fiscal_year_end)
        return previous_fiscal_year_end

    def _compute_report_balance(self, reports):
         # ... (input validation for 'reports' as in your last working version) ...
        if not isinstance(reports, models.Model):
            try:
                if isinstance(reports, (int, list)): reports = self.env['account.financial.report'].browse(reports)
                elif isinstance(reports, models.Model) and len(reports) == 1: reports = self.env['account.financial.report'].browse(reports.id)
                else:
                    if not reports: return {}
                    _logger.error("Unsupported 'reports' input type %s", type(reports))
                    return {}
            except Exception as e:
                _logger.error("Error processing 'reports' input: %s", e)
                return {}
        if not reports: return {}

        res = {}
        fields_to_compute = ['credit', 'debit', 'balance']

        # 'self' here is the wizard instance this method is currently operating on.
        _logger.info(
            "--- _compute_report_balance (wizard ID %s) CALLED for reports: %s. "
            "This wizard's dates: FROM %s TO %s ---",
            self.id or "NewId-InitialSelf", reports.mapped('name'), self.date_from, self.date_to
        )
        
        # Fiscal/period dates are determined based on the 'self.date_to' of the *current wizard instance* this method is running on.
        current_fy_start_for_this_context = self._get_current_fiscal_year_start_date() # Uses self.date_to
        prev_fy_end_for_this_context = self._get_previous_fiscal_year_end_date()     # Uses self.date_to

        for report in reports:
            if report.id in res: continue
            res[report.id] = dict.fromkeys(fields_to_compute, 0.0)
            if report.type in ['accounts', 'account_type']:
                 res[report.id]['account'] = {}

            # This is the wizard instance that will be used for calculations
            # for the P&L components of *this specific 'report' line*.
            wizard_to_use_for_this_line_components = self # Default to current wizard context
            
            # --- Special Date Logic based on report.report_type ---
            if report.report_type == 'CY_CUMULATIVE_PROFIT_TO_DATE': # For "Laba Tahun Ini"
                _logger.info("Report '%s' (ID %s) is CY_CUMULATIVE_PROFIT_TO_DATE. Current wizard is ID %s.", 
                             report.name, report.id, self.id or "NewId-SelfForLTI")
                if self.date_to and current_fy_start_for_this_context:
                    period_from = current_fy_start_for_this_context
                    period_to = self.date_to 
                    
                    wizard_to_use_for_this_line_components = self.new({
                        'date_from': period_from, 'date_to': period_to,
                        'project': self.project.id if self.project else False,
                        'target_move': self.target_move, 'journal_ids': [(6, 0, self.journal_ids.ids)],
                        'company_id': self.company_id.id, 'display_account': self.display_account, 
                        'account_report_id': self.account_report_id.id, 'report_format': self.report_format, 
                    })
                    _logger.info("CY_CUMULATIVE_PROFIT_TO_DATE: Set wizard_to_use_for_this_line_components to temp wizard (ID %s) for '%s'. Dates: %s to %s",
                                 wizard_to_use_for_this_line_components.id or "NewId-TempCY", report.name, 
                                 wizard_to_use_for_this_line_components.date_from, wizard_to_use_for_this_line_components.date_to)
                else:
                    _logger.warning("Cannot set specific dates for CY_CUMULATIVE_PROFIT_TO_DATE '%s', using dates from wizard ID %s.", 
                                    report.name, self.id or "NewId-SelfForLTI")
            
            elif report.report_type == 'PRIOR_YEARS_ACCUMULATED_PNL': # For "Laba Ditahan"
                _logger.info("Report '%s' (ID %s) is PRIOR_YEARS_ACCUMULATED_PNL. Current wizard is ID %s.", 
                             report.name, report.id, self.id or "NewId-SelfForLD")
                if prev_fy_end_for_this_context: 
                    period_from = None 
                    period_to = prev_fy_end_for_this_context
                    wizard_to_use_for_this_line_components = self.new({
                        'date_from': period_from, 'date_to': period_to,
                        'project': self.project.id if self.project else False,
                        'target_move': self.target_move, 'journal_ids': [(6, 0, self.journal_ids.ids)],
                        'company_id': self.company_id.id, 'display_account': self.display_account,
                        'account_report_id': self.account_report_id.id, 'report_format': self.report_format,
                    })
                    _logger.info("PRIOR_YEARS_ACCUMULATED_PNL: Set wizard_to_use_for_this_line_components to temp wizard (ID %s) for '%s'. Dates: earliest to %s",
                                 wizard_to_use_for_this_line_components.id or "NewId-TempPY", report.name, 
                                 wizard_to_use_for_this_line_components.date_to)
                else:
                    _logger.warning("Cannot set specific dates for PRIOR_YEARS_ACCUMULATED_PNL '%s', using dates from wizard ID %s.", 
                                    report.name, self.id or "NewId-SelfForLD")

            # --- Actual Calculation using 'wizard_to_use_for_this_line_components' ---
            if report.type == 'accounts':
                account_balances = wizard_to_use_for_this_line_components._compute_account_balance(report.account_ids)
                if account_balances:
                    res[report.id]['account'].update(account_balances)
                    for value in account_balances.values():
                        for field_name in fields_to_compute:
                            res[report.id][field_name] += value.get(field_name, 0.0)

            elif report.type == 'account_type':
                accounts = self.env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
                if accounts:
                    all_account_balances = wizard_to_use_for_this_line_components._compute_account_balance(accounts)
                    if all_account_balances:
                        res[report.id]['account'].update(all_account_balances)
                        for value in all_account_balances.values():
                            for field_name in fields_to_compute:
                                res[report.id][field_name] += value.get(field_name, 0.0)
            
            elif report.type == 'sum_report_pl' and report.account_report_id:
                _logger.info("RECURSIVE CALL for sum_report_pl '%s': Will call _compute_report_balance on wizard (ID %s), dates FROM %s TO %s, for target '%s'",
                             report.name,
                             wizard_to_use_for_this_line_components.id or "NewId-sum_report_pl-CALLER", 
                             wizard_to_use_for_this_line_components.date_from, 
                             wizard_to_use_for_this_line_components.date_to,
                             report.account_report_id.name)
                res2 = wizard_to_use_for_this_line_components._compute_report_balance(report.account_report_id) 
                source_balances = res2.get(report.account_report_id.id, {})
                for field_name in fields_to_compute:
                    res[report.id][field_name] += source_balances.get(field_name, 0.0)

            elif report.type in ('account_report', 'sum', 'sum_report'):
                target_children = None
                if report.type == 'account_report': target_children = report.account_report_id
                elif report.type == 'sum': target_children = report.children_ids
                elif report.type == 'sum_report': target_children = report.report_line_ids

                if target_children:
                    _logger.debug("Type '%s' for '%s': Calling _compute_report_balance on wizard ID %s for children/source", 
                                  report.type, report.name, wizard_to_use_for_this_line_components.id or "NewId-Sum")
                    res2 = wizard_to_use_for_this_line_components._compute_report_balance(target_children)
                    
                    ids_to_sum_from = target_children.ids if isinstance(target_children, models.Model) else []
                    if report.type == 'account_report' and report.account_report_id and isinstance(report.account_report_id, models.Model):
                        ids_to_sum_from = [report.account_report_id.id]

                    for item_id in ids_to_sum_from:
                        item_balances = res2.get(item_id, {})
                        for field_name in fields_to_compute:
                            res[report.id][field_name] += item_balances.get(field_name, 0.0)
            
           
            for field_name in fields_to_compute: # Float conversion
                if not isinstance(res[report.id][field_name], (int, float)):
                    try: res[report.id][field_name] = float(res[report.id][field_name])
                    except: res[report.id][field_name] = 0.0
            _logger.info("Report '%s' (ID %s) final computed balances: %s", report.name, report.id, res[report.id])
        
        _logger.info(
            "--- _compute_report_balance FINISHED for original wizard (%s) main dates: FROM %s TO %s. Returning: %s ---",
            self.id, self.date_from, self.date_to, res
        )
        return res
        


    def _compute_account_balance(self, accounts):
        """ compute the balance, debit and credit for the provided accounts """
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = dict.fromkeys(mapping, 0.0)
        if accounts:
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            tables = tables.replace('"', '') if tables else "account_move_line"
            old_year = fields.Date.today() - relativedelta(years=20)
            from_date = self.date_from if self.date_from else old_year
            to_date = self.date_to if self.date_to else fields.Date.today()
            target_move = self.target_move

            if self.project:
                sql = ("""SELECT account_id as id, aa.name as account, 
                        COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance, 
                        COALESCE(SUM(debit), 0) as debit, 
                        COALESCE(SUM(credit), 0) as credit 
                        FROM account_move_line ml
                        JOIN account_move am ON (ml.move_id=am.id)
                        LEFT JOIN account_account aa ON (ml.account_id=aa.id)
                        LEFT JOIN project_project pro ON (ml.project=pro.id)
                        WHERE account_id IN %s 
                        AND am.project = %s 
                        AND ml.date >= %s 
                        AND ml.date <= %s 
                        AND am.state IN %s 
                        GROUP BY account_id, account""")
                params = (tuple(accounts._ids), self.project.id, from_date, to_date, tuple(['draft', 'posted']))
            else:
                sql = ("""SELECT account_id as id, aa.name as account, 
                        COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance, 
                        COALESCE(SUM(debit), 0) as debit, 
                        COALESCE(SUM(credit), 0) as credit 
                        FROM account_move_line ml
                        JOIN account_move am ON (ml.move_id=am.id)
                        LEFT JOIN account_account aa ON (ml.account_id=aa.id)
                        LEFT JOIN project_project pro ON (ml.project=pro.id)
                        WHERE account_id IN %s 
                        AND ml.date >= %s 
                        AND ml.date <= %s 
                        AND am.state IN %s 
                        GROUP BY account_id, account""")
                params = (tuple(accounts._ids), from_date, to_date, tuple(['draft', 'posted']))
            self.env.cr.execute(sql, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row
        return res

    def _get_current_fiscal_year_start_date(self):
        if not self.date_to:
            _logger.warning("_get_current_fiscal_year_start_date: self.date_to is not set.")
            return None
        # Simplified: Assumes fiscal year starts Jan 1st of the year of self.date_to.
        # Implement robust fiscal year lookup if needed.
        current_fiscal_year_start = self.date_to.replace(month=1, day=1)
        _logger.info("Determined current fiscal year start for date_to %s as: %s", self.date_to, current_fiscal_year_start)
        return current_fiscal_year_start

    def _compute_report_balance_20250528(self, reports):
        if not isinstance(reports, models.Model):
            try:
                if isinstance(reports, (int, list)): reports = self.env['account.financial.report'].browse(reports)
                elif isinstance(reports, models.Model) and len(reports) == 1: reports = self.env['account.financial.report'].browse(reports.id)
                else:
                    if not reports: return {}
                    _logger.error("Unsupported 'reports' input type %s", type(reports))
                    return {}
            except Exception as e:
                _logger.error("Error processing 'reports' input: %s", e)
                return {}
        if not reports: return {}

        res = {}
        fields_to_compute = ['credit', 'debit', 'balance']
        _logger.info(
            "--- _compute_report_balance CALLED for reports: %s. Current wizard (%s) dates: FROM %s TO %s ---",
            reports.mapped('name'), self.id, self.date_from, self.date_to
        )
        current_fiscal_year_start_date = self._get_current_fiscal_year_start_date()

        for report in reports:
            if report.id in res: continue
            res[report.id] = dict.fromkeys(fields_to_compute, 0.0)
            if report.type in ['accounts', 'account_type']:
                 res[report.id]['account'] = {}

            calculation_wizard_for_line = self # Default
            create_new_wizard_for_line = False
            target_pl_date_from = None
            target_pl_date_to = None

            # Special handling for "Cumulative P&L for Current Fiscal Year up to date_to"
            if report.report_type == 'CY_CUMULATIVE_PROFIT_TO_DATE': # e.g., for your "Laba Tahun Ini" line
                _logger.info("Report '%s' (ID %s) is CY_CUMULATIVE_PROFIT_TO_DATE.", report.name, report.id)
                if not self.date_to or not current_fiscal_year_start_date:
                    _logger.warning("Cannot calc CY_CUMULATIVE_PROFIT_TO_DATE for '%s': missing date_to or fiscal_year_start.", report.name)
                    res[report.id]['balance'] = 0.0
                    continue 
                
                target_pl_date_from = current_fiscal_year_start_date
                target_pl_date_to = self.date_to # Use the main wizard's date_to
                create_new_wizard_for_line = True
                _logger.info("CY_CUMULATIVE_PROFIT_TO_DATE '%s': P&L period: FROM %s TO %s", 
                             report.name, target_pl_date_from, target_pl_date_to)

            # You might still have the "current month profit" logic if it's used elsewhere (e.g., on a P&L report explicitly)
            # elif report.report_type == 'CY_PROFIT_CURRENT_MONTH': 
            #     _logger.info("Report '%s' (ID %s) is CY_PROFIT_CURRENT_MONTH.", report.name, report.id)
            #     if not self.date_to: # ... error handling ...
            #         res[report.id]['balance'] = 0.0; continue
            #     target_pl_date_from = self.date_to.replace(day=1)
            #     target_pl_date_to = self.date_to
            #     create_new_wizard_for_line = True

            if create_new_wizard_for_line:
                calculation_wizard_for_line = self.new({
                    'date_from': target_pl_date_from,
                    'date_to': target_pl_date_to,
                    'project': self.project.id if self.project else False,
                    'target_move': self.target_move,
                    'journal_ids': [(6, 0, self.journal_ids.ids)],
                    'company_id': self.company_id.id,
                    'display_account': self.display_account,
                })
                _logger.info("Created new wizard (%s) for P&L aspect of report '%s' (ID %s) with dates: FROM %s TO %s",
                             calculation_wizard_for_line.id, report.name, report.id, 
                             calculation_wizard_for_line.date_from, calculation_wizard_for_line.date_to)
            
            # --- Actual Calculation using 'calculation_wizard_for_line' ---

            if report.type == 'accounts':
                _logger.info("Report '%s' (type 'accounts'): Using wizard (%s) dates: %s to %s",
                             report.name, calculation_wizard_for_line.id, calculation_wizard_for_line.date_from, calculation_wizard_for_line.date_to)
                account_balances = calculation_wizard_for_line._compute_account_balance(report.account_ids)
                res[report.id]['account'].update(account_balances)
                for value in account_balances.values():
                    for field_name in fields_to_compute:
                        res[report.id][field_name] += value.get(field_name, 0.0)

            elif report.type == 'account_type':
                _logger.info("Report '%s' (type 'account_type'): Processing with wizard (%s) dates: %s to %s",
                             report.name, calculation_wizard_for_line.id, calculation_wizard_for_line.date_from, calculation_wizard_for_line.date_to)
                accounts = self.env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
                if not accounts: continue

                all_account_balances = calculation_wizard_for_line._compute_account_balance(accounts)
                res[report.id]['account'].update(all_account_balances)
                for value in all_account_balances.values():
                    for field_name in fields_to_compute:
                        res[report.id][field_name] += value.get(field_name, 0.0)

            elif report.type == 'sum_report_pl' and report.account_report_id:
                # This report line ('report') gets its value from another P&L summary line ('report.account_report_id').
                # The P&L summary line must be calculated for the period defined by 'calculation_wizard_for_line'.
                _logger.info("Report '%s' (type 'sum_report_pl'): Target P&L source '%s'. Using wizard (%s) dates: %s to %s for recursive call to calculate source.",
                             report.name, report.account_report_id.name, calculation_wizard_for_line.id, 
                             calculation_wizard_for_line.date_from, calculation_wizard_for_line.date_to)
                
                # The recursive call to calculate the source P&L is made on 'calculation_wizard_for_line'
                res2 = calculation_wizard_for_line._compute_report_balance(report.account_report_id) 
                source_balances = res2.get(report.account_report_id.id, {})
                for field_name in fields_to_compute:
                    res[report.id][field_name] += source_balances.get(field_name, 0.0)
                _logger.info("Report '%s' ('sum_report_pl') final balance: %s (from source '%s')", 
                             report.name, res[report.id]['balance'], report.account_report_id.name)

            elif report.type in ('account_report', 'sum', 'sum_report'):
                target_children_or_source_report = None
                if report.type == 'account_report': target_children_or_source_report = report.account_report_id
                elif report.type == 'sum': target_children_or_source_report = report.children_ids
                elif report.type == 'sum_report': target_children_or_source_report = report.report_line_ids

                if target_children_or_source_report:
                    _logger.info("Report '%s' (type '%s'): Recursively calling on wizard (%s) dates: %s to %s for targets: %s.",
                                 report.name, report.type, calculation_wizard_for_line.id,
                                 calculation_wizard_for_line.date_from, calculation_wizard_for_line.date_to,
                                 target_children_or_source_report.mapped('name'))
                    res2 = calculation_wizard_for_line._compute_report_balance(target_children_or_source_report)
                    
                    ids_to_sum_from = target_children_or_source_report.ids if isinstance(target_children_or_source_report, models.Model) else []
                    if report.type == 'account_report' and report.account_report_id:
                        ids_to_sum_from = [report.account_report_id.id]

                    for item_id in ids_to_sum_from:
                        item_balances = res2.get(item_id, {})
                        for field_name in fields_to_compute:
                            res[report.id][field_name] += item_balances.get(field_name, 0.0)
            
            for field_name in fields_to_compute: # Float conversion
                if not isinstance(res[report.id][field_name], (int, float)):
                    try: res[report.id][field_name] = float(res[report.id][field_name])
                    except: res[report.id][field_name] = 0.0
            _logger.info("Report '%s' (ID %s) final computed balances: %s", report.name, report.id, res[report.id])
        
        _logger.info(
            "--- _compute_report_balance FINISHED for original wizard (%s) main dates: FROM %s TO %s. Returning: %s ---",
            self.id, self.date_from, self.date_to, res
        )
        return res


    def get_last_day_of_month(self, year, month):
        if month in ['01', '03', '05', '07', '08', '10', '12']:
            return '31'
        elif month in ['04', '06', '09', '11']:
            return '30'
        elif month == '02':
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                return '29'  # Leap year
            else:
                return '28'

    def _compute_monthly_account_balance(self, accounts, bulan, year=None):
        """ Compute the monthly balance, debit, and credit for the provided accounts """
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = dict.fromkeys(mapping, 0.0)
        if accounts:
            _logger.info("Computing monthly account balance for accounts: %s with bulan: %s and year: %s", accounts, bulan, year)
            
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            tables = tables.replace('"', '') if tables else "account_move_line"
            to_date = self.env.context.get('date_to', fields.Date.today())
            target_move = self.target_move

            _logger.info("Tables: %s, Date To: %s, Target Move: %s", tables, to_date, target_move)

            if self.project:
                sql = ("""SELECT account_id as id, aa.name as account, 
                        COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance, 
                        COALESCE(SUM(debit), 0) as debit, 
                        COALESCE(SUM(credit), 0) as credit 
                        FROM account_move_line ml
                        JOIN account_move am ON (ml.move_id=am.id)
                        LEFT JOIN account_account aa ON (ml.account_id=aa.id)
                        LEFT JOIN project_project pro ON (ml.project=pro.id)
                        WHERE account_id IN %s 
                        AND am.project = %s 
                        AND ml.date <= %s
                        AND am.state IN %s 
                        GROUP BY account_id, account""")
                end_day = self.get_last_day_of_month(year, bulan)
                to_date_str = '{}-{}-{}'.format(year, bulan, end_day)
                params = (tuple(accounts._ids), self.project.id, to_date_str, tuple(['draft', 'posted']))
            else:
                sql = ("""SELECT account_id as id, aa.name as account, 
                        COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance, 
                        COALESCE(SUM(debit), 0) as debit, 
                        COALESCE(SUM(credit), 0) as credit 
                        FROM account_move_line ml
                        JOIN account_move am ON (ml.move_id=am.id)
                        LEFT JOIN account_account aa ON (ml.account_id=aa.id)
                        LEFT JOIN project_project pro ON (ml.project=pro.id)
                        WHERE account_id IN %s 
                        AND ml.date <= %s
                        AND am.state IN %s 
                        GROUP BY account_id, account""")
                end_day = self.get_last_day_of_month(year, bulan)
                to_date_str = '{}-{}-{}'.format(year, bulan, end_day)
                params = (tuple(accounts._ids), to_date_str, tuple(['draft', 'posted']))

            _logger.info("Executing SQL: %s", sql)
            _logger.info("Parameters: %s", params)
            
            self.env.cr.execute(sql, params)
            for row in self.env.cr.dictfetchall():
                _logger.info("Fetched row: %s", row)
                res[row['id']] = row
        return res


    def _compute_rasio_keuangan_balance(self, reports, bulan=None, year=None):
        res = {}
        fields_to_compute = ['credit', 'debit', 'balance']
        
        used_context_dict = self.env.context
        year = used_context_dict.get('date_to', fields.Date.today()).year
        _logger.info("Using year: %s from context", year)
        
        _logger.info("Unlinking existing computed report balances")
        # Unlink existing records before creating new ones
        self.env['computed.report.balance'].search([]).unlink()

        for report in reports:
            _logger.info("Processing report: %s", report.name)
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields_to_compute)

            if report.type == 'accounts':
                if bulan == '00':  # Yearly report
                    _logger.info("Computing yearly balance for accounts")
                    res[report.id]['account'] = self._compute_account_balance(report.account_ids)
                else:  # Monthly report
                    _logger.info("Computing monthly balance for accounts with bulan: %s and year: %s", bulan, year)
                    res[report.id]['account'] = self._compute_monthly_account_balance(report.account_ids, bulan, year)
                for value in res[report.id]['account'].values():
                    for field in fields_to_compute:
                        res[report.id][field] += value.get(field)

            elif report.type == 'account_type':
                accounts = self.env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
                if bulan == '00':  # Yearly report
                    _logger.info("Computing yearly balance for account types")
                    res[report.id]['account'] = self._compute_account_balance(accounts)
                else:  # Monthly report
                    _logger.info("Computing monthly balance for account types with bulan: %s and year: %s", bulan, year)
                    res[report.id]['account'] = self._compute_monthly_account_balance(accounts, bulan, year)
                for value in res[report.id]['account'].values():
                    for field in fields_to_compute:
                        res[report.id][field] += value.get(field)

            elif report.type == 'account_report' and report.account_report_id:
                date_to = self.env.context.get('date_to', fields.Date.today())
                if bulan == '00':  # Yearly
                    specific_date = fields.Date.to_date('{}-01-01'.format(date_to.year))
                    date_to = fields.Date.to_date('{}-12-31'.format(date_to.year))
                else:
                    specific_date = fields.Date.to_date('{}-{}-01'.format(date_to.year, bulan))
                    end_day = self.get_last_day_of_month(date_to.year, bulan)
                    date_to = fields.Date.to_date('{}-{}-{}'.format(date_to.year, bulan, end_day))

                _logger.info("date_to_account_report: %s", date_to)

                new_context = dict(self.env.context, date_to=date_to)
                _logger.info("New context for account_report: %s", new_context)
                res2 = self.with_context(new_context)._compute_rasio_keuangan_balance(report.account_report_id, bulan, year)
                for key, value in res2.items():
                    for field in fields_to_compute:
                        res[report.id][field] += value[field]

            elif report.type == 'sum_report' and report.report_line_ids:
                _logger.info("Computing balance for sum_report lines in report: %s", report.name)
                date_to = self.env.context.get('date_to', fields.Date.today())
                if bulan == '00':  # Yearly
                    specific_date = fields.Date.to_date('{}-01-01'.format(date_to.year))
                    date_to = fields.Date.to_date('{}-12-31'.format(date_to.year))
                else:
                    specific_date = fields.Date.to_date('{}-{}-01'.format(date_to.year, bulan))
                    end_day = self.get_last_day_of_month(date_to.year, bulan)
                    date_to = fields.Date.to_date('{}-{}-{}'.format(date_to.year, bulan, end_day))

                _logger.info("date_to_sum_report: %s", date_to)

                new_context = dict(self.env.context, date_to=date_to)
                _logger.info("New context for sum_report: %s", new_context)
                res2 = self.with_context(new_context)._compute_rasio_keuangan_balance(report.report_line_ids, bulan, year)
                for key, value in res2.items():
                    for field in fields_to_compute:
                        res[report.id][field] += value[field]

            elif report.type == 'sum':
                _logger.info("Computing balance for sum of children reports in report: %s", report.name)
                date_to = self.env.context.get('date_to', fields.Date.today())
                if bulan == '00':  # Yearly
                    specific_date = fields.Date.to_date('{}-01-01'.format(date_to.year))
                    date_to = fields.Date.to_date('{}-12-31'.format(date_to.year))
                else:
                    specific_date = fields.Date.to_date('{}-{}-01'.format(date_to.year, bulan))
                    end_day = self.get_last_day_of_month(date_to.year, bulan)
                    date_to = fields.Date.to_date('{}-{}-{}'.format(date_to.year, bulan, end_day))

                _logger.info("date_to_sum_only: %s", date_to)

                new_context = dict(self.env.context, date_to=date_to)
                _logger.info("New context for sum: %s", new_context)
                res2 = self.with_context(new_context)._compute_rasio_keuangan_balance(report.children_ids, bulan, year)
                for key, value in res2.items():
                    for field in fields_to_compute:
                        res[report.id][field] += value[field]

            # Store the computed values in the database
            for field in fields_to_compute:
                self.env['computed.report.balance'].create({
                    'report_id': report.id,
                    'field_name': field,
                    'value': res[report.id][field],
                    'compute_date': fields.Date.context_today(self),
                })
                _logger.info("Stored computed value for report: %s, field: %s, value: %s", report.id, field, res[report.id][field])

        return res

    def get_account_lines_20250528(self):
        lines = []
        account_report = self.env['account.financial.report'].search([('id', '=', self.account_report_id.id)])
        child_reports = account_report._get_children_by_order()
        used_context_dict = {
            'state': self.target_move,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'journal_ids': [a.id for a in self.journal_ids],
            'strict_range': True
        }
        res = self.with_context(used_context_dict)._compute_report_balance(child_reports)
        if self.enable_filter:
            comparison_context_dict = {
                'journal_ids': [a.id for a in self.journal_ids],
                'state': self.target_move,
            }
            if self.filter_cmp == 'filter_date':
                comparison_context_dict.update({"date_to": self.date_to_cmp,
                                                "date_from": self.date_from_cmp})
            comparison_res = self.with_context(comparison_context_dict)._compute_report_balance(child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in comparison_res[report_id].get('account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']

        for report in child_reports:
            vals = {
                'name': report.name,
                'balance': res[report.id]['balance'] * report.sign,
                'type': report.type,
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type or False,  # used to underline the financial report balances
            }
            if self.debit_credit:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if self.enable_filter:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * report.sign

            lines.append(vals)
            if report.display_detail == 'no_detail':
                continue

            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value in res[report.id]['account'].items():
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance': value['balance'] * report.sign or 0.0,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and 4,
                        'account_type': account.internal_type,
                    }
                    if self.debit_credit:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not account.company_id.currency_id.is_zero(
                                vals['debit']) or not account.company_id.currency_id.is_zero(vals['credit']):
                            flag = True
                    if not account.company_id.currency_id.is_zero(vals['balance']):
                        flag = True
                    if self.enable_filter:
                        vals['balance_cmp'] = value['comp_bal'] * report.sign
                        if not account.company_id.currency_id.is_zero(vals['balance_cmp']):
                            flag = True
                    if flag:
                        sub_lines.append(vals)
                lines += sorted(sub_lines, key=lambda sub_line: sub_line['name'])
        return lines


    @api.multi
    def check_report_20250528(self):
        if not self.account_report_id:
            raise UserError('Misconfiguration. Please Update module.\n There is no any associated report.')
        final_dict = {}
        old_year = fields.Date.today() - relativedelta(years=20)
        from_date = self.date_from if self.date_from else old_year
        to_date = self.date_to if self.date_to else fields.Date.today()

        if self.date_to or self.date_from:
            if to_date <= from_date:
                raise UserError('End date should be greater then to start date.')
        if self.enable_filter and self.filter_cmp == 'filter_date':
            if self.date_to_cmp <= self.date_from_cmp:
                raise UserError('Comparison end date should be greater then to Comparison start date.')
        report_lines = self.get_account_lines()
        final_dict.update({'report_lines': report_lines,
                           'name': self.account_report_id.name,
                           'debit_credit': self.debit_credit,
                           'enable_filter': self.enable_filter,
                           'label_filter': self.label_filter,
                           'target_move': self.target_move,
                           'date_from': self.date_from,
                           'date_to': self.date_to,
                           'project': self.project.no,
                           'create_date': self.create_date,
                           })
        return self.env.ref('bi_financial_pdf_reports.action_report_balancesheet').report_action(self, data=final_dict)


    def _get_accounts(self, accounts, display_account):
        account_result = {}
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res['code'] = account.code
            res['name'] = account.name
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
                account_res.append(res)
        return account_res

    @api.multi
    def print_trial_balance(self):
        if self.date_to or self.date_from:
            if self.date_to <= self.date_from:
                raise UserError('End date should be greater then to start date.')
        display_account = self.display_account
        accounts = self.env['account.account'].search([])
        used_context_dict = {
            'state': self.target_move,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'journal_ids': False,
            'strict_range': True
        }
        account_res = self.with_context(used_context_dict)._get_accounts(accounts, display_account)
        final_dict = {}
        final_dict.update({'account_res': account_res,
                           'display_account': self.display_account,
                           'target_move': self.target_move,
                           'date_from': self.date_from,
                           'date_to': self.date_to,

                           })
        return self.env.ref('bi_financial_pdf_reports.action_report_trial_balance').report_action(self, data=final_dict)

    def _get_account_move_entry(self, accounts, init_balance, sortby, display_account):
        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}
        if init_balance:
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(
                date_from=self.env.context.get('date_from'), date_to=False, initial_bal=True)._query_get()
            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
            sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, '' AS lcode, 0.0 AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, '' AS lpartner_id,\
                '' AS move_name, '' AS mmove_id, '' AS currency_code,\
                NULL AS currency_id,\
                '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                '' AS partner_name\
                FROM account_move_line l\
                LEFT JOIN account_move m ON (l.move_id=m.id)\
                LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                LEFT JOIN account_invoice i ON (m.id =i.move_id)\
                JOIN account_journal j ON (l.journal_id=j.id)\
                WHERE l.account_id IN %s""" + filters + ' GROUP BY l.account_id')
            params = (tuple(accounts.ids),) + tuple(init_where_params)
            cr.execute(sql, params)
            for row in cr.dictfetchall():
                move_lines[row.pop('account_id')].append(row)

        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'

        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = MoveLine._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        filters = filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

        # Get move lines base on sql query and Calculate the total balance of move lines
        sql = ('''SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,\
            m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name\
            FROM account_move_line l\
            JOIN account_move m ON (l.move_id=m.id)\
            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
            JOIN account_journal j ON (l.journal_id=j.id)\
            JOIN account_account acc ON (l.account_id = acc.id) \
            WHERE l.account_id IN %s ''' + filters + ''' GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name ORDER BY ''' + sql_sort)
        params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)

        for row in cr.dictfetchall():
            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('account_id')].append(row)

        # Calculate the debit, credit and balance for Accounts
        account_res = []
        for account in accounts:
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['code'] = account.code
            res['name'] = account.name
            res['move_lines'] = move_lines[account.id]
            for line in res.get('move_lines'):
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['balance'] = line['balance']
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)

        return account_res

    @api.multi
    def print_general_ledger(self):
        if self.date_to or self.date_from:
            if self.date_to <= self.date_from:
                raise UserError('End date should be greater then to start date.')
        init_balance = self.initial_balance
        sortby = self.sortby
        display_account = self.display_account
        codes = []
        if self.journal_ids:
            codes = [journal.code for journal in
                     self.env['account.journal'].search([('id', 'in', self.journal_ids.ids)])]
        used_context_dict = {
            'state': self.target_move,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'journal_ids': [a.id for a in self.journal_ids],
            'strict_range': True
        }
        accounts = self.env['account.account'].search([])
        accounts_res = self.with_context(used_context_dict)._get_account_move_entry(accounts, init_balance, sortby,
                                                                                    display_account)
        final_dict = {}
        final_dict.update(
            {
                'time': time,
                'Account': accounts_res,
                'print_journal': codes,
                'display_account': display_account,
                'target_move': self.target_move,
                'sortby': sortby,
                'date_from': self.date_from,
                'date_to': self.date_to
            }
        )
        return self.env.ref('bi_financial_pdf_reports.action_report_general_ledger').report_action(self,
                                                                                                   data=final_dict)

