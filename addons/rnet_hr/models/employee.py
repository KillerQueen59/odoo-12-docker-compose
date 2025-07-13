from odoo import api, fields, models, _
from datetime import date, datetime , timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError

STATESREGION = [
    ('islam', 'Islam'),
    ('protestan', 'Protestan'),
    ('Katolik', 'Katolik'),
    ('hindu', 'Hindu'),
    ('budha', 'Budha'),
    ('konghucu', 'Konghucu'),
]

STATESKAWIN = [
    ('tk0', 'TK0'),
    ('tk1', 'TK1'),
    ('tk2', 'TK2'),
    ('tk3', 'TK3'),
    ('k0', 'K0'),
    ('k1', 'K1'),
    ('k2', 'K2'),
    ('k3', 'K3'),
]

class Employee(models.Model):
    _inherit = 'hr.employee'

    gut_nik = fields.Char('No Induk Karyawan')
    gut_npwp = fields.Char('NPWP')

    employee_grade = fields.Many2one('employee.grade', string='Employee Grade')
    project = fields.Many2one('project.project', string='Project')
    # task = fields.One2many('project.task', 'employee_id')
    status= fields.Selection(STATESKAWIN, string='Status kawin', compute='_compute_status_kawin')
    status_karyawan = fields.Many2one('hr.contract.type', string='Status Karyawan',)
    region = fields.Selection(STATESREGION, string='Region')
    employee_certificate = fields.Many2one('hr.employee.certificate', string='Employee Certificate')
    employee_count_certificate = fields.Integer(string='Employee count certificate', compute='_get_employee_count_certificate')
    employee_count_cv = fields.Integer(string='Employee count cv', compute='_get_employee_count_cv')
    appraisal_id = fields.Many2one('hr.employee.appraisal', string='Employee Appraisal',)

    age = fields.Integer('Umur')
    refresh_onchange_actual_value = fields.Datetime(string="Update Actual Value??", help="untuk dummy saja tidak berhungungan dengan employee")
    keahlian = fields.Many2many('hr.employee.cv.spesialisasi.line', 'employee_cv_spesialiasi', string="Keahlian")
    pelatihan = fields.Many2many('hr.employee.cv.seminar.line', 'employee_cv_seminar', string="Pelatihan")
    pengalaman_kerja_gut = fields.Many2many('hr.employee.cv.project.line', 'employee_cv_pengalaman_gut_line', string="Pengalaman kerja")
    job_on_site = fields.Char('Available On Site')
    pendidikan = fields.Many2many('hr.employee.cv.pendidikan.line', 'employee_cv_pendidikan', string='Pendidikan')
    employee_location_history = fields.Char(string='Location History')
    employee_penilaian = fields.Many2many('hr.employee.penilaian', string='Penilaian Kinerja')
    penilaian_not = fields.Boolean(string='NOT')
    work_schedule_id = fields.Many2one('hr.work.schedule', string='Work Schedule')

# action untuk trigger onchange di bawah (umur, keahlian) supaya bisa fieldnya bisa difilter di tree view
    def action_update_employee_value(self):
        self.write({
                'refresh_onchange_actual_value' : fields.Datetime.now(),
            })
        self.onchange_employee_age()
        self.onchange_employee_keahlian()
        self.onchange_employee_pelatihan()
        self.onchange_employee_standby()
        self.onchange_employee_location_history()
        self.onchange_employee_pendidikan()
        self.prepare_create_pengalaman_kerja_attendance()
        self.onchange_employee_penilaian()
        self.onchange_employee_penilaian_not()
        self.onchange_employee_pengalman_gut()

        

        return True

# get employee age --- umur
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_employee_age(self):
        for rec in self:
            if rec.birthday:
               rec.age = relativedelta(date.today(),rec.birthday).years

    # onchange birthday
    @api.onchange('birthday')
    def onchange_employee_birthday_age(self):
        for rec in self:
            if rec.birthday:
               rec.age = relativedelta(date.today(),rec.birthday).years           

# get employee keahlian --- spesialiasi line di employee CV
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_employee_keahlian(self):
        for rec in self:
            res = self.env['hr.employee.cv.spesialisasi.line'].search([ ('cv_spesialisasi_id.name.id', '=', rec.id)])
            rec.keahlian = res or False

# get employee pelatihan --- seminar line di employee CV
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_employee_pelatihan(self):
        for rec in self:
            res = self.env['hr.employee.cv.seminar.line'].search([ ('cv_seminar_id.name.id', '=', rec.id)])
            rec.pelatihan = res or False

# get employee pengalaman kerja GUT --- project gut line di employee CV
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_employee_pengalman_gut(self):
        for rec in self:
            res = self.env['hr.employee.cv.project.line'].search([ ('cv_pengalaman_gut_id.name.id', '=', rec.id)])
            rec.pengalaman_kerja_gut = res or False

