from odoo import _, api, fields, models
from datetime import date, datetime , timedelta, time
import logging
from calendar import monthrange
import calendar
from dateutil.relativedelta import relativedelta
from pytz import timezone
import json



_logger = logging.getLogger(__name__)


class TimesheetSheetForm(models.Model):
    _inherit = 'hr_timesheet.sheet'

    potongan_kasbon = fields.Float('Potongan Kasbon')
    project = fields.Many2one('project.project', )
    employee_id = fields.Many2one('hr.employee', )
    total_alw_in = fields.Float('Total Allowance Dalam Kota', compute='_compute_tota1_alw_in', store=True)
    total_alw_out = fields.Float('Total Allowance Luar Kota', compute='_compute_tota1_alw_out', store=True)
    total_upah = fields.Float('Total Upah', compute='_compute_total_upah', store=True)
    total_bayar = fields.Float('Total Bayar', compute='_compute_tota1_bayar', store=True)
    attend_alw_in = fields.Char('Attendance and allowance',compute='_compute_attend_allow_in', store=True)
    attend_alw_out = fields.Char('Attendance and allowance',compute='_compute_attend_allow_out', store=True)
    total_all_alw = fields.Integer(string="Allowance", compute='_compute_total_all_alw', store=True)
    total_hours = fields.Integer(string="Total Hours", compute='_compute_total_hours', store=True)
    allow_in_code = fields.Integer(string='Dalam Kota' , compute='_compute_allow_in_code', store=True)
    allow_out_code = fields.Integer(string='Luar Kota' , compute='_compute_allow_out_code', store=True)
    total_normal = fields.Integer(string='Total Normal', compute='_compute_total_normal', store=True)
    total_class1 = fields.Integer(string='Total Class 1', compute='_compute_total_class1', store=True)
    total_class2 = fields.Integer(string='Total Class 2', compute='_compute_total_class2', store=True)
    total_class3 = fields.Integer(string='Total Class 3', compute='_compute_total_class3', store=True)
    total_class4 = fields.Integer(string='Total Class 4', compute='_compute_total_class4', store=True)
    total_gut_telat = fields.Integer('Total Telat', compute="_compute_total_gut_telat", store=True)
    active = fields.Boolean(default=True)
    date_start = fields.Date(default=datetime.now().strftime('%Y-%m-01'), required=True,readonly=False,)
    date_end = fields.Date(
        string='Date To',
        readonly=False,
        required=True,
        default=lambda self: fields.Date.to_string(
            (datetime.combine(
                self.date_start or fields.Date.context_today(self), datetime.min.time()
            ) + relativedelta(day=31)).date()
        )
    )
    leave_on_timsheet = fields.Integer( string="Leave On Timesheet", compute="_compute_get_leave_remaining",)
    leave_count = fields.Integer( compute='_get_timesheet_leave_count')
    leave_line_ids = fields.One2many('hr.leave','leave_timesheet_id',string="Leaves")
    tgl_calendar = fields.Char(compute='compute_tgl_calendar',string="tgl cuti")
    gut_absen = fields.Integer( 'Absen', default=1)
    total_gut_absen = fields.Integer( 'Total Absen')
    holiday_line_ids = fields.Many2many('hr.holidays.public.line', 'holiday_timesheet_id',string="Public Holiday", compute='_compute_holiday_line_timesheet' )
    total_attn = fields.Integer(string='Total attendance', compute='_get_timesheet_attn_count' )
    attendances_ids = fields.One2many(
        comodel_name='hr.attendance',
        inverse_name='sheet_id',
        string='Attendances')

    attendance_state = fields.Selection(
        related='employee_id.attendance_state',
        string='Current Status')

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        default=lambda self: self._default_employee(),
        required=True,
        states={'done': [('readonly', False)]},
    )
    grade = fields.Many2one('employee.grade',related="employee_id.employee_grade", string='Grade',store=True,readonly=False)
    alw_out = fields.Float(string='Allowance Luar', store=True)
    alw_in = fields.Float(string='Allowance Dalam', store=True)

    manhour_timesheet_line_ids = fields.One2many(
        'hr.manhour.timesheet.line', 'manhour_timesheet_id', string="Manhour Timesheet", store=True
    )
    contract_type_id = fields.Many2one('hr.contract.type', string='Kontrak', compute='_compute_contract_type', store=True)
    job_id = fields.Many2one('hr.job', string='Job Position', compute='_compute_job_position', store=True)
    gut_nik = fields.Char(compute='_compute_gut_nik', string='NIK',store=True,readonly=True)
    is_kontrak_project = fields.Boolean(string='Is Kontrak Project', compute='_compute_is_kontrak_project', store=True)
    work_schedule_id = fields.Many2one('hr.work.schedule', string='Work Schedule', compute='_compute_work_schedule', store=True)
    
    upah_pokok = fields.Float(string='Upah Pokok/Bulan', store=True)
    upah_lembur = fields.Float(string='Upah lembur/Jam', store=True)
    tunjangan_kehadiran = fields.Float(string='Tunjangan kehadiran', store=True)
    tunjangan_proyek = fields.Float(string='Tunjangan Proyek', store=True)
    uang_makan = fields.Float(string='Uang Makan', store=True)

    potongan_absen = fields.Float(string='Potongan Absen', compute="_compute_potongan_absen", store=True)

    potongan_telat = fields.Float(string='Potongan Telat', store=True)
    potongan_pph_21 = fields.Float('Potongan PPh 21')
    potongan_lain = fields.Float('Potongan Lain')
    total_potongan_telat = fields.Float(string='Total Potongan Absen', compute="_compute_total_potongan_telat",  store=True)
    total_potongan_absen = fields.Float(string='Total Potongan Absen', compute="_compute_total_potongan_absen",  store=True)

    total_potongan = fields.Float('Total Potongan', compute='_compute_total_potongan', store=True)

    total_upah_lembur = fields.Float(string='Total Upah Lembur', compute='_compute_total_upah_lembur', store=True)
    total_tunjangan_kehadiran = fields.Float(string='Total Tunjangan Kehadiran', compute='_compute_total_tunjangan_kehadiran', store=True)
    total_tunjangan_proyek = fields.Float(string='Total Tunjangan Proyek', compute='_compute_total_tunjangan_proyek', store=True)
    total_uang_makan = fields.Float(string='Total Uang Makan', compute='_compute_total_uang_makan', store=True)
    total_upah_kotor = fields.Float(string='Total Upah Kotor', compute='_compute_total_upah_kotor', store=True)

    attend_upah_lembur = fields.Char('Attendance and Upah Lembur',compute='_compute_attend_upah_tunjangan') #for report only
    attend_tunjangan_kehadiran = fields.Char('Attendance and kehadiran',compute='_compute_attend_upah_tunjangan') #for report only
    attend_tunjangan_proyek= fields.Char('Attendance and proyek',compute='_compute_attend_upah_tunjangan') #for report only
    attend_uang_makan= fields.Char('Attendance and uang makan',compute='_compute_attend_upah_tunjangan') #for report only
    attend_potongan_absen = fields.Char('Attendance and potongan absen',compute='_compute_attend_potongan') #for report only
    attend_potongan_telat = fields.Char('Attendance and potongan telat',compute='_compute_attend_potongan') #for report only
    
    total_travel = fields.Integer(string='Total Travel', compute='_compute_total_travel', store=True)
    allowance_ho = fields.Boolean(string='Allowance HO', default=False)

    @api.multi
    def attendance_action_change(self):
        '''Call attendance_action_change to
        perform Check In/Check Out action
        Returns last attendance record'''

        return self.employee_id.attendance_action_change()
        
