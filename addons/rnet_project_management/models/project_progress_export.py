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

class ProjectProgressExport(models.Model):
    _inherit = 'project.progress.plan'

    # Report data
    start_date = fields.Date(string="Start Date")
    finish_date = fields.Date(string="Finish Date")
    project_actual_plan_curve_report = fields.One2many('project.actual.plan.curve.report',
                                                       'actual_curve_plan_report_id',
                                                       string='Project Actual Curve Report')
    project_cash_flow_report = fields.One2many('project.cash.flow.report', 'cash_flow_report_id',
                                               string='Project Cash Flow Report')
    project_cash_out_report = fields.One2many('project.cash.out.report', 'cash_out_report_id',
                                              string='Project Cash Out Report')
    total_plan_cash_out = fields.Float(string="Total Plan Cash Out")
    total_actual_cash_out = fields.Float(string="Total Actual Cash Out")
    project_cash_in_report = fields.One2many('project.cash.in.report', 'cash_in_report_id',
                                             string='Project Cash In Report')
    total_plan_cash_in = fields.Float(string="Total Plan Cash In")
    total_actual_cash_in = fields.Float(string="Total Actual Cash In")
    project_invoice_report = fields.One2many('project.invoice.report', 'invoice_report_id',
                                             string='Project Invoice Report')
    project_manhour_report = fields.One2many('project.manhour.report', 'manhour_report_id',
                                             string='Project Man Hour Report')
    remaining_budget = fields.Float(string="Remaining Budget")
    remaining_sales = fields.Float(string="Remaining Sales")
    timezone = pytz.timezone('Asia/Jakarta')
    current_date = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
    last_accumulative_actual_progress = fields.Float(string="Last accumulative actual progress")

    def _get_weeks_between_dates(self, start_date, end_date):
        """
        Generate week numbers between start_date and end_date.
        This assumes that each week starts on Monday.
        """
        # Parse the dates if they are in DD/MM/YYYY format
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%d/%m/%Y").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%d/%m/%Y").date()

        current_date = start_date
        week_numbers = []

        while current_date <= end_date:
            week_number = current_date.isocalendar()[1]
            if week_number not in week_numbers:
                week_numbers.append(week_number)
            current_date += timedelta(weeks=1)

        return week_numbers

    def sCurveChart(self):
        for rec in self:
            records = self.env['project.actual.plan.curve.report'].search([
                ('actual_curve_plan_report_id', '=', rec.id),
            ])
            labels = []
            actual_data = []
            plan_data = []
            accumulative_actual_data = []
            accumulative_plan_data = []

            sorted_records = sorted(records, key=lambda r: (r.year, r.weeks))

            for record in sorted_records:
                labels.append(str(record.year) + " W" + str(record.weeks))
                actual_data.append(record.actual)
                plan_data.append(record.plan)
                accumulative_actual_data.append(record.accumulative_actual)
                accumulative_plan_data.append(record.accumulative_plan)

            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Plan Accumulative',
                            'data': accumulative_plan_data,
                            'fill': False,
                            'backgroundColor': 'rgb(66, 112, 193)',
                            'borderColor': 'rgb(66, 112, 193)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Actual Accumulative',
                            'data': accumulative_actual_data,
                            'fill': False,
                            'backgroundColor': 'rgb(233, 124, 48)',
                            'borderColor': 'rgb(233, 124, 48)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Planned',
                            'data': plan_data,
                            'backgroundColor': 'rgb(66, 112, 193)',
                        },
                        {
                            'label': 'Actual',
                            'data': actual_data,
                            'backgroundColor': 'rgb(233, 124, 48)',
                        },
                    ]
                },
                'options': {
                    'plugins': {
                        'tickFormat': {
                            'minimumFractionDigits': 2
                        }
                    }
                }
            }

            return "https://quickchart.io/chart?c=" + json.dumps(chart_data)

    def cashflowChart(self):
        for rec in self:
            records = self.env['project.cash.flow.report'].search([
                ('cash_flow_report_id', '=', rec.id),
            ])

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

    def cashflowPlanChart(self):
        for rec in self:
            records = self.env['project.cash.flow.report'].search([
                ('cash_flow_report_id', '=', rec.id),
            ])

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
            records = self.env['project.cash.flow.report'].search([
                ('cash_flow_report_id', '=', rec.id),
            ])

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

    def costChart(self):
        for rec in self:
            records = self.env['project.cash.out.report'].search([
                ('cash_out_report_id', '=', rec.id),
            ])

            labels = []
            plan_cash_out = []
            actual_cash_out = []
            estimated_cash_out = []

            sorted_records = sorted(records, key=lambda r: (r.year, r.weeks))

            for record in sorted_records:
                labels.append(str(record.year) + " W" + str(record.weeks))
                plan_cash_out.append(record.plan_cash_out)
                actual_cash_out.append(record.actual_cash_out)
                estimated_cash_out.append(record.estimated_cash_out)


            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Plan Cash Out',
                            'data': plan_cash_out,
                            'backgroundColor': 'rgb(66, 112, 193)',
                        },
                        {
                            'label': 'Estimated Cash Out',
                            'data': actual_cash_out,
                            'backgroundColor': 'rgb(189, 126, 190)',
                        },
                        {
                            'label': 'Actual Cash Out',
                            'data': actual_cash_out,
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

    def remainingBudgetChart(self):
        for rec in self:
            remain_percentage = 0
            usage_percentage = 0

            if self.remaining_budget and self.total_actual_cash_out:
                remain_percentage = round(
                    ((self.remaining_budget - self.total_actual_cash_out) / self.remaining_budget) * 100, 2)
                usage_percentage = round((self.total_actual_cash_out / self.remaining_budget) * 100, 2)

            chart_data = {
                'type': 'pie',
                'data': {
                    'labels': ['Actual Cost','Remaining from Budget'],
                    'datasets': [
                        {
                            'data': [usage_percentage, remain_percentage],
                            'backgroundColor': [
                                'rgb(233, 124, 48)',
                                'rgb(66, 112, 193)',
                            ],
                        }
                    ]
                },
                'options': {
                    'plugins': {
                        'datalabels': {
                            'color': 'white',
                        }
                    }
                }
            }

            return "https://quickchart.io/chart?c=" + json.dumps(chart_data)

    def remainingSalesChart(self):
        for rec in self:
            remain_percentage = 0
            usage_percentage = 0

            if self.remaining_budget and self.total_actual_cash_out:
                remain_percentage = round(
                    ((self.remaining_sales - self.total_actual_cash_out) / self.remaining_sales) * 100, 2)
                usage_percentage = round((self.total_actual_cash_out / self.remaining_sales) * 100, 2)

            chart_data = {
                'type': 'pie',
                'data': {
                    'labels': ['Actual Cost','Remaining from Sales'],
                    'datasets': [
                        {
                            'data': [usage_percentage, remain_percentage],
                            'backgroundColor': [
                                'rgb(233, 124, 48)',
                                'rgb(66, 112, 193)',
                            ],
                        }
                    ]
                },
                'options': {
                    'plugins': {
                        'datalabels': {
                            'color': 'white',
                        }
                    }
                }
            }

            return "https://quickchart.io/chart?c=" + json.dumps(chart_data)

    def remainingFromBoth(self):
        for rec in self:
            total_actual_cash_out = 0
            remaining_sales = 0
            remaining_budget = 0
            if self.remaining_budget:
                remaining_budget = self.remaining_budget
            if self.remaining_sales:
                remaining_sales = self.remaining_sales
            if self.total_actual_cash_out:
                total_actual_cash_out = self.total_actual_cash_out


            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': ['From Sales', 'From Budget'],
                    'datasets': [
                        {
                            'label': 'Used',
                            'data': [total_actual_cash_out, total_actual_cash_out],
                            'backgroundColor': 'rgb(233, 124, 48)',  # Green for used percentages
                        },
                        {
                            'label': 'Remaining',
                            'data': [remaining_sales, remaining_budget],
                            'backgroundColor': 'rgb(66, 112, 193)',  # Yellow for remaining percentages
                        },
                    ]
                },
                'options': {  # Corrected placement of the options key
                    'plugins': {
                        'tickFormat': {
                        }
                    },
                    'scales': {
                        'xAxes': [
                            {
                                'stacked': True,
                            },
                        ],
                        'yAxes': [
                            {
                                'stacked': True,
                            },
                        ],
                    },
                },
            }

            return "https://quickchart.io/chart?c=" + json.dumps(chart_data)

    def remainingFromBothV2(self):
        for rec in self:
            total_actual_cash_out = 0
            remaining_budget = 0
            if self.remaining_budget:
                remaining_budget = self.remaining_budget
            if self.total_actual_cash_out:
                total_actual_cash_out = self.total_actual_cash_out


            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': [ 'From Budget'],
                    'datasets': [
                        {
                            'label': 'Used',
                            'data': [ total_actual_cash_out],
                            'backgroundColor': 'rgb(233, 124, 48)',  # Green for used percentages
                        },
                        {
                            'label': 'Remaining',
                            'data': [remaining_budget],
                            'backgroundColor': 'rgb(66, 112, 193)',  # Yellow for remaining percentages
                        },
                    ]
                },
                'options': {  # Corrected placement of the options key
                    'plugins': {
                        'tickFormat': {
                        }
                    },
                    'scales': {
                        'xAxes': [
                            {
                                'stacked': True,
                            },
                        ],
                        'yAxes': [
                            {
                                'stacked': True,
                            },
                        ],
                    },
                },
            }

            return "https://quickchart.io/chart?c=" + json.dumps(chart_data)

    def paymentChart(self):
        for rec in self:
            records = self.env['project.cash.in.report'].search([
                ('cash_in_report_id', '=', rec.id),
            ])

            labels = []
            plan_cash_in = []
            actual_cash_in = []

            sorted_records = sorted(records, key=lambda r: (r.year, r.weeks))

            for record in sorted_records:
                labels.append(str(record.year) + " W" + str(record.weeks))
                plan_cash_in.append(record.plan_cash_in)
                actual_cash_in.append(record.actual_cash_in)

            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Plan Cash In',
                            'data': plan_cash_in,
                            'backgroundColor': 'rgb(66, 112, 193)',
                        },
                        {
                            'label': 'Actual Cash In',
                            'data': actual_cash_in,
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

    def invoiceChart(self):
        for rec in self:
            records = self.env['project.invoice.report'].search([
                ('invoice_report_id', '=', rec.id),
            ])

            labels = []
            plan_invoice = []
            actual_invoice = []
            accumulative_plan_invoice = []
            accumulative_actual_invoice = []

            sorted_records = sorted(records, key=lambda r: (r.year, r.weeks))

            for record in sorted_records:
                labels.append(str(record.year) + " W" + str(record.weeks))
                plan_invoice.append(record.plan_invoice)
                actual_invoice.append(record.actual_invoice)
                accumulative_plan_invoice.append(record.accumulative_plan_invoice)
                accumulative_actual_invoice.append(record.accumulative_actual_invoice)

            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Plan Invoice Accumulative',
                            'data': accumulative_plan_invoice,
                            'fill': False,
                            'backgroundColor': 'rgb(66, 112, 193)',
                            'borderColor': 'rgb(66, 112, 193)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Actual Invoice Accumulative',
                            'data': accumulative_actual_invoice,
                            'fill': False,
                            'backgroundColor': 'rgb(233, 124, 48)',
                            'borderColor': 'rgb(233, 124, 48)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Plan Invoice',
                            'data': plan_invoice,
                            'backgroundColor': 'rgb(66, 112, 193)',
                        },
                        {
                            'label': 'Actual Invoice',
                            'data': actual_invoice,
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

    def manHourChart(self):
        for rec in self:
            records = self.env['project.manhour.report'].search([
                ('manhour_report_id', '=', rec.id),
            ])

            labels = []
            plan_manhour = []
            actual_manhour = []
            accumulative_plan_manhour = []
            accumulative_actual_manhour = []

            sorted_records = sorted(records, key=lambda r: (r.year, r.weeks))

            for record in sorted_records:
                labels.append(str(record.year) + " W" + str(record.weeks))
                plan_manhour.append(record.plan_manhour)
                actual_manhour.append(record.actual_manhour)
                accumulative_plan_manhour.append(record.accumulative_plan_manhour)
                accumulative_actual_manhour.append(record.accumulative_actual_manhour)


            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Plan Accumulative Man Hour',
                            'data': accumulative_plan_manhour,
                            'fill': False,
                            'backgroundColor': 'rgb(66, 112, 193)',
                            'borderColor': 'rgb(66, 112, 193)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Actual Accumulative Man Hour',
                            'data': accumulative_actual_manhour,
                            'fill': False,
                            'backgroundColor': 'rgb(233, 124, 48)',
                            'borderColor': 'rgb(233, 124, 48)',
                            'tension': 0.1,
                            'type': 'line',
                        },
                        {
                            'label': 'Planned',
                            'data': plan_manhour,
                            'backgroundColor': 'rgb(66, 112, 193)',
                        },
                        {
                            'label': 'Actual',
                            'data': actual_manhour,
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

    def financialHighlight(self):
        for rec in self:
            # Make sure data is generated
            rec.generate_report_data()
            invoice = 0
            cost = 0
            gross_margin = 0
            cash_in = 0
            cash_out = 0
            cash_flow = 0

            invoice_reports = rec.project_invoice_report.sorted(key=lambda r: (r.year, r.weeks))
            if invoice_reports:
                invoice = invoice_reports[-1].accumulative_actual_invoice if hasattr(invoice_reports[-1], 'accumulative_actual_invoice') else invoice_reports[-1].actual_invoice
            cost_reports = rec.project_cash_out_report.sorted(key=lambda r: (r.year, r.weeks))
            if cost_reports:
                cost = cost_reports[-1].accumulative_actual_cash_out if hasattr(cost_reports[-1], 'accumulative_actual_cash_out') else cost_reports[-1].actual_cash_out
            gross_margin = invoice - cost

            # Add cash_in, cash_out, cash_flow
            cash_in_reports = rec.project_cash_in_report.sorted(key=lambda r: (r.year, r.weeks))
            if cash_in_reports:
                cash_in = cash_in_reports[-1].accumulative_actual_cash_in if hasattr(cash_in_reports[-1], 'accumulative_actual_cash_in') else cash_in_reports[-1].actual_cash_in
            cash_out_reports = rec.project_cash_out_report.sorted(key=lambda r: (r.year, r.weeks))
            if cash_out_reports:
                cash_out = cash_out_reports[-1].actual_cash_out
            cash_flow = cash_in - cash_out

            labels = ['Invoice', 'Cost', 'Gross Margin', 'Cash In', 'Cash Out', 'Cash Flow']
            data = [invoice, cost, gross_margin, cash_in, cash_out, cash_flow]

            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [
                        {
                            'label': 'Financial Highlight',
                            'data': data,
                            'backgroundColor': [
                                'rgb(66, 112, 193)',
                                'rgb(233, 124, 48)',
                                'rgb(124, 17, 88)',
                                'rgb(26, 83, 255)',
                                'rgb(255, 163, 0)',
                                'rgb(253, 204, 229)'
                            ],
                        }
                    ]
                },
                'options': {
                    'plugins': {
                        'tickFormat': {
                            'minimumFractionDigits': 2
                        }
                    }
                }
            }

            return "https://quickchart.io/chart?c=" + json.dumps(chart_data)

    @api.model
    def get_default_date_model(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone('Asia/Jakarta'))

    file_data = fields.Binary('File', readonly=True)

    def cell_format(self, workbook):
        cell_format = {}
        cell_format['title'] = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 20,
            'font_name': 'Arial',
        })
        cell_format['sub-title'] = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 14,
            'font_name': 'Arial',
        })
        cell_format['no'] = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': True,
        })
        cell_format['header'] = workbook.add_format({
            'align': 'left',
            'border': True,
            'font_name': 'Arial',
        })

        cell_format['content'] = workbook.add_format({
            'font_size': 11,
            'align': 'left',
            'border': True,
            'font_name': 'Arial',
        })
        cell_format['content_float'] = workbook.add_format({
            'font_size': 11,
            'border': True,
            'num_format': '#,##0.00',
            'font_name': 'Arial',
        })
        cell_format['content_integer'] = workbook.add_format({
            'font_size': 11,
            'border': True,
            'num_format': '0',
            'font_name': 'Arial',
        })
        cell_format['total'] = workbook.add_format({
            'bold': True,
            'bg_color': '#d9d9d9',
            'num_format': '#,##0.00',
            'border': True,
            'font_name': 'Arial',
        })
        cell_format['percentage'] = workbook.add_format({
            'font_size': 11,
            'border': True,
            'num_format': '#,##0.00%',  # Format for percentage values
            'font_name': 'Arial',
        })
        return cell_format, workbook

    def action_export_progress_to_excel_v2(self):
        self.generate_report_data()
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        cell_format, workbook = self.cell_format(workbook)
        report_name = 'Project Progress'

        # Validate and truncate sheet name
        sheet_name = self.name.no if isinstance(self.name.no, str) else 'Sheet1'
        sheet_name = sheet_name[:31]  # Excel sheet name limit
        worksheet = workbook.add_worksheet(sheet_name)

        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 40)
        worksheet.set_column('D:G', 40)

        # Offset for headers and data
        start_row = 2 # Start from B5
        start_col = 1  # Start headers in column 1 (B column)

        for rec in self:
            # Progress Analysis
            worksheet.write(start_row, start_col, 'Progress Analysis', cell_format['title'])
            start_row += 1

            worksheet.write(start_row, start_col, 'Table 1 S-Curve', cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Plan Progress', 'Actual Progress'
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            dataSCurve = self.env['project.actual.plan.curve.report'].search([
                ('actual_curve_plan_report_id', '=', rec.id)
            ])
            start_row += 1
            for record in dataSCurve:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.actual / 100, cell_format['percentage'])
                worksheet.write(start_row, start_col + 2, record.plan / 100, cell_format['percentage'])
                start_row += 1
            start_row += 1

            worksheet.write(start_row, start_col, "Table 2 S-Curve Accumulative", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Plan Progress Accumulative', 'Actual Progress Accumulative'
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1
            for record in dataSCurve:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.accumulative_actual / 100, cell_format['percentage'])
                worksheet.write(start_row, start_col + 2, record.accumulative_plan / 100, cell_format['percentage'])
                start_row += 1
            start_row += 1

            # Cashflow Analysis
            worksheet.write(start_row, start_col, "Cashflow Analysis", cell_format['title'])
            start_row += 1
            worksheet.write(start_row, start_col, "Table 3 Cashflow Plan", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Plan Cash In', 'Plan Cash Out', 'Plan CashFlow'
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1
            dataCashFlow = self.env['project.cash.flow.report'].search([
                ('cash_flow_report_id', '=', rec.id)
            ])

            for record in dataCashFlow:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.cash_in_plan, cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.cash_out_plan, cell_format['content_float'])
                worksheet.write(start_row, start_col + 3, record.cash_flow_plan, cell_format['content_float'])
                start_row += 1
            start_row += 1

            worksheet.write(start_row, start_col, "Table 4 Cashflow Plan Accumulative", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Accumulative Plan Cash In', 'Accumulative Plan Cash Out', 'Accumulative Plan CashFlow'
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1

            for record in dataCashFlow:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.accumulative_cash_in_plan,
                                cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.accumulative_cash_out_plan,
                                cell_format['content_float'])
                worksheet.write(start_row, start_col + 3, record.accumulative_cash_flow_plan,
                                cell_format['content_float'])
                start_row += 1
            start_row += 1

            worksheet.write(start_row, start_col, "Table 5 Cashflow Actual", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Actual Cash In', 'Actual Cash Out', 'Actual CashFlow'
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1

            for record in dataCashFlow:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.cash_in_actual, cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.cash_out_actual, cell_format['content_float'])
                worksheet.write(start_row, start_col + 3, record.cash_flow_actual, cell_format['content_float'])
                start_row += 1
            start_row += 1

            worksheet.write(start_row, start_col, "Table 6 Cashflow Actual Accumulative", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Accumulative Actual Cash In', 'Accumulative Actual Cash Out',
                'Accumulative Actual CashFlow'
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1

            for record in dataCashFlow:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.accumulative_cash_in_actual,
                                cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.accumulative_cash_out_actual,
                                cell_format['content_float'])
                worksheet.write(start_row, start_col + 3, record.accumulative_cash_flow_actual,
                                cell_format['content_float'])
                start_row += 1
            start_row += 1

            # Budget Analysis
            worksheet.write(start_row, start_col, "Budget Analysis", cell_format['title'])
            start_row += 1
            worksheet.write(start_row, start_col, "Table 7 Cash Out", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Plan Cash Out', 'Actual Cash Out',
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1
            dataCashOut = self.env['project.cash.out.report'].search([
                ('cash_out_report_id', '=', rec.id)
            ])

            total_plan_cash_out = 0
            total_actual_cash_out = 0
            for record in dataCashOut:
                total_plan_cash_out += record.plan_cash_out
                total_actual_cash_out += record.actual_cash_out
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.plan_cash_out, cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.actual_cash_out, cell_format['content_float'])
                start_row += 1
            # add total
            worksheet.write(start_row, start_col, "Total", cell_format['content'])
            worksheet.write(start_row, start_col + 1, total_plan_cash_out, cell_format['content_float'])
            worksheet.write(start_row, start_col + 2, total_actual_cash_out, cell_format['content_float'])
            start_row += 1

            worksheet.write(start_row, start_col, "Table 8 Cash Out Estimated", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Plan Cash Out', 'Estimated Cash Out', 'Actual Cash Out',
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1

            for record in dataCashOut:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.plan_cash_out, cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.estimated_cash_out, cell_format['content_float'])
                worksheet.write(start_row, start_col + 3, record.actual_cash_out, cell_format['content_float'])
                start_row += 1
            start_row += 1

            worksheet.write(start_row, start_col, "Table 9 Remaining from budget", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Actual Cash Out', 'Remaining from Budget'
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1

            worksheet.write(start_row, start_col, self.total_actual_cash_out, cell_format['content_float'])
            worksheet.write(start_row, start_col + 1, self.remaining_budget, cell_format['content_float'])
            start_row += 1
            worksheet.write(start_row, start_col,
                            ((self.total_actual_cash_out or 0) / (self.remaining_budget or 1)) * 100,
                            cell_format['content_float'])
            worksheet.write(start_row, start_col + 1, (
                        ((self.remaining_budget or 1) - (self.total_actual_cash_out or 0)) / (
                            self.remaining_budget or 1)) * 100, cell_format['content_float'])
            start_row += 1

            worksheet.write(start_row, start_col, "Table 10 Remaining from Sales", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Actual Cash Out', 'Remaining from Budget'
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1

            worksheet.write(start_row, start_col, self.total_actual_cash_out, cell_format['content_float'])
            worksheet.write(start_row, start_col + 1, self.remaining_sales, cell_format['content_float'])
            start_row += 1
            worksheet.write(start_row, start_col,
                            ((self.total_actual_cash_out or 0) / (self.remaining_sales or 1)) * 100,
                            cell_format['content_float'])
            worksheet.write(start_row, start_col + 1, (
                    ((self.remaining_sales or 1) - (self.total_actual_cash_out or 0)) / (
                    self.remaining_sales or 1)) * 100, cell_format['content_float'])
            start_row += 1

            # Revenue Analysis
            worksheet.write(start_row, start_col, "Revenue Analysis", cell_format['title'])
            start_row += 1
            worksheet.write(start_row, start_col, "Table 11 Invoice", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Plan Invoice', 'Actual Invoice',
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1
            dataInvoice = self.env['project.invoice.report'].search([
                ('invoice_report_id', '=', rec.id)
            ])

            for record in dataInvoice:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.plan_invoice, cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.actual_invoice, cell_format['content_float'])
                start_row += 1
            start_row += 1

            worksheet.write(start_row, start_col, "Table 12 Invoice Accumulative", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Accumulative Plan Invoice', 'Accumulative Actual Invoice',
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1

            for record in dataInvoice:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.accumulative_plan_invoice,
                                cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.accumulative_actual_invoice,
                                cell_format['content_float'])
                start_row += 1
            start_row += 1

            worksheet.write(start_row, start_col, "Table 13 Cash In", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Plan Cash In', 'Actual Cash In',
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1
            dataCashIn = self.env['project.cash.in.report'].search([
                ('cash_in_report_id', '=', rec.id)
            ])

            for record in dataCashIn:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.plan_cash_in, cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.actual_cash_in, cell_format['content_float'])
                start_row += 1
            start_row += 1

            worksheet.write(start_row, start_col, "Table 14 Cash In Accumulative", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Accumulative Plan Cash In', 'Accumulative Actual Cash In',
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1

            for record in dataCashIn:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.accumulative_plan_cash_in,
                                cell_format['content_float'])
                worksheet.write(start_row, start_col + 2, record.accumulative_actual_cash_in,
                                cell_format['content_float'])
                start_row += 1
            start_row += 1

            # Manhour Analysis
            worksheet.write(start_row, start_col, "Manhour Analysis", cell_format['title'])
            start_row += 1
            worksheet.write(start_row, start_col, "Table 15 Manhour", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Plan Manhour', 'Actual Manhour',
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1
            dataManhourRec = self.env['project.manhour.report'].search([
                ('manhour_report_id', '=', rec.id)
            ])

            for record in dataManhourRec:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.plan_manhour, cell_format['content_integer'])
                worksheet.write(start_row, start_col + 2, record.actual_manhour, cell_format['content_integer'])
                start_row += 1
            start_row += 1

            worksheet.write(start_row, start_col, "Table 16 Manhour Accumulative", cell_format['sub-title'])
            start_row += 1
            colunms = [
                'Year - Week', 'Accumulative Plan Manhour', 'Accumulative Actual Manhour',
            ]
            for col_idx, col_name in enumerate(colunms):
                worksheet.write(start_row, start_col + col_idx, col_name, cell_format['header'])
            start_row += 1

            for record in dataManhourRec:
                worksheet.write(start_row, start_col, str(record.year) + " - " + str(record.weeks),
                                cell_format['content'])
                worksheet.write(start_row, start_col + 1, record.accumulative_plan_manhour,
                                cell_format['content_integer'])
                worksheet.write(start_row, start_col + 2, record.accumulative_actual_manhour,
                                cell_format['content_integer'])
                start_row += 1
            start_row += 1

        workbook.close()
        result = base64.encodestring(fp.getvalue())
        project = self.name.no or ''
        filename = '%s %s ' % (report_name, project,)
        filename += '%2Ecsv'
        self.write({'file_data': result})
        url = "web/content/?model=" + self._name + "&id=" + str(
            self[:1].id) + "&field=file_data&download=true&filename=" + filename
        return {
            'name': 'Generic Excel Report',
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    @api.multi
    def print_actual_plan_curve_report(self):
        """
        Prepare data and trigger the PDF report.
        """
        self.generate_report_data()
        return self.env.ref('rnet_project_management.report_project_management').report_action(self)

    def generate_report_data(self):
        self.generate_start_finish_dates()  # Populate data dynamically
        self.generate_actual_plan_curve_lines_report()  # Populate data dynamically
        self.generate_cash_flow_report()  # Populate data dynamically
        self.generate_total_report()  # Populate data dynamically
        self.generate_cash_out_report()  # Populate data dynamically
        self.generate_cash_in_report()  # Populate data dynamically
        self.generate_invoice_report()  # Populate data dynamically
        self.generate_manhour_report()  # Populate data dynamically
        self.current_date = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        for rec in self:
            reports = rec.project_actual_plan_curve_report.sorted(key=lambda r: (r.year, r.weeks))
            if reports:
                rec.last_accumulative_actual_progress = reports[-1].accumulative_actual
            else:
                rec.last_accumulative_actual_progress = 0.0

    def generate_start_finish_dates(self):
        for record in self:
            if record.project_plan_curve_line:
                valid_lines = record.project_plan_curve_line.filtered(lambda line: line.date)

                if valid_lines:
                    # Sort the filtered lines by date
                    sorted_lines = valid_lines.sorted('date')
                    record.start_date = sorted_lines[0].date  # First date
                    record.finish_date = sorted_lines[-1].date  # Last date
                else:
                    # Handle case where all dates are empty
                    record.start_date = False
                    record.finish_date = False
            else:
                record.start_date = False
                record.finish_date = False

    @api.multi
    def generate_actual_plan_curve_lines_report(self):
        """
        Function to dynamically update the project_actual_plan_curve_line field.
        """
        for rec in self:
            # Fetch actual plan curve data
            project_actual_plan_curve_report = self.get_actual_plan_curve_lines_report()

            # Clear existing records and prepare new records
            actual_plan_curve_report = rec.project_actual_plan_curve_report.browse([])  # Start with an empty recordset
            for data in project_actual_plan_curve_report:
                actual_plan_curve_report += actual_plan_curve_report.new(data)

            # Assign the dynamically created lines back to the field
            rec.project_actual_plan_curve_report = (actual_plan_curve_report)

    @api.multi
    def generate_cash_flow_report(self):
        """
        Function to dynamically update the project_actual_plan_curve_line field.
        """
        for rec in self:
            # Fetch actual plan curve data
            project_cash_flow_report = self.get_cash_flow_report()

            # Clear existing records and prepare new records
            cash_flow_report = rec.project_cash_flow_report.browse([])  # Start with an empty recordset
            for data in project_cash_flow_report:
                cash_flow_report += cash_flow_report.new(data)

            # Assign the dynamically created lines back to the field
            rec.project_cash_flow_report = cash_flow_report

    @api.multi
    def generate_cash_out_report(self):
        """
        Function to dynamically update the project_actual_plan_curve_line field.
        """
        for rec in self:
            # Fetch actual plan curve data
            project_cash_out_report = self.get_cash_out_report()

            # Clear existing records and prepare new records
            cash_out_report = rec.project_cash_out_report.browse([])  # Start with an empty recordset
            for data in project_cash_out_report:
                cash_out_report += cash_out_report.new(data)

            # Assign the dynamically created lines back to the field
            rec.project_cash_out_report = cash_out_report

    @api.multi
    def generate_total_report(self):
        """
        Function to dynamically update the project_actual_plan_curve_line field.
        """
        for rec in self:
            # Fetch actual plan curve data
            project_cash_out_report = self.get_cash_out_report()
            project_invoice_report = self.get_invoice_report()

            # Clear existing records and prepare new records
            total_plan_cash_out = 0  # Initialize total
            total_actual_cash_out = 0  # Initialize total
            total_invoice = 0  # Initialize total
            for data in project_cash_out_report:
                total_plan_cash_out += data.get('plan_cash_out', 0)  # Accumulate the total
                total_actual_cash_out += data.get('actual_cash_out', 0)  # Accumulate the total

            for data in project_invoice_report:
                total_invoice += data.get('plan_invoice',0)


            remaining_budget = total_plan_cash_out - total_actual_cash_out
            remaining_sales = total_invoice - total_actual_cash_out

            # Assign the dynamically created lines back to the field
            rec.total_plan_cash_out = total_plan_cash_out
            rec.remaining_budget = remaining_budget
            rec.total_actual_cash_out = total_actual_cash_out
            rec.remaining_sales = remaining_sales

    @api.multi
    def generate_cash_in_report(self):
        """
        Function to dynamically update the project_actual_plan_curve_line field.
        """
        for rec in self:
            # Fetch actual plan curve data
            project_cash_in_report = self.get_cash_in_report()

            # Clear existing records and prepare new records
            cash_in_report = rec.project_cash_in_report.browse([])  # Start with an empty recordset
            total_plan_cash_in = 0  # Initialize total
            total_actual_cash_in = 0  # Initialize total
            for data in project_cash_in_report:
                cash_in_report += cash_in_report.new(data)
                total_plan_cash_in += data.get('plan_cash_in', 0)  # Accumulate the total
                total_actual_cash_in += data.get('actual_cash_in', 0)  # Accumulate the total

            # Assign the dynamically created lines back to the field
            rec.project_cash_in_report = cash_in_report
            rec.total_plan_cash_in = total_plan_cash_in
            rec.total_actual_cash_in = total_actual_cash_in

    @api.multi
    def generate_invoice_report(self):
        """
        Function to dynamically update the project_actual_plan_curve_line field.
        """
        for rec in self:
            # Fetch actual plan curve data
            project_invoice_report = self.get_invoice_report()

            # Clear existing records and prepare new records
            invoice_report = rec.project_invoice_report.browse([])  # Start with an empty recordset
            for data in project_invoice_report:
                invoice_report += invoice_report.new(data)


            # Assign the dynamically created lines back to the field
            rec.project_invoice_report = invoice_report

    @api.multi
    def generate_manhour_report(self):
        """
        Function to dynamically update the project_actual_plan_curve_line field.
        """
        for rec in self:
            # Fetch actual plan curve data
            project_manhour_report = self.get_manhour_report()

            # Clear existing records and prepare new records
            manhour_report = rec.project_manhour_report.browse([])  # Start with an empty recordset
            for data in project_manhour_report:
                manhour_report += manhour_report.new(data)

            # Assign the dynamically created lines back to the field
            rec.project_manhour_report = manhour_report

    @api.model
    def get_actual_plan_curve_lines_report(self):
        result = []  # Initialize a list to store report data
        for rec in self:
            # Initialize variables for accumulative values
            accumulative_actual = 0
            accumulative_plan = 0

            # Fetch actual and plan curves
            actual_curves = self.env['project.actual.curve'].search([('plan_actual_curve_id', '=', rec.id)])
            plan_curves = self.env['project.plan.curve'].search([('plan_plan_curve_id', '=', rec.id)])

            # Group data by weeks
            weekly_data = {}

            # Process actual curves
            for curve in actual_curves:
                if curve.date:
                    year_start = datetime(curve.date.year, 1, 1).date()
                    week_number = math.ceil((curve.date - year_start).days / 7.0)
                    year = curve.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    if key not in weekly_data:
                        weekly_data[key] = {'actual': 0, 'plan': 0}
                    weekly_data[key]['actual'] += curve.name

            # Process plan curves
            for curve in plan_curves:
                if curve.date:
                    year_start = datetime(curve.date.year, 1, 1).date()
                    week_number = math.ceil((curve.date - year_start).days / 7.0)
                    year = curve.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    if key not in weekly_data:
                        weekly_data[key] = {'actual': 0, 'plan': 0}
                    weekly_data[key]['plan'] += curve.name

            # Create report data
            for key in sorted(weekly_data.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
                year, week_number = key.split('-')  # Split back into components if needed
                data = weekly_data[key]
                accumulative_actual += data['actual']
                accumulative_plan += data['plan']

                # Append the data to the result list
                result.append({
                    'actual_curve_plan_report_id': rec.id,
                    'weeks': int(week_number),  # Convert week back to integer
                    'year': int(year),  # Convert year back to integer
                    'actual': data['actual'],
                    'accumulative_actual': accumulative_actual,
                    'plan': data['plan'],
                    'accumulative_plan': accumulative_plan,
                })
        return result

    @api.model
    def get_cash_flow_report(self):
        result = []  # Initialize a list to store report data
        for rec in self:
            # Initialize variables for accumulative values
            accumulative_cash_in_plan = 0
            accumulative_cash_out_plan = 0
            accumulative_cash_flow_plan = 0
            accumulative_cash_in_actual = 0
            accumulative_cash_out_actual = 0
            accumulative_cash_flow_actual = 0

            # Fetch cash-in and cash-out data for the current project
            cash_in_data_plan = self.env['project.plan.cashin'].search([
                ('plan_plan_cashin_id', '=', rec.id),
            ])
            cash_out_data_plan = self.env['project.plan.cashout'].search([
                ('plan_plan_cashout_id', '=', rec.id)
            ])
            cash_in_data_actual = self.env['project.actual.cashin'].search([
                ('actual_cashin_line_id', '=', rec.id),
            ])
            cash_out_data_actual = self.env['project.actual.cashout'].search([
                ('actual_cashout_line_id', '=', rec.id)
            ])

            # Group data by weeks
            weekly_data = {}

            # Process cash-in data
            for cash_in in cash_in_data_plan:
                if cash_in.date:
                    year_start = datetime(cash_in.date.year, 1, 1).date()
                    week_number = math.ceil((cash_in.date - year_start).days / 7.0)
                    year = cash_in.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key

                    if key not in weekly_data:
                        weekly_data[key] = {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_out_actual': 0,
                                            'cash_in_actual': 0}
                    weekly_data[key]['cash_in_plan'] += cash_in.name

            # Process cash-out data
            for cash_out in cash_out_data_plan:
                if cash_out.date:
                    year_start = datetime(cash_out.date.year, 1, 1).date()
                    week_number = math.ceil((cash_out.date - year_start).days / 7.0)
                    year = cash_out.date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    if key not in weekly_data:
                        weekly_data[key] = {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_out_actual': 0,
                                            'cash_in_actual': 0}
                    weekly_data[key]['cash_out_plan'] += cash_out.name

            # Process cash-in data
            for cash_in in cash_in_data_actual:
                if cash_in.payment_date:
                    year_start = datetime(cash_in.payment_date.year, 1, 1).date()
                    week_number = math.ceil((cash_in.payment_date - year_start).days / 7.0)
                    year = cash_in.payment_date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key

                    if key not in weekly_data:
                        weekly_data[key] = {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_out_actual': 0,
                                            'cash_in_actual': 0}
                    weekly_data[key]['cash_in_actual'] += cash_in.amount

            # Process cash-out data
            for cash_out in cash_out_data_actual:
                if cash_out.payment_date:
                    year_start = datetime(cash_out.payment_date.year, 1, 1).date()
                    week_number = math.ceil((cash_out.payment_date - year_start).days / 7.0)
                    year = cash_out.payment_date.year
                    key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                    if key not in weekly_data:
                        weekly_data[key] = {'cash_in_plan': 0, 'cash_out_plan': 0, 'cash_out_actual': 0,
                                            'cash_in_actual': 0}
                    weekly_data[key]['cash_out_actual'] += cash_out.amount

            # Create report data
            for key in sorted(weekly_data.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
                year, week_number = key.split('-')  # Split back into components if needed
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

                # Append the data to the result list
                result.append({
                    'cash_flow_report_id': rec.id,
                    'weeks': int(week_number),  # Convert week back to integer
                    'year': int(year),  # Convert year back to integer
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
                })

            # Optionally, create records in the `project.cash.flow.report` model
            for data in result:
                self.env['project.cash.flow.report'].create(data)

        return result

    @api.model
    def get_cash_out_report(self):
        result = []  # Initialize a list to store report data
        for rec in self:
            # Fetch actual and planned cash out data
            actual_cash_out_data = self.env['project.actual.cashout'].search([
                ('actual_cashout_line_id', '=', rec.id)
            ])

            plan_cash_out_data = self.env['project.plan.cashout'].search([
                ('plan_plan_cashout_id', '=', rec.id)
            ])

            estimated_cash_out_data = self.env['project.estimated.cashout'].search([
                ('estimated_cashout_line_id', '=', rec.id)
            ])

            # Group data by weeks
            weekly_data = {}
            accumulative_actual_cashout = 0

            # Process actual cash out data
            for actual in actual_cash_out_data:
                year_start = datetime(actual.payment_date.year, 1, 1).date()
                week_number = math.ceil((actual.payment_date - year_start).days / 7.0)
                year = actual.payment_date.year
                key = str(year) + "-" + str(week_number)  # Use a tuple for the key

                weekly_data.setdefault(key, {'actual_cash_out': 0, 'plan_cash_out': 0, 'estimated_cash_out': 0})
                weekly_data[key]['actual_cash_out'] += actual.amount  # Assuming `amount` is the field

            # Process planned cash out data
            for plan in plan_cash_out_data:
                year_start = datetime(plan.date.year, 1, 1).date()
                week_number = math.ceil((plan.date - year_start).days / 7.0)
                year = plan.date.year
                key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                weekly_data.setdefault(key, {'actual_cash_out': 0, 'plan_cash_out': 0, 'estimated_cash_out': 0})
                weekly_data[key]['plan_cash_out'] += plan.name

            # Process planned cash out data
            for estimated in estimated_cash_out_data:
                year_start = datetime(estimated.created_date.year, 1, 1).date()
                week_number = math.ceil((estimated.created_date - year_start).days / 7.0)
                year = estimated.created_date.year
                key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                weekly_data.setdefault(key, {'actual_cash_out': 0, 'plan_cash_out': 0, 'estimated_cash_out': 0})
                weekly_data[key]['estimated_cash_out'] += estimated.amount

            # Create report data
            for key in sorted(weekly_data.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
                year, week_number = key.split('-')  # Split back into components if needed
                data = weekly_data[key]
                # Append the data to the result list
                result.append({
                    'cash_out_report_id': rec.id,
                    'weeks': int(week_number),  # Convert week back to integer
                    'year': int(year),  # Convert year back to integer
                    'actual_cash_out': data['actual_cash_out'],
                    'estimated_cash_out': data['estimated_cash_out'],
                    'plan_cash_out': data['plan_cash_out'],
                })

            # Optionally, create records in the `project.cash.out.report` model
            for data in result:
                self.env['project.cash.out.report'].create(data)

        return result

    @api.model
    def get_cash_in_report(self):
        result = []  # Initialize a list to store report data
        for rec in self:
            accumulative_plan_cash_in = 0
            accumulative_actual_cash_in = 0
            # Fetch actual and planned cash out data
            actual_cash_in_data = self.env['project.actual.cashin'].search([
                ('actual_cashin_line_id', '=', rec.id)
            ])

            plan_cash_in_data = self.env['project.plan.cashin'].search([
                ('plan_plan_cashin_id', '=', rec.id)
            ])

            # Group data by weeks
            weekly_data = {}

            # Process actual cash out data
            for actual in actual_cash_in_data:
                year_start = datetime(actual.payment_date.year, 1, 1).date()
                week_number = math.ceil((actual.payment_date - year_start).days / 7.0)
                year = actual.payment_date.year
                key = str(year) + "-" + str(week_number)  # Use a tuple for the key

                weekly_data.setdefault(key, {'actual_cash_in': 0, 'plan_cash_in': 0})
                weekly_data[key]['actual_cash_in'] += actual.amount  # Assuming `amount` is the field

            # Process planned cash out data
            for plan in plan_cash_in_data:
                year_start = datetime(plan.date.year, 1, 1).date()
                week_number = math.ceil((plan.date - year_start).days / 7.0)
                year = plan.date.year
                key = str(year) + "-" + str(week_number)  # Use a tuple for the key

                weekly_data.setdefault(key, {'actual_cash_in': 0, 'plan_cash_in': 0})
                weekly_data[key]['plan_cash_in'] += plan.name

            # Create report data
            for key in sorted(weekly_data.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
                year, week_number = key.split('-')  # Split back into components if needed
                data = weekly_data[key]
                accumulative_plan_cash_in += data['plan_cash_in']
                accumulative_actual_cash_in += data['actual_cash_in']
                # Append the data to the result list
                result.append({
                    'cash_in_report_id': rec.id,
                    'weeks': int(week_number),  # Convert week back to integer
                    'year': int(year),  # Convert year back to integer
                    'actual_cash_in': data['actual_cash_in'],
                    'plan_cash_in': data['plan_cash_in'],
                    'accumulative_plan_cash_in': accumulative_plan_cash_in,
                    'accumulative_actual_cash_in': accumulative_actual_cash_in,
                })

            # Optionally, create records in the `project.cash.out.report` model
            for data in result:
                self.env['project.cash.in.report'].create(data)

        return result

    @api.model
    def get_invoice_report(self):
        result = []  # Initialize a list to store report data
        for rec in self:
            accumulative_plan_invoice = 0
            accumulative_actual_invoice = 0
            # Fetch actual and planned cash out data
            actual_invoice_data = self.env['project.actual.invoice'].search([
                ('actual_invoice_line_id', '=', rec.id)
            ])

            plan_invoice_data = self.env['project.plan.invoice'].search([
                ('plan_plan_invoice_id', '=', rec.id)
            ])

            # Group data by weeks
            weekly_data = {}

            # Process actual cash out data
            for actual in actual_invoice_data:
                year_start = datetime(actual.created_date.year, 1, 1).date()
                week_number = math.ceil((actual.created_date - year_start).days / 7.0)
                year = actual.created_date.year
                key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                weekly_data.setdefault(key, {'actual_invoice': 0, 'plan_invoice': 0})
                weekly_data[key]['actual_invoice'] += actual.amount  # Assuming `amount` is the field

            # Process planned cash out data
            for plan in plan_invoice_data:
                year_start = datetime(plan.date.year, 1, 1).date()
                week_number = math.ceil((plan.date - year_start).days / 7.0)
                year = plan.date.year
                key = str(year) + "-" + str(week_number)  # Use a tuple for the key
                weekly_data.setdefault(key, {'actual_invoice': 0, 'plan_invoice': 0})
                weekly_data[key]['plan_invoice'] += plan.name

            # Create report data
            for key in sorted(weekly_data.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
                year, week_number = key.split('-')  # Split back into components if needed
                data = weekly_data[key]
                accumulative_plan_invoice += data['plan_invoice']
                accumulative_actual_invoice += data['actual_invoice']

                # Append the data to the result list
                result.append({
                    'invoice_report_id': rec.id,
                    'weeks': int(week_number),  # Convert week back to integer
                    'year': int(year),  # Convert year back to integer
                    'actual_invoice': data['actual_invoice'],
                    'plan_invoice': data['plan_invoice'],
                    'accumulative_plan_invoice': accumulative_plan_invoice,
                    'accumulative_actual_invoice': accumulative_actual_invoice,
                })

            # Optionally, create records in the `project.cash.out.report` model
            for data in result:
                self.env['project.invoice.report'].create(data)

        return result

    @api.model
    def get_manhour_report(self):
        result = []  # Initialize a list to store report data
        for rec in self:
            accumulative_plan_manhour = 0
            accumulative_actual_manhour = 0
            # Fetch actual and planned cash out data
            actual_man_hour_data = self.env['project.actual.manhour'].search([
                ('actual_manhour_line_id', '=', rec.id)
            ])

            plan_man_hour_data = self.env['project.plan.manhour'].search([
                ('plan_plan_manhour_id', '=', rec.id)
            ])

            # Group data by weeks
            weekly_data = {}

            # Process actual manhour data
            for actual in actual_man_hour_data:
                year_start = datetime(actual.date_from.year, 1, 1).date()
                week_number = math.ceil((actual.date_from - year_start).days / 7.0)
                year = actual.date_from.year
                key = str(year) + "-" + str(week_number)
                weekly_data.setdefault(key, {'actual_manhour': 0, 'plan_manhour': 0})
                weekly_data[key]['actual_manhour'] += actual.total


            # Process planned manhour data
            for plan in plan_man_hour_data:
                year_start = datetime(plan.date.year, 1, 1).date()
                week_number = math.ceil((plan.date - year_start).days / 7.0)
                year = plan.date.year
                key = str(year) + "-" + str(week_number)
                weekly_data.setdefault(key, {'actual_manhour': 0, 'plan_manhour': 0})
                weekly_data[key]['plan_manhour'] += plan.name  # assuming `plan.name` is the number of manhours

            # Create report data
            for key in sorted(weekly_data.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
                year, week_number = key.split('-')  # Split back into components if needed
                data = weekly_data[key]
                accumulative_plan_manhour += data['plan_manhour']
                accumulative_actual_manhour += data['actual_manhour']
                # Append the data to the result list
                result.append({
                    'manhour_report_id': rec.id,
                    'weeks': int(week_number),  # Convert week back to integer
                    'year': int(year),  # Convert year back to integer
                    'actual_manhour': data['actual_manhour'],
                    'plan_manhour': data['plan_manhour'],
                    'accumulative_plan_manhour': accumulative_plan_manhour,
                    'accumulative_actual_manhour': accumulative_actual_manhour,
                })

            # Optionally, create records in the `project.cash.out.report` model
            for data in result:
                self.env['project.manhour.report'].create(data)

        return result

    def _get_date_from_year_week(self, year, week):
        # Calculate the first day of the given year and week number
        # Week 1 starts from the first Monday of the year
        first_day_of_year = datetime(year, 1, 1)

        # Adjust to the first Monday of the year
        days_to_first_monday = (7 - first_day_of_year.weekday()) % 7
        first_monday = first_day_of_year + timedelta(days=days_to_first_monday)

        # Calculate the start of the given week
        start_of_week = first_monday + timedelta(weeks=week - 1)

        # Return the start date as a date object (not datetime)
        return start_of_week.date()

    def action_export_dashboard(self):
        self.generate_report_data()
        return self.env.ref('rnet_project_management.report_project_management_test_pdf').report_action(self)

class ProjectActualPlanCurveReport(models.Model):
    _name = 'project.actual.plan.curve.report'
    _description = 'Actual and Plan Curve Report'

    actual_curve_plan_report_id = fields.Many2one('project.progress.plan', string='Actual Curve Report', ondelete='cascade')
    weeks = fields.Integer(string='Week Number', required=True)
    year = fields.Integer(string='Year Number', required=True)
    actual = fields.Float(string='Actual Value', required=True)
    accumulative_actual = fields.Float(string='Actual Accumulative Value', required=True)
    plan = fields.Float(string='Planned Value', required=True)
    accumulative_plan = fields.Float(string='Planned Accumulative Value', required=True)

class ProjectCashFlowReport(models.Model):
    _name = 'project.cash.flow.report'
    _description = 'Cash Flow Report'

    cash_flow_report_id = fields.Many2one('project.progress.plan', string='Cash Flow Report', ondelete='cascade')
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
    _name = 'project.cash.out.report'
    _description = 'Cash Out Report'

    cash_out_report_id = fields.Many2one('project.progress.plan', string='Cash Out Report', ondelete='cascade')
    weeks = fields.Integer(string='Week Number', required=True)
    year = fields.Integer(string='Year Number', required=True)
    plan_cash_out = fields.Float(string='Plan Cash Out', required=True)
    actual_cash_out = fields.Float(string='Actual Cash Out', required=True)
    estimated_cash_out = fields.Float(string='Estimated Cash Out', required=True)

class ProjectCashInReport(models.Model):
    _name = 'project.cash.in.report'
    _description = 'Cash In Report'

    cash_in_report_id = fields.Many2one('project.progress.plan', string='Cash In Report', ondelete='cascade')
    weeks = fields.Integer(string='Week Number', required=True)
    year = fields.Integer(string='Year Number', required=True)
    plan_cash_in = fields.Float(string='Plan Cash In', required=True)
    actual_cash_in = fields.Float(string='Actual Cash In', required=True)
    accumulative_plan_cash_in = fields.Float(string='Accumulative Plan Cash In', required=True)
    accumulative_actual_cash_in = fields.Float(string='Accumulative Actual Cash In', required=True)

class ProjectInvoiceReport(models.Model):
    _name = 'project.invoice.report'
    _description = 'Invoice Report'

    invoice_report_id = fields.Many2one('project.progress.plan', string='Invoice Report', ondelete='cascade')
    weeks = fields.Integer(string='Week Number', required=True)
    year = fields.Integer(string='Year Number', required=True)
    plan_invoice = fields.Float(string='Plan Invoice', required=True)
    actual_invoice = fields.Float(string='Actual Invoice', required=True)
    accumulative_plan_invoice = fields.Float(string='Accumulative Plan Invoice', required=True)
    accumulative_actual_invoice = fields.Float(string='Accumulative Actual Invoice', required=True)

class ProjectManhourReport(models.Model):
    _name = 'project.manhour.report'
    _description = 'Manhour Report'

    manhour_report_id = fields.Many2one('project.progress.plan', string='Manhour Report', ondelete='cascade')
    weeks = fields.Integer(string='Week Number', required=True)
    year = fields.Integer(string='Year Number', required=True)
    plan_manhour = fields.Float(string='Plan Man Hour', required=True)
    actual_manhour = fields.Float(string='Actual Man Hour', required=True)
    accumulative_plan_manhour = fields.Float(string='Accumulative Plan Man Hour', required=True)
    accumulative_actual_manhour = fields.Float(string='Accumulative Actual Man Hour', required=True)
