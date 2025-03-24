import math

from odoo.exceptions import UserError
from odoo import api, fields, models, _
from datetime import datetime, date
from io import BytesIO
import pytz
import xlsxwriter
import base64
from datetime import datetime, timedelta
from pytz import timezone
import json

class ProjectCashflowSummary(models.Model):
    _name = 'project.cashflow.summary'
    _description = 'Project Cashflow Summary'
    _rec_name = 'name'
    _auto = True  # Automatically create the table in the database

    name = fields.Char(string='Name', default='Cashflow Summary', readonly=True)
    total_plan_cash_in = fields.Float(string='Total Plan Cash In', compute='_compute_totals', store=False, readonly=True)
    total_actual_cash_in = fields.Float(string='Total Actual Cash In', compute='_compute_totals', store=False, readonly=True)
    total_plan_cash_out = fields.Float(string='Total Plan Cash Out', compute='_compute_totals', store=False, readonly=True)
    total_actual_cash_out = fields.Float(string='Total Actual Cash Out', compute='_compute_totals', store=False, readonly=True)
    net_plan_cashflow = fields.Float(string='Net Plan Cashflow', compute='_compute_net_cashflow', store=False, readonly=True)
    net_actual_cashflow = fields.Float(string='Net Actual Cashflow', compute='_compute_net_cashflow', store=False, readonly=True)
    cashout_plan_lines = fields.One2many(
        'project.cashflow.plan.cashout.line', 'summary_id', string='Cash Out Plan by Project', compute='_compute_lines', store=True
    )
    cashout_actual_lines = fields.One2many(
        'project.cashflow.actual.cashout.line', 'summary_id', string='Cash Out Actual by Project', compute='_compute_lines', store=True
    )
    cashin_plan_lines = fields.One2many(
        'project.cashflow.plan.cashin.line', 'summary_id', string='Cash In Plan by Project', compute='_compute_lines', store=True
    )
    cashin_actual_lines = fields.One2many(
        'project.cashflow.actual.cashin.line', 'summary_id', string='Cash In Actual by Project', compute='_compute_lines', store=True
    )
    report = fields.One2many(
        'project.summary.cash.flow.report', 'summary_id', string='Cash Flor Report by Project', compute='_compute_lines', store=True
    )

    @api.multi
    def print_report(self):
        """
        Prepare data and trigger the PDF report.
        """
        return self.env.ref('rnet_project_management.report_project_cashflow_summary').report_action(self)

    @api.model
    def _get_or_create_singleton(self):
        """Ensure a singleton record exists and return it."""
        summary = self.search([('name', '=', 'Cashflow Summary')], limit=1)
        if not summary:
            # Avoid recursion by creating the record without triggering computed fields
            summary = self.with_context(no_compute=True).create({'name': 'Cashflow Summary'})
        return summary

    @api.model
    def action_open_cashflow_summary(self):
        """Custom action to open the cashflow summary with the singleton record."""
        summary = self._get_or_create_singleton()
        # Ensure computed fields are calculated
        if 'no_compute' not in self.env.context:
            summary.with_context(no_compute=True)._compute_lines()
            summary.with_context(no_compute=True)._compute_totals()
            summary.with_context(no_compute=True)._compute_net_cashflow()
        action = self.env.ref('rnet_project_management.act_project_cashflow_summary').read()[0]
        action['res_id'] = summary.id
        return action

    @api.model
    def default_get(self, fields_list):
        """Override default_get to load the singleton record and compute values."""
        res = super(ProjectCashflowSummary, self).default_get(fields_list)
        # Only compute fields if not in a creation context that might cause recursion
        if not self.env.context.get('no_compute'):
            summary = self._get_or_create_singleton()
            if 'total_plan_cash_in' in fields_list:
                summary._compute_totals()
            if any(field in fields_list for field in
                   ['cashout_plan_lines', 'cashout_actual_lines', 'cashin_plan_lines', 'cashin_actual_lines']):
                summary._compute_lines()
            if 'net_plan_cashflow' in fields_list or 'net_actual_cashflow' in fields_list:
                summary._compute_net_cashflow()
        return res

    @api.depends()
    def _compute_totals(self):
        progress_plans = self.env['project.progress.plan'].search([])
        self.total_plan_cash_in = sum(progress_plans.mapped('project_plan_cashin_line').mapped('name'))
        self.total_plan_cash_out = sum(progress_plans.mapped('project_plan_cashout_line').mapped('name'))
        self.total_actual_cash_in = sum(self.env['project.actual.cashin'].search([]).mapped('amount'))
        self.total_actual_cash_out = sum(self.env['project.actual.cashout'].search([]).mapped('amount'))

    @api.depends()
    def _compute_net_cashflow(self):
        for record in self:
            record.net_plan_cashflow = record.total_plan_cash_in - record.total_plan_cash_out
            record.net_actual_cashflow = record.total_actual_cash_in - record.total_actual_cash_out

    @api.depends()
    def _compute_lines(self):
        progress_plans = self.env['project.progress.plan'].search([])
        for record in self:
            record.report = [(5, 0, 0)]
            result = []
            cashout_plan_data = []
            cashin_plan_data = []
            actual_cashout_data = []
            actual_cashin_data = []
            for plan in progress_plans:
                for line in plan.project_plan_cashin_line:
                    cashin_plan_data.append({
                        'project_id': plan.name.id,
                        'project_name': plan.name.name,
                        'date': line.date,
                        'total_cash_in': line.name,
                    })
                for line in plan.project_plan_cashout_line:
                    cashout_plan_data.append({
                        'project_id': plan.name.id,
                        'project_name': plan.name.name,
                        'date': line.date,
                        'total_cash_out': line.name,
                    })
                for line in plan.project_actual_cashout_line:
                    actual_cashout_data.append({
                        'project_id': plan.name.id,
                        'project_name': plan.name.name,
                        'date': line.payment_date,
                        'total_cash_out': line.name,
                    })
                for line in plan.project_actual_cashin_line:
                    actual_cashin_data.append({
                        'project_id': plan.name.id,
                        'project_name': plan.name.name,
                        'date': line.payment_date,
                        'total_cash_out': line.name,
                    })

            # Write computed lines to One2many fields
            record.cashout_plan_lines = [(5, 0, 0)] + [(0, 0, vals) for vals in cashout_plan_data]
            record.cashin_plan_lines = [(5, 0, 0)] + [(0, 0, vals) for vals in cashin_plan_data]
            record.cashout_actual_lines = [(5, 0, 0)] + [(0, 0, vals) for vals in actual_cashout_data]
            record.cashin_actual_lines = [(5, 0, 0)] + [(0, 0, vals) for vals in actual_cashin_data]

            # Initialize accumulative values
            accumulative_cash_in_plan = 0
            accumulative_cash_out_plan = 0
            accumulative_cash_flow_plan = 0
            accumulative_cash_in_actual = 0
            accumulative_cash_out_actual = 0
            accumulative_cash_flow_actual = 0

            # Use existing One2many fields
            weekly_data = {}
            # Process cash-in plan data
            for cash_in in record.cashin_plan_lines:
                if cash_in.date:
                    year_start = datetime(cash_in.date.year, 1, 1).date()
                    week_number = math.ceil((cash_in.date - year_start).days / 7.0)
                    year = cash_in.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    weekly_data.setdefault(key, {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_in_actual': 0,
                                                 'cash_out_actual': 0})
                    weekly_data[key]['cash_in_plan'] += cash_in.total_cash_in

            # Process cash-out plan data
            for cash_out in record.cashout_plan_lines:
                if cash_out.date:
                    year_start = datetime(cash_out.date.year, 1, 1).date()
                    week_number = math.ceil((cash_out.date - year_start).days / 7.0)
                    year = cash_out.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    weekly_data.setdefault(key, {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_in_actual': 0,
                                                 'cash_out_actual': 0})
                    weekly_data[key]['cash_out_plan'] += cash_out.total_cash_out

            # Process cash-in actual data
            for cash_in in record.cashin_actual_lines:
                if cash_in.date:
                    year_start = datetime(cash_in.date.year, 1, 1).date()
                    week_number = math.ceil((cash_in.date - year_start).days / 7.0)
                    year = cash_in.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    weekly_data.setdefault(key, {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_in_actual': 0,
                                                 'cash_out_actual': 0})
                    weekly_data[key]['cash_in_actual'] += cash_in.total_cash_in

            # Process cash-out actual data
            for cash_out in record.cashout_actual_lines:
                if cash_out.date:
                    year_start = datetime(cash_out.date.year, 1, 1).date()
                    week_number = math.ceil((cash_out.date - year_start).days / 7.0)
                    year = cash_out.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    weekly_data.setdefault(key, {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_in_actual': 0,
                                                 'cash_out_actual': 0})
                    weekly_data[key]['cash_out_actual'] += cash_out.total_cash_out

            # Create report data
            for key in sorted(weekly_data.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
                year, week_number = map(int, key.split('-'))
                data = weekly_data[key]
                cash_in_plan = data['cash_in_plan']
                cash_out_plan = data['cash_out_plan']
                cash_flow_plan = cash_in_plan - cash_out_plan
                cash_in_actual = data['cash_in_actual']
                cash_out_actual = data['cash_out_actual']
                cash_flow_actual = cash_in_actual - cash_out_actual

                # Update accumulative values
                accumulative_cash_in_plan += cash_in_plan
                accumulative_cash_out_plan += cash_out_plan
                accumulative_cash_flow_plan += cash_flow_plan
                accumulative_cash_in_actual += cash_in_actual
                accumulative_cash_out_actual += cash_out_actual
                accumulative_cash_flow_actual += cash_flow_actual

                report_data = {
                    'summary_id': record.id,
                    'weeks': week_number,
                    'year': year,
                    'cash_in_plan': cash_in_plan,
                    'cash_out_plan': cash_out_plan,
                    'cash_flow_plan': cash_flow_plan,
                    'cash_in_actual': cash_in_actual,
                    'cash_out_actual': cash_out_actual,
                    'cash_flow_actual': cash_flow_actual,
                    'accumulative_cash_in_plan': accumulative_cash_in_plan,
                    'accumulative_cash_out_plan': accumulative_cash_out_plan,
                    'accumulative_cash_flow_plan': accumulative_cash_flow_plan,
                    'accumulative_cash_in_actual': accumulative_cash_in_actual,
                    'accumulative_cash_out_actual': accumulative_cash_out_actual,
                    'accumulative_cash_flow_actual': accumulative_cash_flow_actual,
                }
                result.append(report_data)
            record.report = result

    def get_cash_flow_report(self):
        result = []
        for rec in self:

            # Initialize accumulative values
            accumulative_cash_in_plan = 0
            accumulative_cash_out_plan = 0
            accumulative_cash_flow_plan = 0
            accumulative_cash_in_actual = 0
            accumulative_cash_out_actual = 0
            accumulative_cash_flow_actual = 0

            # Use existing One2many fields
            weekly_data = {}

            # Process cash-in plan data
            for cash_in in rec.cashin_plan_lines:
                if cash_in.date:
                    year_start = datetime(cash_in.date.year, 1, 1).date()
                    week_number = math.ceil((cash_in.date - year_start).days / 7.0)
                    year = cash_in.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    weekly_data.setdefault(key, {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_in_actual': 0,
                                                 'cash_out_actual': 0})
                    weekly_data[key]['cash_in_plan'] += cash_in.total_cash_in

            # Process cash-out plan data
            for cash_out in rec.cashout_plan_lines:
                if cash_out.date:
                    year_start = datetime(cash_out.date.year, 1, 1).date()
                    week_number = math.ceil((cash_out.date - year_start).days / 7.0)
                    year = cash_out.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    weekly_data.setdefault(key, {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_in_actual': 0,
                                                 'cash_out_actual': 0})
                    weekly_data[key]['cash_out_plan'] += cash_out.total_cash_out

            # Process cash-in actual data
            for cash_in in rec.cashin_actual_lines:
                if cash_in.date:
                    year_start = datetime(cash_in.date.year, 1, 1).date()
                    week_number = math.ceil((cash_in.date - year_start).days / 7.0)
                    year = cash_in.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    weekly_data.setdefault(key, {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_in_actual': 0,
                                                 'cash_out_actual': 0})
                    weekly_data[key]['cash_in_actual'] += cash_in.total_cash_in

            # Process cash-out actual data
            for cash_out in rec.cashout_actual_lines:
                if cash_out.date:
                    year_start = datetime(cash_out.date.year, 1, 1).date()
                    week_number = math.ceil((cash_out.date - year_start).days / 7.0)
                    year = cash_out.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    weekly_data.setdefault(key, {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_in_actual': 0,
                                                 'cash_out_actual': 0})
                    weekly_data[key]['cash_out_actual'] += cash_out.total_cash_out

            # Create report data
            for key in sorted(weekly_data.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
                year, week_number = map(int, key.split('-'))
                data = weekly_data[key]
                cash_in_plan = data['cash_in_plan']
                cash_out_plan = data['cash_out_plan']
                cash_flow_plan = cash_in_plan - cash_out_plan
                cash_in_actual = data['cash_in_actual']
                cash_out_actual = data['cash_out_actual']
                cash_flow_actual = cash_in_actual - cash_out_actual

                # Update accumulative values
                accumulative_cash_in_plan += cash_in_plan
                accumulative_cash_out_plan += cash_out_plan
                accumulative_cash_flow_plan += cash_flow_plan
                accumulative_cash_in_actual += cash_in_actual
                accumulative_cash_out_actual += cash_out_actual
                accumulative_cash_flow_actual += cash_flow_actual

                report_data = {
                    'summary_id': rec.id,
                    'weeks': week_number,
                    'year': year,
                    'cash_in_plan': cash_in_plan,
                    'cash_out_plan': cash_out_plan,
                    'cash_flow_plan': cash_flow_plan,
                    'cash_in_actual': cash_in_actual,
                    'cash_out_actual': cash_out_actual,
                    'cash_flow_actual': cash_flow_actual,
                    'accumulative_cash_in_plan': accumulative_cash_in_plan,
                    'accumulative_cash_out_plan': accumulative_cash_out_plan,
                    'accumulative_cash_flow_plan': accumulative_cash_flow_plan,
                    'accumulative_cash_in_actual': accumulative_cash_in_actual,
                    'accumulative_cash_out_actual': accumulative_cash_out_actual,
                    'accumulative_cash_flow_actual': accumulative_cash_flow_actual,
                }
                result.append(report_data)
        return result

    def cashflowPlanChart(self):
        for rec in self:
            records = self.report

            labels = []
            cash_in_plan = []
            cash_out_plan = []
            cash_flow_plan = []

            sorted_records = sorted(records, key=lambda r: (r.year, r.weeks))

            for record in sorted_records:
                labels.append(str(record.year) + " W" + str(record.weeks))
                cash_in_plan.append(record.cash_in_plan)
                cash_out_plan.append(-record.cash_out_plan)
                cash_flow_plan.append(record.accumulative_cash_flow_plan)

            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Accumulative Plan Cash Flow',
                            'data': cash_flow_plan,
                            'fill': False,
                            'backgroundColor': 'rgb(124, 17, 88)',
                            'borderColor': 'rgb(124, 17, 88)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Plan Cash In',
                            'data': cash_in_plan,
                            'backgroundColor': 'rgb(66, 112, 193)',
                        },
                        {
                            'label': 'Plan Cash Out',
                            'data': cash_out_plan,
                            'backgroundColor': 'rgb(233, 124, 48)',
                        },
                    ]
                },
                 'options': {
                    'plugins': {
                        'tickFormat': {
                        }
                    }
                }
            }

            return "https://quickchart.io/chart?c=" + json.dumps(chart_data)

    def cashflowActualChart(self):
        for rec in self:
            records = self.report

            labels = []
            cash_in_actual = []
            cash_out_actual = []
            cash_flow_actual = []

            sorted_records = sorted(records, key=lambda r: (r.year, r.weeks))

            for record in sorted_records:
                labels.append(str(record.year) + " W" + str(record.weeks))
                cash_in_actual.append(record.cash_in_actual)
                cash_out_actual.append(-record.cash_out_actual)
                cash_flow_actual.append(record.accumulative_cash_flow_actual)


            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Accumulative Actual Cash Flow',
                            'data': cash_flow_actual,
                            'fill': False,
                            'backgroundColor': 'rgb(124, 17, 88)',
                            'borderColor': 'rgb(124, 17, 88)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Actual Cash In',
                            'data': cash_in_actual,
                            'backgroundColor': 'rgb(66, 112, 193)',
                        },
                        {
                            'label': 'Actual Cash Out',
                            'data': cash_out_actual,
                            'backgroundColor': 'rgb(233, 124, 48)',
                        },
                    ]
                },
                'options': {
                    'plugins': {
                        'tickFormat': {
                        }
                    }
                }
            }

            return "https://quickchart.io/chart?c=" + json.dumps(chart_data)

    def cashflowChart(self):
        for rec in self:
            records = self.report

            labels = []
            cash_in_plan = []
            cash_out_plan = []
            cash_flow_plan = []
            cash_in_actual = []
            cash_out_actual = []
            cash_flow_actual = []

            sorted_records = sorted(records, key=lambda r: (r.year, r.weeks))

            for record in sorted_records:
                labels.append(str(record.year) + " W" + str(record.weeks))
                cash_in_plan.append(record.cash_in_plan)
                cash_out_plan.append(-record.cash_out_plan)
                cash_flow_plan.append(record.accumulative_cash_flow_plan)
                cash_in_actual.append(record.cash_in_actual)
                cash_out_actual.append(-record.cash_out_actual)
                cash_flow_actual.append(record.accumulative_cash_flow_actual)

            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Accumulative Plan Cash Flow',
                            'data': cash_flow_plan,
                            'fill': False,
                            'backgroundColor': 'rgb(253, 204, 229)',
                            'borderColor': 'rgb(253, 204, 229)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Accumulative Actual Cash Flow',
                            'data': cash_flow_actual,
                            'fill': False,
                            'backgroundColor': 'rgb(124, 17, 88)',
                            'borderColor': 'rgb(124, 17, 88)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Plan Cash In',
                            'data': cash_in_plan,
                            'backgroundColor': 'rgb(179, 212, 255)',
                        },
                        {
                            'label': 'Plan Cash Out',
                            'data': cash_out_plan,
                            'backgroundColor': 'rgb(253, 220, 120)',
                        },
                        {
                            'label': 'Actual Cash In',
                            'data': cash_in_actual,
                            'backgroundColor': 'rgb(26, 83, 255)',
                        },
                        {
                            'label': 'Actual Cash Out',
                            'data': cash_out_actual,
                            'backgroundColor': 'rgb(255, 163, 0)',
                        },
                    ]
                },
                 'options': {
                    'plugins': {
                        'tickFormat': {
                        }
                    }
                }
            }

            return "https://quickchart.io/chart?c=" + json.dumps(chart_data)

    def action_refresh(self):
        """Refresh the summary by recomputing all fields."""
        self.with_context(no_compute=True)._compute_lines()
        self.with_context(no_compute=True)._compute_totals()
        self.with_context(no_compute=True)._compute_net_cashflow()
        return True



