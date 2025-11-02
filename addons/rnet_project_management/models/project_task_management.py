from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import json


class ProjectTaskManagement(models.Model):
    _inherit = 'project.progress.plan'

    gantt_task_line = fields.One2many('gantt.task', 'project_id', string='Gantt Tasks')

    def action_sync_all_task_dependencies(self):
        """Bulk sync predecessor/successor for all tasks in this project
        This will create missing links and refresh computed fields"""
        self.ensure_one()

        # First, create any missing links based on text fields
        result = self.gantt_task_line.action_create_missing_links()

        # Then refresh all computed fields
        for task in self.gantt_task_line:
            task._compute_predecessor_successor()

        return result

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
            # Use baseline start_date for initial gantt view positioning
            dates = []
            for t in gantt_tasks:
                if t.start_date:  # Baseline start date (used for main gantt bar)
                    dates.append(t.start_date)
                elif t.actual_start_date:  # Actual start date (used for comparison bar)
                    dates.append(t.actual_start_date)
            if dates:
                initial_date = min(dates)

        context = {
            'default_project_id': self.id,
            'search_default_project_id': self.id,
            'search_default_dummy': 1,  # forces Gantt to load properly
            'default_scale': 'month',  # Set default Gantt scale to 'month'. Options: 'month', 'week', 'year', 'day'
        }
        if initial_date:
            context['initialDate'] = initial_date.strftime('%Y-%m-%d') if hasattr(initial_date, 'strftime') else str(
                initial_date)

        # Build domain for project and revision
        domain = [('project_id', '=', self.id)]

        if hasattr(self, 'revision_id') and self.revision_id:
            domain.append(('revision_id', '=', self.revision_id.id))

        # Allow Gantt view to open even if no tasks exist
        # Users can create tasks directly in the Gantt view

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
    _parent_name = "parent_id"  # ADD THIS
    _parent_store = True  # ADD THIS

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Task Name', required=True)
    project_id = fields.Many2one('project.progress.plan', string='Project', required=True, ondelete='cascade')
    revision_id = fields.Many2one('project.revision', string='Revision', ondelete='set null')

    # UNIQUE TASK ID FOR WBS REFERENCE
    task_id = fields.Char(string='Task ID', required=True, index=True,
                          help='Unique identifier for this task within the project (e.g., T001, T002)')
    parent_task_id = fields.Char(string='Parent Task ID',
                                  help='Enter the Task ID of the parent task to create a hierarchy')

    # ADD THESE HIERARCHY FIELDS
    parent_id = fields.Many2one('gantt.task', string='Parent Task',
                                index=True, ondelete='cascade',
                                domain="[('project_id', '=', project_id), ('task_type', '!=', 'milestone')]")
    child_ids = fields.One2many('gantt.task', 'parent_id', string='Sub-tasks')
    parent_path = fields.Char(index=True)  # Required for _parent_store

    # CHANGED: wbs_code is now editable instead of computed
    wbs_code = fields.Char(string='WBS Code', index=True,
                           help='Enter WBS code (e.g., 1, 1.1, 1.2, 2, 2.1). Parent relationships will be auto-created.')
    level = fields.Integer(string='Level', compute='_compute_level', store=True)

    # Baseline dates (original plan) - Not required for parent tasks
    start_date = fields.Date(string='Baseline Start Date')
    end_date = fields.Date(string='Baseline End Date')
    duration = fields.Integer(string='Baseline Duration (Days)', compute='_compute_duration', store=True)

    # Actual dates (current/revised plan)
    actual_start_date = fields.Date(string='Actual Start Date')
    actual_end_date = fields.Date(string='Actual End Date')
    actual_duration = fields.Integer(string='Actual Duration (Days)', compute='_compute_actual_duration', store=True)

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
        ('milestone', 'Milestone'),
        ('group', 'Group')  # ADD THIS
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

    # Predecessor and Successor fields (comma-separated task IDs)
    predecessor_ids = fields.Char(
        string='Predecessors',
        compute='_compute_predecessor_successor',
        inverse='_inverse_predecessors',
        store=False,
        help='Comma-separated list of predecessor task IDs (tasks that must finish before this task can start)'
    )
    successor_ids = fields.Char(
        string='Successors',
        compute='_compute_predecessor_successor',
        inverse='_inverse_successors',
        store=False,
        help='Comma-separated list of successor task IDs (tasks that depend on this task)'
    )

    # METHOD TO PARSE WBS CODE AND FIND PARENT
    def _get_parent_wbs_code(self, wbs_code):
        """Extract parent WBS code from a given WBS code
        Examples:
        1.1.1 -> 1.1
        1.1 -> 1
        1 -> None (root level)
        """
        if not wbs_code or '.' not in wbs_code:
            return None
        parts = wbs_code.split('.')
        return '.'.join(parts[:-1])

    @api.depends('parent_id')
    def _compute_level(self):
        """Compute hierarchy level"""
        for task in self:
            level = 0
            parent = task.parent_id
            while parent:
                level += 1
                parent = parent.parent_id
            task.level = level

    # ADD THESE CONSTRAINT METHODS
    @api.constrains('wbs_code', 'project_id')
    def _check_unique_wbs_code(self):
        """Ensure wbs_code is unique within the project"""
        for task in self:
            if task.wbs_code and task.project_id:
                duplicate = self.search([
                    ('id', '!=', task.id),
                    ('project_id', '=', task.project_id.id),
                    ('wbs_code', '=', task.wbs_code)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _('WBS Code "%s" already exists in this project. Each task must have a unique WBS Code.') % task.wbs_code
                    )

    @api.constrains('task_id', 'project_id')
    def _check_unique_task_id(self):
        """Ensure task_id is unique within the project"""
        for task in self:
            if task.task_id and task.project_id:
                duplicate = self.search([
                    ('id', '!=', task.id),
                    ('project_id', '=', task.project_id.id),
                    ('task_id', '=', task.task_id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _('Task ID "%s" already exists in this project. Each task must have a unique Task ID.') % task.task_id
                    )

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        """Prevent circular parent references"""
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive task hierarchies.'))

    @api.constrains('parent_id', 'project_id')
    def _check_parent_project(self):
        """Ensure parent task belongs to same project"""
        for task in self:
            if task.parent_id and task.parent_id.project_id != task.project_id:
                raise ValidationError(
                    _('Parent task must belong to the same project.')
                )

    @api.constrains('wbs_code', 'project_id', 'parent_id')
    def _check_wbs_parent_exists(self):
        """Validate that parent WBS code exists when saving
        This runs on Save, not on each row add"""
        for task in self:
            if task.wbs_code and task.project_id:
                parent_wbs = self._get_parent_wbs_code(task.wbs_code)
                if parent_wbs:
                    # Check if parent exists
                    parent = self.search([
                        ('wbs_code', '=', parent_wbs),
                        ('project_id', '=', task.project_id.id),
                        ('id', '!=', task.id)
                    ], limit=1)
                    if not parent:
                        raise ValidationError(
                            _('Parent WBS code "%s" not found. Please create the parent task first or adjust the WBS code "%s".') % (parent_wbs, task.wbs_code)
                        )

    @api.constrains('parent_task_id', 'task_id')
    def _check_parent_task_id_not_self(self):
        """Ensure task cannot reference itself as parent"""
        for task in self:
            if task.parent_task_id and task.task_id and task.parent_task_id == task.task_id:
                raise ValidationError(
                    _('Task cannot be its own parent. Parent Task ID cannot equal Task ID.')
                )

    def unlink(self):
        """Override unlink to warn users before deleting parent tasks with children"""
        for task in self:
            if task.child_ids:
                # Count children
                child_count = len(task.child_ids)
                child_names = ', '.join([c.name for c in task.child_ids[:5]])  # Show first 5
                if child_count > 5:
                    child_names += ', ... and {0} more'.format(child_count - 5)

                raise UserError(
                    _('Cannot delete parent task "%s" (WBS: %s) because it has %d sub-task(s):\n\n%s\n\n'
                      'Please either:\n'
                      '1. Delete all sub-tasks first, or\n'
                      '2. Move sub-tasks to another parent, or\n'
                      '3. Use the "Delete with Sub-tasks" action to delete all at once.') %
                    (task.name, task.wbs_code or task.task_id, child_count, child_names)
                )
        return super(GanttTask, self).unlink()

    def action_delete_with_children(self):
        """Delete this task and all its children (cascade delete)"""
        self.ensure_one()
        if not self.child_ids:
            # No children, just delete normally
            return self.unlink()

        # Count total tasks to be deleted (including nested children)
        def count_all_children(task):
            count = len(task.child_ids)
            for child in task.child_ids:
                count += count_all_children(child)
            return count

        total_count = 1 + count_all_children(self)  # +1 for the task itself

        # Show confirmation with task tree
        def build_tree(task, level=0):
            indent = '  ' * level
            tree = "{0}- {1}: {2}\n".format(indent, task.wbs_code or task.task_id, task.name)
            for child in task.child_ids:
                tree += build_tree(child, level + 1)
            return tree

        task_tree = build_tree(self)

        # Return a confirmation wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('Confirm Cascade Delete'),
            'res_model': 'gantt.task.delete.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.id,
                'default_task_count': total_count,
                'default_task_tree': task_tree,
            }
        }

    def action_delete_cascade_confirmed(self):
        """Actually perform the cascade delete after confirmation"""
        for task in self:
            # Recursively delete all children first
            if task.child_ids:
                # Delete children's children first (recursive)
                task.child_ids.action_delete_cascade_confirmed()
            # Then delete the task itself (bypass normal unlink protection)
            super(GanttTask, task).unlink()

    # ADD THIS METHOD TO AUTO-UPDATE PARENT DATES
    def _update_parent_dates(self):
        """Recursively update parent task dates (both BASELINE and ACTUAL) based on children"""
        for task in self:
            if task.parent_id:
                parent = task.parent_id
                children = parent.child_ids.filtered(lambda c: c.id != False)

                if children:
                    # Calculate min start and max end from all children BASELINE dates
                    baseline_starts = [c.start_date for c in children if c.start_date]
                    baseline_ends = [c.end_date for c in children if c.end_date]

                    # Calculate min start and max end from all children ACTUAL dates
                    actual_starts = [c.actual_start_date for c in children if c.actual_start_date]
                    actual_ends = [c.actual_end_date for c in children if c.actual_end_date]

                    # Update parent dates - BOTH BASELINE AND ACTUAL
                    vals = {}
                    if baseline_starts:
                        vals['start_date'] = min(baseline_starts)
                    if baseline_ends:
                        vals['end_date'] = max(baseline_ends)

                    # Update actual dates from children
                    if actual_starts:
                        vals['actual_start_date'] = min(actual_starts)
                    if actual_ends:
                        vals['actual_end_date'] = max(actual_ends)

                    # Calculate average progress
                    avg_progress = sum(c.progress for c in children) / len(children)
                    vals['progress'] = avg_progress

                    # Auto-set task_type to 'group' or 'project' if has children
                    if parent.task_type not in ['group', 'project']:
                        vals['task_type'] = 'group'

                    if vals:
                        # Use sudo to avoid recursion issues
                        parent.sudo().write(vals)
                        parent._update_parent_dates()  # Recursive update

    @api.model
    def search_read_links(self, domain=None):
        """Return links data for gantt view"""
        # Build a simple domain for links based on project_id only
        link_domain = []
        project_ids = set()

        if domain:
            # Extract project_id values from the domain
            for condition in domain:
                if isinstance(condition, (list, tuple)) and len(condition) >= 3:
                    field, operator, value = condition[0], condition[1], condition[2]
                    if field == 'project_id' and operator == '=':
                        project_ids.add(value)

        # Create a clean domain with unique project_ids
        if project_ids:
            if len(project_ids) == 1:
                link_domain = [('project_id', '=', list(project_ids)[0])]
            else:
                link_domain = [('project_id', 'in', list(project_ids))]

        links = self.env['gantt.task.link'].search(link_domain)
        result = []
        for link in links:
            result.append({
                'id': link.id,  # Use raw link ID, renderer will add prefix
                'source': link.task_id.id,
                'target': link.target_task_id.id,
                'type': link.link_type
            })
        return result

    @api.constrains('start_date', 'end_date', 'actual_start_date', 'actual_end_date', 'child_ids')
    def _check_dates(self):
        for task in self:
            # Baseline dates are required ONLY for leaf tasks (tasks without children)
            if not task.child_ids:
                if not (task.start_date and task.end_date):
                    raise ValidationError(_('Baseline dates (Start Date & End Date) are required for tasks without sub-tasks'))

            # Check baseline dates consistency (if provided)
            if task.start_date and task.end_date and task.start_date > task.end_date:
                raise ValidationError(_('Baseline start date must be before baseline end date'))

            # Check actual dates consistency only if both are provided
            if task.actual_start_date and task.actual_end_date and task.actual_start_date > task.actual_end_date:
                raise ValidationError(_('Actual start date must be before actual end date'))

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for task in self:
            if task.start_date and task.end_date:
                delta = fields.Date.from_string(task.end_date) - fields.Date.from_string(task.start_date)
                task.duration = delta.days
            else:
                task.duration = 0

    @api.depends('actual_end_date', 'actual_start_date')
    def _compute_actual_duration(self):
        for task in self:
            if task.actual_start_date and task.actual_end_date:
                delta = fields.Date.from_string(task.actual_end_date) - fields.Date.from_string(task.actual_start_date)
                task.actual_duration = delta.days
            else:
                task.actual_duration = 0

    @api.depends('start_date', 'end_date', 'actual_start_date', 'actual_end_date')
    def _compute_delay_status(self):
        for task in self:
            if task.end_date and task.actual_end_date:
                baseline_end = fields.Date.from_string(task.end_date)
                actual_end = fields.Date.from_string(task.actual_end_date)
                delay = (actual_end - baseline_end).days
                task.delay_days = delay
                task.is_delayed = delay > 0
            else:
                task.delay_days = 0
                task.is_delayed = False

    @api.depends('task_link_ids', 'task_link_ids.target_task_id')
    def _compute_predecessor_successor(self):
        """Compute predecessor and successor task IDs from task links"""
        for task in self:
            # Get predecessors (tasks that link TO this task - this task depends on them)
            predecessor_links = self.env['gantt.task.link'].search([
                ('target_task_id', '=', task.id),
                ('link_type', '=', '0')  # Finish to Start
            ])
            # Filter out any deleted/non-existent records
            predecessors = [link.task_id.task_id for link in predecessor_links.exists() if link.task_id.exists()]
            task.predecessor_ids = ', '.join(predecessors) if predecessors else ''

            # Get successors (tasks that this task links TO - they depend on this task)
            # Use exists() to filter out deleted records
            successor_links = task.task_link_ids.exists().filtered(lambda l: l.link_type == '0')
            successors = [link.target_task_id.task_id for link in successor_links if link.target_task_id.exists()]
            task.successor_ids = ', '.join(successors) if successors else ''

    def _inverse_predecessors(self):
        """Update task links when predecessor_ids is modified"""
        for task in self:
            # Skip if task is not yet created (no ID)
            if not task.id:
                continue

            # Get existing predecessor links (where this task is the target)
            existing_links = self.env['gantt.task.link'].search([
                ('target_task_id', '=', task.id),
                ('link_type', '=', '0')
            ])

            # Parse new predecessor task IDs
            new_predecessor_task_ids = []
            if task.predecessor_ids:
                new_predecessor_task_ids = [tid.strip() for tid in task.predecessor_ids.split(',') if tid.strip()]

                # Check for duplicates within the same field
                if len(new_predecessor_task_ids) != len(set(new_predecessor_task_ids)):
                    duplicates = [tid for tid in new_predecessor_task_ids if new_predecessor_task_ids.count(tid) > 1]
                    raise ValidationError(
                        _('Duplicate predecessor task IDs found: %s') % ', '.join(set(duplicates))
                    )

            # Build set of existing predecessor task IDs from links
            existing_pred_task_ids = set()
            links_to_keep = self.env['gantt.task.link']
            for link in existing_links.exists():
                if link.task_id and link.task_id.exists():
                    existing_pred_task_ids.add(link.task_id.task_id)
                    links_to_keep |= link

            # Determine which links to delete (no longer in the new list)
            links_to_delete = self.env['gantt.task.link']
            for link in links_to_keep:
                if link.task_id.task_id not in new_predecessor_task_ids:
                    links_to_delete |= link

            # Delete obsolete links
            if links_to_delete:
                links_to_delete.unlink()

            # Create new predecessor links (only for new ones)
            missing_tasks = []
            for pred_task_id in new_predecessor_task_ids:
                # Skip if link already exists
                if pred_task_id in existing_pred_task_ids:
                    continue

                # Validate task is not linking to itself
                if pred_task_id == task.task_id:
                    raise ValidationError(
                        _('Task "%s" cannot be its own predecessor.') % task.task_id
                    )

                # Find the predecessor task
                pred_task = self.search([
                    ('task_id', '=', pred_task_id),
                    ('project_id', '=', task.project_id.id)
                ], limit=1)

                if pred_task:
                    # Check if opposite link already exists (circular dependency)
                    opposite_link = self.env['gantt.task.link'].search([
                        ('task_id', '=', task.id),
                        ('target_task_id', '=', pred_task.id),
                        ('link_type', '=', '0')
                    ], limit=1)

                    if opposite_link:
                        raise ValidationError(
                            _('Conflicting link detected: Task "%s" already links to "%s". '
                              'Cannot create opposite link (circular dependency).') %
                            (task.task_id, pred_task_id)
                        )

                    # Create the link (predecessor -> this task)
                    self.env['gantt.task.link'].create({
                        'task_id': pred_task.id,
                        'target_task_id': task.id,
                        'link_type': '0',  # Finish to Start
                        'project_id': task.project_id.id
                    })
                else:
                    # Task not found - collect for warning message
                    missing_tasks.append(pred_task_id)

            # If there are missing tasks, show a warning but don't fail
            if missing_tasks:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(
                    'Task "%s": Predecessor task(s) not found: %s. '
                    'Create the missing tasks first, then use "Sync Task Dependencies" button to create links.' %
                    (task.task_id, ', '.join(missing_tasks))
                )

    def _inverse_successors(self):
        """Update task links when successor_ids is modified"""
        for task in self:
            # Skip if task is not yet created (no ID)
            if not task.id:
                continue

            # Get existing successor links (where this task is the source)
            existing_links = self.env['gantt.task.link'].search([
                ('task_id', '=', task.id),
                ('link_type', '=', '0')
            ])

            # Parse new successor task IDs
            new_successor_task_ids = []
            if task.successor_ids:
                new_successor_task_ids = [tid.strip() for tid in task.successor_ids.split(',') if tid.strip()]

                # Check for duplicates within the same field
                if len(new_successor_task_ids) != len(set(new_successor_task_ids)):
                    duplicates = [tid for tid in new_successor_task_ids if new_successor_task_ids.count(tid) > 1]
                    raise ValidationError(
                        _('Duplicate successor task IDs found: %s') % ', '.join(set(duplicates))
                    )

            # Build set of existing successor task IDs from links
            existing_succ_task_ids = set()
            links_to_keep = self.env['gantt.task.link']
            for link in existing_links.exists():
                if link.target_task_id and link.target_task_id.exists():
                    existing_succ_task_ids.add(link.target_task_id.task_id)
                    links_to_keep |= link

            # Determine which links to delete (no longer in the new list)
            links_to_delete = self.env['gantt.task.link']
            for link in links_to_keep:
                if link.target_task_id.task_id not in new_successor_task_ids:
                    links_to_delete |= link

            # Delete obsolete links
            if links_to_delete:
                links_to_delete.unlink()

            # Create new successor links (only for new ones)
            missing_tasks = []
            for succ_task_id in new_successor_task_ids:
                # Skip if link already exists
                if succ_task_id in existing_succ_task_ids:
                    continue

                # Validate task is not linking to itself
                if succ_task_id == task.task_id:
                    raise ValidationError(
                        _('Task "%s" cannot be its own successor.') % task.task_id
                    )

                # Find the successor task
                succ_task = self.search([
                    ('task_id', '=', succ_task_id),
                    ('project_id', '=', task.project_id.id)
                ], limit=1)

                if succ_task:
                    # Check if opposite link already exists (circular dependency)
                    opposite_link = self.env['gantt.task.link'].search([
                        ('task_id', '=', succ_task.id),
                        ('target_task_id', '=', task.id),
                        ('link_type', '=', '0')
                    ], limit=1)

                    if opposite_link:
                        raise ValidationError(
                            _('Conflicting link detected: Task "%s" already links to "%s". '
                              'Cannot create opposite link (circular dependency).') %
                            (succ_task_id, task.task_id)
                        )

                    # Create the link (this task -> successor)
                    self.env['gantt.task.link'].create({
                        'task_id': task.id,
                        'target_task_id': succ_task.id,
                        'link_type': '0',  # Finish to Start
                        'project_id': task.project_id.id
                    })
                else:
                    # Task not found - collect for warning message
                    missing_tasks.append(succ_task_id)

            # If there are missing tasks, show a warning but don't fail
            if missing_tasks:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(
                    'Task "%s": Successor task(s) not found: %s. '
                    'Create the missing tasks first, then use "Sync Task Dependencies" button to create links.' %
                    (task.task_id, ', '.join(missing_tasks))
                )

    def write(self, vals):
        # Resolve wbs_code to parent_id before write (takes priority)
        if 'wbs_code' in vals and vals['wbs_code']:
            for task in self:
                parent_wbs = self._get_parent_wbs_code(vals['wbs_code'].strip())
                if parent_wbs:
                    parent = self.search([
                        ('wbs_code', '=', parent_wbs),
                        ('project_id', '=', task.project_id.id),
                        ('id', '!=', task.id)
                    ], limit=1)
                    if parent:
                        vals['parent_id'] = parent.id
                        vals['parent_task_id'] = parent.task_id
                    # If parent not found, don't raise error here - let constraint handle it
                    # This allows users to add rows first, then validate on save
                else:
                    # Root level task
                    vals['parent_id'] = False
                    vals['parent_task_id'] = False

        # Resolve parent_task_id to parent_id before write (if wbs_code not provided)
        elif 'parent_task_id' in vals:
            for task in self:
                if vals['parent_task_id']:
                    parent = self.search([
                        ('task_id', '=', vals['parent_task_id']),
                        ('project_id', '=', task.project_id.id)
                    ], limit=1)
                    if parent:
                        vals['parent_id'] = parent.id
                    # Don't raise error here - let constraint handle it on save
                else:
                    vals['parent_id'] = False

        # Auto-set progress to 100% when status is set to done
        if 'state' in vals and vals['state'] == 'done':
            vals['progress'] = 100.0

        # Handle datetime conversion for all date fields
        date_fields = ['start_date', 'end_date', 'actual_start_date', 'actual_end_date']
        for field in date_fields:
            if field in vals and isinstance(vals[field], datetime):
                vals[field] = vals[field].strftime('%Y-%m-%d')

        result = super(GanttTask, self).write(vals)

        # Note: Links are now allowed for both parent and leaf tasks
        # No automatic link removal when a task becomes a parent

        # Update parent dates if any date fields were changed
        date_fields_changed = {'start_date', 'end_date', 'actual_start_date', 'actual_end_date', 'progress'}
        if any(field in vals for field in date_fields_changed):
            self._update_parent_dates()

        return result

    @api.model
    def create(self, vals):
        # Resolve wbs_code to parent_id before create (takes priority)
        if 'wbs_code' in vals and vals['wbs_code']:
            project_id = vals.get('project_id')
            if project_id:
                parent_wbs = self._get_parent_wbs_code(vals['wbs_code'].strip())
                if parent_wbs:
                    parent = self.search([
                        ('wbs_code', '=', parent_wbs),
                        ('project_id', '=', project_id)
                    ], limit=1)
                    if parent:
                        vals['parent_id'] = parent.id
                        vals['parent_task_id'] = parent.task_id
                    # If parent not found, continue without error - constraint validation will handle it
                    # This allows users to add multiple rows first, then validate on save
                else:
                    # Root level task
                    vals['parent_id'] = False

        # Resolve parent_task_id to parent_id before create (if wbs_code not provided)
        elif 'parent_task_id' in vals and vals['parent_task_id']:
            # Get project_id from vals or use default
            project_id = vals.get('project_id')
            if project_id:
                parent = self.search([
                    ('task_id', '=', vals['parent_task_id']),
                    ('project_id', '=', project_id)
                ], limit=1)
                if parent:
                    vals['parent_id'] = parent.id
                # Don't raise error here - let constraint handle it on save

        # Handle datetime conversion for all date fields
        date_fields = ['start_date', 'end_date', 'actual_start_date', 'actual_end_date']
        for field in date_fields:
            if field in vals and isinstance(vals[field], datetime):
                vals[field] = vals[field].strftime('%Y-%m-%d')

        # If actual dates are not provided but baseline dates are, copy from baseline dates
        # This is helpful for new tasks
        if 'start_date' in vals and 'actual_start_date' not in vals:
            vals['actual_start_date'] = vals['start_date']
        if 'end_date' in vals and 'actual_end_date' not in vals:
            vals['actual_end_date'] = vals['end_date']

        return super(GanttTask, self).create(vals)

    @api.onchange('wbs_code')
    def _onchange_wbs_code(self):
        """Auto-resolve parent based on WBS code hierarchy
        Examples:
        - If you enter '1.1', it will find the task with WBS '1' as parent
        - If you enter '1.1.2', it will find the task with WBS '1.1' as parent
        - If you enter '1', it will have no parent (root level)

        NOTE: This only tries to auto-link parent. Validation happens on Save.
        """
        if self.wbs_code and self.project_id:
            # Clean up WBS code (remove extra spaces)
            self.wbs_code = self.wbs_code.strip()

            # Get parent WBS code
            parent_wbs = self._get_parent_wbs_code(self.wbs_code)

            if parent_wbs:
                # Find parent task with this WBS code
                parent = self.search([
                    ('wbs_code', '=', parent_wbs),
                    ('project_id', '=', self.project_id.id),
                    ('id', '!=', self.id or 0)  # Exclude self
                ], limit=1)

                if parent:
                    self.parent_id = parent.id
                    # Also update parent_task_id for consistency
                    self.parent_task_id = parent.task_id
                else:
                    # Parent WBS not found - clear parent but keep WBS code
                    # Don't show error here - let user add multiple rows first
                    # Validation will happen when they click Save
                    self.parent_id = False
                    self.parent_task_id = False
            else:
                # Root level task (no parent)
                self.parent_id = False
                self.parent_task_id = False

    @api.onchange('parent_task_id')
    def _onchange_parent_task_id(self):
        """Auto-resolve parent_task_id to parent_id

        NOTE: This only tries to auto-link parent. Validation happens on Save.
        """
        if self.parent_task_id and self.project_id:
            parent = self.search([
                ('task_id', '=', self.parent_task_id),
                ('project_id', '=', self.project_id.id)
            ], limit=1)
            if parent:
                self.parent_id = parent.id
            else:
                # Clear parent_id if parent_task_id doesn't match any task
                # Don't show warning - validation will happen on Save
                self.parent_id = False
        elif not self.parent_task_id:
            self.parent_id = False

    @api.onchange('start_date')
    def _onchange_baseline_start_date(self):
        """Auto-fill baseline end date when baseline start date is selected"""
        if self.start_date and not self.end_date:
            self.end_date = self.start_date

    @api.onchange('actual_start_date')
    def _onchange_actual_start_date(self):
        """Auto-fill actual end date when actual start date is selected"""
        if self.actual_start_date and not self.actual_end_date:
            self.actual_end_date = self.actual_start_date

    def action_sync_predecessor_successor(self):
        """Manually trigger recompute of predecessor/successor fields
        Useful for syncing existing data or refreshing the display"""
        for task in self:
            task._compute_predecessor_successor()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronized'),
                'message': _('Predecessor and Successor fields have been updated from links.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_create_missing_links(self):
        """Create missing task links based on predecessor_ids and successor_ids text fields
        This is useful after creating multiple tasks at once where some predecessors/successors
        didn't exist yet during initial save."""
        links_created = 0
        errors = []

        for task in self:
            # Process predecessors
            if task.predecessor_ids:
                predecessor_task_ids = [tid.strip() for tid in task.predecessor_ids.split(',') if tid.strip()]
                for pred_task_id in predecessor_task_ids:
                    pred_task = self.search([
                        ('task_id', '=', pred_task_id),
                        ('project_id', '=', task.project_id.id)
                    ], limit=1)

                    if pred_task:
                        # Check if link already exists
                        existing_link = self.env['gantt.task.link'].search([
                            ('task_id', '=', pred_task.id),
                            ('target_task_id', '=', task.id),
                            ('link_type', '=', '0')
                        ], limit=1)

                        if not existing_link:
                            self.env['gantt.task.link'].create({
                                'task_id': pred_task.id,
                                'target_task_id': task.id,
                                'link_type': '0',
                                'project_id': task.project_id.id
                            })
                            links_created += 1
                    else:
                        errors.append(_('Task %s: Predecessor %s not found') % (task.task_id, pred_task_id))

            # Process successors
            if task.successor_ids:
                successor_task_ids = [tid.strip() for tid in task.successor_ids.split(',') if tid.strip()]
                for succ_task_id in successor_task_ids:
                    succ_task = self.search([
                        ('task_id', '=', succ_task_id),
                        ('project_id', '=', task.project_id.id)
                    ], limit=1)

                    if succ_task:
                        # Check if link already exists
                        existing_link = self.env['gantt.task.link'].search([
                            ('task_id', '=', task.id),
                            ('target_task_id', '=', succ_task.id),
                            ('link_type', '=', '0')
                        ], limit=1)

                        if not existing_link:
                            self.env['gantt.task.link'].create({
                                'task_id': task.id,
                                'target_task_id': succ_task.id,
                                'link_type': '0',
                                'project_id': task.project_id.id
                            })
                            links_created += 1
                    else:
                        errors.append(_('Task %s: Successor %s not found') % (task.task_id, succ_task_id))

        # Refresh the computed fields after creating links
        self._compute_predecessor_successor()

        message = _('%d link(s) created successfully.') % links_created
        if errors:
            message += '\n\n' + _('Errors:') + '\n- ' + '\n- '.join(errors[:10])
            if len(errors) > 10:
                message += '\n- ... and %d more errors' % (len(errors) - 10)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Complete'),
                'message': message,
                'type': 'success' if not errors else 'warning',
                'sticky': True if errors else False,
            }
        }


