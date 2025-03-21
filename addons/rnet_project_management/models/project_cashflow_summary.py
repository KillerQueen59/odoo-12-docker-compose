from odoo import models, fields, api

class ProjectCashflowSummary(models.Model):
    _name = 'project.cashflow.summary'
    _description = 'Project Cashflow Summary'
    _rec_name = 'name'
    _auto = True  # Automatically create the table in the database

    name = fields.Char(string='Name', default='Cashflow Summary', readonly=True)
    total_plan_cash_in = fields.Float(string='Total Plan Cash In', compute='_compute_totals', store=True, readonly=True)
    total_actual_cash_in = fields.Float(string='Total Actual Cash In', compute='_compute_totals', store=True, readonly=True)
    total_plan_cash_out = fields.Float(string='Total Plan Cash Out', compute='_compute_totals', store=True, readonly=True)
    total_actual_cash_out = fields.Float(string='Total Actual Cash Out', compute='_compute_totals', store=True, readonly=True)
    net_plan_cashflow = fields.Float(string='Net Cashflow', compute='_compute_net_cashflow', store=True, readonly=True)
    net_actual_cashflow = fields.Float(string='Net Cashflow', compute='_compute_net_cashflow', store=True, readonly=True)
    cashout_plan_lines = fields.One2many(
        'project.cashflow.plan.cashout.line', 'summary_id', string='Cash Out Plan by Project', readonly=True
    )
    cashout_actual_lines = fields.One2many(
        'project.cashflow.actual.cashout.line', 'summary_id', string='Cash Out Actual by Project', readonly=True
    )
    cashin_plan_lines = fields.One2many(
        'project.cashflow.plan.cashin.line', 'summary_id', string='Cash In Plan by Project', readonly=True
    )
    cashin_actual_lines = fields.One2many(
        'project.cashflow.actual.cashin.line', 'summary_id', string='Cash In Actual by Project', readonly=True
    )

    @api.depends('total_plan_cash_in','total_actual_cash_in', 'total_plan_cash_out', 'total_actual_cash_out')
    def _compute_net_cashflow(self):
        for record in self:
            record.net_plan_cashflow = record.total_plan_cash_in - record.total_plan_cash_out
            record.net_actual_cashflow = record.total_actual_cash_in - record.total_actual_cash_out

    @api.depends('cashin_plan_lines.total_cash_in', 'cashin_actual_lines.total_cash_in',
                 'cashout_plan_lines.total_cash_out','cashout_actual_lines.total_cash_out')
    def _compute_totals(self):
        print("_compute_totals")
        for record in self:
            try:
                # Get all active project.progress.plan records
                progress_plans = self.env['project.progress.plan'].search([('active', '=', True)])

                # Aggregate cash_in from all project.plan.cashin linked to active project.progress.plan
                plan_cashin_records = self.env['project.plan.cashin'].search([
                    ('plan_plan_cashin_id', 'in', progress_plans.ids)
                ])
                total_plan_cash_in = sum(float(rec.name or 0.0) for rec in plan_cashin_records if rec.name is not None)

                actual_cashin_records = self.env['project.actual.cashin'].search([
                    ('actual_cashin_line_id', 'in', progress_plans.ids)
                ])
                total_actual_cash_in = sum(float(rec.name or 0.0) for rec in actual_cashin_records if rec.name is not None)

                # Aggregate cash_out from all project.plan.cashout linked to active project.progress.plan
                plan_cashout_records = self.env['project.plan.cashout'].search([
                    ('plan_plan_cashout_id', 'in', progress_plans.ids)
                ])
                total_plan_cash_out = sum(float(rec.name or 0.0) for rec in plan_cashout_records if rec.name is not None)

                actual_cashout_records = self.env['project.actual.cashout'].search([
                    ('actual_cashout_line_id', 'in', progress_plans.ids)
                ])
                total_actual_cash_out = sum(
                    float(rec.name or 0.0) for rec in actual_cashout_records if rec.name is not None)

                # Compute per-project cash out summary by date
                cashout_plan_lines = []
                cashout_actual_lines = []
                for plan in progress_plans:
                    project_plan_cashout = self.env['project.plan.cashout'].search([
                        ('plan_plan_cashout_id', '=', plan.id)
                    ])
                    project_actual_cashout = self.env['project.actual.cashout'].search([
                        ('actual_cashout_line_id', '=', plan.id)
                    ])
                    # Group cash out by date for this project
                    plan_cashout_by_date = {}
                    actual_cashout_by_date = {}
                    for cashout in project_plan_cashout:
                        if cashout.date:
                            date_str = str(cashout.date)
                            if date_str not in plan_cashout_by_date:
                                plan_cashout_by_date[date_str] = 0.0
                            plan_cashout_by_date[date_str] += float(cashout.name or 0.0)
                    for cashout in project_actual_cashout:
                        if cashout.date:
                            date_str = str(cashout.date)
                            if date_str not in actual_cashout_by_date:
                                actual_cashout_by_date[date_str] = 0.0
                            actual_cashout_by_date[date_str] += float(cashout.name or 0.0)

                    # Create a summary line for each date
                    for date_str, total in plan_cashout_by_date.items():
                        cashout_plan_lines.append((0, 0, {
                            'project_id': plan.name.id,  # Link to project.project
                            'project_name': plan.name.name,  # Display project name
                            'date': date_str,
                            'total_cash_out': total,
                        }))
                    for date_str, total in actual_cashout_by_date.items():
                        cashout_actual_lines.append((0, 0, {
                            'project_id': plan.name.id,  # Link to project.project
                            'project_name': plan.name.name,  # Display project name
                            'date': date_str,
                            'total_cash_out': total,
                        }))

                # Compute per-project cash in summary by date
                cashin_plan_lines = []
                cashin_actual_lines = []
                for plan in progress_plans:
                    plan_project_cashin = self.env['project.plan.cashin'].search([
                        ('plan_plan_cashin_id', '=', plan.id)
                    ])
                    actual_project_cashin = self.env['project.actual.cashin'].search([
                        ('actual_cashin_line_id', '=', plan.id)
                    ])

                    # Group cash in by date for this project
                    plan_cashin_by_date = {}
                    actual_cashin_by_date = {}
                    for cashin in plan_project_cashin:
                        if cashin.date:
                            date_str = str(cashin.date)
                            if date_str not in plan_cashin_by_date:
                                plan_cashin_by_date[date_str] = 0.0
                            plan_cashin_by_date[date_str] += float(cashin.name or 0.0)
                    for cashin in actual_project_cashin:
                        if cashin.date:
                            date_str = str(cashin.date)
                            if date_str not in actual_cashin_by_date:
                                actual_cashin_by_date[date_str] = 0.0
                            actual_cashin_by_date[date_str] += float(cashin.name or 0.0)

                    # Create a summary line for each date
                    for date_str, total in plan_cashin_by_date.items():
                        cashin_plan_lines.append((0, 0, {
                            'project_id': plan.name.id,  # Link to project.project
                            'project_name': plan.name.name,  # Display project name
                            'date': date_str,
                            'total_cash_in': total,
                        }))
                    for date_str, total in actual_cashin_by_date.items():
                        cashin_actual_lines.append((0, 0, {
                            'project_id': plan.name.id,  # Link to project.project
                            'project_name': plan.name.name,  # Display project name
                            'date': date_str,
                            'total_cash_in': total,
                        }))

                # Update the record
                record.total_plan_cash_in = total_plan_cash_in
                record.total_actual_cash_in = total_actual_cash_in
                record.total_plan_cash_out = total_plan_cash_out
                record.total_actual_cash_out = total_actual_cash_out
                record.cashout_plan_lines = cashout_plan_lines
                record.cashout_actual_lines = cashout_actual_lines
                record.cashin_plan_lines = cashin_plan_lines
                record.cashin_actual_lines = cashin_actual_lines
            except Exception as e:
                print("Error computing totals: " + str(e))
                record.total_plan_cash_in = 0.0
                record.total_actual_cash_in = 0.0
                record.total_plan_cash_out = 0.0
                record.total_actual_cash_out = 0.0
                record.cashout_plan_lines = [(5, 0, 0)]  # Clear lines in case of error
                record.cashout_actual_lines = [(5, 0, 0)]  # Clear lines in case of error
                record.cashin_plan_lines = [(5, 0, 0)]  # Clear lines in case of error
                record.cashin_actual_lines = [(5, 0, 0)]  # Clear lines in case of error

    @api.model
    def create(self, vals):
        # Ensure the record is created with initial computation
        record = super(ProjectCashflowSummary, self).create(vals)
        print("trigger _compute_totals")
        record._compute_totals()  # Trigger computation on creation
        return record

    def action_refresh(self):
        # Method to manually trigger computation via a button
        self._compute_totals()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class ProjectCashflowPlanCashOutLine(models.Model):
    _name = 'project.cashflow.plan.cashout.line'
    _description = 'Project Cashflow plan Cash Out Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_out = fields.Float(string='Cash Out', readonly=True)

class ProjectCashflowPlanCashInLine(models.Model):
    _name = 'project.cashflow.plan.cashin.line'
    _description = 'Project Cashflow plan Cash In Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_in = fields.Float(string='Cash In', readonly=True)

class ProjectCashflowActualCashOutLine(models.Model):
    _name = 'project.cashflow.actual.cashout.line'
    _description = 'Project Cashflow actual Cash Out Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_out = fields.Float(string='Cash Out', readonly=True)

class ProjectCashflowActualCashInLine(models.Model):
    _name = 'project.cashflow.actual.cashin.line'
    _description = 'Project Cashflow actual Cash In Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_in = fields.Float(string='Cash In', readonly=True)