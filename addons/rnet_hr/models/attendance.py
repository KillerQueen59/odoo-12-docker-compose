
from odoo import api, fields, models, _
from datetime import date, datetime , timedelta
from odoo.exceptions import UserError, ValidationError


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    employee_id = fields.Many2one('hr.employee', string='Employee', )
    public_holiday = fields.Many2one('hr.holidays.public.line', string='Public Holidays', compute='_compute_tgl_merah')
    task = fields.Char( string='Task',)
    jo_no = fields.Char( string='JO',)
    project = fields.Many2one('project.project', string='Project', compute='_compute_get_project_from_jo_no', store=True)
    active = fields.Boolean(default=True)
    gut_absen = fields.Char('Absent', compute='_compute_hari_absen')
    sheet_id = fields.Many2one(
        comodel_name='hr_timesheet.sheet',
        compute="_compute_sheet_id",
        string='Sheet',
        store=True)
    status_karyawan = fields.Many2one(related='employee_id.status_karyawan', string='Status Karyawan', store=True)
    actual_hours = fields.Float(
        string='Actual Hours', compute='_compute_actual_hours', store=True)
    start_overtime_hours = fields.Datetime(
        string='Start Overtime', compute='_compute_start_overtime',)
    contract_type_id = fields.Many2one('hr.contract.type', string='Contract Type', compute='_compute_contract_type', store=True)
    job_id = fields.Many2one('hr.job', string='Job Position', compute='_compute_job_position', store=True)

# onchange jika check in < jam 7, set jadi jam 7
    @api.onchange('check_in')
    def _onchange_minimum_hours_check_in(self):
         for attendance in self:
            if attendance.check_in.hour > 16:
                attendance.check_in = attendance.check_in.replace(hour=0, minute=00, second=00) + timedelta(days=1)

# triggered create on change
    @api.model
    def create(self, vals):
        result = super(HrAttendance, self).create(vals)
        result._onchange_minimum_hours_check_in()
        return result


# compute get project form jo no
    @api.multi
    @api.depends('jo_no')
    def _compute_get_project_from_jo_no(self):
        for rec in self:
            if rec.jo_no:
                pro = self.env['project.project'].search([('no', '=', rec.jo_no)], limit=1)
                rec.project = pro if pro else False
            else:
                rec.project = False
                        
# compute actual hour
    # @api.multi
    # @api.depends('check_out', 'check_in')
    # def _compute_actual_hours(self):
    #     for attendance in self:
    #         if attendance.check_out:
    #             assert isinstance(attendance.check_out, datetime), 'Datetime instance expected'

    #             newdate_in_7 = attendance.check_in.replace(hour=0, minute=0, second=0) # set to 07:00
    #             newdate_out_17 = attendance.check_out.replace(hour=10, minute=0, second=0)  # set to 17:00
    #             newdate_out_18 = attendance.check_out.replace(hour=11, minute=0, second=0)  # set to 18:00

    #             if attendance.check_in < newdate_in_7:
    #                 if newdate_out_17 <= attendance.check_out < newdate_out_18:
    #                     delta = newdate_out_17 - newdate_in_7 - timedelta(hours=1)
    #                 elif attendance.check_out >= newdate_out_18:
    #                     delta = attendance.check_out - newdate_in_7 - timedelta(hours=1)
    #                 else:
    #                     delta = attendance.check_out - attendance.check_in - timedelta(hours=1)
    #             else:
    #                 delta = attendance.check_out - attendance.check_in - timedelta(hours=1)
                
    #             actual_hours = delta.total_seconds() / 3600.0
    #         else:
    #             delta = datetime.now() - attendance.check_in
    #             actual_hours = delta.total_seconds() / 3600.0
            
    #         attendance.actual_hours = actual_hours


