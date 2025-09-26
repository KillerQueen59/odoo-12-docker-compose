# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
import math
import logging

_logger = logging.getLogger(__name__)

class ProjectManagementDashboard(models.TransientModel):
    """
    This is a transient model that acts as a data provider for the custom
    Project Management Dashboard. It does not store any records in the database.
    Its sole purpose is to house the methods that are called via RPC from the
    JavaScript widget to fetch and process dashboard data.
    """
    _name = 'project.management.dashboard'
    _description = 'Project Management Dashboard Data Provider'

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _format_project_display_name(self, project):
        if not project: return ''
        if hasattr(project, 'no') and project.no:
            return u"[%s] %s" % (project.no, project.name)
        return project.name

    def _get_user_project_domain(self):
        uid = self.env.user.id
        is_director = self.env.user.has_group('purchase_tripple_approval.group_purchase_director')
        if not is_director:
            Project = self.env['project.project']
            if 'project_manager' in Project._fields and 'site_manager' in Project._fields:
                 return ['|', ('project_manager.user_id', '=', uid), ('site_manager.user_id', '=', uid)]
        return []

    def _aggregate_by_month(self, lines, date_field, value_field, is_progress=False):
        monthly_data = {}
        for line in lines:
            line_date = getattr(line, date_field)
            if line_date:
                month_key = line_date.strftime('%Y-%m')
                value = getattr(line, value_field)
                if is_progress:
                    if month_key not in monthly_data or line_date > monthly_data[month_key]['last_date']:
                        monthly_data[month_key] = {'value': value, 'last_date': line_date}
                else:
                    monthly_data.setdefault(month_key, {'value': 0})
                    monthly_data[month_key]['value'] += value
        if is_progress:
            return {m: v['value'] for m, v in monthly_data.items()}
        return {m: v['value'] for m, v in monthly_data.items()}


    @api.model
    def get_dashboard_filters(self, show_all_projects=False):
        uid = self.env.user.id
        Project = self.env['project.project']
        Employee = self.env['hr.employee']
        employee_domain = []
        if 'status_karyawan' in Employee._fields:
            employee_domain.append(('status_karyawan.name', '=', 'PKWT Project'))
        employees = Employee.search_read(employee_domain, ['id', 'name'])
        project_domain = self._get_user_project_domain()
        if show_all_projects:
            project_domain = []
        projects = Project.search(project_domain)
        formatted_projects = [{'id': proj.id, 'name': self._format_project_display_name(proj)} for proj in projects]
        default_project_ids = [p['id'] for p in formatted_projects] if not show_all_projects and projects else []
        rating_options = []
        if 'hr.employee.review.line' in self.env:
            ReviewLineModel = self.env['hr.employee.review.line']
            if 'name' in ReviewLineModel._fields and ReviewLineModel._fields['name'].type == 'selection':
                rating_options = ReviewLineModel._fields['name'].selection
        return {'employees': employees, 'projects': formatted_projects, 'rating_options': [{'key': r[0], 'label': r[1]} for r in rating_options], 'default_project_ids': default_project_ids}

    @api.model
    def get_kpi_data(self, filters=None):
        filters = filters or {}
        
        project_domain = self._get_user_project_domain()
        if filters.get('project_ids'):
            project_domain = [('id', 'in', filters['project_ids'])]
        
        projects_to_consider = self.env['project.project'].search(project_domain)
        project_ids_for_queries = projects_to_consider.ids

        attendance_domain = [('project', 'in', project_ids_for_queries)]
        if filters.get('date_from'): attendance_domain.append(('check_in', '>=', filters['date_from'] + " 00:00:00"))
        if filters.get('date_to'): attendance_domain.append(('check_in', '<=', filters['date_to'] + " 23:59:59"))
        if filters.get('employee_ids'): attendance_domain.append(('employee_id', 'in', filters['employee_ids']))
        
        attendances = self.env['hr.attendance'].search(attendance_domain)
        
        project_data = {}
        employee_data = {}
        has_overtime = all(f in self.env['hr.attendance']._fields for f in ['gut_class1', 'gut_class2', 'gut_class3', 'gut_class4'])

        for att in attendances:
            overtime = att.gut_class1 + att.gut_class2 + att.gut_class3 + att.gut_class4 if has_overtime else 0
            total = att.worked_hours + overtime
            
            if att.project:
                proj_label = att.project.no or att.project.name
                project_data.setdefault(proj_label, {'hours': 0})
                project_data[proj_label]['hours'] += total
            if att.employee_id:
                employee_data.setdefault(att.employee_id.name, {'hours': 0})
                employee_data[att.employee_id.name]['hours'] += total

        sorted_projects = sorted(project_data.items(), key=lambda item: item[1]['hours'], reverse=True)
        top_projects_data = [{'name': name, 'hours': data['hours']} for name, data in sorted_projects[:5]]
        sorted_employees = sorted(employee_data.items(), key=lambda item: item[1]['hours'], reverse=True)
        top_employees_data = [{'name': name, 'hours': data['hours']} for name, data in sorted_employees[:5]]

        return {
            'charts': {
                'top_projects': top_projects_data,
                'top_employees': top_employees_data,
            }
        }

   # --- NEW: The advanced review data logic from your reference file is added here ---
    @api.model
    def get_advanced_review_data(self, filters=None, page=1, limit=10, sort='employee_name asc'):
        filters = filters or {}
        line_domain = []
        search_term = filters.get('search_term')
        if search_term:
            search_domain = [
                '|', ('employee_id.name', 'ilike', search_term),
                '|', ('job_id.name', 'ilike', search_term),
                '|', ('review_id.project_id.name', 'ilike', search_term),
                ('description', 'ilike', search_term),
            ]
            line_domain.extend(search_domain)
        if filters.get('ratings'):
            line_domain.append(('name', 'in', filters['ratings']))
        
        all_matching_lines = self.env['hr.employee.review.line'].sudo().search(line_domain)
        employee_data = {}
        for line in all_matching_lines:
            emp_id = line.employee_id.id
            if emp_id not in employee_data:
                employee_data[emp_id] = { 'employee_id': emp_id, 'employee_name': line.employee_id.name, 'job_position': line.job_id.name or '', 'ratings': [], 'projects': set(), 'notes': [] }
            employee_data[emp_id]['ratings'].append(int(line.rating))
            project = line.review_id.project_id
            if project:
                display_name = "[{}] {}".format(project.no, project.name) if project.no else project.name
                employee_data[emp_id]['projects'].add(display_name)
            if line.description:
                employee_data[emp_id]['notes'].append(line.description)
        
        aggregated_list = []
        for emp_id, data in employee_data.items():
            ratings = data['ratings']
            review_count = len(ratings)
            total_score = sum(int(r) + 1 for r in ratings)
            avg_rating = total_score / review_count if review_count > 0 else 0.0
            aggregated_list.append({
                'employee_id': data['employee_id'], 'employee_name': data['employee_name'],
                'job_position': data['job_position'], 'avg_rating': round(avg_rating, 2),
                'projects_str': ', '.join(sorted(list(data['projects']))),
                'all_notes': '\n\n---\n\n'.join(data['notes']),
            })
        sort_key, sort_dir = sort.split(' ')
        is_reverse = sort_dir == 'desc'
        aggregated_list.sort(key=lambda x: x.get(sort_key, ''), reverse=is_reverse)
        
        total_employees = len(aggregated_list)
        offset = (int(page) - 1) * int(limit)
        paginated_list = aggregated_list[offset : offset + int(limit)]

        return {
            'total_employees': total_employees,
            'employee_ratings': paginated_list,
        }
        
    @api.model
    def get_project_progress_data(self, filters=None, page=1, limit=10):
        """
        Provides paginated data for the "Project Progress Overview" table.
        """
        filters = filters or {}
        if 'project.progress.plan' not in self.env:
            return {'total': 0, 'progress_data': []}
        
        project_domain = self._get_user_project_domain()
        if filters.get('project_ids'):
            project_domain = [('id', 'in', filters['project_ids'])]
        
        projects_to_filter = self.env['project.project'].search(project_domain)
        
        domain = [('active', '=', True), ('name', 'in', projects_to_filter.ids)]
        
        progress_model = self.env['project.progress.plan']
        total_records = progress_model.search_count(domain)
        
        offset = (int(page) - 1) * int(limit)
        progress_plans = progress_model.search(domain, limit=int(limit), offset=offset, order='name asc')
        
        progress_data = []
        for plan in progress_plans:
            progress_data.append({
                'id': plan.id,
                'seq': plan.seq or '',
                'name': self._format_project_display_name(plan.name),
                'project_manager': plan.project_manager.name if plan.project_manager else '',
                'plan_progress': plan.current_accum_plan_progress,
                'actual_progress': plan.current_accum_actual_progress,
                'plan_cash_out': u'{:,.0f}'.format(plan.current_accum_plan_cash_out).replace(',', '.'),
                'actual_cash_out': u'{:,.0f}'.format(plan.current_accum_actual_cash_out).replace(',', '.'),
                'plan_cash_in': u'{:,.0f}'.format(plan.current_accum_plan_cash_in).replace(',', '.'),
                'actual_cash_in': u'{:,.0f}'.format(plan.current_accum_actual_cash_in).replace(',', '.'),
                'plan_invoice': u'{:,.0f}'.format(plan.current_accum_plan_invoice).replace(',', '.'),
                'actual_invoice': u'{:,.0f}'.format(plan.current_accum_actual_invoice).replace(',', '.'),
                'plan_manhour': u'{:,.0f}'.format(plan.current_accum_plan_manhour).replace(',', '.'),
                'actual_manhour': u'{:,.0f}'.format(plan.current_accum_actual_manhour).replace(',', '.'),
            })

        return {
            'total': total_records,
            'progress_data': progress_data
        }

   
    @api.model
    def get_cashflow_chart_data(self, filters=None):
        filters = filters or {}
        if 'project.progress.plan' not in self.env:
            return {}

        domain = [('active', '=', True)]
        if filters.get('project_ids'):
            domain.append(('name', 'in', filters['project_ids']))

        progress_plans = self.env['project.progress.plan'].search(domain)
        
        date_from = fields.Date.from_string(filters.get('date_from')) if filters.get('date_from') else None
        date_to = fields.Date.from_string(filters.get('date_to')) if filters.get('date_to') else None
        
        # 1. Gather only the actual cash flow lines
        actual_cashin_lines = progress_plans.mapped('project_actual_cashin_line').filtered(
            lambda l: l.payment_date and (not date_from or l.payment_date >= date_from) and (not date_to or l.payment_date <= date_to)
        )
        actual_cashout_lines = progress_plans.mapped('project_actual_cashout_line').filtered(
            lambda l: l.payment_date and (not date_from or l.payment_date >= date_from) and (not date_to or l.payment_date <= date_to)
        )
        
        # 2. Group the data by month
        monthly_data = {}
        for line in actual_cashin_lines:
            month_key = line.payment_date.strftime('%Y-%m') # e.g., "2025-08"
            monthly_data.setdefault(month_key, {'in': 0, 'out': 0})
            monthly_data[month_key]['in'] += line.amount

        for line in actual_cashout_lines:
            month_key = line.payment_date.strftime('%Y-%m')
            monthly_data.setdefault(month_key, {'in': 0, 'out': 0})
            monthly_data[month_key]['out'] += line.amount
        
        # 3. Calculate accumulative values and prepare chart data
        sorted_months = sorted(monthly_data.keys())
        
        chart_data = { 'labels': [], 'actual_in': [], 'actual_out': [], 'accum_flow': [] }
        accumulated_balance = 0
        
        for month in sorted_months:
            data = monthly_data[month]
            monthly_balance = data['in'] - data['out']
            accumulated_balance += monthly_balance
            
            chart_data['labels'].append(month)
            chart_data['actual_in'].append(data['in'])
            chart_data['actual_out'].append(-data['out']) # Negative for chart display
            chart_data['accum_flow'].append(accumulated_balance)
            
        return chart_data
    
    @api.model
    def get_s_curve_data(self, filters=None):
        filters = filters or {}
        if 'project.progress.plan' not in self.env: return {}
        
        project_domain = self._get_user_project_domain()
        if filters.get('project_ids'):
            project_domain = [('id', 'in', filters['project_ids'])]
        
        projects = self.env['project.project'].search(project_domain)
        progress_plans = self.env['project.progress.plan'].search([('name', 'in', projects.ids)])

        date_from = fields.Date.from_string(filters.get('date_from')) if filters.get('date_from') else None
        date_to = fields.Date.from_string(filters.get('date_to')) if filters.get('date_to') else None

        plan_lines = progress_plans.mapped('project_plan_curve_line').filtered(
            lambda l: l.date and (not date_from or l.date >= date_from) and (not date_to or l.date <= date_to)
        )
        actual_lines = progress_plans.mapped('project_actual_curve_line').filtered(
            lambda l: l.date and (not date_from or l.date >= date_from) and (not date_to or l.date <= date_to)
        )

        plan_monthly = self._aggregate_by_month(plan_lines, 'date', 'name', is_progress=True)
        actual_monthly = self._aggregate_by_month(actual_lines, 'date', 'name', is_progress=True)
        
        all_months = sorted(list(set(plan_monthly.keys()) | set(actual_monthly.keys())))

        return {
            'labels': all_months,
            'plan_data': [plan_monthly.get(m, 0) for m in all_months],
            'actual_data': [actual_monthly.get(m, 0) for m in all_months],
        }

    @api.model
    def get_cash_in_vs_plan_out_data(self, filters=None):
        filters = filters or {}
        if 'project.progress.plan' not in self.env: return {}
        
        project_domain = self._get_user_project_domain()
        if filters.get('project_ids'):
            project_domain = [('id', 'in', filters['project_ids'])]

        projects = self.env['project.project'].search(project_domain)
        progress_plans = self.env['project.progress.plan'].search([('name', 'in', projects.ids)])

        date_from = fields.Date.from_string(filters.get('date_from')) if filters.get('date_from') else None
        date_to = fields.Date.from_string(filters.get('date_to')) if filters.get('date_to') else None

        plan_out_lines = progress_plans.mapped('project_plan_cashout_line').filtered(
            lambda l: l.date and (not date_from or l.date >= date_from) and (not date_to or l.date <= date_to)
        )
        actual_in_lines = progress_plans.mapped('project_actual_cashin_line').filtered(
            lambda l: l.payment_date and (not date_from or l.payment_date >= date_from) and (not date_to or l.payment_date <= date_to)
        )
        
        plan_out_monthly = self._aggregate_by_month(plan_out_lines, 'date', 'name')
        actual_in_monthly = self._aggregate_by_month(actual_in_lines, 'payment_date', 'amount')
        
        all_months = sorted(list(set(plan_out_monthly.keys()) | set(actual_in_monthly.keys())))

        return {
            'labels': all_months,
            'plan_out_data': [plan_out_monthly.get(m, 0) for m in all_months],
            'actual_in_data': [actual_in_monthly.get(m, 0) for m in all_months],
        }

    @api.model
    def get_invoice_data(self, filters=None):
        filters = filters or {}
        if 'project.progress.plan' not in self.env: return {}

        project_domain = self._get_user_project_domain()
        if filters.get('project_ids'):
            project_domain = [('id', 'in', filters['project_ids'])]

        projects = self.env['project.project'].search(project_domain)
        progress_plans = self.env['project.progress.plan'].search([('name', 'in', projects.ids)])
        
        date_from = fields.Date.from_string(filters.get('date_from')) if filters.get('date_from') else None
        date_to = fields.Date.from_string(filters.get('date_to')) if filters.get('date_to') else None

        plan_lines = progress_plans.mapped('project_plan_invoice_line').filtered(
            lambda l: l.date and (not date_from or l.date >= date_from) and (not date_to or l.date <= date_to)
        )
        actual_lines = progress_plans.mapped('project_actual_invoice_line').filtered(
            lambda l: l.created_date and (not date_from or l.created_date >= date_from) and (not date_to or l.created_date <= date_to)
        )
        
        plan_monthly = self._aggregate_by_month(plan_lines, 'date', 'name')
        actual_monthly = self._aggregate_by_month(actual_lines, 'created_date', 'amount')
        
        all_months = sorted(list(set(plan_monthly.keys()) | set(actual_monthly.keys())))

        return {
            'labels': all_months,
            'plan_data': [plan_monthly.get(m, 0) for m in all_months],
            'actual_data': [actual_monthly.get(m, 0) for m in all_months],
        }

    @api.model
    def get_manhour_data(self, filters=None):
        filters = filters or {}
        if 'project.progress.plan' not in self.env: return {}

        project_domain = self._get_user_project_domain()
        if filters.get('project_ids'):
            project_domain = [('id', 'in', filters['project_ids'])]

        projects = self.env['project.project'].search(project_domain)
        progress_plans = self.env['project.progress.plan'].search([('name', 'in', projects.ids)])
        
        date_from = fields.Date.from_string(filters.get('date_from')) if filters.get('date_from') else None
        date_to = fields.Date.from_string(filters.get('date_to')) if filters.get('date_to') else None
        
        plan_lines = progress_plans.mapped('project_plan_manhour_line').filtered(
            lambda l: l.date and (not date_from or l.date >= date_from) and (not date_to or l.date <= date_to)
        )
        actual_lines = progress_plans.mapped('project_actual_manhour_line').filtered(
            lambda l: l.date_from and (not date_from or l.date_from >= date_from) and (not date_to or l.date_from <= date_to)
        )
        
        plan_monthly = self._aggregate_by_month(plan_lines, 'date', 'name')
        actual_monthly = self._aggregate_by_month(actual_lines, 'date_from', 'total')
        
        all_months = sorted(list(set(plan_monthly.keys()) | set(actual_monthly.keys())))

        return {
            'labels': all_months,
            'plan_data': [plan_monthly.get(m, 0) for m in all_months],
            'actual_data': [actual_monthly.get(m, 0) for m in all_months],
        }