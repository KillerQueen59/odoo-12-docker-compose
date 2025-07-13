from odoo import models, api, fields


class EmployeeGrade(models.Model):
    _name = "employee.grade"


    _sql_constraints = [('code_uniq', 'unique (code)', "Employee Grade code must be unique!"), ]

    code = fields.Char('Code')
    name = fields.Char('Grade')
    alw_out = fields.Float('Allowance Luar Kota', compute='_compute_alw_out_count')
    alw_in = fields.Float('Allowance Dalam Kota', compute='_compute_alw_in_count')
    employee_count = fields.Integer(string='Employee Count', compute='_get_employee_count')
    tunjangan_harian = fields.Float('Tunjangan Harian')
    tunjangan_akomodasi = fields.Float('Tunjangan Akomodasi')
    active = fields.Boolean(default=True)

# get name alw out dan alw in
    def name_get(self):
        result = []
        for record in self:
            if self.env.context.get('out', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id," "+str(record.alw_out)))
            elif self.env.context.get('in', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.alw_in)))
            else:
                result.append((record.id, record.name))
        return result


# compute employee grade
    @api.multi
    def open_employees(self):
        for group in self:
            return {
                'name': 'Employees',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.employee',
                'type': 'ir.actions.act_window',
                'domain': [('employee_grade', '=', group.id)],
            }
        pass

    @api.multi
    def _get_employee_count(self):
        res = self.env['hr.employee'].search_count([('employee_grade', '=', self.id)])
        self.employee_count = res or 0


# compute allowance di luar kota 
    @api.multi
    def _compute_alw_out_count(self):
        for alw in self:
            total = alw.tunjangan_harian + alw.tunjangan_akomodasi
            alw.alw_out = total


# compute allowance di dalam kota 
    @api.multi
    def _compute_alw_in_count(self):
        for alw in self:
            if alw.tunjangan_harian:
                total = (alw.tunjangan_harian * 0.5) + alw.tunjangan_akomodasi
                alw.alw_in = total


# class HrContract(models.Model):
#     _inherit = 'hr.contract'

#     alw_out= fields.Many2one('employee.grade', string='Allowance Luar Kota')
#     alw_in= fields.Many2one('employee.grade', string='Allowance Dalam Kota')
#     wage_hourly = fields.Monetary(string='Hourly', compute='_compute_wage_hourly')


    
# # onchange employee grade
#     @api.onchange('employee_id')
#     def on_change_employee(self):
#         eg = self.employee_id.employee_grade

#         self.alw_out = eg if eg else None
#         self.alw_in = eg if eg else None

# # compute wage hourly
#     @api.multi
#     def _compute_wage_hourly(self):
#         for rec in self:
#             rec.wage_hourly = rec.wage / 173