# onchange reviewer
    @api.onchange('employee_id')
    def on_change_employee_id(self):
        reviewer = self.employee_id.parent_id
        self.reviewer_id = reviewer if reviewer else None

    # compute total Normal
    @api.depends('attendances_ids')
    def _compute_total_normal(self):
        for rec in self:
            total = 0
            for attendance in rec.attendances_ids:
                if hasattr(attendance, 'gut_normal_hours'):
                    total += attendance.gut_normal_hours
            rec.total_normal = total
# compute total class 1
    @api.depends('employee_id','contract_type_id','job_id','attendances_ids')
    def _compute_total_class1(self):
        max_threshold = {
            'Supervisor': 50,
            'Foreman': 70,
            'Skill': 90,
            'Semi Skill': 90,
            'Helper': 90
        }
        for record in self:
            total = sum(rec.gut_class1 for rec in record.attendances_ids)
            if record.contract_type_id and record.contract_type_id.status == 'Kontrak Project':
                record.total_class1 = min(total, max_threshold.get(record.job_id.name, float('inf')))
            else:
                record.total_class1 = total

# compute total class 2
    @api.depends('attendances_ids')
    def _compute_total_class2(self):
        for rec in self:
            total = 0
            for attendance in rec.attendances_ids:
                if hasattr(attendance, 'gut_class2'):
                    total += attendance.gut_class2
            rec.total_class2 = total

    # compute total class 3
    @api.depends('attendances_ids')
    def _compute_total_class3(self):
        for rec in self:
            total = 0
            for attendance in rec.attendances_ids:
                if hasattr(attendance, 'gut_class3'):
                    total += attendance.gut_class3
            rec.total_class3 = total

    # compute total class 4
    @api.depends('attendances_ids')
    def _compute_total_class4(self):
        for rec in self:
            total = 0
            for attendance in rec.attendances_ids:
                if hasattr(attendance, 'gut_class4'):
                    total += attendance.gut_class4
            rec.total_class4 = total

