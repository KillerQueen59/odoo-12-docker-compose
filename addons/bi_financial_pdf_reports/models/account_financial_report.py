# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_
import time
from datetime import datetime, date # Ensure date is imported
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from decimal import Decimal, getcontext
import logging
import psycopg2 # For catching specific SQL errors

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

    @api.multi # Keep api.multi if your Odoo version style requires it (typically < 13/14)
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
        ('sum_report_pl', 'Sum Report From PL'), # Crucial for P&L figures in BS

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
    report_type = fields.Char('Report Type', help="Special type for Balance Sheet lines that derive from P&L, e.g., 'CY_CUMULATIVE_PROFIT_TO_DATE' for Current Year Profit or 'PRIOR_YEARS_ACCUMULATED_PNL' for Retained Earnings.")

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
    date_from = fields.Date(string='Start Date',) # For BS, this is often ignored for BS lines but used for P&L components
    date_to = fields.Date(string='End Date',)     # Primary date for BS and P&L period end
    display_account = fields.Selection([('all', 'All'), ('movement', 'With movements'),
                                        ('not_zero', 'With balance is not equal to 0'), ],
                                       string='Display Accounts', required=True, default='movement')
    target_move = fields.Selection([('all', 'All Entries (Posted and Draft)'), # New 'all' option, made default
                                ('posted', 'Posted Entries Only'),# ('draft_only', 'Draft Entries Only'), # Optional: if you need a specific "draft only"
        ], string='Target Moves', required=False, default='all') # Default set to 'all'
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
    report_name = fields.Char('Report name', compute="_get_account_report_name")

    show_account_code = fields.Boolean(string="Show Account Code", default=False)


    report_format = fields.Selection([
        ('standard', 'Standard Period'),
        ('monthly', 'Monthly Period')
    ], string="Report Format", default='standard', required=True)

    year_filter = fields.Integer(string="Year", default=lambda self: fields.Date.today().year)

    hide_zero_balance_lines = fields.Boolean(
        string="Hide Zero-Balance",
        default=False,
        help="If checked, lines with a final balance of zero will not be displayed on the report (for standard period reports)."
    )

    # --- HELPER METHODS FOR FISCAL PERIODS ---
    def _get_current_fiscal_year_start_date(self):
        """
        Determines the start date of the fiscal year based on self.date_to.
        This is a simplified version assuming fiscal year starts Jan 1st.
        For more complex fiscal years, consult company settings or account.fiscal.year.
        """
        if not self.date_to:
            _logger.warning("Wizard %s: self.date_to is not set for _get_current_fiscal_year_start_date. Using fallback.", self.id or "UnsavedWizard")
            # Fallback to Jan 1st of current year if date_to is not available
            return fields.Date.today().replace(month=1, day=1)
        # Simplified assumption:
        return self.date_to.replace(month=1, day=1)

    def _get_previous_fiscal_year_end_date(self):
        """
        Determines the end date of the previous fiscal year based on self.date_to.
        """
        if not self.date_to:
            _logger.warning("Wizard %s: self.date_to is not set for _get_previous_fiscal_year_end_date. Cannot determine.", self.id or "UnsavedWizard")
            return None
        current_fiscal_year_start = self._get_current_fiscal_year_start_date() # Uses self.date_to of the current wizard
        if not current_fiscal_year_start:
             _logger.warning("Wizard %s: Could not determine current fiscal year start for _get_previous_fiscal_year_end_date.", self.id or "UnsavedWizard")
             return None
        previous_fiscal_year_end = current_fiscal_year_start - relativedelta(days=1)
        _logger.info("Determined previous fiscal year end for wizard %s (report date_to %s) as: %s",
                     self.id or "UnsavedWizard", self.date_to, previous_fiscal_year_end)
        return previous_fiscal_year_end

    # --- CORE BALANCE COMPUTATION ---
    def _compute_account_balance(self, accounts):
        """
        This is now a simple wrapper around the new high-performance method.
        It computes for the main date range of the wizard.
        """
        # Create an empty result map first
        res = {acc.id: {'debit': 0.0, 'credit': 0.0, 'balance': 0.0} for acc in accounts}
        # Get balances and update the map
        balances = self._get_balances_from_move_lines(accounts, self.date_from, self.date_to)
        res.update(balances)
        return res

    def _compute_report_balance(self, reports):
        """
        This is the new, high-performance report balance calculator.
        It fetches all data once, then assembles the report in memory.
        """
        res = {r.id: {'debit': 0.0, 'credit': 0.0, 'balance': 0.0, 'account': {}} for r in reports}
        if not reports:
            return res

        _logger.info("PERFORMANCE: Starting high-performance _compute_report_balance.")
        
        # 1. Get all unique accounts from the entire report structure at once.
        all_accounts = self._get_all_accounts_in_report(reports)
        _logger.info("PERFORMANCE: Found %s unique accounts to process.", len(all_accounts))

        # 2. Get all balances for those accounts in a SINGLE database query.
        account_balances = self._get_balances_from_move_lines(all_accounts, self.date_from, self.date_to)
        _logger.info("PERFORMANCE: Fetched balances for %s accounts from the database.", len(account_balances))
        
        # This will hold the balance for P&L-derived lines, calculated only once if needed.
        cy_pnl_balance = None
        prior_pnl_balance = None

        # 3. Build the report totals in Python memory (very fast).
        for report in reports:
            # Handle lines that are based directly on accounts
            if report.type in ('accounts', 'account_type'):
                line_accounts = report.account_ids if report.type == 'accounts' else self.env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
                for acc in line_accounts:
                    if acc.id in account_balances:
                        res[report.id]['debit'] += account_balances[acc.id].get('debit', 0.0)
                        res[report.id]['credit'] += account_balances[acc.id].get('credit', 0.0)
                        res[report.id]['balance'] += account_balances[acc.id].get('balance', 0.0)
                        res[report.id]['account'][acc.id] = account_balances[acc.id]

            # Handle special Balance Sheet lines derived from P&L
            elif report.report_type == 'CY_CUMULATIVE_PROFIT_TO_DATE':
                if cy_pnl_balance is None: # Calculate only once
                    pl_config = self.env['account.financial.report'].search([('name', 'ilike', 'Profit and Loss')], limit=1)
                    if pl_config:
                        pl_accounts = self._get_all_accounts_in_report(pl_config)
                        current_date_to = fields.Date.from_string(self.date_to)
                        fy_start = current_date_to.replace(day=1, month=1)
                        pl_balances = self._get_balances_from_move_lines(pl_accounts, fy_start, current_date_to)
                        cy_pnl_balance = sum(b.get('balance', 0.0) for b in pl_balances.values())
                    else:
                        cy_pnl_balance = 0.0
                res[report.id]['balance'] = cy_pnl_balance
            
            elif report.report_type == 'PRIOR_YEARS_ACCUMULATED_PNL':
                 if prior_pnl_balance is None: # Calculate only once
                    pl_config = self.env['account.financial.report'].search([('name', 'ilike', 'Profit and Loss')], limit=1)
                    if pl_config:
                        pl_accounts = self._get_all_accounts_in_report(pl_config)
                        current_date_to = fields.Date.from_string(self.date_to)
                        fy_start = current_date_to.replace(day=1, month=1)
                        prior_years_end_date = fy_start - relativedelta(days=1)
                        pl_balances = self._get_balances_from_move_lines(pl_accounts, False, prior_years_end_date)
                        prior_pnl_balance = sum(b.get('balance', 0.0) for b in pl_balances.values())
                    else:
                        prior_pnl_balance = 0.0
                 res[report.id]['balance'] = prior_pnl_balance

        # 4. Recursively sum up parent lines. This is now super fast as it's all in-memory.
        for report in reports.sorted('level', reverse=True):
            if report.type in ['sum', 'account_report', 'sum_report', 'header']:
                children_to_sum = report.children_ids if report.type in ['sum', 'header'] else (report.account_report_id or report.report_line_ids)
                for child in children_to_sum:
                    if child.id in res:
                        res[report.id]['balance'] += res[child.id]['balance']
                        res[report.id]['debit'] += res[child.id]['debit']
                        res[report.id]['credit'] += res[child.id]['credit']
        return res

    def _get_balances_from_move_lines(self, accounts, date_from, date_to):
        """
        This is the new high-performance engine.
        It executes a single SQL query to get balances for a given set of accounts and date range.
        """
        if not accounts:
            return {}

        account_ids_tuple = tuple(accounts.ids)
        
        # Build query parts dynamically
        where_params = [account_ids_tuple, self.company_id.id]
        where_clause_parts = ["aml.account_id IN %s", "aml.company_id = %s"]

        if date_from:
            where_clause_parts.append("aml.date >= %s")
            where_params.append(date_from)
        if date_to:
            where_clause_parts.append("aml.date <= %s")
            where_params.append(date_to)
        if self.target_move == 'posted':
            where_clause_parts.append("am.state = 'posted'")
        
        if self.project:
            where_clause_parts.append("aml.project_id = %s")
            where_params.append(self.project.id)

        where_clause = " AND ".join(where_clause_parts)

        sql = """
            SELECT
                aml.account_id,
                SUM(aml.debit) AS debit,
                SUM(aml.credit) AS credit,
                SUM(aml.debit - aml.credit) AS balance
            FROM
                account_move_line aml
            JOIN
                account_move am ON aml.move_id = am.id
            WHERE {}
            GROUP BY
                aml.account_id
        """.format(where_clause)

        self.env.cr.execute(sql, tuple(where_params))
        
        results = {row['account_id']: row for row in self.env.cr.dictfetchall()}
        return results

    def _get_all_accounts_in_report(self, reports, processed_report_ids=None):
        """
        Helper to recursively find all accounts in a report structure.
        This version is safe against infinite loops by tracking processed reports.
        """
        # On the first call, initialize the set of processed IDs
        if processed_report_ids is None:
            processed_report_ids = set()

        all_accounts = self.env['account.account']

        for report in reports:
            # If we have already processed this report line, skip it completely
            if report.id in processed_report_ids:
                continue
            
            # Mark this report as processed BEFORE making any recursive calls
            processed_report_ids.add(report.id)

            # Collect accounts from the current report line
            if report.type == 'accounts':
                all_accounts |= report.account_ids
            elif report.type == 'account_type':
                all_accounts |= self.env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
            
            # Now, make the recursive calls, passing along the set of processed IDs
            if report.children_ids:
                all_accounts |= self._get_all_accounts_in_report(report.children_ids, processed_report_ids)
            if report.account_report_id:
                all_accounts |= self._get_all_accounts_in_report(report.account_report_id, processed_report_ids)
            if report.report_line_ids:
                all_accounts |= self._get_all_accounts_in_report(report.report_line_ids, processed_report_ids)
                
        return all_accounts
     
    @api.multi
    def _get_account_report_name(self): # Needs to be multi if used in older Odoo versions
        for record in self: # Iterate self in case of multi
            report_name = record.account_report_id.name if record.account_report_id else ''
            record.report_name = report_name


    # --- Existing methods from the file that should be preserved (if not listed above) ---
    # _get_monthly_balances_for_report, _compute_report_balance_for_period,
    # get_monthly_report_lines_data, check_report, _format_account_name, get_account_lines
    # (Make sure get_account_lines calls the main _compute_report_balance)

    def _get_children_by_order(self): # This is on AccountFinancialReport, not AccountingReportBi
        # This method is correctly defined on AccountFinancialReport model.
        pass

    # ... (ensure all other methods from the original file are present) ...
    # Placeholder for other methods that were in the original file if they are not above
    # e.g., get_account_lines, check_report, etc.
    # Make sure to use the version of get_account_lines that calls the updated _compute_report_balance
    # The one that starts with "def get_account_lines(self): # For STANDARD reports" seems appropriate.


    # Ensure this is the get_account_lines used for standard reports
    def get_account_lines(self): # For STANDARD reports
        self.ensure_one()
        _logger.info("PDF MODULE - STANDARD: get_account_lines called for wizard ID %s. Hide zero lines: %s",
                     self.id, self.hide_zero_balance_lines)

        if not self.account_report_id:
            _logger.error("PDF MODULE - STANDARD: account_report_id is not set in get_account_lines.")
            return []

        account_report = self.account_report_id
        # Removed isinstance check for int, as account_report_id is M2O, should be object or False

        if not account_report:
            _logger.error("PDF MODULE - STANDARD: account_report_id could not be resolved to a record.")
            return []

        child_reports = account_report._get_children_by_order()
        if not child_reports:
            return []

        _logger.info("PDF MODULE - STANDARD: Calling _compute_report_balance from wizard ID %s with its own dates: From %s To %s",
                     self.id, self.date_from, self.date_to)
        res = self._compute_report_balance(child_reports) # Call on self
        _logger.debug("PDF MODULE - STANDARD: Raw results from _compute_report_balance: %s", res)

        # Comparison logic (if enabled)
        if self.enable_filter and self.filter_cmp == 'filter_date':
            _logger.info("PDF MODULE - STANDARD: Calculating comparison balances.")
            if self.date_from_cmp and self.date_to_cmp:
                # Create a temporary wizard for comparison period
                comparison_wizard = self.new({
                    'date_from': self.date_from_cmp,
                    'date_to': self.date_to_cmp,
                    'journal_ids': [(6, 0, self.journal_ids.ids)],
                    'target_move': self.target_move,
                    'company_id': self.company_id.id,
                    'project': self.project.id if self.project else False,
                    'display_account': self.display_account,
                    'account_report_id': self.account_report_id.id,
                     # ... other relevant fields for consistency ...
                })
                _logger.info("PDF MODULE - STANDARD: Calling _compute_report_balance for comparison on temp wizard ID %s with dates: From %s To %s",
                             comparison_wizard.id or "UnsavedCompWiz", comparison_wizard.date_from, comparison_wizard.date_to)
                temp_comp_res = comparison_wizard._compute_report_balance(child_reports)

                for report_id_cmp, value_cmp in temp_comp_res.items():
                    if report_id_cmp in res:
                        res[report_id_cmp]['comp_bal'] = value_cmp.get('balance', 0.0)
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

            if self.hide_zero_balance_lines and \
               report.type != 'header' and \
               self.company_id.currency_id.is_zero(current_balance):
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
                'show_balance': report.type != 'header',
            }
            if self.enable_filter and report_data.get('comp_bal') is not None:
                vals['balance_cmp'] = report_data['comp_bal'] * sign_multiplier

            processed_lines.append(vals)

            if report.display_detail != 'no_detail' and report_data.get('account'):
                accounts_data_for_report_line = report_data['account']
                
                # +++++++++++++++ START OF THE FIX +++++++++++++++
                skip_details_for_this_line = False
                # If the report line is of type 'accounts' and has only one child account, it's redundant.
                if report.type == 'accounts' and len(accounts_data_for_report_line) == 1:
                    _logger.info("PDF MODULE - STANDARD: Skipping detail for '%s' (type 'accounts') because it has only one child account.", report.name)
                    skip_details_for_this_line = True
                # +++++++++++++++ END OF THE FIX +++++++++++++++

                if not skip_details_for_this_line:
                    sub_lines_for_report = []
                    for account_id, acc_value_dict in accounts_data_for_report_line.items():
                        account = self.env['account.account'].browse(account_id)
                        if not account: continue

                        acc_balance_signed = acc_value_dict.get('balance', 0.0) * sign_multiplier
                        hide_this_acc_detail = False
                        if self.hide_zero_balance_lines and self.company_id.currency_id.is_zero(acc_balance_signed):
                            if self.debit_credit:
                                if self.company_id.currency_id.is_zero(acc_value_dict.get('debit', 0.0)) and \
                                   self.company_id.currency_id.is_zero(acc_value_dict.get('credit', 0.0)):
                                    hide_this_acc_detail = True
                            else:
                                 hide_this_acc_detail = True
                        if hide_this_acc_detail:
                            _logger.debug("PDF MODULE - STANDARD: Hiding zero-balance account detail: %s", self._format_account_name(account))
                            continue

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
                            'id': account.id,
                            'name': self._format_account_name(account),
                            'balance': acc_balance_signed,
                            'type': 'account',
                            'level': (report.level or 0) + 1,
                            'account_type': account.user_type_id.name or account.internal_type,
                            'debit': acc_value_dict.get('debit', 0.0),
                            'credit': acc_value_dict.get('credit', 0.0),
                            'show_balance': True,
                        }
                        if self.enable_filter and acc_value_dict.get('comp_bal') is not None:
                            sub_vals['balance_cmp'] = acc_value_dict['comp_bal'] * sign_multiplier

                        sub_lines_for_report.append(sub_vals)

                    processed_lines.extend(sorted(sub_lines_for_report, key=lambda x: x['name']))

        _logger.info("PDF MODULE - STANDARD: Final lines count for QWeb: %s", len(processed_lines))
        return processed_lines

    def _format_account_name(self, account):
        """ Helper to consistently format account name based on show_account_code """
        if not account:
            return ''
        if self.show_account_code and account.code:
            return "{} {}".format(account.code, account.name)
        return account.name

    # Ensure other methods like check_report, get_monthly_report_lines_data, etc., are also included
    # from the original file. The focus here was on the P&L calculation within BS.
    # The check_report method:
    def check_report(self):
        self.ensure_one()

        if not self.account_report_id:
            raise UserError(_('Misconfiguration. Please select a base Account Report (e.g., Profit and Loss or Balance Sheet).'))

        project_display = self.project.name if self.project else _("All") # Simplified project display
        target_move_display = dict(self._fields['target_move'].selection).get(self.target_move, self.target_move or _('Posted'))


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

            report_lines = self.get_account_lines()

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
                'create_date_report': self.create_date if hasattr(self, 'create_date') else fields.Datetime.now(), # Ensure create_date exists
                'show_account_code': self.show_account_code,
                'report_format': self.report_format,
                # 'company': self.company_id, # Pass company for report templates
            }
            _logger.info("PDF MODULE - STANDARD: Final dictionary for wizard ID %s: %s", self.id, {k: v for k, v in final_dict.items() if k != 'report_lines'})
            action_xml_id = 'bi_financial_pdf_reports.action_report_balancesheet'

        elif self.report_format == 'monthly':
            _logger.info("PDF MODULE - MONTHLY: Preparing report for wizard ID %s, year %s.", self.id, self.year_filter)
            if not self.year_filter or not (1900 <= self.year_filter <= 2200): # Adjusted max year
                raise UserError(_("Please specify a valid year for the monthly report."))

            original_date_from = self.date_from
            original_date_to = self.date_to
            year_start_date_str = "{}-01-01".format(self.year_filter)
            year_end_date_str = "{}-12-31".format(self.year_filter)
            try:
                self.write({
                    'date_from': fields.Date.to_date(year_start_date_str),
                    'date_to': fields.Date.to_date(year_end_date_str)
                })
            except Exception as e:
                _logger.error("Error converting year_filter to dates: %s", e)
                raise UserError(_("Invalid year specified for monthly report."))


            _logger.info("PDF MODULE - MONTHLY: Temporarily set self.date_from=%s, self.date_to=%s on wizard ID %s for layout purposes.",
                         self.date_from, self.date_to, self.id)

            monthly_lines_data = self.get_monthly_report_lines_data()

            months_headers = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            report_title = "{} - Monthly Breakdown {}".format(
                self.account_report_id.name if self.account_report_id else _("Monthly Report"),
                self.year_filter
            )

            final_dict = {
                'report_lines': monthly_lines_data,
                'name': self.account_report_id.name if self.account_report_id else _("Monthly Report"),
                'report_title': report_title,
                'year': self.year_filter,
                'months_headers': months_headers,
                'project': project_display,
                'target_move': target_move_display,
                'create_date_report': fields.Datetime.now(),
                'report_format': self.report_format,
                'show_account_code': self.show_account_code,
                'debit_credit': False, # Monthly usually doesn't show D/C per month
                'enable_filter': False, # Comparison not typical for this monthly view
                'display_date_from': self.date_from, # Year start for display
                'display_date_to': self.date_to,     # Year end for display
                'company': self.company_id,
            }
            _logger.info("PDF MODULE - MONTHLY: Final dictionary for wizard ID %s: %s", self.id, {k: v for k, v in final_dict.items() if k != 'report_lines'})
            action_xml_id = 'bi_financial_pdf_reports.action_report_monthly_financial' # Ensure this XML ID exists

            self.write({ # Restore original dates
                'date_from': original_date_from,
                'date_to': original_date_to
            })
            _logger.info("PDF MODULE - MONTHLY: Restored self.date_from and self.date_to on wizard ID %s.", self.id)

        else:
            raise UserError(_("Unsupported report format: {}").format(self.report_format))

        try:
            report_action_ref = self.env.ref(action_xml_id)
        except ValueError:
            _logger.error("Report action XML ID '%s' not found.", action_xml_id)
            raise UserError(_("The report action '{}' is not defined. Please check the XML ID.").format(action_xml_id))

        if not report_action_ref:
             _logger.error("Report action XML ID '%s' resolved to None.", action_xml_id)
             raise UserError(_("Failed to resolve the report action '{}'.").format(action_xml_id))

        action_to_return = report_action_ref.report_action(self, data=final_dict)
        _logger.info("PDF MODULE: Action dictionary being returned for '%s': %s", action_xml_id, action_to_return)
        return action_to_return


    # _get_monthly_balances_for_report and get_monthly_report_lines_data and _compute_report_balance_for_period
    # are assumed to be correctly implemented as per the original file for the monthly report functionality.
    # I will copy them here for completeness.

    def _get_monthly_balances_for_report(self, report_lines_config, year):
        _logger.info("Starting _get_monthly_balances_for_report for year %s", year)

        monthly_report_data = {}
        for report_line in report_lines_config: # Initialize structure
            monthly_report_data[report_line.id] = {
                'name': report_line.name,
                'level': report_line.style_overwrite or report_line.level, # Use style_overwrite if present
                'type': report_line.type,
                'sign': report_line.sign,
                'display_detail': report_line.display_detail,
                'account_ids': report_line.account_ids, # Keep for reference if needed later
                'account_type_ids': report_line.account_type_ids, # Keep for reference
                'monthly_balances': {i: 0.0 for i in range(1, 13)},
                'ytd_balance': 0.0,
                'monthly_accounts_data': {i: {} for i in range(1,13)} # To store account details per month
            }

        for month in range(1, 13):
            month_start_date_str = "{}-{:02d}-01".format(year, month)
            try:
                month_start_date = fields.Date.to_date(month_start_date_str)
                if not isinstance(month_start_date, date): # Odoo's fields.Date.to_date() returns datetime.date
                    _logger.error(
                        "Month_start_date is not a datetime.date object for month %s, year %s. String was: %s. Got type: %s",
                        month, year, month_start_date_str, type(month_start_date)
                    )
                    continue
            except ValueError as e:
                _logger.error("Invalid date string for month %s, year %s. String: '%s'. Error: %s", month, year, month_start_date_str, e)
                continue

            try:
                month_end_date = month_start_date + relativedelta(months=1) - relativedelta(days=1)
            except TypeError as e_rd: # Handle if month_start_date is not a date object
                _logger.error("TypeError during relativedelta for month %s, year %s. month_start_date: %s (type %s). Error: %s",
                              month, year, month_start_date, type(month_start_date), e_rd)
                continue
            except Exception as e_other: # Catch any other unexpected errors
                 _logger.error("Unexpected error during month_end_date calculation for month %s, year %s. Error: %s", month, year, e_other)
                 continue


            _logger.info("Calculating for month %s: %s to %s", month, month_start_date, month_end_date)

            # Create a temporary wizard for this specific month's calculation
            # Pass necessary fields from the main wizard
            monthly_calc_wizard = self.new({
                'date_from': month_start_date,
                'date_to': month_end_date,
                'project': self.project.id if self.project else False,
                'target_move': self.target_move,
                'journal_ids': [(6, 0, self.journal_ids.ids)], # Use IDs for .new()
                'company_id': self.company_id.id,
                'display_account': self.display_account,
                'account_report_id': self.account_report_id.id, # Main report structure
                'report_format': 'standard', # Force standard calculation for each month's slice
            })

            # _compute_report_balance_for_period is designed for strict period calculation
            month_balances_data = monthly_calc_wizard._compute_report_balance_for_period(report_lines_config)

            for report_line_id, data_val in month_balances_data.items():
                if report_line_id in monthly_report_data:
                    sign_multiplier = 1
                    try:
                        # Ensure sign is int, default to 1 if invalid
                        sign_multiplier = int(monthly_report_data[report_line_id]['sign'])
                        if sign_multiplier not in [-1, 1]: sign_multiplier = 1
                    except (ValueError, TypeError):
                        _logger.warning("Invalid sign for report line %s: %s. Defaulting to 1.",
                                        report_line_id, monthly_report_data[report_line_id]['sign'])

                    balance_for_month = data_val.get('balance', 0.0) * sign_multiplier
                    monthly_report_data[report_line_id]['monthly_balances'][month] = balance_for_month
                    monthly_report_data[report_line_id]['ytd_balance'] += balance_for_month # Accumulate YTD

                    if data_val.get('account'): # Store account details if present
                         monthly_report_data[report_line_id]['monthly_accounts_data'][month] = data_val['account']

        _logger.info("Finished _get_monthly_balances_for_report. Data for first report line (if any): %s",
                     monthly_report_data.get(next(iter(monthly_report_data))) if monthly_report_data else "No data")
        return monthly_report_data


    def _compute_report_balance_for_period(self, reports):
        """
        A simplified version of _compute_report_balance that calculates balances
        strictly for the period defined by self.date_from and self.date_to of the
        wizard instance it's called on. It ignores special report_type flags.
        Used by the monthly report to get balances for each month.
        """
        if not isinstance(reports, models.Model):
            try:
                if isinstance(reports, (int, list)): reports = self.env['account.financial.report'].browse(reports)
                elif isinstance(reports, models.Model) and len(reports) == 1: reports = self.env['account.financial.report'].browse(reports.id)
                else:
                    if not reports: return {}
                    _logger.error("Unsupported 'reports' input type %s for _compute_report_balance_for_period", type(reports))
                    return {}
            except Exception as e:
                _logger.error("Error processing 'reports' input in _compute_report_balance_for_period: %s", e)
                return {}
        if not reports: return {}

        res = {}
        fields_to_compute = ['credit', 'debit', 'balance']
        _logger.info(
            "--- _compute_report_balance_FOR_PERIOD CALLED for reports: %s. Wizard (%s) dates: FROM %s TO %s ---",
            reports.mapped('name'), self.id or "UnsavedWiz_Period", self.date_from, self.date_to
        )

        for report in reports:
            if report.id in res: continue
            res[report.id] = dict.fromkeys(fields_to_compute, 0.0)
            if report.type in ['accounts', 'account_type']:
                 res[report.id]['account'] = {} # To store detailed account balances

            # All calculations use the dates from 'self' (the wizard instance, e.g., monthly_calc_wizard)
            if report.type == 'accounts':
                # _compute_account_balance uses self.date_from/to of the current wizard
                account_balances = self._compute_account_balance(report.account_ids)
                if account_balances:
                    res[report.id]['account'].update(account_balances)
                    for value in account_balances.values():
                        for f in fields_to_compute: res[report.id][f] += value.get(f, 0.0)

            elif report.type == 'account_type':
                accounts = self.env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
                if accounts:
                    all_account_balances = self._compute_account_balance(accounts)
                    if all_account_balances:
                        res[report.id]['account'].update(all_account_balances)
                        for value in all_account_balances.values():
                            for f in fields_to_compute: res[report.id][f] += value.get(f, 0.0)

            elif report.type == 'sum_report_pl' and report.account_report_id:
                # The source P&L report also needs to be calculated for THIS wizard's period.
                # Recursive call is on the same wizard instance (self), so it uses its dates.
                res2 = self._compute_report_balance_for_period(report.account_report_id)
                source_balances = res2.get(report.account_report_id.id, {})
                for f in fields_to_compute: res[report.id][f] += source_balances.get(f, 0.0)

            elif report.type in ('account_report', 'sum', 'sum_report'):
                target_children_or_source = None
                if report.type == 'account_report': target_children_or_source = report.account_report_id
                elif report.type == 'sum': target_children_or_source = report.children_ids
                elif report.type == 'sum_report': target_children_or_source = report.report_line_ids

                if target_children_or_source:
                    res2 = self._compute_report_balance_for_period(target_children_or_source)
                    ids_to_sum = []
                    if isinstance(target_children_or_source, models.Model):
                        ids_to_sum = target_children_or_source.ids
                    if report.type == 'account_report' and report.account_report_id and isinstance(report.account_report_id, models.Model):
                        ids_to_sum = [report.account_report_id.id]

                    for item_id in ids_to_sum:
                        item_bals = res2.get(item_id, {})
                        for f in fields_to_compute: res[report.id][f] += item_bals.get(f, 0.0)

            for f in fields_to_compute: # Float conversion
                if not isinstance(res[report.id][f], (int, float)):
                    try: res[report.id][f] = float(res[report.id][f])
                    except (ValueError, TypeError): res[report.id][f] = 0.0
        return res

    def get_monthly_report_lines_data(self):

        self.ensure_one()
        _logger.info("PDF MODULE - MONTHLY: get_monthly_report_lines_data called for wizard ID %s, year %s. Hide zero YTD: %s",
                     self.id, self.year_filter, self.hide_zero_balance_lines)

        processed_display_lines = []

        if not self.account_report_id:
            _logger.error("PDF MODULE - MONTHLY: account_report_id is not set.")
            return []
        if not self.year_filter:
            _logger.error("PDF MODULE - MONTHLY: year_filter is not set.")
            return [] # Should be caught by check_report, but defensive check

        root_report_config = self.account_report_id
        report_structure_config_lines = root_report_config._get_children_by_order()

        if not report_structure_config_lines:
            _logger.info("PDF MODULE - MONTHLY: No report structure lines found for '%s'.", root_report_config.name)
            return []

        # Fetches all data: {report_line_id: {'name':..., 'monthly_balances':{1:bal,...}, 'ytd_balance':..., ...}}
        monthly_data_map = self._get_monthly_balances_for_report(report_structure_config_lines, self.year_filter)

        for report_config_line in report_structure_config_lines:
            if report_config_line.id not in monthly_data_map:
                _logger.warning("PDF MODULE - MONTHLY: Report line %s (ID %s) not found in monthly_data_map. Skipping.",
                                report_config_line.name, report_config_line.id)
                continue

            data_for_this_config_line = monthly_data_map[report_config_line.id]

            # YTD balance from monthly_data_map should already be correctly signed sum of signed monthly balances.
            ytd_balance_for_filtering_and_display = data_for_this_config_line.get('ytd_balance', 0.0)

            # Filter 1: Hide zero-YTD-balance main lines
            if self.hide_zero_balance_lines and \
               report_config_line.type != 'header' and \
               self.company_id.currency_id.is_zero(ytd_balance_for_filtering_and_display):
                _logger.debug("PDF MODULE - MONTHLY: Hiding zero-YTD-balance line: %s (YTD: %s)",
                             data_for_this_config_line['name'], ytd_balance_for_filtering_and_display)
                continue

            # Prepare displayable monthly balances (list of 12 items)
            # Balances in data_for_this_config_line['monthly_balances'] are already signed.
            display_monthly_balances = [data_for_this_config_line['monthly_balances'].get(m, 0.0) for m in range(1, 13)]

            vals = {
                'id': report_config_line.id,
                'name': data_for_this_config_line['name'],
                'level': data_for_this_config_line['level'], # level is already style_overwrite or report_config_line.level
                'type': data_for_this_config_line['type'],
                'display_detail': data_for_this_config_line['display_detail'],
                'monthly_balances': display_monthly_balances,
                'ytd_balance': ytd_balance_for_filtering_and_display,
                'show_balance': data_for_this_config_line['type'] not in ['header'], # Headers don't show balances
            }
            processed_display_lines.append(vals)

            # Handle detail lines (accounts) if display_detail is not 'no_detail'
            if report_config_line.display_detail != 'no_detail' and \
               data_for_this_config_line.get('monthly_accounts_data'):

                all_present_account_ids_for_line = set()
                for month_num in range(1, 13):
                    for acc_id in data_for_this_config_line['monthly_accounts_data'].get(month_num, {}).keys():
                        all_present_account_ids_for_line.add(acc_id)

                # +++++++++++++++ START OF THE FIX +++++++++++++++
                skip_details_for_this_line = False
                # If the report line has only one underlying account across the whole year, it's redundant.
                if report_config_line.type == 'accounts' and len(all_present_account_ids_for_line) == 1:
                    _logger.info("PDF MODULE - MONTHLY: Skipping detail for '%s' (type 'accounts') because it has only one child account for the year.", report_config_line.name)
                    skip_details_for_this_line = True
                # +++++++++++++++ END OF THE FIX +++++++++++++++

                if not skip_details_for_this_line:
                    account_detail_lines_for_qweb = []
                    for acc_id in sorted(list(all_present_account_ids_for_line)): # Sort for consistent order
                        account = self.env['account.account'].browse(acc_id)
                        if not account: continue

                        acc_monthly_balances_list = []
                        acc_ytd_balance = 0.0
                        # Sign for account details comes from the parent report_config_line's sign
                        sign_multiplier_detail = int(data_for_this_config_line.get('sign', 1))
                        if sign_multiplier_detail not in (-1,1): sign_multiplier_detail = 1

                        has_any_movement_this_account = False

                        for month_num in range(1, 13):
                            acc_month_data = data_for_this_config_line['monthly_accounts_data'].get(month_num, {}).get(acc_id, {})
                            # Balances from _compute_account_balance are typically NOT pre-signed by report.sign.
                            # Apply the parent report_config_line's sign here.
                            bal_for_month_signed = acc_month_data.get('balance', 0.0) * sign_multiplier_detail
                            acc_monthly_balances_list.append(bal_for_month_signed)
                            acc_ytd_balance += bal_for_month_signed

                            if not self.company_id.currency_id.is_zero(acc_month_data.get('debit', 0.0)) or \
                               not self.company_id.currency_id.is_zero(acc_month_data.get('credit', 0.0)):
                                has_any_movement_this_account = True


                        # Filter 2a: Hide zero-YTD-balance account details
                        if self.hide_zero_balance_lines and self.company_id.currency_id.is_zero(acc_ytd_balance):
                            _logger.debug("PDF MODULE - MONTHLY: Hiding zero-YTD-balance account detail: %s (YTD: %s)",
                                         self._format_account_name(account), acc_ytd_balance)
                            continue

                        # Filter 2b: Display Account criteria
                        # If YTD is not zero, it implies a balance or movement contributing to it.
                        if not self.company_id.currency_id.is_zero(acc_ytd_balance):
                            has_any_movement_this_account = True # If YTD not zero, consider it has movement/balance

                        show_this_account_line = False
                        if self.display_account == 'all':
                            show_this_account_line = True
                        elif self.display_account == 'movement' and has_any_movement_this_account:
                            show_this_account_line = True
                        elif self.display_account == 'not_zero' and not self.company_id.currency_id.is_zero(acc_ytd_balance):
                            show_this_account_line = True

                        if not show_this_account_line:
                            continue

                        sub_vals = {
                            'id': account.id,
                            'name': self._format_account_name(account),
                            'level': (data_for_this_config_line['level'] or 0) + 1, # Consistent indentation
                            'type': 'account_detail_monthly', # Special type for QWeb
                            'monthly_balances': acc_monthly_balances_list,
                            'ytd_balance': acc_ytd_balance,
                            'show_balance': True,
                        }
                        account_detail_lines_for_qweb.append(sub_vals)

                    processed_display_lines.extend(sorted(account_detail_lines_for_qweb, key=lambda x: x['name']))

        _logger.info("PDF MODULE - MONTHLY: Final lines count for QWeb: %s", len(processed_display_lines))
        return processed_display_lines
    



    def _get_accounts(self, accounts, display_account):
        _logger.info("Trial Balance _get_accounts: Starting method.")
        _logger.info("Trial Balance _get_accounts: display_account filter type: %s", display_account)
        _logger.info("Trial Balance _get_accounts: Number of accounts initially passed: %s", len(accounts) if accounts else 0)
        _logger.info("Trial Balance _get_accounts: Wizard Context from self.env.context: %s", self.env.context)

        account_result_from_sql = {} # To store results from SQL query

        # Get context values from the wizard (passed via self.with_context(...))
        context = self.env.context
        date_to = context.get('date_to')
        date_from = context.get('date_from')
        target_move_wizard = context.get('state') # This is self.target_move from wizard
        
        # Determine company_id to use
        # If the wizard instance 'self' has a company_id field that is set, use it.
        # Otherwise, fallback to the company_id from the context if present.
        # As a final fallback, use the current user's company.
        company_id_to_use = None
        if hasattr(self, 'company_id') and self.company_id:
            company_id_to_use = self.company_id.id
        elif context.get('force_company') or context.get('allowed_company_ids'):
            # Odoo's _query_get often uses force_company or allowed_company_ids from context
            # For simplicity here, we'll prioritize self.company_id if available,
            # otherwise, ensure a company_id is present.
             company_id_to_use = context.get('force_company', self.env.user.company_id.id)
             if isinstance(context.get('allowed_company_ids'), list) and context.get('allowed_company_ids'):
                 if company_id_to_use not in context.get('allowed_company_ids'): # Check if preferred is allowed
                     company_id_to_use = context.get('allowed_company_ids')[0] # Take the first allowed one
        else:
            company_id_to_use = self.env.user.company_id.id
        
        _logger.info("Trial Balance _get_accounts: Using company_id: %s", company_id_to_use)

        # Fallback for date_from if not provided (as _query_get would do)
        if not date_from:
            # A very old date, similar to how Odoo handles "beginning of time"
            date_from = fields.Date.to_date('1900-01-01')
        elif not isinstance(date_from, fields.date): # Ensure it's a date object
            try:
                date_from = fields.Date.to_date(date_from)
            except: # Fallback if conversion fails
                _logger.warning("Trial Balance _get_accounts: Invalid date_from format '%s'. Defaulting.", date_from)
                date_from = fields.Date.to_date('1900-01-01')
        
        if not date_to: # Should always have a date_to from wizard
            _logger.warning("Trial Balance _get_accounts: date_to not found in context. Defaulting to today.")
            date_to = fields.Date.today()
        elif not isinstance(date_to, fields.date): # Ensure it's a date object
             try:
                date_to = fields.Date.to_date(date_to)
             except:
                _logger.warning("Trial Balance _get_accounts: Invalid date_to format '%s'. Defaulting.", date_to)
                date_to = fields.Date.today()


        _logger.info("Trial Balance _get_accounts: Using date_from: %s, date_to: %s", date_from, date_to)
        _logger.info("Trial Balance _get_accounts: Using target_move_wizard: %s", target_move_wizard)

        # ---- Manually construct WHERE clause and params ----
        sql_where_parts = []
        sql_params = []

        # 1. Account ID filter
        if not accounts: # Should not happen if called from print_trial_balance
            _logger.warning("Trial Balance _get_accounts: No accounts provided to filter by.")
            # Decide how to handle: return empty, or query all if that's desired
            # For now, let's assume 'accounts' is always a valid recordset of accounts to consider
            # If accounts is empty, IN %s with an empty tuple might error or be inefficient.
            # We can add a guard:
            if not accounts.ids:
                _logger.info("Trial Balance _get_accounts: accounts.ids is empty. Returning empty list.")
                return []
            sql_where_parts.append("aml.account_id IN %s")
            sql_params.append(tuple(accounts.ids))
        else: # Ensure accounts.ids is not empty
            if not accounts.ids:
                _logger.info("Trial Balance _get_accounts: accounts.ids is empty after check. Returning empty list.")
                return []
            sql_where_parts.append("aml.account_id IN %s")
            sql_params.append(tuple(accounts.ids))


        # 2. Date filter
        sql_where_parts.append("aml.date <= %s")
        sql_params.append(date_to)
        sql_where_parts.append("aml.date >= %s")
        sql_params.append(date_from)

        # 3. Company filter
        sql_where_parts.append("aml.company_id = %s")
        sql_params.append(company_id_to_use)

        # 4. State filter (CRUCIAL)
        if target_move_wizard == 'all':
            move_states = ('draft', 'posted')
        elif target_move_wizard == 'posted':
            move_states = ('posted',)
        else: 
            _logger.warning("Trial Balance _get_accounts: Unexpected target_move value '%s' from context. Defaulting to ('draft', 'posted').", target_move_wizard)
            move_states = ('draft', 'posted')
        
        sql_where_parts.append("am.state IN %s")
        sql_params.append(move_states)
        _logger.info("Trial Balance _get_accounts: Applying move_states filter: %s", move_states)

        # ---- Construct the full SQL query ----
        sql_select_from = """
            SELECT aml.account_id AS id, 
                   SUM(aml.debit) AS debit, 
                   SUM(aml.credit) AS credit, 
                   (SUM(aml.debit) - SUM(aml.credit)) AS balance
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
        """

        sql_where_clause = " AND ".join(sql_where_parts)
        sql_group_by = " GROUP BY aml.account_id"

        final_sql = sql_select_from + " WHERE " + sql_where_clause + sql_group_by
        
        _logger.info("Trial Balance _get_accounts: Manually Constructed SQL (Final before execute):\n%s", final_sql)
        _logger.info("Trial Balance _get_accounts: Manually Constructed Params (Final before execute):\n%s", tuple(sql_params))
        
        mogrified_sql = ""
        try:
            mogrified_sql = self.env.cr.mogrify(final_sql, tuple(sql_params))
            _logger.info("Trial Balance _get_accounts: Mogrified SQL:\n%s", mogrified_sql)
        except Exception as e:
            _logger.error("Trial Balance _get_accounts: Error mogrifying SQL: %s", e)
            # Continue, execute might still work or fail with more info

        fetched_rows_count = 0
        try:
            self.env.cr.execute(final_sql, tuple(sql_params))
            for row_idx, row in enumerate(self.env.cr.dictfetchall()): # Use enumerate for index
                if row_idx == 0: # Log only the first row to avoid flooding logs
                    _logger.debug("Trial Balance _get_accounts: First SQL result row: %s", row)
                account_result_from_sql[row.pop('id')] = row
                fetched_rows_count +=1
            _logger.info("Trial Balance _get_accounts: SQL query executed. Fetched %s rows (accounts with transactions).", fetched_rows_count)
        except Exception as e:
            _logger.error("Trial Balance _get_accounts: SQL Execution Error: %s", e)
            _logger.error("Faulty Query (mogrified if available, else constructed): %s", mogrified_sql if mogrified_sql else final_sql)
            return []

        # Process results into processed_account_res
        processed_account_res = []
        sql_total_debit = 0.0
        sql_total_credit = 0.0

        # Sum totals directly from SQL results for verification
        for acc_id_sql, data_sql in account_result_from_sql.items():
            sql_total_debit += data_sql.get('debit', 0.0)
            sql_total_credit += data_sql.get('credit', 0.0)
        _logger.info("Trial Balance _get_accounts: SUMS FROM SQL RESULTS - Total Debit: %.2f, Total Credit: %.2f, Difference: %.2f",
                     sql_total_debit, sql_total_credit, sql_total_debit - sql_total_credit)


        for account in accounts: # Iterate through ALL accounts passed (e.g., from self.env['account.account'].search([]))
            res_item = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            # Ensure company_id on account matches the reporting company, or handle if Chart of Accounts is shared.
            # For simplicity, assuming single company context or accounts are already filtered by company if chart is shared.
            currency = account.currency_id or account.company_id.currency_id
            res_item['code'] = account.code
            res_item['name'] = account.name

            if account.id in account_result_from_sql:
                res_item['debit'] = account_result_from_sql[account.id].get('debit', 0.0)
                res_item['credit'] = account_result_from_sql[account.id].get('credit', 0.0)
                res_item['balance'] = account_result_from_sql[account.id].get('balance', 0.0)
            
            should_add = False
            if display_account == 'all':
                should_add = True
            elif display_account == 'not_zero' and not currency.is_zero(res_item['balance']):
                should_add = True
            elif display_account == 'movement' and \
                 (not currency.is_zero(res_item['debit']) or not currency.is_zero(res_item['credit'])):
                should_add = True
            
            if should_add:
                if account.id not in account_result_from_sql and (res_item['debit'] != 0 or res_item['credit'] != 0 or res_item['balance'] !=0 ):
                    # This case should not happen if account_result_from_sql is the source of truth for balances
                    _logger.warning("Trial Balance _get_accounts: Account %s (%s) has non-zero balance but not in SQL results. This is odd.", account.code, account.id)
                processed_account_res.append(res_item)
            elif account.id in account_result_from_sql: # Account had data but filtered out by display_account
                 _logger.debug("Trial Balance _get_accounts: Account %s (%s) had SQL data but filtered out by display_account='%s'. Data: D:%.2f C:%.2f B:%.2f",
                               account.code, account.id, display_account,
                               account_result_from_sql[account.id].get('debit',0.0),
                               account_result_from_sql[account.id].get('credit',0.0),
                               account_result_from_sql[account.id].get('balance',0.0))


        _logger.info("Trial Balance _get_accounts: Processed %s accounts for display based on display_account filter.", len(processed_account_res))
        _logger.info("Trial Balance _get_accounts: Finished method.")
        return processed_account_res

    # Ensure print_trial_balance is also in this class or an inherited one
    @api.multi
    def print_trial_balance(self):
        _logger.info("Trial Balance print_trial_balance: Method Called.")
        if self.date_to or self.date_from: # Basic date validation
            date_to_obj = fields.Date.to_date(self.date_to) if self.date_to else None
            date_from_obj = fields.Date.to_date(self.date_from) if self.date_from else None
            if date_to_obj and date_from_obj and date_to_obj <= date_from_obj:
                raise UserError('End date should be greater than start date.')

        _logger.info("Trial Balance print_trial_balance: self.target_move = %s, self.date_from = %s, self.date_to = %s, self.company_id = %s",
                     self.target_move, self.date_from, self.date_to, self.company_id.id if self.company_id else "None")
        
        display_account = self.display_account
        # Get all accounts for the current company.
        # If self.company_id is set on the wizard, use it. Otherwise, fallback to user's company.
        current_report_company_id = self.company_id.id if self.company_id else self.env.user.company_id.id
        accounts = self.env['account.account'].search([('company_id', '=', current_report_company_id)])
        _logger.info("Trial Balance print_trial_balance: Fetched %s accounts for company_id %s.", len(accounts), current_report_company_id)


        used_context_dict = {
            'state': self.target_move,
            'date_from': self.date_from, # Passed as string/date from wizard
            'date_to': self.date_to,     # Passed as string/date from wizard
            'journal_ids': False,        # Explicitly no journal filter for this TB
            'strict_range': True,
            'force_company': current_report_company_id, # Ensure context uses the correct company
            'allowed_company_ids': [current_report_company_id], # Restrict to this company
        }
        _logger.info("Trial Balance print_trial_balance: Context for _get_accounts: %s", used_context_dict)

        # self for _get_accounts will be the wizard instance, so self.company_id can be used inside if needed
        account_res = self.with_context(used_context_dict)._get_accounts(accounts, display_account)
        _logger.info("Trial Balance print_trial_balance: _get_accounts returned %s lines.", len(account_res) if account_res else 0)

        total_debit_py = 0.0
        total_credit_py = 0.0
        if account_res: 
            for acc_line_idx, acc_line in enumerate(account_res): # Use enumerate
                if acc_line_idx < 5: # Log first few processed lines
                    _logger.debug("Trial Balance print_trial_balance: Processed acc_line %s: %s", acc_line_idx, acc_line)
                total_debit_py += acc_line.get('debit', 0.0)
                total_credit_py += acc_line.get('credit', 0.0)
        
        _logger.info("Trial Balance print_trial_balance: PYTHON SUMMATION of account_res (data for QWeb):")
        _logger.info("  Total Debit: %.2f", total_debit_py)
        _logger.info("  Total Credit: %.2f", total_credit_py)
        _logger.info("  Difference: %.2f", total_debit_py - total_credit_py)

        final_dict = {
            'account_res': account_res,
            'display_account': self.display_account,
            'target_move': self.target_move,
            'date_from': self.date_from, # Pass original wizard values for display
            'date_to': self.date_to,
            # Add company object for QWeb template if it needs it (e.g., for currency)
            # 'company': self.company_id if self.company_id else self.env.user.company_id,
        }
        _logger.info("Trial Balance print_trial_balance: final_dict prepared for QWeb. Number of report lines: %s", len(account_res) if account_res else 0)
        
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