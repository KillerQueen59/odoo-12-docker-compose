from odoo import api, fields, models, _

class ProjectTask(models.Model):
    _inherit = 'project.task'


    employee_id = fields.Many2one('hr.employee', string='Employee',)