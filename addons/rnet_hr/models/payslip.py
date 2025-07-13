from odoo import api, fields, models, tools, _
from datetime import date, datetime, timedelta, time
from pytz import timezone
from time import gmtime
from dateutil.relativedelta import relativedelta
from time import strftime
import logging
import babel
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    grade = fields.Many2one('employee.grade', string='Employee Grade')
    alw_pay = fields.Float(string='Total Allowance',
                           compute='_compute_tota1_alw')
    npwp = fields.Char(related='employee_id.gut_npwp', string='NPWP')
    status_kawin = fields.Selection(
        related='employee_id.status', string='Status')
    grade = fields.Many2one(
        'employee.grade', related='employee_id.employee_grade', string='Grade', readonly="1")
    active = fields.Boolean(default=True)
    timeshseet_month = fields.Char(
        string='Month', compute='_get_timesheet_sheet_month')
    timesheet_id = fields.Many2one('hr_timesheet.sheet', string='Timesheet', compute="_compute_timesheet_id")
    refresh_onchange_actual_value = fields.Datetime(string="Update Actual Value??")

    # trigger untuk onchange update actual value
    def action_update_actual_value(self):
        for rec in self:
            self.write({
                    'refresh_onchange_actual_value' : fields.Datetime.now(),
                })
            rec.onchange_employee()
            rec.compute_sheet()
        return True

    def get_number_of_days_timesheet(self, contract_id, date_from, date_to):
        if not contract_id:
            return {}
        employee_id = contract_id.employee_id
        sheets = self.env['hr_timesheet.sheet'].search([
            ('employee_id', '=', employee_id.id),
            ('date_start', '>=', date_from),
            ('date_end', '<=', date_to),])

        return {
                'hours': sheets.total_normal,
                }
            
    @api.onchange('employee_id', 'date_from')
    def onchange_employee(self):
        super(HrPayslip, self).onchange_employee()
        datas = self.get_number_of_days_timesheet(self.contract_id, self.date_from, self.date_to)
        return


# compute timesheet_id di payslip
    @api.multi
    @api.depends('employee_id', 'date_from')
    def _compute_timesheet_id(self):
        for rec in  self:
            for ts in self.env['hr_timesheet.sheet'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date_start', '>=', rec.date_from),
                ('date_end', '<=', rec.date_to),]):
            
                rec.timesheet_id = ts       