class ProjectCashflowPlanCashOutLine(models.Model):
    _name = 'project.cashflow.plan.cashout.line'
    _description = 'Project Cashflow Plan Cash Out Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_out = fields.Float(string='Cash Out', readonly=True)

class ProjectCashflowPlanCashInLine(models.Model):
    _name = 'project.cashflow.plan.cashin.line'
    _description = 'Project Cashflow Plan Cash In Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_in = fields.Float(string='Cash In', readonly=True)

class ProjectCashflowActualCashOutLine(models.Model):
    _name = 'project.cashflow.actual.cashout.line'
    _description = 'Project Cashflow Actual Cash Out Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_out = fields.Float(string='Cash Out', readonly=True)

class ProjectCashflowActualCashInLine(models.Model):
    _name = 'project.cashflow.actual.cashin.line'
    _description = 'Project Cashflow Actual Cash In Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_in = fields.Float(string='Cash In', readonly=True)

class ProjectCashFlowReport(models.Model):
    _name = 'project.summary.cash.flow.report'
    _description = 'Cash Flow Report'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cash Flow Summary', ondelete='cascade')
    weeks = fields.Integer(string='Week Number', required=True)
    year = fields.Integer(string='Year Number', required=True)
    cash_in_plan = fields.Float(string='Cash In Value Plan', required=True)
    cash_out_plan = fields.Float(string='Cash Out Value Plan', required=True)
    cash_flow_plan = fields.Float(string='Cash Flow Value Plan', required=True)
    cash_in_actual = fields.Float(string='Cash In Value Actual', required=True)
    cash_out_actual = fields.Float(string='Cash Out Value Actual', required=True)
    cash_flow_actual = fields.Float(string='Cash Flow Value Actual', required=True)
    accumulative_cash_in_plan = fields.Float(string='Accumulative Cash In Value Plan', required=True)
    accumulative_cash_out_plan = fields.Float(string='Accumulative Cash Out Value Plan', required=True)
    accumulative_cash_flow_plan = fields.Float(string='Accumulative Cash Flow Value Plan', required=True)
    accumulative_cash_in_actual = fields.Float(string='Accumulative Cash In Value Actual', required=True)
    accumulative_cash_out_actual = fields.Float(string='Accumulative Cash Out Value Actual', required=True)
    accumulative_cash_flow_actual = fields.Float(string='Accumulative Cash Flow Value Actual', required=True)

class ProjectCashOutReport(models.Model):
    _name = 'project.summary.cash.out.report'
    _description = 'Cash Out Report'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cash Out Summary', ondelete='cascade')
    weeks = fields.Integer(string='Week Number', required=True)
    year = fields.Integer(string='Year Number', required=True)
    plan_cash_out = fields.Float(string='Plan Cash Out', required=True)
    actual_cash_out = fields.Float(string='Actual Cash Out', required=True)
    estimated_cash_out = fields.Float(string='Estimated Cash Out', required=True)

class ProjectCashInReport(models.Model):
    _name = 'project.summary.cash.in.report'
    _description = 'Cash In Report'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cash In Summary', ondelete='cascade')
    weeks = fields.Integer(string='Week Number', required=True)
    year = fields.Integer(string='Year Number', required=True)
    plan_cash_in = fields.Float(string='Plan Cash In', required=True)
    actual_cash_in = fields.Float(string='Actual Cash In', required=True)
    accumulative_plan_cash_in = fields.Float(string='Accumulative Plan Cash In', required=True)
    accumulative_actual_cash_in = fields.Float(string='Accumulative Actual Cash In', required=True)