# compute total Hour
    @api.depends('total_normal', 'total_class1', 'total_class2', 'total_class3', 'total_class4')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = rec.total_normal + rec.total_class1 + rec.total_class2 + rec.total_class3 + rec.total_class4


# compute total all allowance
    @api.depends('attendances_ids')
    def _compute_total_all_alw(self):
        for record in self:
            record.total_all_alw = len(record.attendances_ids.filtered(lambda line: line.gut_code > 0 and line.project))


# compute total allowance Dalam Kota
    @api.depends('alw_in', 'allow_in_code') # Ensure this is correct
    def _compute_tota1_alw_in(self):
        _logger.info("==== Computing _compute_tota1_alw_in for %s ====", self.ids) # Log entry
        for rec in self:
            code = rec.allow_in_code or 0
            allowance = rec.alw_in or 0.0
            # Log inputs
            _logger.info("Rec %s Inputs: allow_in_code=%s, alw_in=%s", rec.id, code, allowance)
            rec.total_alw_in = code * allowance
            # Log result
            _logger.info("Rec %s: Calculated total_alw_in = %s", rec.id, rec.total_alw_in)


    @api.onchange('alw_in')
    def _onchange_total_alw_in(self):
        for rec in self:
            if rec.allow_in_code and rec.alw_in:
                rec.total_alw_in = rec.allow_in_code * rec.alw_in
            else:
                rec.total_alw_in = 0

# compute total allowance Luar Kota
    @api.depends('alw_out', 'allow_out_code') # Ensure this depends on 'alw_out'
    def _compute_tota1_alw_out(self):
        _logger.info("==== Computing _compute_tota1_alw_out for %s ====", self.ids) # Log entry
        for rec in self:
            code = rec.allow_out_code or 0
            allowance = rec.alw_out or 0.0
             # Log inputs
            _logger.info("Rec %s Inputs: allow_out_code=%s, alw_out=%s", rec.id, code, allowance)
            rec.total_alw_out = code * allowance
            # Log result
            _logger.info("Rec %s: Calculated total_alw_out = %s", rec.id, rec.total_alw_out)

    @api.onchange('alw_out')
    def _onchange_tota1_alw_out(self):
        for rec in self:
            if rec.allow_out_code and rec.alw_out:
                rec.total_alw_out = rec.allow_out_code * rec.alw_out
            else:
                rec.total_alw_out = 0

# compute total upah
    @api.depends('total_upah_kotor', 'total_potongan') 
    def _compute_total_upah(self):
         for record in self:
            total = record.total_upah_kotor - record.total_potongan
            record.total_upah = total

# compute attendance berdasarkan allowance dalam
    @api.depends('allow_in_code', 'alw_in')
    def _compute_attend_allow_in(self):
        for record in self:
            attend_alw_in = ""
            alw = int(record.alw_in)
            attend_alw_in = str(record.allow_in_code) + ' Hari x ' + str(alw)
            record.attend_alw_in = attend_alw_in if attend_alw_in else None

# compute attendance berdasarkan allowance Luar
    @api.depends('allow_out_code', 'alw_out')
    def _compute_attend_allow_out(self):
        for record in self:
            attend_alw_out = ""
            alw = int(record.alw_out)
            attend_alw_out = str(record.allow_out_code) + ' Hari x ' + str(alw)
            record.attend_alw_out = attend_alw_out if attend_alw_out else None

                
# compute attendance berdasarkan gut code 
    @api.depends('attendances_ids.gut_code', 'attendances_ids.jo_no', 'attendances_ids.gut_code')
    def _compute_allow_in_code(self):
        for rec in self:
            rec.allow_in_code = len([doc for doc in rec.attendances_ids if doc.gut_code == 1 and doc.jo_no])

# compute attendance berdasarkan gut code 
    @api.depends('attendances_ids.gut_code', 'attendances_ids.jo_no', 'attendances_ids.gut_code')
    def _compute_allow_out_code(self):
        for rec in self:
            rec.allow_out_code = len([doc for doc in rec.attendances_ids if doc.gut_code == 2 and doc.jo_no])