# compute normal hour
    @api.multi
    @api.depends('actual_hours', 'hari_libur', 'contract_type_id', 'is_travel')
    def _compute_normal_hours(self):
        """
        Compute the normal hours worked based on actual hours and holiday status.
        Ensures that contract_type_id is calculated first before computing normal hours.
        """
        for record in self:
            if record.is_travel:
                record.gut_normal_hours = 0
                continue  # Skip further calculations for this record

            if record.actual_hours <= 3:
                if record.project:
                    record.gut_normal_hours = 8  # Set 8 if actual_hours is <= 3 and project is set
                else:
                    record.gut_normal_hours = 0  # Set 0 if actual_hours is <= 3 and no project
                continue  # Skip further calculations for this record

            check_in_date = record.check_in.date()  # Extract the date portion
            is_weekday = check_in_date.weekday() < 5  # Monday to Friday
            is_saturday = check_in_date.weekday() == 5  # Saturday

            max_normal_hours = 10 if record.contract_type_id and record.contract_type_id.status == 'Kontrak Project' else 8

            if is_weekday or (record.contract_type_id and record.contract_type_id.status == 'Kontrak Project' and is_saturday):
                if record.hari_libur and record.public_holiday and record.public_holiday.type == 'Public Holiday':
                    record.gut_normal_hours = 0  # No normal hours on public holidays
                else:
                    fractional_minutes = (record.actual_hours % 1) * 60
                    whole_hours = int(record.actual_hours)
                    if fractional_minutes >= 50:
                        record.gut_normal_hours = min(whole_hours + 1, max_normal_hours)  # Round up if fractional minutes >= 50
                    else:
                        record.gut_normal_hours = min(whole_hours, max_normal_hours)  # Otherwise, round down
            else:
                record.gut_normal_hours = False  # No normal hours on weekends



# compute overtime class 1
    # @api.multi
    # @api.depends('actual_hours', 'hari_libur')
    # def _compute_gut_class1(self):
    #     for record in self:
    #         check_in_date = datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date()
    #         weekday = check_in_date.weekday()
    #         is_weekday = weekday < 5  # Monday to Friday
    #         tolerance_hours = 8 + 50 / 60 # Add a tolerance of 8 hours and 50 minutes (which is 8.8333 hours)
            
    #         if is_weekday:
    #             if record.hari_libur and record.actual_hours > 0:
    #                 record.gut_class1 = 0
    #             elif not record.hari_libur and record.actual_hours >= tolerance_hours:
    #                 record.gut_class1 = 1


# compute overtime class 2
    @api.depends('actual_hours', 'hari_libur')
    def _compute_gut_class2(self):
        tolerance_minutes = 50 / 60.0  # 50 minutes out of 60

        for record in self:
            check_in_date = record.check_in.date()  # Extract the date portion
            is_weekday = check_in_date.weekday() < 5  # Monday to Friday

            normal_hours = 8
            adjusted_actual_hours = record.actual_hours

            if is_weekday:
                if record.hari_libur:
                    record.gut_class1 = 0
                    record.gut_class2 = self._round_up_if_tolerance_met(adjusted_actual_hours, tolerance_minutes)
                else:
                    overtime_hours = adjusted_actual_hours - normal_hours
                    record.gut_class1 = min(overtime_hours, 1)
                    remaining_overtime = max(overtime_hours - record.gut_class1, 0)
                    record.gut_class2 = self._round_up_if_tolerance_met(remaining_overtime, tolerance_minutes)
            else:  # Weekend
                if adjusted_actual_hours > 2:
                    record.gut_class1 = 0
                    record.gut_class2 = self._round_up_if_tolerance_met(adjusted_actual_hours, tolerance_minutes)

    def _round_up_if_tolerance_met(self, hours, tolerance):
        fractional_part = hours % 1
        whole_hours = int(hours)
        if fractional_part >= tolerance:
            return whole_hours + 1  # Round up to next hour
        else:
            return whole_hours + fractional_part



# compute overtime class 3
    @api.multi
    @api.depends('actual_hours', 'hari_libur')
    def _compute_gut_class3(self):
        tolerance_minutes = 50 / 60.0  # 50 minutes out of 60
        tolerance_9_hours = 8 + tolerance_minutes  # 9 hours tolerance as 8 hours and 50 minutes

        for record in self:
            check_in_date = record.check_in.date()  # Extract the date portion
            is_weekday = check_in_date.weekday() < 5  # Monday to Friday

            if is_weekday and record.hari_libur:
                record.gut_class3 = self._check_and_set_class3(record.actual_hours, tolerance_9_hours)
            elif not is_weekday:
                record.gut_class3 = self._check_and_set_class3(record.actual_hours, tolerance_9_hours)
            else:
                record.gut_class3 = 0

    def _check_and_set_class3(self, actual_hours, tolerance_9_hours):
        if actual_hours >= tolerance_9_hours:
            return 1
        else:
            return 0



