from odoo import api, fields, models, _
from odoo.exceptions import UserError
 
class ProjectTask(models.Model):
    _inherit = "project.task"
        
    date_from = fields.Datetime(string='Planned start', index=True, copy=False)
    date_to = fields.Datetime(string='Planned stop', index=True, copy=False)
    task_type = fields.Selection([
        ('task', 'Task'),
        ('milestone', 'Milestone')
        ], string="Task Type", required=True, default='task')
    color = fields.Integer('Project color', default=4)
    task_link_ids = fields.One2many('task.link', 'task_id', string="Task Links")
    task_priority = fields.Selection([
        ('normal', 'Normal'),
        ('low', 'Low'),        
        ('high', 'High')
    ], string='Priority', required=True, default='normal')

    @api.onchange('date_to')
    def onchange_gantt_stop_date(self):
        if self.date_from and self.date_to and self.date_to < self.date_from:
            self.date_to = self.date_from

    @api.model
    def search_read_links(self, domain=None):
        datas = []
        tasks = self.env['project.task'].search(domain)
        for task in tasks:
            if task.task_link_ids:                
                for link in task.task_link_ids:                    
                    link_vals = {
                        'id' : link.id,
                        'source' : task.id,
                        'target': link.target_task_id.id, 
                        'type': link.link_type,
                    }
                    datas.append(link_vals)
        return datas

class TaskLink(models.Model):
    _name = "task.link"
    _description = "Task Links"

    task_id = fields.Many2one('project.task', string='Task')
    target_task_id = fields.Many2one('project.task', string='Target Task', required=True)
    link_type = fields.Selection([
        ('0', "Finish to Start"), 
        ('1', "Start to Start"), 
        ('2', "Finish to Finish"),
        ('3', "Start to Finish")
        ], string="Link Type", required=True, default='1')