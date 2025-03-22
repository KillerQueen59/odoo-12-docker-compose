from odoo import models, fields, api

class ProjectCashflowSummary(models.Model):
    _name = 'project.cashflow.summary'
    _description = 'Project Cashflow Summary'
    _rec_name = 'name'
    _auto = True  # Automatically create the table in the database

    name = fields.Char(string='Name', default='Cashflow Summary', readonly=True)
    total_plan_cash_in = fields.Float(string='Total Plan Cash In', compute='_compute_totals', store=False, readonly=True)
    total_actual_cash_in = fields.Float(string='Total Actual Cash In', compute='_compute_totals', store=False, readonly=True)
    total_plan_cash_out = fields.Float(string='Total Plan Cash Out', compute='_compute_totals', store=False, readonly=True)
    total_actual_cash_out = fields.Float(string='Total Actual Cash Out', compute='_compute_totals', store=False, readonly=True)
    net_plan_cashflow = fields.Float(string='Net Plan Cashflow', compute='_compute_net_cashflow', store=False, readonly=True)
    net_actual_cashflow = fields.Float(string='Net Actual Cashflow', compute='_compute_net_cashflow', store=False, readonly=True)
    cashout_plan_lines = fields.One2many(
        'project.cashflow.plan.cashout.line', 'summary_id', string='Cash Out Plan by Project', compute='_compute_lines', store=True
    )
    cashout_actual_lines = fields.One2many(
        'project.cashflow.actual.cashout.line', 'summary_id', string='Cash Out Actual by Project', compute='_compute_lines', store=True
    )
    cashin_plan_lines = fields.One2many(
        'project.cashflow.plan.cashin.line', 'summary_id', string='Cash In Plan by Project', compute='_compute_lines', store=True
    )
    cashin_actual_lines = fields.One2many(
        'project.cashflow.actual.cashin.line', 'summary_id', string='Cash In Actual by Project', compute='_compute_lines', store=True
    )

    @api.model
    def _get_or_create_singleton(self):
        """Ensure a singleton record exists and return it."""
        summary = self.search([('name', '=', 'Cashflow Summary')], limit=1)
        if not summary:
            # Avoid recursion by creating the record without triggering computed fields
            summary = self.with_context(no_compute=True).create({'name': 'Cashflow Summary'})
        return summary

    @api.model
    def action_open_cashflow_summary(self):
        """Custom action to open the cashflow summary with the singleton record."""
        summary = self._get_or_create_singleton()
        # Ensure computed fields are calculated
        summary._compute_totals()
        summary._compute_lines()
        summary._compute_net_cashflow()
        action = self.env.ref('rnet_project_management.act_project_cashflow_summary').read()[0]
        action['res_id'] = summary.id
        return action

    @api.model
    def default_get(self, fields_list):
        """Override default_get to load the singleton record and compute values."""
        res = super(ProjectCashflowSummary, self).default_get(fields_list)
        # Only compute fields if not in a creation context that might cause recursion
        if not self.env.context.get('no_compute'):
            summary = self._get_or_create_singleton()
            if 'total_plan_cash_in' in fields_list:
                summary._compute_totals()
            if any(field in fields_list for field in
                   ['cashout_plan_lines', 'cashout_actual_lines', 'cashin_plan_lines', 'cashin_actual_lines']):
                summary._compute_lines()
            if 'net_plan_cashflow' in fields_list or 'net_actual_cashflow' in fields_list:
                summary._compute_net_cashflow()
        return res

    @api.depends()
    def _compute_totals(self):
        progress_plans = self.env['project.progress.plan'].search([])
        self.total_plan_cash_in = sum(progress_plans.mapped('project_plan_cashin_line').mapped('name'))
        self.total_plan_cash_out = sum(progress_plans.mapped('project_plan_cashout_line').mapped('name'))
        self.total_actual_cash_in = sum(self.env['project.actual.cashin'].search([]).mapped('amount'))
        self.total_actual_cash_out = sum(self.env['project.actual.cashout'].search([]).mapped('amount'))

    @api.depends()
    def _compute_net_cashflow(self):
        for record in self:
            record.net_plan_cashflow = record.total_plan_cash_in - record.total_plan_cash_out
            record.net_actual_cashflow = record.total_actual_cash_in - record.total_actual_cash_out

    @api.depends()
    def _compute_lines(self):
        progress_plans = self.env['project.progress.plan'].search([])
        for record in self:
            # Plan Cash Out Lines
            cashout_plan_data = []
            for plan in progress_plans:
                print("Plan:", plan.name, "Cash Out Lines:", plan.project_plan_cashout_line)
                for line in plan.project_plan_cashout_line:
                    cashout_plan_data.append({
                        'project_id': plan.name.id,
                        'project_name': plan.name.name,
                        'date': line.date,
                        'total_cash_out': line.name,
                    })

            # Plan Cash In Lines
            cashin_plan_data = []
            for plan in progress_plans:
                for line in plan.project_plan_cashin_line:
                    cashin_plan_data.append({
                        'project_id': plan.name.id,
                        'project_name': plan.name.name,
                        'date': line.date,
                        'total_cash_in': line.name,
                    })

            # Actual Cash Out Lines
            actual_cashout_data = []
            cashouts = self.env['project.actual.cashout'].search([])
            for cashout in cashouts:
                actual_cashout_data.append({
                    'project_id': cashout.project.id,
                    'project_name': cashout.project.name,
                    'date': cashout.payment_date,
                    'total_cash_out': cashout.amount,
                })

            # Actual Cash In Lines
            actual_cashin_data = []
            cashins = self.env['project.actual.cashin'].search([])
            for cashin in cashins:
                actual_cashin_data.append({
                    'project_id': cashin.project.id,
                    'project_name': cashin.project.name,
                    'date': cashin.payment_date,
                    'total_cash_in': cashin.amount,
                })

            # Write computed lines to One2many fields
            record.cashout_plan_lines = [(5, 0, 0)] + [(0, 0, vals) for vals in cashout_plan_data]
            record.cashin_plan_lines = [(5, 0, 0)] + [(0, 0, vals) for vals in cashin_plan_data]
            record.cashout_actual_lines = [(5, 0, 0)] + [(0, 0, vals) for vals in actual_cashout_data]
            record.cashin_actual_lines = [(5, 0, 0)] + [(0, 0, vals) for vals in actual_cashin_data]
    def action_refresh(self):
        """Refresh the summary by recomputing all fields."""
        self._compute_totals()
        self._compute_lines()
        self._compute_net_cashflow()
        return True

class ProjectCashflowPlanCashOutLine(models.Model):
    _name = 'project.cashflow.plan.cashout.line'
    _description = 'Project Cashflow Plan Cash Out Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_out = fields.Float(string='Cash Out', readonly=True)

class ProjectCashflowPlanCashInLine(models.Model):
    _name = 'project.cashflow.plan.cashin.line'
    _description = 'Project Cashflow Plan Cash In Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_in = fields.Float(string='Cash In', readonly=True)

class ProjectCashflowActualCashOutLine(models.Model):
    _name = 'project.cashflow.actual.cashout.line'
    _description = 'Project Cashflow Actual Cash Out Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_out = fields.Float(string='Cash Out', readonly=True)

class ProjectCashflowActualCashInLine(models.Model):
    _name = 'project.cashflow.actual.cashin.line'
    _description = 'Project Cashflow Actual Cash In Line'
    _order = 'date, project_name'

    summary_id = fields.Many2one('project.cashflow.summary', string='Cashflow Summary', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    project_name = fields.Char(string='Project Name', readonly=True)
    date = fields.Date(string='Tanggal', readonly=True)
    total_cash_in = fields.Float(string='Cash In', readonly=True)