# compute overtime class 4
    @api.multi
    @api.depends('actual_hours', 'hari_libur')
    def _compute_gut_class4(self):
        tolerance_minutes = 50 / 60.0  # 50 minutes out of 60
        tolerance_9_hours = 8 + tolerance_minutes  # 9 hours tolerance as 8 hours and 50 minutes

        for record in self:
            check_in_date = record.check_in.date()  # Extract the date portion
            is_weekday = check_in_date.weekday() < 5  # Monday to Friday

            adjusted_actual_hours = record.actual_hours

            if is_weekday and record.hari_libur:
                if adjusted_actual_hours >= tolerance_9_hours:
                    record.gut_class4 = adjusted_actual_hours - tolerance_9_hours
                else:
                    record.gut_class4 = 0
            elif not is_weekday:
                if adjusted_actual_hours >= tolerance_9_hours:
                    record.gut_class4 = adjusted_actual_hours - tolerance_9_hours
                else:
                    record.gut_class4 = 0
            else:
                record.gut_class4 = 0


    @api.multi
    @api.depends('check_in', 'check_out')
    def _compute_actual_hours(self):
        for record in self:
            if record.check_out:
                delta = record.check_out - record.check_in
                newdate_in_13 = record.check_out.replace(hour=5, minute=0, second=0)  # set to 13:00
                if record.check_in >= newdate_in_13:
                    actual_hours = delta.total_seconds() / 3600.0  # No reduction if check-in is on or after 13:00
                else:
                    actual_hours = delta.total_seconds() / 3600.0 - 1  # Subtract 1 hour otherwise

                record.actual_hours = actual_hours


    # compute class 1
    @api.multi
    @api.depends('actual_hours', 'hari_libur', 'contract_type_id')
    def _compute_gut_class1(self):
        """
        Compute Class 1 value based on actual hours, holidays, and job position.
        The calculation is based on weekdays, weekends, and actual working hours.
        """
        tolerance_minutes = 49 / 60.0  # 49 minutes out of 60
        project_tolerance_hours = 10 + tolerance_minutes  # 10 hours and 50 minutes
        tolerance_hours = 8 + tolerance_minutes  # 8 hours and 50 minutes

        for record in self:
            check_in_date = record.check_in.date() if record.check_in else None
            is_weekday = check_in_date.weekday() < 5 if check_in_date else False  # Monday to Friday
            is_sunday = check_in_date.weekday() == 6 if check_in_date else False  # Sunday

            if record.contract_type_id and record.contract_type_id.status == 'Kontrak Project':
                if is_sunday or record.hari_libur:
                    record.gut_class1 = record.actual_hours  # Set to actual hours on Sunday or holidays
                else:
                    if record.actual_hours > project_tolerance_hours:
                        excess_hours = self._round_up_if_tolerance_met(record.actual_hours - 10, tolerance_minutes)
                        record.gut_class1 = int(excess_hours)  # Convert excess hours to integer
                    else:
                        record.gut_class1 = 0  # No excess hours beyond tolerance
            else:
                if is_weekday:
                    if record.hari_libur and record.actual_hours > 0:
                        record.gut_class1 = 0
                    elif not record.hari_libur:
                        actual_hours_rounded = self._round_up_if_tolerance_met(record.actual_hours, tolerance_minutes)
                        record.gut_class1 = 1 if actual_hours_rounded >= tolerance_hours else 0
                else:
                    record.gut_class1 = 0

    def _round_up_if_tolerance_met(self, hours, tolerance):
        fractional_part = hours % 1
        whole_hours = int(hours)
        if fractional_part >= tolerance:
            return whole_hours + 1  # Round up to next hour
        else:
            return whole_hours + fractional_part