# compute allowance di payslip
    @api.model
    def _compute_tota1_alw(self):
        for day in self.env['hr_timesheet.sheet'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '>=', self.date_from),
            ('date_end', '<=', self.date_to),]):
            
            for rec in self:
                if rec.timeshseet_month :
                    self.alw_pay = day.total_bayar
                else:
                    self.alw_pay_pay  = 0

    # compute statinfo timesheet di payslip
    @api.multi
    def _get_timesheet_sheet_month(self):
        timesheet = self.env['hr_timesheet.sheet'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '>=', self.date_from),
            ('date_end', '<=', self.date_to),
        ])
        for record in timesheet:
            self.timeshseet_month = record.date_start.strftime('%B')

    @api.multi
    def open_timesheet_sheet(self):
        for rec in self:
            return {
                'name': _('hr_timesheet.sheet.form'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr_timesheet.sheet',
                'type': 'ir.actions.act_window',
                'domain': [
                    ('employee_id', '=', rec.employee_id.id),
                    ('date_start', '>=', rec.date_from),
                    ('date_end', '<=', rec.date_to),
                ],
            }
        pass


# compute work days line overtime
    # @api.model
    # def get_worked_day_lines(self, contracts, date_from, date_to):
    #     def create_empty_worked_lines(employee_id, contract_id, date_from, date_to):

    #         normal = {
    #             "name": 'Normal Time',
    #             "sequence": 1,
    #             "code": "Normal",
    #             "number_of_days": 0.0,
    #             "number_of_hours":0.0,
    #             "contract_id": contract_id,
    #         }

    #         class1 = {
    #             'name': 'Timesheet Overtime Class 1',
    #             'sequence': 2,
    #             'code': 'CLASS1',
    #             'number_of_days': 0.0,
    #             'number_of_hours': 0.0,
    #             'contract_id': contract_id,
    #         }

    #         class2 = {
    #             'name': 'Timesheet Overtime Class 2',
    #             'sequence': 3,
    #             'code': 'CLASS2',
    #             'number_of_days': 0.0,
    #             'number_of_hours': 0.0,
    #             'contract_id': contract_id,
    #         }
    #         class3 = {
    #             'name': 'Timesheet Overtime Class 3',
    #             'sequence': 4,
    #             'code': 'CLASS3',
    #             'number_of_days': 0.0,
    #             'number_of_hours': 0.0,
    #             'contract_id': contract_id,
    #         }
    #         class4 = {
    #             'name': 'Timesheet Overtime Class 4',
    #             'sequence': 5,
    #             'code': 'CLASS4',
    #             'number_of_days': 0.0,
    #             'number_of_hours': 0.0,
    #             'contract_id': contract_id,
    #         }

    #         valid_days = [
    #             ('employee_id', '=', employee_id),
    #             # ('state', '=', 'done'),
    #             ('date_start', '>=', date_from),
    #             ('date_end', '<=', date_to),
    #         ]
    #         return normal, class1, class2, class3, class4, valid_days

    #     normals = []
    #     class1s = []
    #     class2s = []
    #     class3s = []
    #     class4s = []

    #     for contract in contracts:
    #         normal, class1, class2, class3, class4, valid_days = create_empty_worked_lines(
    #             contract.employee_id.id,
    #             contract.id,
    #             date_from,
    #             date_to
    #         )

    #         for day in self.env['hr_timesheet.sheet'].search(valid_days):
    #             if day.total_hours >= 0.0:
    #                 normal['number_of_hours'] = day.total_normal
    #                 normal['number_of_days'] = len(day.attendances_ids.filtered(lambda line: line.gut_normal_hours  > 0))
    #                 class1['number_of_hours'] = day.total_class1
    #                 class1['number_of_days'] = len(day.attendances_ids.filtered(lambda line: line.gut_class1  > 0))
    #                 class2['number_of_hours'] = day.total_class2
    #                 class2['number_of_days'] = len(day.attendances_ids.filtered(lambda line: line.gut_class2  > 0))
    #                 class3['number_of_hours'] = day.total_class3
    #                 class3['number_of_days'] = len(day.attendances_ids.filtered(lambda line: line.gut_class3  > 0))
    #                 class4['number_of_hours'] = day.total_class4
    #                 class4['number_of_days'] = len(day.attendances_ids.filtered(lambda line: line.gut_class4  > 0))

    #         # needed so that the shown hours matches any calculations you use them for
    #         # attendance['number_of_hours'] = round(attendance['number_of_hours'], 2)

    #         normals.append(normal)
    #         class1s.append(class1)
    #         class2s.append(class2)
    #         class3s.append(class3)
    #         class4s.append(class4)

    #     res = super(HrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)
    #     res.extend(normals)
    #     res.extend(class1s)
    #     res.extend(class2s)
    #     res.extend(class3s)
    #     res.extend(class4s)

    #     return res

# compute input line payslip

    # @api.model
    # def get_inputsxx(self, contracts, date_from, date_to):

    #     thrs = []
    #     loans = []
    #     for rec in self:
    #     # fill only if the contract as a working schedule linked
    #         for contract in self.env['hr.contract'].search([
    #                 ('employee_id', '=', rec.employee_id.id),
    #             ]):
                
    #             day_from = datetime.combine(date_from, time.min)
    #             day_to = datetime.combine(date_to, time.max)
    #             day_contract_start = datetime.combine(
    #                 contract.date_start, time.min)
    #             # only use payslip day_from if it's greather than contract start date
    #             if day_from < day_contract_start:
    #                 day_from = day_contract_start

    #             loan = {
    #                 'name': 'Pinjaman',
    #                 'sequence': 10,
    #                 'code': 'LOAN',
    #                 'amount': 0.0,
    #                 "contract_id": contract.id,
    #             }

    #             thr = {
    #                 'name': 'THR',
    #                 'sequence': 9,
    #                 'code': 'THR',
    #                 'amount': 0.0,
    #                 "contract_id": contract.id,
    #             }

    #             loans.append(loan)
    #             thrs.append(thr)

    #         res = super(HrPayslip, self).get_inputs(contracts, date_from, date_to)
    #         res.extend(loans)
    #         res.extend(thrs)

    #         return res
  

    # @api.model
    # def get_worked_day_linesxx(self, contracts, date_from, date_to):
    #     res = [] 

    #     # compute worked days
    #     for day in self.env['hr_timesheet.sheet'].search([
    #         ('employee_id', '=', self.employee_id.id),
    #         ('date_start', '>=', date_from),
    #         ('date_end', '<=', date_to),
    #     ]):
    #         if day.total_hours >= 0.0:
    #             normals = {
    #                 'name': _("Timesheet Normal Hour"),
    #                 'sequence': 1,
    #                 'code': 'Normal',
    #                 'number_of_days': len(day.attendances_ids.filtered(lambda line: line.gut_normal_hours > 0)),
    #                 'number_of_hours': day.total_normal,
    #                 'contract_id': self.contract_id,
    #             }
    #             class1s = {
    #                 'name': _("Timesheet Overtime Class 1"),
    #                 'sequence': 2,
    #                 'code': 'CLASS1',
    #                 'number_of_days': len(day.attendances_ids.filtered(lambda line: line.gut_class1 > 0)),
    #                 'number_of_hours': day.total_class1,
    #                 'contract_id': self.contract_id,
    #             }
    #             class2s = {
    #                 'name': _("Timesheet Overtime Class 2"),
    #                 'sequence': 3,
    #                 'code': 'CLASS2',
    #                 'number_of_days': len(day.attendances_ids.filtered(lambda line: line.gut_class2 > 0)),
    #                 'number_of_hours': day.total_class2,
    #                 'contract_id': self.contract_id,
    #             }
    #             class3s = {
    #                 'name': _("Timesheet Overtime Class 3"),
    #                 'sequence': 4,
    #                 'code': 'CLASS3',
    #                 'number_of_days': len(day.attendances_ids.filtered(lambda line: line.gut_class3 > 0)),
    #                 'number_of_hours': day.total_class3,
    #                 'contract_id': self.contract_id,
    #             }
    #             class4s = {
    #                 'name': _("Timesheet Overtime Class 4"),
    #                 'sequence': 5,
    #                 'code': 'CLASS4',
    #                 'number_of_days': len(day.attendances_ids.filtered(lambda line: line.gut_class4 > 0)),
    #                 'number_of_hours': day.total_class4,
    #                 'contract_id': self.contract_id,
    #             }

    #         res.append(normals)
    #         res.append(class1s)
    #         res.append(class2s)
    #         res.append(class3s)
    #         res.append(class4s)
    #     return res   

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to, calendar=contract.resource_calendar_id)
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': 'LEAVES',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                current_leave_struct['number_of_hours'] += hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct['number_of_days'] += hours / work_hours
            # compute worked days
            work_data = contract.employee_id.get_work_days_data(day_from, day_to, calendar=contract.resource_calendar_id)
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],
                'number_of_hours': work_data['hours'],
                'contract_id': contract.id,
            }
            normals = {
                    'name': _("Timesheet Normal Hour"),
                    'sequence': 1,
                    'code': 'Normal',
                    'number_of_days': len(self.timesheet_id.attendances_ids.filtered(lambda line: line.gut_normal_hours > 0)),
                    'number_of_hours': self.timesheet_id.total_normal,
                    'contract_id': contract.id,
                }

            class1s = {
                    'name': _("Timesheet Overtime Class 1"),
                    'sequence': 2,
                    'code': 'CLASS1',
                    'number_of_days': len(self.timesheet_id.attendances_ids.filtered(lambda line: line.gut_class1 > 0)),
                    'number_of_hours': self.timesheet_id.total_class1,
                    'contract_id': 
                    contract.id,
                }
            class2s = {
                    'name': _("Timesheet Overtime Class 2"),
                    'sequence': 3,
                    'code': 'CLASS2',
                    'number_of_days': len(self.timesheet_id.attendances_ids.filtered(lambda line: line.gut_class2 > 0)),
                    'number_of_hours': self.timesheet_id.total_class2,
                    'contract_id': 
                    contract.id,
                }
            class3s = {
                    'name': _("Timesheet Overtime Class 3"),
                    'sequence': 4,
                    'code': 'CLASS3',
                    'number_of_days': len(self.timesheet_id.attendances_ids.filtered(lambda line: line.gut_class3 > 0)),
                    'number_of_hours': self.timesheet_id.total_class3,
                    'contract_id': 
                    contract.id,
                }
            class4s = {
                    'name': _("Timesheet Overtime Class 4"),
                    'sequence': 5,
                    'code': 'CLASS4',
                    'number_of_days': len(self.timesheet_id.attendances_ids.filtered(lambda line: line.gut_class4 > 0)),
                    'number_of_hours': self.timesheet_id.total_class4,
                    'contract_id': 
                    contract.id,
                }
            # res.append(attendances)
            res.append(normals)
            res.append(class1s)
            res.append(class2s)
            res.append(class3s)
            res.append(class4s)
            res.extend(leaves.values())
        return res


    @api.multi
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        #defaults
        res = {
            'value': {
                'line_ids': [],
                #delete old input lines
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                #delete old worked days lines
                'worked_days_line_ids': [(2, x,) for x in self.worked_days_line_ids.ids],
                #'details_by_salary_head':[], TODO put me back
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        res['value'].update({
           'name': _('Salary Slip of %s for %s') % (employee.name, date_from.strftime('%B %Y')),
            'company_id': employee.company_id.id,
        })

        if not self.env.context.get('contract'):
            #fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                #set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                #if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)

        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        #computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res


    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        for rec in self:
            if (not rec.employee_id) or (not rec.date_from) or (not rec.date_to):
                return

            employee = rec.employee_id
            date_from = rec.date_from
            date_to = rec.date_to
            contract_ids = []

            self.company_id = employee.company_id

            if not self.env.context.get('contract') or not self.contract_id:
                contract_ids = self.get_contract(employee, date_from, date_to)
                if not contract_ids:
                    return
                self.contract_id = self.env['hr.contract'].browse(contract_ids[0])

            if not rec.contract_id.struct_id:
                return
            rec.struct_id = rec.contract_id.struct_id

            #computation of the salary input
            contracts = self.env['hr.contract'].browse(contract_ids)
            worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
            worked_days_lines = rec.worked_days_line_ids.browse([])
            for r in worked_days_line_ids:
                worked_days_lines += worked_days_lines.new(r)
            rec.worked_days_line_ids = worked_days_lines

            input_line_ids = rec.get_inputs(contracts, date_from, date_to)
            input_lines = rec.input_line_ids.browse([])
            for r in input_line_ids:
                input_lines += input_lines.new(r)
            rec.input_line_ids = input_lines
        return

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees')

    @api.multi
    def compute_sheet(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note'])
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
            }
            payslips += self.env['hr.payslip'].create(res)
        payslips.action_update_actual_value()
        payslips.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}
 