# function get allowance claim
    @api.model
    def get_timesheet_allowance_project_group(self):

        query = """SELECT min(att.check_in) as first, 
                  max(att.check_in) as last, 
                  att.gut_code as code, 
                  cc.no as pro_no, 
                  cc.name as pro_name, 
                  COALESCE(ts.alw_in, 0) as alw_in,  -- Prevent None
                  COALESCE(ts.alw_out, 0) as alw_out,  -- Prevent None
                  COALESCE(ts.alw_in, 0) * COUNT(att.project) as total_alw_in,
                  COALESCE(ts.alw_out, 0) * COUNT(att.project) as total_alw_out,
                  COUNT(att.project) as count_day
           FROM hr_attendance att
           LEFT JOIN project_project cc ON (att.project = cc.id)
           INNER JOIN hr_timesheet_sheet AS ts ON ts.id = att.sheet_id
           WHERE att.sheet_id = %s 
             AND (cc.no != '0000MG-0001' OR (cc.no = '0000MG-0001' AND ts.allowance_ho = True))
             AND att.gut_code >= 1
           GROUP BY code, pro_name, pro_no, alw_out, alw_in 
           ORDER BY first, last ASC;
        """

        params = (self.id,)
        self._cr.execute(query, params)
        dat = self._cr.fetchall()
        data = []
        for i in range(0, len(dat)):
            data.append({
                        'first_day': dat[i][0],
                        'last_day': dat[i][1],
                        'code': dat[i][2],
                        'pro_no': dat[i][3],
                        'pro_name': dat[i][4],
                        'alw_in': dat[i][5] if dat[i][5] is not None else 0,  # Default to 0
                        'alw_out': dat[i][6] if dat[i][6] is not None else 0, # Default to 0
                        'total_alw_in': dat[i][7],
                        'total_alw_out': dat[i][8],
                        'count_day': dat[i][9],
                    })

        return data


# compute leave on timesheet
    def _compute_get_leave_remaining(self):
         for leaves in self:

            leave = self.env['hr.leave'].search([('employee_id.id', '=', leaves.employee_id.id),('state', '=', 'validate'), 
                                                ('request_date_from', '>=', leaves.date_start), ('request_date_to', '<=', leaves.date_end)])
            leaves.leave_on_timsheet = sum(leave.mapped('number_of_days'))

# compute statinfo cuti di timesheet
    @api.multi
    def _get_timesheet_leave_count(self):
        leaves = self.env['hr.leave'].search([('employee_id.id', '=', self.employee_id.id), ('state', 'in', ['validate']), ('request_date_from', '>=', self.date_start), ('request_date_to', '<=', self.date_end)])
        count = sum(leaves.mapped('number_of_days'))
        for record in self:
            record.leave_count = count or False

    @api.multi
    def open_leave_timesheet(self):
        for rec in self:
            return {
                    'name': 'Cuti',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'hr.leave',
                    'type': 'ir.actions.act_window',
                    'domain': [('employee_id.id', '=', rec.employee_id.id), ('state', 'in', ['validate']), ('request_date_from', '>=', self.date_start), ('request_date_to', '<=', self.date_end)],
                }
        pass

#  create timesheet generate leave line ids
    @api.model
    def create(self, vals):
        res = super(TimesheetSheetForm, self).create(vals)
        leaves = self.env['hr.leave'].search([
            ('employee_id.id', '=', res.employee_id.id),
            ('state', '=', 'validate'),
            ('request_date_from', '>=', res.date_start), 
            ('request_date_to', '<=', res.date_end),
        ])
        leaves._compute_leave_sheet_id()
        return res


    def compute_tgl_calendar(self):

        for rec in  self.leave_line_ids:
            if rec.holiday_status_id: 
                str_d1 = rec.date_from
                str_d2 = rec.date_to
                d1 = datetime.strptime(str(str_d1), '%Y-%m-%d %H:%M:%S')
                d2 = datetime.strptime(str(str_d2), '%Y-%m-%d %H:%M:%S')
                delta = abs((d2 - d1).days) + 1
      
                d = datetime.strptime(str(rec.date_to), '%Y-%m-%d %H:%M:%S').date()
       
                date_list = [d - timedelta(days=x) for x in range(0, delta)]
                listing = [date_obj.strftime('%d') for date_obj in date_list]
                # list = int("".join(map(str, listing)))
                
                self.tgl_calendar = listing

# get data tgl 1 - 31
    def get_data(self):
        date_list = []
        start_date = self.date_start
        end_date = self.date_end
        delta = relativedelta(days=1)
        while start_date <= end_date:
                date_list.append({
                    "date_list": start_date.day,
                    "tgl": start_date,
                    "hari": start_date.strftime('%a'),
                    "weekend": start_date.weekday(),
                })
                start_date += delta
        return date_list
    
    # check kehadiran di attendance
    def check_attendance(self):
        data = []
        report = self.env['hr.attendance'].search(
            [('employee_id.id', '=', self.employee_id.id), ('check_in', '>=', self.date_start),
             ('check_in', '<=', self.date_end)])
        for rec in report:
            val = rec.check_in.date()
            check_in_7 = rec.check_in + timedelta(hours=7)
            check_out_7 = rec.check_out+ timedelta(hours=7)
            pro = str(rec.project.name)

            if rec.project :
                pro_trim = pro[:19]
            else :
                pro_trim = None

            if rec.check_in:
                data.append({
                    'date': val.day,
                    'state': 'P',
                    'employee': rec.employee_id.id,
                    'check_in': check_in_7.strftime("%H:%M"),
                    'check_out': check_out_7.strftime("%H:%M"),
                    'normal': rec.gut_normal_hours,
                    'class_1': rec.gut_class1,
                    'class_2': rec.gut_class2,
                    'class_3': rec.gut_class3,
                    'class_4': rec.gut_class4,
                    'travel': rec.gut_travel,
                    'code': rec.gut_code,
                    'telat': rec.total_waktu_telat,
                    'pro_no': rec.project.no,
                    'pro_name': pro_trim,
                    'desc': rec.task,
                    'libur': rec.hari_libur,
                    "hari": val.strftime('%a'),
                    
                })
        res_list = [i for n, i in enumerate(data)
                    if i not in data[n + 1:]]
        return res_list