# compute class 2, 3, 4
    @api.multi
    @api.depends('actual_hours', 'hari_libur', 'contract_type_id', 'public_holiday', 'is_travel')
    def _compute_gut_classes(self):
        tolerance_minutes = 50 / 60.0  # 50 minutes out of 60
        tolerance_9_hours = 8 + tolerance_minutes  # 9 hours tolerance as 8 hours and 50 minutes

        for record in self:
            if record.is_travel:
                record.gut_class1 = 0
                record.gut_class2 = 0
                record.gut_class3 = 0
                record.gut_class4 = 0
                continue  # Skip further calculations for this record

            if record.contract_type_id and record.contract_type_id.status == 'Kontrak Project':
                continue  # Skip computation for 'Kontrak Project' contract type

            if record.actual_hours <= 1:
                record.gut_class1 = False
                record.gut_class2 = False
                record.gut_class3 = False
                record.gut_class4 = False
                continue  # Skip further calculations for this record

            check_in_date = record.check_in.date()  # Extract the date portion
            is_weekday = check_in_date.weekday() < 5  # Monday to Friday

            adjusted_actual_hours = record.actual_hours

            # Check if it's a weekend or a public holiday
            if not is_weekday or (record.hari_libur and record.public_holiday and record.public_holiday.type == 'Public Holiday'):
                # Weekend or Public Holiday logic
                record.gut_class2 = self._round_up_if_tolerance_met(min(8, adjusted_actual_hours), tolerance_minutes)
                record.gut_class3 = 1 if adjusted_actual_hours > 8 else 0
                record.gut_class4 = max(0, adjusted_actual_hours - 9)
            else:  # Weekday and not a Public Holiday
                normal_hours = 8
                overtime_hours = adjusted_actual_hours - normal_hours
                record.gut_class1 = min(overtime_hours, 1)
                remaining_overtime = max(overtime_hours - record.gut_class1, 0)
                
                if adjusted_actual_hours >= 9:  # Ensure minimum actual hours for class 2
                    record.gut_class2 = self._round_up_if_tolerance_met(remaining_overtime, tolerance_minutes)
                else:
                    record.gut_class2 = 0
                record.gut_class3 = 0
                record.gut_class4 = 0

            # Ensure all values are not negative
            record.gut_class1 = max(record.gut_class1, 0) if record.gut_class1 else 0
            record.gut_class2 = max(record.gut_class2, 0) if record.gut_class2 else 0
            record.gut_class3 = max(record.gut_class3, 0) if record.gut_class3 else 0
            record.gut_class4 = max(record.gut_class4, 0) if record.gut_class4 else 0

    def _round_up_if_tolerance_met(self, hours, tolerance):
        fractional_part = hours % 1
        whole_hours = int(hours)
        if fractional_part >= tolerance:
            return whole_hours + 1  # Round up to next hour
        else:
            return whole_hours + fractional_part

    

# compute start overtime hours
    @api.multi
    @api.depends('actual_hours')
    def _compute_start_overtime(self):
        for record in self:
            check_in_date = datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date()
            weekday = check_in_date.weekday()
            is_weekend = weekday >= 5  # Saturday and Sunday

            if record.actual_hours >= 9:
                overtime_start = timedelta(hours=9, minutes=1)
                record.start_overtime_hours = record.check_in + overtime_start
            elif is_weekend and record.actual_hours >= 3:
                record.start_overtime_hours = record.check_in

# compute waktu telat
    @api.multi
    @api.depends('check_in', 'contract_type_id','check_out')
    def _compute_waktu_telat(self):
        for record in self:
            check_in_date = datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date()
            weekday = check_in_date.weekday()
            is_weekday = weekday < 5  # Monday to Friday

            if is_weekday and record.check_out:
                # set to 7:00 AM
                newdate_in_07 = record.check_in.replace(hour=0, minute=1, second=0)  
                # set to 9:00 AM
                newdate_in_09 = record.check_in.replace(hour=2, minute=0, second=0)

                if record.contract_type_id and record.contract_type_id.status == 'Kontrak Project':
                    newdate_in = newdate_in_07
                else:
                    newdate_in = newdate_in_09

                if record.check_in > newdate_in:
                    delta = record.check_in - newdate_in
                    diff = delta.total_seconds() / 3600.0  # convert to hours
                else:
                    diff = 0.0

                record.waktu_telat = diff


# compute total waktu telat + early out
    @api.multi
    def _compute_total_waktu_telat(self):
        for record in self:
            total = record.waktu_telat + record.gut_early_hours

            record.total_waktu_telat = total


