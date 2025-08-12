from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import json


class ProjectTaskManagement(models.Model):
    _inherit = 'project.progress.plan'

    gantt_task_line = fields.One2many('gantt.task', 'project_id', string='Gantt Tasks')

    def action_view_gantt(self):
        self.ensure_one()
        # Get all required view references
        gantt_view = self.env.ref('rnet_project_management.view_task_gantt')
        tree_view = self.env.ref('rnet_project_management.view_task_tree')
        form_view = self.env.ref('rnet_project_management.view_task_form')

        # Find the earliest start_date among gantt tasks for this project
        gantt_tasks = self.gantt_task_line
        initial_date = None
        if gantt_tasks:
            # Filter out tasks without a start_date (use baseline if available, otherwise actual)
            dates = []
            for t in gantt_tasks:
                if t.baseline_start_date:
                    dates.append(t.baseline_start_date)
                elif t.start_date:
                    dates.append(t.start_date)
            if dates:
                initial_date = min(dates)

        context = {
            'default_project_id': self.id,
            'search_default_project_id': self.id,
            'search_default_dummy': 1,  # forces Gantt to load properly
            'default_scale': 'month',  # Set default Gantt scale to 'month'. Options: 'month', 'week', 'year', 'day'
        }
        print("initial_date", initial_date)
        print("context", context)
        if initial_date:
            context['initialDate'] = initial_date.strftime('%Y-%m-%d') if hasattr(initial_date, 'strftime') else str(initial_date)

        # Build domain for project and revision
        domain = [('project_id', '=', self.id)]
        print("domain", domain)

        if hasattr(self, 'revision_id') and self.revision_id:
            domain.append(('revision_id', '=', self.revision_id.id))

        # Check if there are any tasks for this project and revision
        task_count = self.env['gantt.task'].search_count(domain)
        if not task_count:
            # Optionally, show a warning to the user
            raise UserError(_('No tasks found for the selected project and revision. Please add tasks to see them in the Gantt view.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Tasks Gantt'),
            'res_model': 'gantt.task',
            'view_type': 'form',
            'view_mode': 'ganttview,tree,form',
            'views': [
                (gantt_view.id, 'ganttview'),
                (tree_view.id, 'tree'),
                (form_view.id, 'form'),
            ],
            'domain': domain,
            'context': context,
            'target': 'current',
        }