class GanttTaskLink(models.Model):
    _name = 'gantt.task.link'
    _description = 'Gantt Task Links'

    task_id = fields.Many2one('gantt.task', string='Task', required=True, ondelete='cascade')
    target_task_id = fields.Many2one('gantt.task', string='Target Task', required=True, ondelete='cascade')
    project_id = fields.Many2one('project.progress.plan', string='Project', readonly=True, ondelete='cascade')
    link_type = fields.Selection([
        ('0', "Finish to Start"),
        ('1', "Start to Start"),
        ('2', "Finish to Finish"),
        ('3', "Start to Finish")
    ], string="Link Type", required=True, default='0')

    @api.constrains('task_id', 'target_task_id')
    def _check_circular_dependency(self):
        """Prevent circular dependencies in task links"""
        for link in self:
            if link.task_id.id == link.target_task_id.id:
                raise ValidationError(_('Cannot create a link from a task to itself.'))

    def write(self, vals):
        """Override write to trigger recompute on related tasks"""
        result = super(GanttTaskLink, self).write(vals)

        # Trigger recompute of predecessor/successor fields for affected tasks
        for link in self:
            if link.task_id:
                link.task_id._compute_predecessor_successor()
            if link.target_task_id:
                link.target_task_id._compute_predecessor_successor()

        return result

    def unlink(self):
        """Override unlink to trigger recompute before deletion"""
        # Store task references before unlinking
        tasks_to_recompute = set()
        for link in self:
            if link.task_id:
                tasks_to_recompute.add(link.task_id.id)
            if link.target_task_id:
                tasks_to_recompute.add(link.target_task_id.id)

        result = super(GanttTaskLink, self).unlink()

        # Trigger recompute after deletion
        if tasks_to_recompute:
            tasks = self.env['gantt.task'].browse(list(tasks_to_recompute))
            tasks._compute_predecessor_successor()

        return result

    @api.model
    def create(self, vals):
        # Set project_id from the task_id when creating the link
        if 'task_id' in vals and not vals.get('project_id'):
            task = self.env['gantt.task'].browse(vals['task_id'])
            if task.exists():
                vals['project_id'] = task.project_id.id

        link = super(GanttTaskLink, self).create(vals)

        # Trigger recompute of predecessor/successor fields for both tasks
        if link.task_id:
            link.task_id._compute_predecessor_successor()
        if link.target_task_id:
            link.target_task_id._compute_predecessor_successor()

        return link

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

