from odoo import models, api, fields, _
from datetime import date, datetime , timedelta
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools import float_compare


class HRLeave(models.Model):
    _inherit = 'hr.leave'

    leave_allocation = fields.Integer(string='Hak Cuti', compute="_compute_remaining_leaves")
    leave_balance = fields.Integer(string='Saldo Cuti', compute="_compute_get_leave_balance")
    leave_remaining = fields.Integer(string='Sisa Cuti', compute="_compute_get_leave_remaining")
    jabatan = fields.Many2one('hr.job', related='employee_id.job_id', string='Jabatan Sekarang')
    atasan = fields.Many2one('hr.employee', related='employee_id.parent_id', string='Atasan Langsung')
    leave_timesheet_id = fields.Many2one('hr_timesheet.sheet',  compute="_compute_leave_sheet_id", store=True)
    department = fields.Many2one('hr.department', related='employee_id.department_id', string='Departemen')
    alamat = fields.Many2one('res.partner', related='employee_id.address_home_id', )
    gut_alamat= fields.Char('Client Address', compute="_get_alamat")
    gut_phone= fields.Char('Client Address', compute="_get_phone")

    @api.depends('employee_id','holiday_status_id')
    def _compute_remaining_leaves(self):
        for leaves in self:
            # Get number of days for all validated leaves filtered by employee and leave type
            allocation = self.env['hr.leave.allocation'].search([
                ('employee_id.id', '=', leaves.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id', '=', leaves.holiday_status_id.id),
                # ('holiday_status_id.id', '=',  allocation.holiday_status_id.id)
            ])
            leaves.leave_allocation = sum(allocation.mapped('number_of_days'))

    @api.depends('employee_id','holiday_status_id')     
    def _compute_get_leave_remaining(self):
         for leaves in self:
            if leaves.holiday_status_id:
                allocation = self.env['hr.leave.allocation'].search([('employee_id.id', '=', leaves.employee_id.id),('holiday_status_id', '=', leaves.holiday_status_id.id),('state', '=', 'validate')])
                leaves.leave_remaining = allocation.remaining_leaves

    @api.multi
    @api.depends('employee_id','holiday_status_id')
    def _compute_get_leave_balance(self):
         for rec in self:
            if rec.holiday_status_id:
                rec.leave_balance = rec.number_of_days + rec.leave_remaining 

# compute get leave ids on timesheet
    def _get_leave_timesheet_sheet(self):
        """Find and return current timesheet-sheet
        :return: recordset of hr_timesheet.sheet or False"""

        sheet_obj = self.env['hr_timesheet.sheet']
        domain = [('employee_id', '=', self.employee_id.id)]

        sheet_ids = sheet_obj.search(domain, limit=1)
        return sheet_ids[:1] or False

    @api.depends('employee_id')
    def _compute_leave_sheet_id(self):
        """Find and set current timesheet-sheet in
        current attendance record"""
        for leave in self:
            leave.leave_timesheet_id = leave._get_leave_timesheet_sheet()

    def _get_alamat(self):
        if not self.employee_id.address_home_id:
                alamat = self.employee_id.address_home_id
                if alamat.street:
                    self.gut_alamat = alamat.street
                if alamat.city:
                    self.gut_alamat = str(self.gut_alamat) + ', </br>' + alamat.city
                if alamat.state_id:
                    self.gut_alamat = str(self.gut_alamat) + ', ' + alamat.state_id.name
                if alamat.zip:
                    self.gut_alamat = str(self.gut_alamat) + ' - ' + alamat.zip

    def _get_phone(self):
        if not self.employee_id.address_home_id:
                alamat = self.employee_id.address_home_id
                if alamat.mobile:
                    self.gut_phone = alamat.mobile

# override button reset to draft
    @api.multi
    def action_draft(self):
        for holiday in self:
            if not holiday.can_reset:
                raise UserError(_('Only an HR Manager or the concerned employee can reset to draft.'))
            holiday.write({
                'state': 'draft',
                'manager_id': False,
                'manager_id2': False,
            })
            linked_requests = holiday.mapped('linked_request_ids')
            for linked_request in linked_requests:
                linked_request.action_draft()
            linked_requests.unlink()
        return True

class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'


    def name_get(self):
        result = []
        for record in self:
            if self.env.context.get('hak', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id," "+str(record.max_leaves)))
            else:
                result.append((record.id, record.name))
        return result

class HolidaysAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    # fields
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', index=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    remaining_leaves = fields.Float(compute='_compute_remaining_leaves')
    remaining_leaves_display = fields.Char('Remaining (Days)', compute='_compute_remaining_leaves_display')
    taken_leaves = fields.Float('Taken (Days)', compute='_compute_remaining_leaves')
    holiday_type = fields.Selection([
        ('employee', 'Employee'),
        # ('category', 'By Employee Tag'),
        ('department', 'By Department'),
        ('company', 'By Company'),
        ('employee_ho', 'HO Employee'),
        ('company', 'By Company'),
        ], string="Mode"
    )

    gender_mode = fields.Selection([
        ('female', 'Female'),
        ('male', 'Male')
    ], string='Gender',)
    double_validation = fields.Boolean('Apply Double Validation', related='holiday_status_id.double_validation')

    def _compute_remaining_leaves(self):
        for allocation in self:

            # Get number of days for all validated leaves filtered by employee and leave type
            leaves = self.env['hr.leave'].search([
                # ('active', 'in', [True, False]),
                ('employee_id', '=', allocation.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id', '=',  allocation.holiday_status_id.id)
            ])
            allocation.remaining_leaves = allocation.number_of_days - sum(leaves.mapped('number_of_days'))
            allocation.taken_leaves = sum(leaves.mapped('number_of_days'))
    
    def _compute_remaining_leaves_display(self):
        for allocation in self:
            allocation.remaining_leaves_display = '%g %s' % (float_round(allocation.remaining_leaves, precision_digits=2), _('days'))


# override button reset to draft
    @api.multi
    def action_draft(self):
        for holiday in self:
            if not holiday.can_reset:
                raise UserError(_('Only an HR Manager or the concerned employee can reset to draft.'))
            holiday.write({
                'state': 'draft',
                'manager_id': False,
                'manager_id2': False,
            })
            linked_requests = holiday.mapped('linked_request_ids')
            for linked_request in linked_requests:
                linked_request.action_draft()
            linked_requests.unlink()
        return True


    # @api.multi
    # def _prepare_create_by_gender(self, employee):
    #     self.ensure_one()
    #     values = {
    #         'name': self.name,
    #         'holiday_type': 'gender',
    #         'holiday_status_id': self.holiday_status_id.id,
    #         'date_from': self.date_from,
    #         'date_to': self.date_to,
    #         'notes': self.notes,
    #         'number_of_days': self.number_of_days,
    #         'parent_id': self.id,
    #         'employee_id': employee.id,
    #         'state': 'validate',
    #     }
    #     return values

# override allocation mode -- holiday_type
    # @api.multi
    # def _check_security_action_validate(self):
    #     if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
    #         raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

    # @api.multi
    # def action_validatexxx(self):
    #     self._check_security_action_validate()

    #     current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    #     for holiday in self:
    #         if holiday.state not in ['confirm', 'validate1']:
    #             raise UserError(_('Leave request must be confirmed in order to approve it.'))
    #         if holiday.state == 'validate1' and not holiday.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
    #             raise UserError(_('Only an HR Manager can apply the second approval on leave requests.'))

    #         holiday.write({'state': 'validate'})
    #         if holiday.double_validation:
    #             holiday.write({'second_approver_id': current_employee.id})
    #         else:
    #             holiday.write({'first_approver_id': current_employee.id})
    #         if holiday.holiday_type == 'category':
    #             leaves = self.env['hr.leave.allocation']
    #             for employee in holiday.category_id.employee_ids:
    #                 values = holiday._prepare_create_by_category(employee)
    #                 leaves += self.with_context(mail_notify_force_send=False).create(values)
    #         elif holiday.holiday_type == 'department':
    #             leaves = self.env['hr.leave.allocation']
    #             for employee in holiday.department_id.member_ids:
    #                 values = holiday._prepare_create_by_gender(employee)
    #                 leaves += self.with_context(mail_notify_force_send=False).create(values)
    #         elif holiday.holiday_type == 'company':
    #             leaves = self.env['hr.leave.allocation']
    #             for employee in self.env['hr.employee'].search([('active','=', True)]):
    #                 values = holiday._prepare_create_by_gender(employee)
    #                 leaves += self.with_context(mail_notify_force_send=False).create(values)
    #         elif holiday.holiday_type == 'gender':
    #             leaves = self.env['hr.leave.allocation']
    #             for employee in self.env['hr.employee'].search([('gender','=', holiday.gender_mode)]):
    #                 values = holiday._prepare_create_by_gender(employee)
    #                 leaves += self.with_context(mail_notify_force_send=False).create(values)
    #             # TODO is it necessary to interleave the calls?
    #             # leaves.action_approve()
    #             # if leaves and leaves[0].double_validation:
    #             #     leaves.action_validate()
    #     return True

    
    @api.multi
    def action_validate(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            if holiday.state not in ['confirm', 'validate1']:
                raise UserError(_('Leave request must be confirmed in order to approve it.'))

            holiday.write({'state': 'validate'})
            if holiday.validation_type == 'both':
                holiday.write({'second_approver_id': current_employee.id})
            else:
                holiday.write({'first_approver_id': current_employee.id})

            holiday._action_validate_create_childs()
        self.activity_update()
        return True

    def _action_validate_create_childs(self):
        childs = self.env['hr.leave.allocation']
        if self.state == 'validate' and self.holiday_type in ['category', 'department', 'company', 'gender','employee_ho']:
            if self.holiday_type == 'category':
                employees = self.category_id.employee_ids
            elif self.holiday_type == 'department':
                employees = self.department_id.member_ids
            elif self.holiday_type == 'gender':
                employees = self.env['hr.employee'].search([('gender','=', self.gender_mode)])
            elif self.holiday_type == 'employee_ho':
                employees = self.env['hr.employee'].search([('status_karyawan','!=','PKWT Project')])
            else:
                employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id)])

            for employee in employees:
                childs += self.with_context(
                    mail_notify_force_send=False,
                    mail_activity_automation_skip=True
                ).create(self._prepare_holiday_values(employee))
            # TODO is it necessary to interleave the calls?
            childs.action_approve()
            if childs and self.holiday_status_id.validation_type == 'both':
                childs.action_validate()
        return childs

    @api.onchange('holiday_type')
    def _onchange_type(self):
        if self.holiday_type == 'employee':
            # if not self.employee_id:
            #     self.employee_id = self.env.user.employee_ids[:1].id
            self.mode_company_id = False
            self.category_id = False
        elif self.holiday_type == 'company':
            self.employee_id = False
            if not self.mode_company_id:
                self.mode_company_id = self.env.user.company_id.id
            self.category_id = False
        elif self.holiday_type == 'department':
            self.employee_id = False
            self.mode_company_id = False
            self.category_id = False
            if not self.department_id:
                self.department_id = self.env.user.employee_ids[:1].department_id.id
        elif self.holiday_type == 'category':
            self.employee_id = False
            self.mode_company_id = False
            self.department_id = False
        elif self.holiday_type == 'gender':
            self.employee_id = False
            self.mode_company_id = False
            self.department_id = False
        elif self.holiday_type == 'employee_ho':
            self.employee_id = False
            self.mode_company_id = False
            self.department_id = False

