from odoo import models, api, fields


class HrEmployeePenilain(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin'] 
    _name = "hr.employee.penilaian"
    _description = 'Employee Penilaian Kinerja'
   
    def default_reviewer_(self):
        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.id

    employee_id = fields.Many2many('hr.employee', string="Employee", domain=[('status_karyawan','=','PKWT Project')], track_visibility='always')
    penilaian_date = fields.Date(string="Date", track_visibility='always')
    name = fields.Selection([('ok','OK'),('not','NOT')],'Penilaian', track_visibility='always')
    reviewer = fields.Many2one('hr.employee', string="Reviewer", track_visibility='always', readonly=True, default=default_reviewer_)
    project = fields.Many2one('project.project', string="Project", track_visibility='always')

