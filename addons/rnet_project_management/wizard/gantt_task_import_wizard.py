# -*- coding: utf-8 -*-

import base64
import csv
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class GanttTaskImportWizard(models.TransientModel):
    _name = 'gantt.task.import.wizard'
    _description = 'Import Gantt Tasks from CSV'

    project_id = fields.Many2one('project.progress.plan', string='Project', required=True)
    csv_file = fields.Binary(string='CSV File', help='Upload CSV file to import tasks', attachment=False)
    filename = fields.Char(string='Filename')
    date_format = fields.Selection([
        ('ymd', 'YYYY-MM-DD (Year-Month-Day)'),
        ('ydm', 'YYYY-DD-MM (Year-Day-Month)'),
    ], default='ymd', string='Date Format in CSV', required=True,
        help='Select the date format used in your CSV file')
    state = fields.Selection([
        ('draft', 'Upload File'),
        ('validate', 'Validation Results'),
        ('done', 'Import Complete')
    ], default='draft', string='State')

    # Validation results
    validation_message = fields.Html(string='Validation Results', readonly=True)
    has_errors = fields.Boolean(string='Has Errors', default=False)
    total_rows = fields.Integer(string='Total Rows', readonly=True)
    valid_rows = fields.Integer(string='Valid Rows', readonly=True)
    error_rows = fields.Integer(string='Error Rows', readonly=True)

    def _parse_date(self, date_str):
        """Parse date string according to selected format and return date object"""
        if not date_str:
            return None
        date_str = date_str.strip()
        if not date_str:
            return None

        try:
            if self.date_format == 'ydm':
                # YYYY-DD-MM format - parse and convert
                parsed = datetime.strptime(date_str, '%Y-%d-%m').date()
            else:
                # YYYY-MM-DD format (default)
                parsed = datetime.strptime(date_str, '%Y-%m-%d').date()
            return parsed
        except ValueError:
            return None

    @api.multi
    def action_validate_csv(self):
        """Validate the CSV file and show validation results"""
        self.ensure_one()

        if not self.csv_file:
            raise UserError(_('Please upload a CSV file first.'))

        # Decode the file
        try:
            csv_data = base64.b64decode(self.csv_file)
            csv_file = io.StringIO(csv_data.decode('utf-8'))
            reader = csv.DictReader(csv_file)
        except Exception as e:
            raise UserError(_('Error reading CSV file: %s') % str(e))

        # Validate and collect errors
        errors = []
        warnings = []
        valid_count = 0
        row_num = 1  # Start from 1 (header is 0)

        # Required and optional columns
        required_columns = ['task_id', 'name', 'task_type', 'start_date', 'end_date']
        optional_columns = [
            'wbs_code', 'supervisor_id', 'actual_start_date', 'actual_end_date',
            'progress', 'state', 'priority', 'predecessor_ids', 'successor_ids'
        ]
        all_expected_columns = required_columns + optional_columns

        # Check if all required columns are present
        if reader.fieldnames:
            missing_required = set(required_columns) - set(reader.fieldnames)
            extra_columns = set(reader.fieldnames) - set(all_expected_columns)

            if missing_required:
                errors.append({
                    'row': 0,
                    'type': 'error',
                    'message': _('Missing required columns: %s') % ', '.join(missing_required)
                })

            if extra_columns:
                warnings.append({
                    'row': 0,
                    'type': 'warning',
                    'message': _('Extra columns will be ignored: %s') % ', '.join(extra_columns)
                })
        else:
            raise UserError(_('CSV file is empty or has no header row.'))

        # Validate each row
        task_ids_seen = set()
        wbs_codes_seen = set()

        for row in reader:
            row_num += 1
            row_errors = []

            # 1. Validate task_id (required, unique)
            task_id = row.get('task_id', '').strip()
            if not task_id:
                row_errors.append('task_id is required')
            elif task_id in task_ids_seen:
                row_errors.append('Duplicate task_id: {}'.format(task_id))
            else:
                task_ids_seen.add(task_id)
                # Check if task_id already exists in database for this project
                existing = self.env['gantt.task'].search([
                    ('task_id', '=', task_id),
                    ('project_id', '=', self.project_id.id)
                ], limit=1)
                if existing:
                    row_errors.append('task_id "{}" already exists in project'.format(task_id))

            # 2. Validate wbs_code (optional but must be unique if provided)
            wbs_code = row.get('wbs_code', '').strip()
            if wbs_code:
                if wbs_code in wbs_codes_seen:
                    row_errors.append('Duplicate wbs_code: {}'.format(wbs_code))
                else:
                    wbs_codes_seen.add(wbs_code)
                    # Check if wbs_code already exists
                    existing = self.env['gantt.task'].search([
                        ('wbs_code', '=', wbs_code),
                        ('project_id', '=', self.project_id.id)
                    ], limit=1)
                    if existing:
                        row_errors.append('wbs_code "{}" already exists in project'.format(wbs_code))

            # 3. Validate name (required)
            name = row.get('name', '').strip()
            if not name:
                row_errors.append('name is required')

            # 4. Validate supervisor_id (optional, must exist if provided)
            supervisor_id = row.get('supervisor_id', '').strip()
            if supervisor_id:
                # Try to find by name or login
                supervisor = self.env['res.users'].search([
                    '|', ('name', '=ilike', supervisor_id),
                    ('login', '=', supervisor_id)
                ], limit=1)
                if not supervisor:
                    row_errors.append('Supervisor "{}" not found'.format(supervisor_id))

            # 5. Validate task_type (required, must be valid value)
            task_type = row.get('task_type', '').strip()
            valid_task_types = ['task', 'milestone', 'group', 'project']
            if not task_type:
                row_errors.append('task_type is required')
            elif task_type not in valid_task_types:
                row_errors.append('task_type must be one of: {}'.format(", ".join(valid_task_types)))

            # 6. Validate dates based on selected format
            date_fields = ['actual_start_date', 'actual_end_date', 'start_date', 'end_date']
            parsed_dates = {}
            date_format_label = 'YYYY-DD-MM' if self.date_format == 'ydm' else 'YYYY-MM-DD'
            for date_field in date_fields:
                date_str = row.get(date_field, '').strip()
                if date_str:
                    parsed_date = self._parse_date(date_str)
                    if parsed_date:
                        parsed_dates[date_field] = parsed_date
                    else:
                        row_errors.append('{} must be in format {}, got: {}'.format(date_field, date_format_label, date_str))

            # 7. Validate date logic
            if 'start_date' in parsed_dates and 'end_date' in parsed_dates:
                if parsed_dates['start_date'] > parsed_dates['end_date']:
                    row_errors.append('start_date must be before end_date')

            if 'actual_start_date' in parsed_dates and 'actual_end_date' in parsed_dates:
                if parsed_dates['actual_start_date'] > parsed_dates['actual_end_date']:
                    row_errors.append('actual_start_date must be before actual_end_date')

            # 8. Validate progress (0-100)
            progress_str = row.get('progress', '').strip()
            if progress_str:
                try:
                    progress = float(progress_str)
                    if progress < 0 or progress > 100:
                        row_errors.append('progress must be between 0 and 100')
                except ValueError:
                    row_errors.append('progress must be a number, got: {}'.format(progress_str))

            # 9. Validate state (optional, must be valid value)
            state = row.get('state', '').strip()
            valid_states = ['draft', 'in_progress', 'done', 'cancelled']
            if state and state not in valid_states:
                row_errors.append('state must be one of: {} or empty'.format(", ".join(valid_states)))

            # 10. Validate priority (optional, must be valid value)
            priority = row.get('priority', '').strip()
            valid_priorities = ['0', '1', '2', '3']
            if priority and priority not in valid_priorities:
                row_errors.append('priority must be one of: {} (0=Low, 1=Normal, 2=High, 3=Very High)'.format(", ".join(valid_priorities)))

            # 11. Validate predecessor_ids (optional, comma-separated task IDs)
            predecessor_ids = row.get('predecessor_ids', '').strip()
            if predecessor_ids:
                pred_ids = [pid.strip() for pid in predecessor_ids.split(',') if pid.strip()]

                # Check for duplicates within predecessor_ids
                if len(pred_ids) != len(set(pred_ids)):
                    duplicates = [pid for pid in pred_ids if pred_ids.count(pid) > 1]
                    row_errors.append('Duplicate predecessor IDs: {}'.format(', '.join(set(duplicates))))

                for pred_id in pred_ids:
                    if pred_id == task_id:
                        row_errors.append('Task cannot be its own predecessor: {}'.format(pred_id))
                    # Note: We'll check if predecessor task IDs exist in the second pass during import
                    # since they might be defined later in the CSV

            # 12. Validate successor_ids (optional, comma-separated task IDs)
            successor_ids = row.get('successor_ids', '').strip()
            if successor_ids:
                succ_ids = [sid.strip() for sid in successor_ids.split(',') if sid.strip()]

                # Check for duplicates within successor_ids
                if len(succ_ids) != len(set(succ_ids)):
                    duplicates = [sid for sid in succ_ids if succ_ids.count(sid) > 1]
                    row_errors.append('Duplicate successor IDs: {}'.format(', '.join(set(duplicates))))

                for succ_id in succ_ids:
                    if succ_id == task_id:
                        row_errors.append('Task cannot be its own successor: {}'.format(succ_id))
                    # Check for circular dependencies (predecessor and successor)
                    if predecessor_ids:
                        pred_ids = [pid.strip() for pid in predecessor_ids.split(',') if pid.strip()]
                        if succ_id in pred_ids:
                            row_errors.append('Circular dependency: {} is both predecessor and successor'.format(succ_id))

            # Add row errors to main errors list
            if row_errors:
                errors.append({
                    'row': row_num,
                    'type': 'error',
                    'task_id': task_id or 'N/A',
                    'message': '; '.join(row_errors)
                })
            else:
                valid_count += 1

        # Generate validation message HTML
        total_rows = row_num - 1  # Exclude header
        error_count = len([e for e in errors if e['type'] == 'error'])
        warning_count = len([w for w in warnings if w['type'] == 'warning'])

        html_message = '<div style="font-family: Arial, sans-serif;">'

        # Summary
        html_message += '<h3>Validation Summary</h3>'
        html_message += '<p><strong>Total Rows:</strong> {}</p>'.format(total_rows)
        html_message += '<p><strong>Valid Rows:</strong> <span style="color: green;">{}</span></p>'.format(valid_count)
        html_message += '<p><strong>Error Rows:</strong> <span style="color: red;">{}</span></p>'.format(error_count)

        if warning_count > 0:
            html_message += '<p><strong>Warnings:</strong> <span style="color: orange;">{}</span></p>'.format(warning_count)

        # Warnings
        if warnings:
            html_message += '<h4 style="color: orange;">⚠ Warnings</h4>'
            html_message += '<ul style="color: orange;">'
            for warning in warnings:
                html_message += '<li>{}</li>'.format(warning["message"])
            html_message += '</ul>'

        # Errors
        if errors:
            html_message += '<h4 style="color: red;">❌ Errors</h4>'
            html_message += '<div style="overflow-x: auto; max-width: 100%;">'
            html_message += '<table style="width: 100%; border-collapse: collapse; min-width: 500px;">'
            html_message += '<tr style="background-color: #f2f2f2;">'
            html_message += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Row</th>'
            html_message += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Task ID</th>'
            html_message += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Error Details</th>'
            html_message += '</tr>'

            for error in errors:
                if error['type'] == 'error':
                    html_message += '<tr>'
                    html_message += '<td style="border: 1px solid #ddd; padding: 8px;">{}</td>'.format(error["row"])
                    html_message += '<td style="border: 1px solid #ddd; padding: 8px;">{}</td>'.format(error.get("task_id", "N/A"))
                    html_message += '<td style="border: 1px solid #ddd; padding: 8px; color: red; word-wrap: break-word;">{}</td>'.format(error["message"])
                    html_message += '</tr>'

            html_message += '</table>'
            html_message += '</div>'
        else:
            html_message += '<p style="color: green; font-size: 16px;">✅ All rows are valid and ready to import!</p>'

        html_message += '</div>'

        # Update wizard state
        self.write({
            'state': 'validate',
            'validation_message': html_message,
            'has_errors': error_count > 0,
            'total_rows': total_rows,
            'valid_rows': valid_count,
            'error_rows': error_count
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gantt.task.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context
        }

    @api.multi
    def action_import_tasks(self):
        """Import tasks from validated CSV"""
        self.ensure_one()

        if self.has_errors:
            raise UserError(_('Cannot import tasks with validation errors. Please fix the errors and try again.'))

        if not self.csv_file:
            raise UserError(_('Please upload a CSV file first.'))

        # Decode the file
        try:
            csv_data = base64.b64decode(self.csv_file)
            csv_file = io.StringIO(csv_data.decode('utf-8'))
            reader = csv.DictReader(csv_file)
        except Exception as e:
            raise UserError(_('Error reading CSV file: %s') % str(e))

        # Import tasks
        created_tasks = []
        task_map = {}  # Map task_id to record for parent resolution
        task_links_data = []  # Store link data for second pass

        # First pass: Create all tasks
        for row in reader:
            task_id = row.get('task_id', '').strip()
            if not task_id:
                continue

            # Prepare values
            vals = {
                'project_id': self.project_id.id,
                'task_id': task_id,
                'name': row.get('name', '').strip(),
                'wbs_code': row.get('wbs_code', '').strip() or False,
                'task_type': row.get('task_type', 'task').strip(),
                'state': row.get('state', 'draft').strip() or 'draft',
                'priority': row.get('priority', '1').strip() or '1',
            }

            # Supervisor
            supervisor_id = row.get('supervisor_id', '').strip()
            if supervisor_id:
                supervisor = self.env['res.users'].search([
                    '|', ('name', '=ilike', supervisor_id),
                    ('login', '=', supervisor_id)
                ], limit=1)
                if supervisor:
                    vals['supervisor_id'] = supervisor.id

            # Dates - use selected format
            for date_field in ['actual_start_date', 'actual_end_date', 'start_date', 'end_date']:
                date_str = row.get(date_field, '').strip()
                if date_str:
                    parsed_date = self._parse_date(date_str)
                    if parsed_date:
                        vals[date_field] = parsed_date

            # Progress
            progress_str = row.get('progress', '').strip()
            if progress_str:
                try:
                    vals['progress'] = float(progress_str)
                except:
                    vals['progress'] = 0.0
            else:
                vals['progress'] = 0.0

            # Create task
            task = self.env['gantt.task'].create(vals)
            created_tasks.append(task)
            task_map[task_id] = task

            # Store predecessor/successor data for second pass
            predecessor_ids = row.get('predecessor_ids', '').strip()
            successor_ids = row.get('successor_ids', '').strip()
            if predecessor_ids or successor_ids:
                task_links_data.append({
                    'task_id': task_id,
                    'task': task,
                    'predecessor_ids': predecessor_ids,
                    'successor_ids': successor_ids
                })

        # Second pass: Create task links
        link_errors = []
        created_links = []  # Track created links to prevent duplicates and conflicts

        for link_data in task_links_data:
            task = link_data['task']
            task_id = link_data['task_id']

            # Process predecessors
            if link_data['predecessor_ids']:
                pred_ids = [pid.strip() for pid in link_data['predecessor_ids'].split(',') if pid.strip()]
                for pred_id in pred_ids:
                    if pred_id in task_map:
                        pred_task = task_map[pred_id]

                        # Check for conflicting link (opposite direction)
                        opposite_key = (task_id, pred_id)  # task -> pred_task
                        if opposite_key in created_links:
                            link_errors.append('Conflicting link: {} already links to {}. Cannot create opposite link.'.format(task_id, pred_id))
                            continue

                        # Check for duplicate link
                        link_key = (pred_id, task_id)  # pred_task -> task
                        if link_key in created_links:
                            continue  # Skip duplicate

                        try:
                            # Create the link (predecessor -> this task)
                            self.env['gantt.task.link'].create({
                                'task_id': pred_task.id,
                                'target_task_id': task.id,
                                'link_type': '0',  # Finish to Start
                                'project_id': self.project_id.id
                            })
                            created_links.append(link_key)
                        except Exception as e:
                            link_errors.append('Failed to create link from {} to {}: {}'.format(pred_id, task_id, str(e)))
                    else:
                        # Check if it exists in database (existing tasks)
                        existing_pred = self.env['gantt.task'].search([
                            ('task_id', '=', pred_id),
                            ('project_id', '=', self.project_id.id)
                        ], limit=1)
                        if existing_pred:
                            # Check for conflicting link (opposite direction)
                            opposite_key = (task_id, pred_id)
                            if opposite_key in created_links:
                                link_errors.append('Conflicting link: {} already links to {}. Cannot create opposite link.'.format(task_id, pred_id))
                                continue

                            # Check for duplicate link
                            link_key = (pred_id, task_id)
                            if link_key in created_links:
                                continue

                            try:
                                self.env['gantt.task.link'].create({
                                    'task_id': existing_pred.id,
                                    'target_task_id': task.id,
                                    'link_type': '0',
                                    'project_id': self.project_id.id
                                })
                                created_links.append(link_key)
                            except Exception as e:
                                link_errors.append('Failed to create link from {} to {}: {}'.format(pred_id, task_id, str(e)))
                        else:
                            link_errors.append('Predecessor task {} not found for task {}'.format(pred_id, task_id))

            # Process successors
            if link_data['successor_ids']:
                succ_ids = [sid.strip() for sid in link_data['successor_ids'].split(',') if sid.strip()]
                for succ_id in succ_ids:
                    if succ_id in task_map:
                        succ_task = task_map[succ_id]

                        # Check for conflicting link (opposite direction)
                        opposite_key = (succ_id, task_id)  # succ_task -> task
                        if opposite_key in created_links:
                            link_errors.append('Conflicting link: {} already links to {}. Cannot create opposite link.'.format(succ_id, task_id))
                            continue

                        # Check for duplicate link
                        link_key = (task_id, succ_id)  # task -> succ_task
                        if link_key in created_links:
                            continue  # Skip duplicate

                        try:
                            # Create the link (this task -> successor)
                            self.env['gantt.task.link'].create({
                                'task_id': task.id,
                                'target_task_id': succ_task.id,
                                'link_type': '0',  # Finish to Start
                                'project_id': self.project_id.id
                            })
                            created_links.append(link_key)
                        except Exception as e:
                            link_errors.append('Failed to create link from {} to {}: {}'.format(task_id, succ_id, str(e)))
                    else:
                        # Check if it exists in database (existing tasks)
                        existing_succ = self.env['gantt.task'].search([
                            ('task_id', '=', succ_id),
                            ('project_id', '=', self.project_id.id)
                        ], limit=1)
                        if existing_succ:
                            # Check for conflicting link (opposite direction)
                            opposite_key = (succ_id, task_id)
                            if opposite_key in created_links:
                                link_errors.append('Conflicting link: {} already links to {}. Cannot create opposite link.'.format(succ_id, task_id))
                                continue

                            # Check for duplicate link
                            link_key = (task_id, succ_id)
                            if link_key in created_links:
                                continue

                            try:
                                self.env['gantt.task.link'].create({
                                    'task_id': task.id,
                                    'target_task_id': existing_succ.id,
                                    'link_type': '0',
                                    'project_id': self.project_id.id
                                })
                                created_links.append(link_key)
                            except Exception as e:
                                link_errors.append('Failed to create link from {} to {}: {}'.format(task_id, succ_id, str(e)))
                        else:
                            link_errors.append('Successor task {} not found for task {}'.format(succ_id, task_id))

        # Build success message HTML
        success_html = '<div style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">'
        success_html += '<h2 style="color: green;">&#10004; Import Complete</h2>'
        success_html += '<p style="font-size: 18px;"><strong>{}</strong> tasks imported successfully!</p>'.format(len(created_tasks))

        if link_errors:
            success_html += '<h4 style="color: orange;">Warnings:</h4>'
            success_html += '<ul style="text-align: left; color: orange;">'
            for error in link_errors[:10]:
                success_html += '<li>{}</li>'.format(error)
            if len(link_errors) > 10:
                success_html += '<li>... and {} more warnings</li>'.format(len(link_errors) - 10)
            success_html += '</ul>'

        success_html += '<p style="margin-top: 20px; color: #666;">Click <strong>Close</strong> to return to the project view.</p>'
        success_html += '</div>'

        # Update wizard to show done state
        self.write({
            'state': 'done',
            'validation_message': success_html,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gantt.task.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context
        }

    @api.multi
    def action_back_to_upload(self):
        """Go back to upload state"""
        self.write({
            'state': 'draft',
            'validation_message': False,
            'has_errors': False,
            'total_rows': 0,
            'valid_rows': 0,
            'error_rows': 0
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gantt.task.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context
        }

    @api.model
    def action_download_template(self):
        """Download the static CSV template file"""
        # Return URL to static CSV template file
        return {
            'type': 'ir.actions.act_url',
            'url': '/rnet_project_management/static/csv/gantt_tasks_import_template.csv',
            'target': 'self',
        }