# class HolidaysPublicLine(models.Model):
#     _inherit = 'hr.holidays.public.line'

#     holiday_timesheet_id = fields.Many2one('hr_timesheet.sheet')


# class EmployeeCUti(models.Model):
#     _name = 'hr.employee.cuti'

#     name = fields.Many2one('hr.employee', string='Employee')
#     jabatan = fields.Many2one('hr.job', related='name.job_id', string='Jabatan Sekarang')
#     department = fields.Many2one('hr.department', related='name.department_id', string='Departemen')
#     atasan = fields.Many2one('hr.employee', related='name.parent_id', string='Atasan Langsung')
#     street = fields.Many2one('res.partner', related='name.address_home_id', )
#     city = fields.Many2one('res.partner', related='name.address_home_id', string='Kota')
#     state = fields.Many2one('res.partner', related='name.address_home_id', string='Provinsi')
#     phone = fields.Many2one('res.partner', related='name.address_home_id', string='Phone')
#     mobile = fields.Many2one('res.partner', related='name.address_home_id', string='Mobile')
#     date_from = fields.Datetime(string="")
#     date_to = fields.Datetime(string="")
#     jumlah_hari = fields.Integer(string="day", )
#     hak_cuti = fields.Integer(string="Hak Cuti", compute="_compute_hak_cuti")
#     active = fields.Boolean(default=True)

#     def _compute_jumlah_hari(self):
#         for rec in self:
#             assert isinstance(rec.date_to, datetime)
#             delta = rec.date_to - rec.date_from + timedelta(days=1)
#             total = delta.total_seconds() / 86400

#             self.jumlah_hari = total

#     def _compute_hak_cuti(self):
#             total = 12
#             self.hak_cuti = total

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # get name alamat dan phone
    def name_get(self):
        result = []
        for record in self:
            if self.env.context.get('hp', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id," "+str(record.mobile)))
            elif self.env.context.get('phone', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.phone)))
            elif self.env.context.get('email', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.email)))
            elif self.env.context.get('street', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.street)))
            elif self.env.context.get('kota', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.city)))
            elif self.env.context.get('provinsi', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.state_id.name)))
            else:
                result.append((record.id, record.name))
        return result
        
        