# compute waktu early
    @api.multi
    def _compute_early_hours(self):
        for record in self:
            if record.actual_hours > 1:
                check_in_date = datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date()
                weekday = check_in_date.weekday()
                is_weekday = weekday < 5  # Monday to Friday

                if is_weekday and record.check_out:
                    newdate_out_17 = record.check_out.replace(hour=10, minute=0)  # set to 17:00
                    newdate_out_1730 = record.check_out.replace(hour=10, minute=30)  # set to 17:30
                    newdate_out_18 = record.check_out.replace(hour=11, minute=0)  # set to 18:00
                    newdate_in_8 = record.check_in.replace(hour=1, minute=0, second=0)  # set to 8:00
                    newdate_in_830 = record.check_in.replace(hour=1, minute=30, second=0)  # set to 8:30
                    newdate_in_9 = record.check_in.replace(hour=2, minute=0, second=0)  # set to 9:00

                    if record.check_in < newdate_in_8 and record.check_out < newdate_out_17 and record.worked_hours < 9.0:
                        delta = newdate_out_17 - record.check_out
                        duration = delta.total_seconds() / 3600.0
                    elif newdate_in_8 <= record.check_in <= newdate_in_830 and record.check_out < newdate_out_1730 and record.worked_hours < 9.0:
                        duration = 8.0 - record.actual_hours
                    elif newdate_in_830 < record.check_in <= newdate_in_9 and record.check_out <= newdate_out_1730:
                        delta = newdate_out_1730 - record.check_out
                        duration = delta.total_seconds() / 3600.0
                    elif record.check_in > newdate_in_9 and record.check_out <= newdate_out_18:
                        delta = newdate_out_18 - record.check_out
                        duration = delta.total_seconds() / 3600.0
                    else:
                        duration = 0.0

                    record.gut_early_hours = duration


    # compute Absen
    @api.multi
    @api.depends('actual_hours', 'hari_libur')
    def _compute_hari_absen(self):
        for record in self:
            check_in_date = datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date()
            is_weekday = check_in_date.weekday() < 5  # Monday to Friday

            if is_weekday and not record.hari_libur and not record.worked_hours:
                record.gut_absen = 1


# compute nama hari
    @api.multi
    @api.depends('check_in')
    def _compute_gut_day(self):
        for record in self:
            check_in_date = datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date()
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            record.gut_day = days[check_in_date.weekday()]

# compute jika tgl merah == public holiday
    @api.multi
    @api.depends('check_in')
    def _compute_tgl_merah(self):
        """
        Compute whether the attendance date is a public holiday and set `hari_libur` and `public_holiday` fields.
        """
        for record in self:
            check_in_date = datetime.strptime(str(record.check_in), "%Y-%m-%d %H:%M:%S").date()
            public_holiday = self.env['hr.holidays.public.line'].search([('date', '=', check_in_date)], limit=1)
            
            if public_holiday:
                record.hari_libur = True
                record.public_holiday = public_holiday
            else:
                record.hari_libur = False
                record.public_holiday = False
                    
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

    gut_class1 = fields.Integer(
        string='Class 1',compute='_compute_gut_class1',
    )

    gut_class2 = fields.Integer(
        string='Class 2',compute='_compute_gut_classes',
    )
    gut_class3 = fields.Integer(
        string='Class 3',compute='_compute_gut_classes',
    )

    gut_class4 = fields.Integer(
        string='Class 4',compute='_compute_gut_classes',
    )
    gut_day = fields.Char(
        string='Day',compute='_compute_gut_day',
    )
    gut_normal_hours = fields.Integer(
        string='Normal',compute='_compute_normal_hours',
    
    )
    hari_libur = fields.Boolean(string='Tanggal Merah?', compute='_compute_tgl_merah'
    )

    gut_code = fields.Integer(string='All Code', default= 0,
    )
    gut_early_hours = fields.Float(
        string='Early Out',compute='_compute_early_hours',
    )
    waktu_telat = fields.Float(
        string='Waktu Telat', compute='_compute_waktu_telat',
    )
    total_waktu_telat = fields.Float(
        string='Total Telat & PSW', compute='_compute_total_waktu_telat',
    )
    is_travel = fields.Boolean(string='Is Travel')
    gut_travel = fields.Integer(string='Travel', compute='_compute_gut_travel', store=True)

    @api.depends('is_travel')
    def _compute_gut_travel(self):
        for record in self:
            if record.is_travel:
                record.gut_travel = 8
            else:
                record.gut_travel = 0  # or any default value you want


