from odoo import models, api, fields

class HrContract(models.Model):
    _inherit = 'hr.contract'

    wage_hourly = fields.Monetary(string='Hourly', compute='_compute_wage_hourly')
    bpjs_kary = fields.Monetary(string='BPJS Kes. Karyawan',)
    jp = fields.Monetary(string='Jaminan Pensiun 1%',compute='_compute_jp')
    jht2= fields.Monetary(string='JHT 2',compute='_compute_jht2')
    bpjs_peru = fields.Monetary(string='BPJS Kes. Perusahaan',)
    jkm03 = fields.Monetary(string='JKM03',compute='_compute_jkm03')
    jkk024 = fields.Monetary(string='JKK024',compute='_compute_jkk024')
    employee_id = fields.Many2one('hr.employee', )
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', string="Department")
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', string='Job Title')

    alw_out = fields.Many2one('employee.grade', related='employee_id.employee_grade', string='Allowance Luar',readonly="1")
    alw_in = fields.Many2one('employee.grade', related='employee_id.employee_grade', string='Allowance Dalam',readonly="1")


# compute wage hourly
    @api.multi
    def _compute_wage_hourly(self):
        for rec in self:
            rec.wage_hourly = rec.wage / 173

# compute Jaminan Pensiun 1%
    @api.multi
    def _compute_jp(self):
        for rec in self:
            if rec.wage >= 10423000:
                rec.jp = 100423
            else:
                rec.jp = rec.wage * 0.01

 # compute JHT 2
    @api.multi
    def _compute_jht2(self):
        for rec in self:
            rec.jht2 = rec.wage * 0.02

# compute JKM03
    @api.multi
    def _compute_jkm03(self):
        for rec in self:
            rec.jkm03 = rec.wage * 0.003

# compute JKK024
    @api.multi
    def _compute_jkk024(self):
        for rec in self:
            rec.jkk024 = rec.wage * 0.0024

# onchange employee_id
    @api.onchange('employee_id')
    def on_change_employee_id(self):
        contract = self.employee_id.status_karyawan

        self.type_id = contract if contract else None


class HrContract(models.Model):
    _inherit = 'hr.contract.type'

    status = fields.Char(string="Status")
    description = fields.Text(string="Description")
    employee_count = fields.Integer(string='Employee Count', compute='_get_employee_count')
    active = fields.Boolean(default=True)

    # compute open employee Contract Type
    @api.multi
    def open_employees(self):
        for group in self:
            return {
                'name': 'Employees',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.employee',
                'type': 'ir.actions.act_window',
                'domain': [('status_karyawan', '=', group.id)],
            }
        pass

    @api.multi
    def _get_employee_count(self):
        res = self.env['hr.employee'].search_count([('status_karyawan', '=', self.id)])
        self.employee_count = res or 0

class WorkSchedule(models.Model):
    _name = 'hr.work.schedule'
    _description = 'Work Schedule'

    name = fields.Char(string='Work Schedule Name', required=True)
    description = fields.Text(string='Description')
    
    @api.multi
    def name_get(self):
        data = []
        for schedule in self:
            display_name = schedule.name
            if schedule.description:
                display_name += ' - ' + schedule.description
            data.append((schedule.id, display_name))
        return data