# get Cuti di Leave
    def get_leave(self):
        
        if self.leave_line_ids: #baru ditambahkan 7-08-2023
            leave_list = []
            report = self.env['hr.leave'].search(
                [('employee_id.id', '=', self.employee_id.id), ('request_date_from', '>=', self.date_start),
                ('request_date_to', '<=', self.date_end), ('state', '=', 'validate') ])
            for rec in report:
                start_date = rec.request_date_from
                end_date = rec.request_date_to
                delta = relativedelta(days=1)
                while start_date <= end_date:
                    leave_list.append({
                        "leave_list": start_date.day,
                        'cuti': rec.holiday_status_id.name,
                        'employee': rec.employee_id.id,
                    })
                    start_date += delta
                return leave_list

# check har libut di public holiday
    def check_public_holiday(self):
        data = []
        report = self.env['hr.holidays.public.line'].search(
            [('date', '>=', self.date_start),
             ('date', '<=', self.date_end),])
        for rec in report:
            val = rec.date
            if rec.date:
                data.append({
                    'date': val.day,
                    'tgl': rec.date,
                    'state': 'L',
                    
                })
        holiday_list = [i for n, i in enumerate(data)
                    if i not in data[n + 1:]]
        return holiday_list

    # compute total absen
    @api.one
    def _compute_total_absen(self):
        date_list =  self.get_data()
        leave_list =  self.get_leave()
        start = self.date_start
        end = self.date_end
        total = []
        attn = len(self.attendances_ids.filtered(lambda line: line.gut_normal_hours  > 0 and line.gut_day not in ('Saturday', 'Sunday')))
        holiday = len(self.holiday_line_ids.filtered(lambda line: line.date  >= self.date_start and line.date  <= self.date_end and line.day_holiday not in ('Saturday', 'Sunday')))

    # get sum total weekend dalam range sebulan
        weekend = 0
        current_date = start
        while current_date <= end:
            if current_date.weekday() > 4:
                weekend += 1
            current_date += timedelta(days=1)
        if len(self.leave_line_ids) > 0:
            total = len(date_list) - holiday - len(leave_list) - attn - weekend
        else:
            total =  len(date_list) - holiday - attn - weekend  
        self.total_gut_absen = total


# get Public holiday in timesheet
    @api.one
    @api.depends('date_start') 
    def _compute_holiday_line_timesheet(self):
         for rec in self:
            if rec.date_start:
                record = self.env['hr.holidays.public.line'].search([('date', '>=', self.date_start),('date', '<=', self.date_end),])
                rec.holiday_line_ids = record

# overiride dari addons hr_timesheet_sheet_attendance
    def _compute_attendance_time(self):
        '''Compute total attendance time and
        difference in total attendance-time
        and timesheet-entry '''

        current_date = datetime.now()
        for sheet in self:
            atte_without_checkout = sheet.attendances_ids.filtered(
                lambda attendance: not attendance.check_out)
            atte_with_checkout = sheet.attendances_ids - atte_without_checkout
            total_time = sum(atte_with_checkout.mapped('actual_hours'))
            for attendance in atte_without_checkout:
                delta = current_date - attendance.check_in
                total_time += delta.total_seconds() / 3600.0
            sheet.total_attendance = total_time

            # calculate total difference
            total_working_time = sum(sheet.mapped('timesheet_ids.unit_amount'))
            sheet.total_difference = total_time - total_working_time