# get employee currrent location history --- employee location line di employee CV
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_employee_location_history(self):
        for rec in self:
            res = self.env['hr.employee.cv.project.line'].search([ ('cv_pengalaman_gut_id.name.id', '=', rec.id)],order='work_date desc')
            if res:
                for line in res.filtered(lambda x: x.work_date).sorted(key=lambda r: r.work_date): 
                    pro = line.name.name[:20] if line else ''
                    pro_no = line.name.no if line else ''
                    rec.employee_location_history = "["+pro_no+"] " +pro +" " if line else ""


# get employee last state --- stand by or on site
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_employee_standby(self):
        for rec in self:
            res = self.env['hr.attendance'].search(['&',('employee_id', '=', rec.id),('gut_code', '>=', 1)],order='check_in desc')
            if res:
                for line in res.filtered(lambda x: x.check_in).sorted(key=lambda r: r.check_in):
                    previous_month = (date.today().replace(day=1) - timedelta(days=1)).month
                    last_month = datetime.now().month - 1
                    checkin_last_month = line.check_in.month - 1
                    jo = line.project.name if line else ''
                    jo_no = line.project.no if line else ''
                    if rec.status_karyawan.name == 'PKWT Project' and checkin_last_month in [ last_month, previous_month]:
                        rec.job_on_site = "On Site [" + jo_no  +"] " + jo +""
                    else: 
                        rec.job_on_site = "Standby"

    # get employee penilaian
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_employee_penilaian(self):
        for rec in self:
            res = self.env['hr.employee.penilaian'].search([('employee_id', '=', rec.id)],order='penilaian_date desc')
            if res:
                # rec.employee_penilaian = dict(res._fields['name'].selection).get(res.name)
                rec.employee_penilaian = res

    # check employee penilaian is not > 3
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_employee_penilaian_not(self):
         for rec in self:
            res = self.env['hr.employee.penilaian'].search(['&',('employee_id', '=', rec.id),('name', '=', 'not')])
            if len(res) >= 3:
                rec.penilaian_not = True

# get employee pengalaman kerja GUT from attendance--- project gut line di employee CV
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def prepare_create_pengalaman_kerja_attendance(self):
        for rec in self:

                query = """select  pro.id as pro, pro.name as pro_name,  date_trunc('month',check_in)::date as bulan 
                    from hr_attendance attn
                                LEFT JOIN 
                        project_project pro on pro.id=attn.project
                                LEFT JOIN 
                        hr_employee emp on pro.id=attn.employee_id
                    where attn.gut_code >= 1 AND attn.employee_id IN %s			
                    group by pro, bulan ORDER BY bulan ASC""" 
            
                self.env.cr.execute(query, (tuple(rec.ids),))
                cr = self.env.cr.dictfetchall()

                cv = self.env['hr.employee.cv'].search([('name', '=', rec.id)])

                pengalaman_lines = []
                for line in cr:
                    pengalaman_lines.append([0,0,{
                                            'name' :  line['pro'],
                                            'work_date' :  line['bulan'],
                                            }])
                print('pengalaman line>>>', pengalaman_lines)
                cv.pengalaman_gut_line_ids = [(6, 0, [])]
                cv.write({'pengalaman_gut_line_ids' : pengalaman_lines})
                return 
                                
                    

# compute pendidikan
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_employee_pendidikan(self):
        for rec in self:
            res = self.env['hr.employee.cv.pendidikan.line'].search([ ('cv_pendidikan_id.name.id', '=', rec.id)])
            rec.pendidikan = res or False


# compute status kawin
    @api.one
    def _compute_status_kawin(self):
        status_mapping = {
            'single': {0: 'tk0', 1: 'tk1', 2: 'tk2', 3: 'tk3'},
            'married': {0: 'k0', 1: 'k1', 2: 'k2', 3: 'k3'}
        }
        
        for rec in self:
            children = min(rec.children, 3)  # Cap the children count at 3
            self.status = status_mapping.get(rec.marital, {}).get(children, None)



    @api.multi
    def open_project(self):
        for group in self:
            return {
                'name': 'Projects',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'project.task',
                'type': 'ir.actions.act_window',
                'domain': [('employee_id', '=', group.id)],
            }
        pass

    project_count = fields.Integer(
        compute='_compute_project_count',
        string='Timesheet Sheets Count',
    )

    @api.multi
    def _compute_project_count(self):
        res = self.env['project.task'].search_count([ ('employee_id', '=', self.id)])
        self.project_count = res or 0


 # compute employee certificate
    @api.multi
    def open_employees_cetificate(self):
        for group in self:
            return {
                'name': 'Employees',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.employee.certificate',
                'type': 'ir.actions.act_window',
                'domain': [('name', '=', group.id)],
            }
        pass

    @api.multi
    def _get_employee_count_certificate(self):
        res = self.env['hr.employee.certificate'].search_count([('name', '=', self.id)])
        self.employee_count_certificate = res or 0


 # compute employee certificate
    @api.multi
    def open_employees_cv(self):
        for group in self:
            return {
                'name': 'Employees',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.employee.cv',
                'type': 'ir.actions.act_window',
                'domain': [('name', '=', group.id)],
            }
        pass

    @api.multi
    def _get_employee_count_cv(self):
        res = self.env['hr.employee.cv'].search_count([('name', '=', self.id)])
        self.employee_count_cv = res or 0