class GanttTask(models.Model):
    _name = 'gantt.task'
    _description = 'Gantt Task with Baseline'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Task Name', required=True)
    project_id = fields.Many2one('project.progress.plan', string='Project', required=True, ondelete='cascade')
    revision_id = fields.Many2one('project.revision', string='Revision', ondelete='set null')
    
    # Baseline dates (original plan)
    baseline_start_date = fields.Date(string='Baseline Start Date')
    baseline_end_date = fields.Date(string='Baseline End Date')
    baseline_duration = fields.Integer(string='Baseline Duration (Days)', compute='_compute_baseline_duration', store=True)
    
    # Actual dates (current/revised plan)
    start_date = fields.Date(string='Actual Start Date', required=True)
    end_date = fields.Date(string='Actual End Date', required=True)
    duration = fields.Integer(string='Actual Duration (Days)', compute='_compute_duration', store=True)
    
    supervisor_id = fields.Many2one('hr.employee', string='Supervisor')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    progress = fields.Float(string='Progress (%)', default=0.0)
    task_type = fields.Selection([
        ('task', 'Task'),
        ('project', 'Project'),
        ('milestone', 'Milestone')
    ], string='Task Type', default='task')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High')
    ], string='Priority', default='1')
    color = fields.Integer(string='Color', default=0)
    deadline = fields.Date(string='Deadline')
    
    # Baseline comparison fields
    is_delayed = fields.Boolean(string='Is Delayed', compute='_compute_delay_status', store=True)
    delay_days = fields.Integer(string='Delay (Days)', compute='_compute_delay_status', store=True)
    
    # Task links for dependencies
    task_link_ids = fields.One2many('gantt.task.link', 'task_id', string='Task Links')

    @api.model
    def search_read_links(self, domain=None):
        """Return links data for gantt view"""
        # Filter domain to only include fields that exist on gantt.task.link model
        link_domain = []
        if domain:
            for condition in domain:
                if isinstance(condition, (list, tuple)) and len(condition) >= 3:
                    field, operator, value = condition[0], condition[1], condition[2]
                    # Map task fields to link model fields
                    if field == 'project_id':
                        link_domain.append(('project_id', operator, value))
                    elif field in ['start_date', 'end_date']:
                        # For date filters, we need to filter through related task fields
                        link_domain.append(('task_id.' + field, operator, value))
                    # Skip other fields that don't apply to links
                else:
                    # Handle logical operators like '&', '|', '!'
                    link_domain.append(condition)
        
        links = self.env['gantt.task.link'].search(link_domain)
        result = []
        for link in links:
            result.append({
                'id': 'gantt_task_' + str(link.id),
                'source': link.task_id.id,
                'target': link.target_task_id.id,
                'type': link.link_type
            })
        return result

    @api.constrains('start_date', 'end_date', 'baseline_start_date', 'baseline_end_date')
    def _check_dates(self):
        for task in self:
            if task.start_date and task.end_date and task.start_date > task.end_date:
                raise ValidationError(_('Actual start date must be before actual end date'))
            if task.baseline_start_date and task.baseline_end_date and task.baseline_start_date > task.baseline_end_date:
                raise ValidationError(_('Baseline start date must be before baseline end date'))

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for task in self:
            if task.start_date and task.end_date:
                delta = fields.Date.from_string(task.end_date) - fields.Date.from_string(task.start_date)
                task.duration = delta.days
            else:
                task.duration = 0
    
    @api.depends('baseline_start_date', 'baseline_end_date')
    def _compute_baseline_duration(self):
        for task in self:
            if task.baseline_start_date and task.baseline_end_date:
                delta = fields.Date.from_string(task.baseline_end_date) - fields.Date.from_string(task.baseline_start_date)
                task.baseline_duration = delta.days
            else:
                task.baseline_duration = 0
    
    @api.depends('start_date', 'end_date', 'baseline_start_date', 'baseline_end_date')
    def _compute_delay_status(self):
        for task in self:
            if task.baseline_end_date and task.end_date:
                baseline_end = fields.Date.from_string(task.baseline_end_date)
                actual_end = fields.Date.from_string(task.end_date)
                delay = (actual_end - baseline_end).days
                task.delay_days = delay
                task.is_delayed = delay > 0
            else:
                task.delay_days = 0
                task.is_delayed = False

    def write(self, vals):
        # Handle datetime conversion for all date fields
        date_fields = ['start_date', 'end_date', 'baseline_start_date', 'baseline_end_date']
        for field in date_fields:
            if field in vals and isinstance(vals[field], datetime):
                vals[field] = vals[field].strftime('%Y-%m-%d')
        return super(GanttTask, self).write(vals)

    @api.model
    def create(self, vals):
        # Handle datetime conversion for all date fields
        date_fields = ['start_date', 'end_date', 'baseline_start_date', 'baseline_end_date']
        for field in date_fields:
            if field in vals and isinstance(vals[field], datetime):
                vals[field] = vals[field].strftime('%Y-%m-%d')
        
        # If baseline dates are not provided, copy from actual dates
        if 'start_date' in vals and 'baseline_start_date' not in vals:
            vals['baseline_start_date'] = vals['start_date']
        if 'end_date' in vals and 'baseline_end_date' not in vals:
            vals['baseline_end_date'] = vals['end_date']
            
        return super(GanttTask, self).create(vals)





class GanttTaskLink(models.Model):
    _name = 'gantt.task.link'
    _description = 'Gantt Task Links'

    task_id = fields.Many2one('gantt.task', string='Task', required=True)
    target_task_id = fields.Many2one('gantt.task', string='Target Task', required=True)
    project_id = fields.Many2one('project.progress.plan', string='Project', readonly=True)
    link_type = fields.Selection([
        ('0', "Finish to Start"),
        ('1', "Start to Start"),
        ('2', "Finish to Finish"),
        ('3', "Start to Finish")
    ], string="Link Type", required=True, default='0')

    @api.model
    def create(self, vals):
        # Set project_id from the task_id when creating the link
        if 'task_id' in vals and not vals.get('project_id'):
            task = self.env['gantt.task'].browse(vals['task_id'])
            if task.exists():
                vals['project_id'] = task.project_id.id
        return super(GanttTaskLink, self).create(vals)

    @api.model
    def clean_orphaned_links(self):
        """Clean up any orphaned or problematic link records"""
        try:
            # Find links with invalid project_id references
            problematic_links = self.search([])
            for link in problematic_links:
                try:
                    # Try to access project_id to see if it causes an error
                    _ = link.project_id
                    # If task exists, update project_id
                    if link.task_id and link.task_id.project_id:
                        link.write({'project_id': link.task_id.project_id.id})
                except Exception:
                    # If there's any error accessing the link, delete it
                    link.unlink()
            return True
        except Exception as e:
            # Log the error but don't fail
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning("Error cleaning orphaned links: %s", str(e))
            return False