# trigger get_manhour_timesheet_lines with onchange employee id
    @api.model
    def create(self, vals):
        record = super(TimesheetSheetForm, self).create(vals)
        record._compute_and_update_manhour_timesheet_lines()
        return record

    def write(self, vals):
        res = super(TimesheetSheetForm, self).write(vals)
        self._compute_and_update_manhour_timesheet_lines()
        return res

    @api.model
    def load(self, fields, data):
        result = super(TimesheetSheetForm, self).load(fields, data)
        for record in self.browse(result['ids']):
            record._compute_and_update_manhour_timesheet_lines()
        return result

    def _compute_and_update_manhour_timesheet_lines(self):
        for rec in self:
            rec.ensure_one()  # Ensure we're working with a single record
            summary = rec._calculate_manhour_timesheet_summary()

            # Unlink existing lines before creating new ones
            self.env['hr.manhour.timesheet.line'].search([
                ('manhour_timesheet_id', '=', rec.id)
            ]).unlink()

            # Create new lines
            lines_to_create = []
            for item in summary:
                lines_to_create.append({
                    'total_day': item['total_day'],
                    'total_hour': item['total_hour'],
                    'project_id': item['project_id'],
                    'month': item['month'],
                    'manhour_timesheet_id': rec.id
                })
            self.env['hr.manhour.timesheet.line'].create(lines_to_create)


    def _calculate_manhour_timesheet_summary(self):
        summary = []
        for rec in self:
            result = {}
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('check_in', '>=', rec.date_start),
                ('check_in', '<=', rec.date_end),
                '|',
                ('check_out', '=', False),
                '&',
                ('check_out', '>=', rec.date_start),
                ('check_out', '<=', rec.date_end)
            ])
            for att in attendances:
                if att.project:
                    check_in_date = fields.Date.from_string(att.check_in)
                    year_month = "{} {}".format(calendar.month_name[check_in_date.month],check_in_date.year)

                    if att.project.id not in result:
                        result[att.project.id] = {}

                    if year_month not in result[att.project.id]:
                        result[att.project.id][year_month] = {
                            'total_day': 0.0,
                            'total_hour': 0.0,
                            'project_id': att.project.id,
                            'month': year_month,
                        }

                    result[att.project.id][year_month]['total_hour'] += (
                        att.gut_normal_hours + att.gut_class1 + att.gut_class2 + att.gut_class3 + att.gut_class4
                    )

                    if 'days' not in result[att.project.id][year_month]:
                        result[att.project.id][year_month]['days'] = set()
                    result[att.project.id][year_month]['days'].add(check_in_date)

            for project_id, months in result.items():
                for year_month, values in months.items():
                    values['total_day'] = len(values.pop('days'))
                    summary.append(values)

        return summary

        
# remove self._timesheet_subscribe_users(), supaya tidak mengirim email ke subsciber
    @api.multi
    def action_timesheet_confirm(self):
        self.reset_add_line()
        self.write({'state': 'confirm'})

# compute kontrak type
    @api.multi
    @api.depends('employee_id')
    def _compute_contract_type(self):
        """
        Compute the contract type based on the employee's status_karyawan field.
        """
        for record in self:
            record.contract_type_id = record.employee_id.status_karyawan if record.employee_id else False

# compute job position
    @api.multi
    @api.depends('employee_id')
    def _compute_job_position(self):
        """
        Compute the job position based on the employee's job_id field.
        """
        for record in self:
            record.job_id = record.employee_id.job_id if record.employee_id else False

# compute gut nik
    @api.multi
    @api.depends('employee_id')
    def _compute_gut_nik(self):
        """
        Compute the gut_nik based on the employee's identification_id field.
        """
        for record in self:
            record.gut_nik = record.employee_id.identification_id if record.employee_id else False

# compute is kontrak project or not
    @api.depends('contract_type_id')
    def _compute_is_kontrak_project(self):
        for record in self:
            record.is_kontrak_project = record.contract_type_id and record.contract_type_id.status == 'Kontrak Project'

# compute work schedule
    @api.depends('employee_id')
    def _compute_work_schedule(self):
        for record in self:
            record.work_schedule_id = record.employee_id.work_schedule_id


# compute potongan absen
    @api.depends('upah_pokok', 'work_schedule_id')
    def _compute_potongan_absen(self):
        for record in self:
            if record.work_schedule_id:
                if record.work_schedule_id.name == '6 hari kerja':
                    record.potongan_absen = record.upah_pokok / 25
                elif record.work_schedule_id.name == '5 hari kerja':
                    record.potongan_absen = record.upah_pokok / 21
                elif record.work_schedule_id.name == 'NH 10 jam':
                    record.potongan_absen = record.upah_pokok / 25
                else:
                    record.potongan_absen = 0

# compute total upah lembur
    @api.depends('upah_lembur', 'total_all_alw')
    def _compute_total_upah_lembur(self):
        for record in self:
            record.total_upah_lembur = record.upah_lembur * record.total_all_alw

# compute total tunjangan kehadiran
    @api.depends('tunjangan_kehadiran', 'total_all_alw')
    def _compute_total_tunjangan_kehadiran(self):
        for record in self:
            record.total_tunjangan_kehadiran = record.tunjangan_kehadiran * record.total_all_alw

# compute total tunjangan proyek
    @api.depends('tunjangan_proyek', 'total_all_alw')
    def _compute_total_tunjangan_proyek(self):
        for record in self:
            record.total_tunjangan_proyek = record.tunjangan_proyek * record.total_all_alw

# compute total uang makan
    @api.depends('uang_makan', 'total_all_alw')
    def _compute_total_uang_makan(self):
        for record in self:
            record.total_uang_makan = record.uang_makan * record.total_all_alw

