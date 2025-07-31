from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import json


class ProjectTaskManagement(models.Model):
    _inherit = 'project.progress.plan'

    project_plan_task_line = fields.One2many('project.plan.task', 'project_id', string='Plan Tasks')
    project_actual_task_line = fields.One2many('project.actual.task', 'project_id', string='Actual Tasks')

    def action_view_gantt(self):
        self.ensure_one()
        # Get all required view references
        gantt_view = self.env.ref('rnet_project_management.view_task_gantt')
        tree_view = self.env.ref('rnet_project_management.view_task_tree')
        form_view = self.env.ref('rnet_project_management.view_task_form')

        # Find the earliest start_date among plan tasks for this project
        plan_tasks = self.project_plan_task_line
        initial_date = None
        if plan_tasks:
            # Filter out tasks without a start_date
            dates = [t.start_date for t in plan_tasks if t.start_date]
            if dates:
                initial_date = min(dates)

        context = {
            'default_project_id': self.id,
            'search_default_project_id': self.id,
        }
        if initial_date:
            context['initialDate'] = initial_date.strftime('%Y-%m-%d') if hasattr(initial_date, 'strftime') else str(initial_date)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Tasks Gantt'),
            'res_model': 'project.plan.task',
            'view_type': 'form',
            'view_mode': 'ganttview,tree,form',
            'views': [
                (gantt_view.id, 'ganttview'),
                (tree_view.id, 'tree'),
                (form_view.id, 'form'),
            ],
            'domain': [('project_id', '=', self.id)],
            'context': context,
            'target': 'current',
        }


class ProjectPlanTask(models.Model):
    _name = 'project.plan.task'
    _description = 'Project Plan Task'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Task Name', required=True)
    project_id = fields.Many2one('project.progress.plan', string='Project', required=True, ondelete='cascade')
    duration = fields.Integer(string='Duration (Days)', compute='_compute_duration', store=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    supervisor_id = fields.Many2one('hr.employee', string='Supervisor')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    progress = fields.Float(string='Progress (%)', default=0.0)
    # links_serialized_json = fields.Char('Serialized Links JSON', compute='_compute_links_json')
    task_type = fields.Selection([
        ('task', 'Task'),
        ('milestone', 'Milestone')
    ], string='Task Type', default='task')
    baseline_start = fields.Date(string='Baseline Start')
    baseline_end = fields.Date(string='Baseline End')
    task_link_ids = fields.One2many('project.plan.task.link', 'task_id', string='Task Links')

    @api.model
    def search_read_links(self, domain=None):
        datas = []
        tasks = self.env['project.plan.task'].search(domain or [])
        for task in tasks:
            for link in task.task_link_ids:
                if link.target_task_id:
                    datas.append({
                        'id': link.id,
                        'source': task.id,
                        'target': link.target_task_id.id,
                        'type': link.link_type,
                    })
        return datas

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for task in self:
            if task.start_date and task.end_date and task.start_date > task.end_date:
                raise ValidationError(_('Start date must be before end date'))

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for task in self:
            if task.start_date and task.end_date:
                delta = fields.Date.from_string(task.end_date) - fields.Date.from_string(task.start_date)
                task.duration = delta.days
            else:
                task.duration = 0

    def write(self, vals):
        if 'start_date' in vals and isinstance(vals['start_date'], datetime):
            vals['start_date'] = vals['start_date'].strftime('%Y-%m-%d')
        if 'end_date' in vals and isinstance(vals['end_date'], datetime):
            vals['end_date'] = vals['end_date'].strftime('%Y-%m-%d')
        return super(ProjectPlanTask, self).write(vals)

    @api.model
    def create(self, vals):
        if 'start_date' in vals and isinstance(vals['start_date'], datetime):
            vals['start_date'] = vals['start_date'].strftime('%Y-%m-%d')
        if 'end_date' in vals and isinstance(vals['end_date'], datetime):
            vals['end_date'] = vals['end_date'].strftime('%Y-%m-%d')
        return super(ProjectPlanTask, self).create(vals)

    # @api.multi
    # def _compute_links_json(self):
    #     for task in self:
    #         links = []
    #         for predecessor in task.predecessor_ids:
    #             json_obj = {
    #                 'id': str(task.id) + '_' + str(predecessor.id),
    #                 'source': predecessor.id,
    #                 'target': task.id,
    #                 'type': '0'  # Finish to Start by default
    #             }
    #             links.append(json_obj)
    #         task.links_serialized_json = json.dumps(links)


class ProjectPlanTaskLink(models.Model):
    _name = 'project.plan.task.link'
    _description = 'Task Links'

    task_id = fields.Many2one('project.plan.task', string='Task')
    target_task_id = fields.Many2one('project.plan.task', string='Target Task', required=True)
    link_type = fields.Selection([
        ('0', "Finish to Start"),
        ('1', "Start to Start"),
        ('2', "Finish to Finish"),
        ('3', "Start to Finish")
    ], string="Link Type", required=True, default='0')


class ProjectActualTask(models.Model):
    _name = 'project.actual.task'
    _description = 'Project Actual Task'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Task Name', required=True)
    project_id = fields.Many2one('project.progress.plan', string='Project', required=True, ondelete='cascade')
    plan_task_id = fields.Many2one('project.plan.task', string='Plan Task Reference',
                                   domain="[('project_id', '=', project_id)]")
    actual_duration = fields.Integer(string='Actual Duration (Days)', required=True)
    actual_start_date = fields.Date(string='Actual Start Date', required=True)
    actual_end_date = fields.Date(string='Actual End Date', required=True)
    supervisor_id = fields.Many2one('hr.employee', string='Supervisor')
    state = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed')
    ], string='Status', default='not_started')
    progress = fields.Float(string='Progress (%)', default=0.0)
    delay_reason = fields.Text(string='Delay Reason')
    remarks = fields.Text(string='Remarks')

    @api.constrains('actual_start_date', 'actual_end_date')
    def _check_dates(self):
        for task in self:
            if task.actual_start_date and task.actual_end_date and task.actual_start_date > task.actual_end_date:
                raise ValidationError(_('Actual start date must be before actual end date'))

    @api.onchange('plan_task_id')
    def _onchange_plan_task(self):
        if self.plan_task_id:
            self.name = self.plan_task_id.name
            self.supervisor_id = self.plan_task_id.supervisor_id

    @api.onchange('actual_duration', 'actual_start_date')
    def _onchange_duration(self):
        if self.actual_duration and self.actual_start_date:
            end_date = fields.Date.from_string(self.actual_start_date) + timedelta(days=self.actual_duration)
            self.actual_end_date = end_date