# # compute total potongan absen
    @api.depends('potongan_absen', 'total_gut_absen')
    def _compute_total_potongan_absen(self):
        for record in self:
            record.total_potongan_absen = record.total_gut_absen * record.potongan_absen

# # compute telat
    @api.depends('attendances_ids')
    def _compute_total_gut_telat(self):
        for record in self:
            record.total_gut_telat = sum(line.total_waktu_telat for line in record.attendances_ids)
                                        
# # compute total potongan telat
    @api.depends('total_gut_telat', 'upah_pokok')
    def _compute_total_potongan_telat(self):
        for record in self:
            # Convert total_gut_telat from hours to decimal (e.g., 5 hours -> 5/24 = 0.208333333333333)
            total_gut_telat_decimal = record.total_gut_telat / 24 if record.total_gut_telat else 0
            upah_pokok = record.upah_pokok

            # Apply conditions based on the decimal value
            if 0.0840277777777778 <= total_gut_telat_decimal <= 0.125:
                record.total_potongan_telat = upah_pokok * 0.025
            elif 0.125694444444444 <= total_gut_telat_decimal <= 0.166666667:
                record.total_potongan_telat = upah_pokok * 0.05
            elif 0.167361111 <= total_gut_telat_decimal <= 0.208333333333333:
                record.total_potongan_telat = upah_pokok * 0.075
            elif total_gut_telat_decimal >= 0.209027777777778:
                record.total_potongan_telat = upah_pokok * 0.1
            else:
                record.total_potongan_telat = 0

# compute total potongan
    @api.depends('total_potongan_absen', 'total_potongan_telat')
    def _compute_total_potongan(self):
        for record in self:
            record.total_potongan = record.total_potongan_absen + record.total_potongan_telat

# compute upah kotor
    @api.depends('alw_in', 'alw_out', 'total_alw_in', 'total_alw_out', 'upah_pokok', 'total_upah_lembur', 'total_tunjangan_kehadiran', 'total_tunjangan_proyek', 'total_uang_makan')
    def _compute_total_upah_kotor(self):
        for record in self:
            record.total_upah_kotor = (record.total_alw_in + record.total_alw_out + record.upah_pokok + 
                                    record.total_upah_lembur + record.total_tunjangan_kehadiran + 
                                    record.total_tunjangan_proyek + record.total_uang_makan)

# compute total dibayar
    @api.depends('potongan_kasbon', 'potongan_pph_21', 'potongan_lain', 'total_upah_kotor','total_potongan') 
    def _compute_tota1_bayar(self):
         for record in self:
            total = record.total_upah_kotor - record.total_potongan - record.potongan_kasbon - record.potongan_pph_21 - record.potongan_lain
            record.total_bayar = total

# compute tunjangan untuk di report timehseet form-C
    @api.depends('total_all_alw', 'upah_lembur')
    def _compute_attend_upah_tunjangan(self):
        for record in self:
            # Initialize default values
            attend_upah_lembur = ""
            attend_tunjangan_kehadiran = ""
            attend_tunjangan_proyek = ""

            # Compute attend_upah_lembur
            total_class1= record.total_class1
            total_all_alw = record.total_all_alw
            upah_lembur = int(record.upah_lembur)
            tunjangan_kehadiran = int(record.tunjangan_kehadiran)
            tunjangan_proyek = int(record.tunjangan_proyek)
            uang_makan = int(record.uang_makan)

            attend_upah_lembur = str(total_class1) + '  Jam x ' + str(upah_lembur)
            attend_tunjangan_kehadiran = str(total_all_alw) + '  Hari x  ' + str(tunjangan_kehadiran)
            attend_tunjangan_proyek = str(total_all_alw) + '  Hari x  ' + str(tunjangan_proyek)
            attend_uang_makan = str(total_all_alw) + '  Hari x  ' + str(uang_makan)

            # Assign computed values to the respective fields
            record.attend_upah_lembur = attend_upah_lembur
            record.attend_tunjangan_kehadiran = attend_tunjangan_kehadiran
            record.attend_tunjangan_proyek = attend_tunjangan_proyek
            record.attend_uang_makan = attend_uang_makan

# compute potongan untuk di report timehseet form-C
    @api.depends('total_gut_telat', 'total_gut_absen')
    def _compute_attend_potongan(self):
        for record in self:
            # Initialize default values
            attend_potongan_absen = ""
            attend_potongan_telat = ""

            # Compute attend_potongan_absen
            total_absen = record.total_gut_absen
            total_telat = record.total_gut_telat

            potongan_absen = int(record.potongan_absen)

            attend_potongan_absen = str(total_absen) + '  Hari x ' + str(potongan_absen)
            attend_potongan_telat = str(total_telat) + '  Jam x  ' 

            # Assign computed values to the respective fields
            record.attend_potongan_absen = attend_potongan_absen
            record.attend_potongan_telat = attend_potongan_telat

# compute total travel
    @api.depends('attendances_ids')
    def _compute_total_travel(self):
        for rec in self:
            total = 0
            for attendance in rec.attendances_ids:
                if hasattr(attendance, 'gut_travel'):
                    total += attendance.gut_travel
            rec.total_travel = total

    # --- Onchange Method to Check Attendance Data when Allowance *Values* Change ---
    @api.onchange('alw_in', 'alw_out', 'attendances_ids')
    def _onchange_check_attendance_for_allowance_warning(self):
        """
        Checks linked attendance data when form values change.
        Warns by grouping issues by type and listing affected dates:
         - Missing JO No for lines with Allowance Code (1 or 2).
         - Missing Allowance Code (1 or 2) for lines with non-exempt JO No.
        """
        if not self.employee_id or not self.date_start or not self.date_end:
             _logger.debug("_onchange_check_attendance_warning: Skipping, missing employee/dates.")
             return

        _logger.info("Running _onchange_check_attendance_warning for sheet (ID: %s)", self._origin.id if self._origin else 'New')

        # Use dictionaries to group problematic dates by issue type
        missing_jo_dates = {} # Key: gut_code (1 or 2), Value: set of dates
        missing_code_dates = set() # Store dates where a non-exempt JO is missing a code

        mg_jo_code = '0000MG-0001'

        for attendance in self.attendances_ids:
            attendance_date = attendance.check_in.date() if attendance.check_in else None
            if not attendance_date: continue # Skip if no date

            attendance_date_str = attendance_date.strftime('%Y-%m-%d')
            has_allowance_code = attendance.gut_code in [1, 2]
            has_jo = bool(attendance.jo_no)
            is_exempt_jo = attendance.jo_no == mg_jo_code

            # Condition 1: Allowance code requires JO, but JO is missing
            if has_allowance_code and not has_jo:
                code = attendance.gut_code
                if code not in missing_jo_dates:
                    missing_jo_dates[code] = set()
                missing_jo_dates[code].add(attendance_date_str)
                _logger.debug("--> Added Warning: Code %s missing JO on %s", code, attendance_date_str)

            # Condition 2: JO is present, is NOT exempt, but allowance code is missing
            elif has_jo and not is_exempt_jo and not has_allowance_code:
                 missing_code_dates.add(attendance_date_str)
                 _logger.debug("--> Added Warning: Missing Code (1/2) on %s (JO: %s)", attendance_date_str, attendance.jo_no)

        # Build the final warning messages
        warning_messages = []

        # Format messages for missing JO numbers
        if missing_jo_dates:
            for code, dates in missing_jo_dates.items():
                sorted_dates = ", ".join(sorted(list(dates)))
                warning_messages.append(_("Missing JO No for Allowance Code [%s] on dates: %s") % (code, sorted_dates))
                warning_messages.append(_("Cek kembali JO No pada Attendance kosong untuk allowance [%s]. Tanggal: %s") % (code, sorted_dates))

        # Format message for missing allowance codes
        if missing_code_dates:
            sorted_dates = ", ".join(sorted(list(missing_code_dates)))
            warning_messages.append(_("Cek kembali All code pada Attendance kosong (1 or 2) untuk allowance luar atau dalam. Tanggal: %s") % sorted_dates)

        # Return warning if any issues were found
        if warning_messages:
            _logger.warning("Onchange Check - Allowance Data Issues Found for Sheet %s: %s", self._origin.id if self._origin else 'New', "; ".join(warning_messages))
            title = _("Potential Allowance Calculation Issues")
            message = _("Gagal menghitung Total Upah Kotor.\n\n- %s") % ("\n- ".join(warning_messages))
            return {
                'warning': {
                    'title': title,
                    'message': message,
                }
            }
        else:
             _logger.info("Onchange check passed for sheet %s (related to alw_in/alw_out/attendance trigger).", self._origin.id if self._origin else 'New')
             return {} 


class HrPublicHoliday(models.Model):
    _inherit = 'hr.holidays.public.line'

    holiday_timesheet_id = fields.Many2one('hr_timesheet.sheet')
    day_holiday = fields.Char('Day', compute='_compute_holiday_day')

    @api.multi
    def _compute_holiday_day(self):
        for holiday in self:
            val = holiday.date
            holiday.day_holiday = val.strftime('%A')
            
class HrManhourTimesheetLine(models.Model):
    _name = 'hr.manhour.timesheet.line'
    _description = 'Manhour Timesheet Line'

    manhour_timesheet_id = fields.Many2one('hr_timesheet.sheet', string="Timesheet")
    project_id = fields.Many2one('project.project', string="Project")
    total_day = fields.Integer(string="Total Days")
    total_hour = fields.Integer(string="Total Hours")
    month = fields.Char(string="Month")


                