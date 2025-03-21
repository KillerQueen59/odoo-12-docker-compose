import math

from odoo.exceptions import UserError
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime, date


class ProjectProgressPlan(models.Model):
    _name = 'project.progress.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Many2one('project.project', string='Project', track_visibility='onchange')
    seq = fields.Char(string='No', compute='_compute_seq', store=True)
    revision_date = fields.Date("Revision Date", readonly=True)
    show_experience_note = fields.Boolean(string="Show Experience Note", default=False)

    project_manager = fields.Many2one('hr.employee', string='Project Manager', compute='_compute_project_manager', store=True)
    
    project_plan_curve_line = fields.One2many('project.plan.curve', 'plan_plan_curve_id', string='Project Plan Curve')
    project_plan_cashout_line = fields.One2many('project.plan.cashout', 'plan_plan_cashout_id', string='Project Plan Cash Out',store=True)
    project_plan_cashin_line = fields.One2many('project.plan.cashin', 'plan_plan_cashin_id', string='Project Plan Cash In')
    project_plan_invoice_line = fields.One2many('project.plan.invoice', 'plan_plan_invoice_id', string='Project Plan Invoice')
    project_plan_manhour_line = fields.One2many('project.plan.manhour', 'plan_plan_manhour_id', string='Project Plan Manhour')
    project_actual_curve_line = fields.One2many('project.actual.curve', 'plan_actual_curve_id', string='Project Actual Curve')

    project_actual_cashout_line = fields.One2many('project.actual.cashout', 'actual_cashout_line_id',string='Project Actual Cashout')
    project_estimated_cashout_line = fields.One2many('project.estimated.cashout', 'estimated_cashout_line_id', string='Project Estimated Cashout')
    project_actual_invoice_line = fields.One2many('project.actual.invoice', 'actual_invoice_line_id', string='Project Actual Invoice')
    project_actual_cashin_line = fields.One2many('project.actual.cashin', 'actual_cashin_line_id', string='Project Actual Cash In')
    project_actual_manhour_line = fields.One2many('project.actual.manhour', 'actual_manhour_line_id', string='Project Actual Manhour In')
    refresh_onchange_actual_value = fields.Datetime(string="Update Actual Value??")

    project_actual_plan_curve_line = fields.One2many('project.actual.plan.curve', 'actual_curve_plan_line_id',string='Project Actual Curve')
    project_actual_plan_cashout_line = fields.One2many('project.actual.plan.cashout', 'actual_cashout_plan_line_id',string='Project Actual Cashout')
    project_actual_plan_cashin_line = fields.One2many('project.actual.plan.cashin', 'actual_cashin_plan_line_id',string='Project Actual Cashin')
    project_actual_plan_invoice_line = fields.One2many('project.actual.plan.invoice', 'actual_invoice_plan_line_id',string='Project Actual Invoice')
    project_actual_plan_manhour_line = fields.One2many('project.actual.plan.manhour', 'actual_manhour_plan_line_id',string='Project Actual Manhour')

    expense_sheet_count = fields.Integer( compute='_get_expense_sheet_count')
    expense_sheet_amount = fields.Integer( compute='_get_expense_sheet_amount')
    expense_advance_count = fields.Integer( compute='_get_expense_advance_count')
    expense_advance_amount = fields.Integer( compute='_get_expense_advance_amount')
    purchase_order_amount = fields.Integer( compute='_get_purchase_order_amount')

    # Project Execution Experience
    project_execution_experience_date = fields.Date(string='Experience Date')
    project_execution_experience_value = fields.Text(string='Experience Value')

    # Lesson Learned
    lesson_learned_date = fields.Date(string='Lesson Date')
    lesson_learned_value = fields.Text(string='Lesson Value')

    # Subcon Performance Service
    subcon_performance_service_date = fields.Date(string='Subcon Date')
    subcon_performance_service_value = fields.Text(string='Subcon Value')

    # Procurement / Logistic Recommendation
    procurement_recommendation_date = fields.Date(string='Procurement Date')
    procurement_recommendation_value = fields.Text(string='Procurement Value')

    def toggle_notebook(self):
        for record in self:
            record.show_experience_note = not record.show_experience_note

    @api.depends('name')
    def _compute_seq(self):
        for record in self:
            record.seq = record.name.seq if record.name else ''

    @api.depends('name')
    def _compute_project_manager(self):
        for record in self:
            record.project_manager = record.name.project_manager if record.name else None
    
    # trigger untuk onchange update actual value
    def action_update_actual_value(self):
        self.write({
            'refresh_onchange_actual_value': fields.Datetime.now(),
        })
        self.onchange_estimated_cash_out()
        self.onchange_actual_cashout()
        self.onchange_actual_invoice()
        self.onchange_actual_cashin()
        self.onchange_actual_manhour()
        self.onchange_actual_plan_cashout()
        self.onchange_actual_plan_invoice()
        self.onchange_actual_plan_cashin()
        self.onchange_actual_plan_manhour()
        return True

    # get value Estimated cash out
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_estimated_cash_out(self):
        for rec in self:
            project_estimated_cashout_line = self.get_actual_estimated_lines()
            actual_estimated_lines = rec.project_estimated_cashout_line.browse([])
            for r in project_estimated_cashout_line:
                actual_estimated_lines += actual_estimated_lines.new(r)
            rec.project_estimated_cashout_line = actual_estimated_lines

            return

    # get list Estimated cashout form CVR & Purchase Order
    @api.model
    def get_actual_estimated_lines(self):
        res = []
        for rec in self:
            # compute list BAR
            for expense in self.env['hr.expense.advance'].search(['&',('project_id', '=', rec.name.id),('state', 'in', ['partial','paid']),]):
                expenses = {
                        'code': 'BAR',
                        'name': expense.name,
                        'created_date': expense.requested_date,
                        'amount': expense.total_paid,
                        'project': expense.project_id,
                    }
                res.append(expenses)

            # compute list PR
            for pr in self.env['material.purchase.requisition'].search(['&',('project', '=', rec.name.id),('state', 'in', ['stock']),]):
                requisitions = {
                        'code': 'PR',
                        'created_date': pr.request_date,
                        'name': pr.name,
                        'amount': 0.0,
                        'project': pr.project,
                        }
                res.append(requisitions)

            # compute list Purchase
            for purchase in self.env['purchase.order'].search(['&',('project', '=', rec.name.id),('state', 'in', ['purchase']),]):
                date_new = purchase.date_order.date()
                purchases = {
                        'code': 'PO',
                        'created_date': date_new,
                        'name': purchase.name,
                        'amount': purchase.amount_total,
                        'project': purchase.project,
                        }
                res.append(purchases)

        return res

        # get value actual cash out

    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_cashout(self):
        for rec in self:
            project_actual_cashout_line = self.get_actual_cashout_lines()
            actual_cashout_lines = rec.project_actual_cashout_line.browse([])
            for r in project_actual_cashout_line:
                actual_cashout_lines += actual_cashout_lines.new(r)
            rec.project_actual_cashout_line = actual_cashout_lines

        return

    # get list actual cashout form CVR & Purchase Order
    @api.model
    def get_actual_cashout_lines(self):
        res = []
        for rec in self:

            # compute list CVR
            for expense in self.env['hr.expense.sheet'].search(
                    ['&', ('project', '=', rec.name.id), ('state', 'in', ['approve', 'post']), ]):
                expenses = {
                    'code': 'CVR',
                    'name': expense.name,
                    'payment_date': expense.created_date,
                    'amount': expense.total_amount,
                    'project': expense.project,
                }
                res.append(expenses)

            # compute list Purchase paid/ account payment
            po_obj = self.env['purchase.order'].search([('project', '=', rec.name.id )])
            for payment in self.env['account.payment'].search([('state', '!=', 'cancelled'), ('payment_type', '=', 'outbound')]):
                amount = payment.amount_idr_curr if payment.currency_id != payment.company_id.currency_id else payment.amount
                payments = {
                    'code': 'PI',
                    'payment_date': payment.payment_date,
                    'name': payment.name,
                    'amount': amount,
                    'project': payment.project,
                }
                res.append(payments)


             # compute list BAR paid
            for payment in self.env['account.payment'].search(['&',('state','!=', 'cancelled'),('payment_type', '=', 'transfer'),]):
                payments = {
                        'code': 'BAR',
                        'payment_date': payment.payment_date,
                        'name': payment.name,
                        'amount': payment.amount,
                        'project': payment.project,
                    }
                res.append(payments)

        return res

        # get value actual Invoice

    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_invoice(self):
        for rec in self:
            project_actual_invoice_line = self.get_actual_invoice_lines()
            actual_invoice_lines = rec.project_actual_invoice_line.browse([])
            for r in project_actual_invoice_line:
                actual_invoice_lines += actual_invoice_lines.new(r)
            rec.project_actual_invoice_line = actual_invoice_lines

        return

    # get list actual invoice form Account Invoice
    @api.model
    def get_actual_invoice_lines(self):
        res = []
        for rec in self:
            # compute list Invoice
            for inv in self.env['account.invoice'].search(['&','&',('project', '=', rec.name.id),('type', '=', 'out_invoice'),('state', 'not in', ['draft','cancel']),]):
                invoices = {
                        'name': inv.number,
                        'created_date': inv.date_invoice,
                        'amount': inv.amount_total,
                        'amount_company_signed' : inv.amount_untaxed_signed,
                        'currency_id': inv.currency_id,
                        'project': inv.project
                    }
                res.append(invoices)

        return res

    # get value actual Actual Cash In
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_cashin(self):
        for rec in self:
            project_actual_cashin_line = self.get_actual_cashin_lines()
            actual_cashin_lines = rec.project_actual_cashin_line.browse([])
            for r in project_actual_cashin_line:
                actual_cashin_lines += actual_cashin_lines.new(r)
            rec.project_actual_cashin_line = actual_cashin_lines

        return

    # get list actual Cash In form account payment
    @api.model
    def get_actual_cashin_lines(self):
        res = []
        for rec in self:
            # compute list Invoice
            for pay in self.env['account.payment'].search(['&','&',('invoice_ids.project', '=', rec.name.id),('payment_type', '=', 'inbound'),('state', '=', 'posted'),]):
                invoices = {
                        'name': pay.name,
                        'payment_date': pay.payment_date,
                        'amount': pay.amount,
                        'project': pay.invoice_ids.project,
                    }
                res.append(invoices)

        return res

    # get value actual Manhour
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_manhour(self):
        for rec in self:
            project_actual_manhour_lines = rec.get_actual_manhour_lines()
            actual_manhour_lines = self.env['project.actual.manhour'].browse()

            for project, months in project_actual_manhour_lines.items():
                for year_month, values in months.items():
                    actual_manhour_lines |= actual_manhour_lines.new({
                        'name': values.get('name'),
                        'date_from': values.get('date_from'),
                        'date_to': values.get('date_to'),
                        'total': values.get('total'),
                        'project': project,
                        'month': year_month,
                    })

            rec.project_actual_manhour_line = actual_manhour_lines
        return


    @api.model
    def get_actual_manhour_lines(self):
        result = {}
        for rec in self:
            # Compute list of manhour lines grouped by project and month
            timesheets = self.env['hr_timesheet.sheet'].search([('attendances_ids.project', '=', rec.name.id)])
            for ts in timesheets:
                for att in ts.attendances_ids:
                    if att.project and att.project.id == rec.name.id:  # Ensure correct project
                        # Extract year and month from check_in date
                        check_in_date = fields.Date.from_string(att.check_in)
                        year_month = "{}-{:02d}".format(check_in_date.year, check_in_date.month)

                        total_hours = att.gut_normal_hours + att.gut_class1 + att.gut_class2 + att.gut_class3 + att.gut_class4

                        if att.project.id not in result:
                            result[att.project.id] = {}

                        if year_month not in result[att.project.id]:
                            result[att.project.id][year_month] = {
                                'name': ts.name,
                                'date_from': ts.date_start,
                                'date_to': ts.date_end,
                                'total': 0.0,
                                'project': att.project.id,
                                'month': year_month,
                            }

                        # Aggregate hours by project and month
                        result[att.project.id][year_month]['total'] += total_hours
        return result

    # get value actual and plan cash out
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_plan_cashout(self):
        for rec in self:
            project_actual_plan_cashout_line = self.get_actual_plan_cashout_lines()
            actual_plan_cashout_lines = rec.project_actual_plan_cashout_line.browse([])
            for r in project_actual_plan_cashout_line:
                actual_plan_cashout_lines += actual_plan_cashout_lines.new(r)
            rec.project_actual_plan_cashout_line = actual_plan_cashout_lines

        return

    # get list actual and plan cashout
    @api.model
    def get_actual_plan_cashout_lines(self):
        res = []
        for rec in self:

            # compute list actual cashout
            for actual in self.env['project.actual.cashout'].search([('actual_cashout_line_id', '=', rec.id)]):
                actuals = {
                    'code': 'Actual',
                    'name': actual.name,
                    'payment_date': actual.payment_date,
                    'amount': actual.amount,
                    'project': actual.project,
                }
                res.append(actuals)

            # compute list plan cashout
            for plan in self.env['project.plan.cashout'].search([('plan_plan_cashout_id', '=', rec.id)]):
                plans = {
                    'code': 'Plan',
                    'name': plan.seq,
                    'payment_date': plan.date,
                    'amount': plan.name,
                    'project': plan.plan_plan_cashout_id.name,
                }
                res.append(plans)
        return res

    # get list actual and plan cashout
    @api.model
    def get_actual_plan_curve_lines(self):
        res = []
        for rec in self:
            if rec.name.id == False:
                raise UserError(_('Project id cant be null'))
            # compute list actual curve
            accumulative_actual = 0
            accumulative_plan = 0
            for actual in self.env['project.actual.curve'].search([('plan_actual_curve_id', '=', rec.id)]):
                accumulative_actual += actual.name
                actuals = {
                    'code': 'Actual',
                    'name': actual.seq,
                    'payment_date': actual.date,
                    'amount': accumulative_actual,
                    'project': actual.plan_actual_curve_id.name,
                }
                res.append(actuals)

            # compute list plan curve
            for plan in self.env['project.plan.curve'].search([('plan_plan_curve_id', '=', rec.id)]):
                accumulative_plan += plan.name
                plans = {
                    'code': 'Plan',
                    'name': plan.seq,
                    'payment_date': plan.date,
                    'amount': accumulative_plan,
                    'project': plan.plan_plan_curve_id.name,
                }
                res.append(plans)
        return res

        # get list actual and plan cashout

    @api.multi
    def open_actual_plan_cashout_chart(self):
        for rec in self:
            return {
                'name': _('Actual and Plan Cashout'),
                'view_type': 'form',
                'view_mode': 'graph,pivot',
                'res_model': 'project.actual.plan.cashout',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'option': {'no_create_edit': True},
                'domain': [('project.id', '=', rec.name.id)],
            }

    @api.multi
    def open_actual_plan_curve_chart(self):
        for rec in self:
            project_actual_plan_curve_line = self.get_actual_plan_curve_lines()
            actual_plan_curve_lines = rec.project_actual_plan_curve_line.browse([])
            for r in project_actual_plan_curve_line:
                actual_plan_curve_lines += actual_plan_curve_lines.new(r)
            rec.project_actual_plan_curve_line = actual_plan_curve_lines
            return {
                'name': _('Actual and Plan Curve'),
                'view_type': 'form',
                'view_mode': 'graph,pivot',
                'res_model': 'project.actual.plan.curve',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'option': {'no_create_edit': True},
                'domain': [('project.id', '=', rec.name.id)],
            }

    # get value actual and plan cash in
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_plan_cashin(self):
        for rec in self:
            project_actual_plan_cashin_line = self.get_actual_plan_cashin_lines()
            actual_plan_cashin_lines = rec.project_actual_plan_cashin_line.browse([])
            for r in project_actual_plan_cashin_line:
                actual_plan_cashin_lines += actual_plan_cashin_lines.new(r)
            rec.project_actual_plan_cashin_line = actual_plan_cashin_lines

        return

    # get list actual and plan cashin
    @api.model
    def get_actual_plan_cashin_lines(self):
        res = []
        for rec in self:

            # compute list actual cashin
            for actual in self.env['project.actual.cashin'].search([('actual_cashin_line_id', '=', rec.id)]):
                actuals = {
                    'code': 'Actual',
                    'name': actual.name,
                    'payment_date': actual.payment_date,
                    'amount': actual.amount,
                    'project': actual.project,
                }
                res.append(actuals)

            # compute list plan cashin
            for plan in self.env['project.plan.cashin'].search([('plan_plan_cashin_id', '=', rec.id)]):
                plans = {
                    'code': 'Plan',
                    'name': plan.seq,
                    'payment_date': plan.date,
                    'amount': plan.name,
                    'project': plan.plan_plan_cashin_id.name,
                }
                res.append(plans)
        return res

    @api.multi
    def open_actual_plan_cashin_chart(self):
        for rec in self:
            return {
                'name': _('Actual and Plan cashin'),
                'view_type': 'form',
                'view_mode': 'graph,pivot',
                'res_model': 'project.actual.plan.cashin',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'option': {'no_create_edit': True},
                'domain': [('project.id', '=', rec.name.id)],
            }

            # get value actual and plan Invoice

    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_plan_invoice(self):
        for rec in self:
            project_actual_plan_invoice_line = self.get_actual_plan_invoice_lines()
            actual_plan_invoice_lines = rec.project_actual_plan_invoice_line.browse([])
            for r in project_actual_plan_invoice_line:
                actual_plan_invoice_lines += actual_plan_invoice_lines.new(r)
            rec.project_actual_plan_invoice_line = actual_plan_invoice_lines

        return

    # get list actual and plan invoice
    @api.model
    def get_actual_plan_invoice_lines(self):
        res = []
        for rec in self:

            # compute list actual invoice
            for actual in self.env['project.actual.invoice'].search([('actual_invoice_line_id', '=', rec.id)]):
                actuals = {
                    'code': 'Actual',
                    'name': actual.name,
                    'payment_date': actual.created_date,
                    'amount': actual.amount,
                    'project': actual.project,
                }
                res.append(actuals)

            # compute list plan invoice
            for plan in self.env['project.plan.invoice'].search([('plan_plan_invoice_id', '=', rec.id)]):
                plans = {
                    'code': 'Plan',
                    'name': plan.seq,
                    'payment_date': plan.date,
                    'amount': plan.name,
                    'project': plan.plan_plan_invoice_id.name,
                }
                res.append(plans)
        return res

    @api.multi
    def open_actual_plan_invoice_chart(self):
        for rec in self:
            return {
                'name': _('Actual and Plan invoice'),
                'view_type': 'form',
                'view_mode': 'graph,pivot',
                'res_model': 'project.actual.plan.invoice',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'option': {'no_create_edit': True},
                'domain': [('project.id', '=', rec.name.id)],
            }

    # get value actual and plan manhour
    @api.multi
    @api.depends('refresh_onchange_actual_value')
    def onchange_actual_plan_manhour(self):
        for rec in self:
            project_actual_plan_manhour_line = self.get_actual_plan_manhour_lines()
            actual_plan_manhour_lines = rec.project_actual_plan_manhour_line.browse([])
            for r in project_actual_plan_manhour_line:
                actual_plan_manhour_lines += actual_plan_manhour_lines.new(r)
            rec.project_actual_plan_manhour_line = actual_plan_manhour_lines

        return

    # get list actual and plan manhour
    @api.model
    def get_actual_plan_manhour_lines(self):
        res = []
        for rec in self:
            for actual in self.env['project.actual.manhour'].search([('actual_manhour_line_id', '=', rec.id)], limit=1):
                act = self.env['project.actual.manhour'].search([('actual_manhour_line_id', '=', rec.id)])
                actuals = {
                    'code': 'Actual',
                    'name': actual.name,
                    'date': actual.date_from,
                    'total': sum(line.total for line in act),
                    'project': actual.project,
                }
                res.append(actuals)

            # compute list plan manhour
            for plan in self.env['project.plan.manhour'].search([('plan_plan_manhour_id', '=', rec.id)], limit=1):
                pln = self.env['project.plan.manhour'].search([('plan_plan_manhour_id', '=', rec.id)])
                plans = {
                    'code': 'Plan',
                    'name': plan.seq,
                    'date': plan.date,
                    'total': sum(line.name for line in pln),
                    'project': plan.plan_plan_manhour_id.name,
                }
                res.append(plans)
        return res

    @api.multi
    def open_actual_plan_manhour_chart(self):
        for rec in self:
            return {
                'name': _('Actual and Plan manhour'),
                'view_type': 'form',
                'view_mode': 'graph,pivot',
                'res_model': 'project.actual.plan.manhour',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'option': {'no_create_edit': True},
                'domain': [('project.id', '=', rec.name.id)],
            }

    @api.model
    def get_details(self):
        query = '''SELECT  COALESCE(SUM(out.name),0) as cashout, count(plan_plan_cashout_id)
                        FROM project_plan_cashout out
						LEFT JOIN project_progress_plan pp ON pp.id = out.plan_plan_cashout_id
                        WHERE plan_plan_cashout_id  = %s AND pp.active = 't' """ % (data.id)'''
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        cashout = []
        for record in data:
            cashout.append(record.get('cashout'))

        return {
            'cashout': cashout,
        }

    def _get_cashout(self):
        for task in self:
            if len(task.project_plan_cashout_line) > 0:
                for detail in self.get_details():
                    task.total_cashout = detail['cashout']
            task.total_cashout = 0.0

    # @api.multi
    # def onchange_actual_cashout(self):
    #     res = {
    #             'value': {
    #                 #delete old input lines
    #                 'project_actual_cashout_line': map(lambda x: (2, x,), self.project_actual_cashout_line.ids),
    #                 }
    #         }
    #     project_actual_cashout_line = self.get_actual_cashout_lines()
    #             # rec.update({
    #             # 'project_actual_cashout_line': project_actual_cashout_line
    #             # })
    #     res['value'].update({
    #                 'worked_days_line_ids': project_actual_cashout_line,
    #         })
    #     return res

    # Revisi Project Plan
    @api.depends('current_revision_id', 'old_revision_ids')
    def _compute_has_old_revisions(self):
        for plan in self:
            if plan.old_revision_ids:
                plan.has_old_revisions = True

    @api.one
    @api.depends('old_revision_ids')
    def _compute_revision_count(self):
        self.revision_count = len(self.old_revision_ids)

    current_revision_id = fields.Many2one(
        comodel_name='project.progress.plan',
        string='Current revision',
        readonly=True,
        copy=True
    )
    old_revision_ids = fields.One2many(
        comodel_name='project.progress.plan',
        inverse_name='current_revision_id',
        string='Old revisions',
        readonly=True,
        context={'active_test': False}
    )
    revision_number = fields.Integer(
        string='Revision',
        copy=False,
        default=0
    )
    unrevisioned_seq = fields.Char(
        string='Original Plan Reference',
        copy=True,
        readonly=True,
    )
    active = fields.Boolean(
        default=True
    )
    has_old_revisions = fields.Boolean(
        compute='_compute_has_old_revisions')

    revision_count = fields.Integer(compute='_compute_revision_count')

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}

        return super(ProjectProgress, self).copy(default=default)

    def copy_revision_with_context(self):
        default_data = self.default_get([])
        new_rev_number = self.revision_number + 1
        default_data.update({
            'revision_number': new_rev_number,
            'unrevisioned_seq': self.seq,
            'seq': '%s(REV-%02d)' % (self.seq, new_rev_number),
            'revision_date': date.today(),
            'old_revision_ids': [(4, self.id, False)],
        })

        actual_curve_line = []
        for line in self.project_actual_curve_line:
            actual_curve_line.append([0, False,
                                      {'seq': line.seq,
                                       'name': line.name,
                                       'date': line.date,
                                       }])

        actual_cashin_line = []
        for line in self.project_actual_cashin_line:
            actual_cashin_line.append([0, False,
                                       {'name': line.name,
                                        'amount': line.amount,
                                        'payment_date': line.payment_date,
                                        }])

        actual_invoice_line = []
        for line in self.project_actual_invoice_line:
            actual_invoice_line.append([0, False,
                                        {'name': line.name,
                                         'amount': line.amount,
                                         'amount_company_signed': line.amount_company_signed,
                                         'created_date': line.created_date,
                                         }])

        actual_cashout_line = []
        for line in self.project_actual_cashout_line:
            actual_cashout_line.append([0, False,
                                        {'name': line.name,
                                         'code': line.code,
                                         'amount': line.amount,
                                         'payment_date': line.payment_date,
                                         'project': line.project.id,
                                         }])

        actual_manhour_line = []
        for line in self.project_actual_manhour_line:
            actual_manhour_line.append([0, False,
                                        {'name': line.name,
                                         'total': line.total,
                                         'date_from': line.date_from,
                                         'date_to': line.date_to,
                                         }])

        plan_curve_line = []
        for line in self.project_plan_curve_line:
            plan_curve_line.append([0, False,
                                    {'seq': line.seq,
                                     'name': line.name,
                                     'date': line.date,
                                     }])
        plan_cashin_line = []
        for line in self.project_plan_cashin_line:
            plan_cashin_line.append([0, False,
                                     {'seq': line.seq,
                                      'name': line.name,
                                      'date': line.date,
                                      }])

        plan_cashout_line = []
        for line in self.project_plan_cashout_line:
            plan_cashout_line.append([0, False,
                                      {'seq': line.seq,
                                       'name': line.name,
                                       'date': line.date,
                                       }])
        plan_invoice_line = []
        for line in self.project_plan_invoice_line:
            plan_invoice_line.append([0, False,
                                      {'seq': line.seq,
                                       'name': line.name,
                                       'date': line.date,
                                       }])

        plan_manhour_line = []
        for line in self.project_plan_manhour_line:
            plan_manhour_line.append([0, False,
                                      {'seq': line.seq,
                                       'name': line.name,
                                       'date': line.date,
                                       }])

        estimated_cashout_line = []
        for line in self.project_estimated_cashout_line:
            estimated_cashout_line.append([0, False,
                                           {'name': line.name,
                                            'code': line.code,
                                            'amount': line.amount,
                                            'created_date': line.created_date,
                                            'project': line.project.id,
                                            }])

        default_data['project_actual_curve_line'] = actual_curve_line
        default_data['project_actual_cashin_line'] = actual_cashin_line
        default_data['project_actual_invoice_line'] = actual_invoice_line
        default_data['project_actual_cashout_line'] = actual_cashout_line
        default_data['project_actual_manhour_line'] = actual_manhour_line
        default_data['project_estimated_cashout_line'] = estimated_cashout_line

        default_data['project_plan_curve_line'] = plan_curve_line
        default_data['project_plan_cashin_line'] = plan_cashin_line
        default_data['project_plan_cashout_line'] = plan_cashout_line
        default_data['project_plan_invoice_line'] = plan_invoice_line
        default_data['project_plan_manhour_line'] = plan_manhour_line

        new_revision = self.copy(default_data)
        self.old_revision_ids.write({
            'current_revision_id': new_revision.id,
        })
        self.write({'active': False,
                    'current_revision_id': new_revision.id,
                    })

        return new_revision

    @api.multi
    def create_revision(self):
        revision_ids = []
        # Looping over Project Progress records
        for project_progress_rec in self:
            # Calling  Copy method
            copied_progress_rec = project_progress_rec.copy_revision_with_context()

            msg = _('New revision created: %s') % copied_progress_rec.seq
            copied_progress_rec.message_post(body=msg)
            project_progress_rec.message_post(body=msg)

            revision_ids.append(copied_progress_rec.id)

        res = {
            'type': 'ir.actions.act_window',
            'name': _('Revisions'),
            'res_model': 'project.progress.plan',
            'domain': "[('id', 'in', %s)]" % revision_ids,
            'auto_search': True,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'target': 'current',
            'nodestroy': True,
        }

        # Returning the new Project Progress Plan view with new record.
        return res

    @api.multi
    def open_revision_list(self):
        if self.old_revision_ids:
            for rec in self:
                return {
                    'name': _('Revision History'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'project.progress.plan',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': ['&', ['current_revision_id', '=', rec.id], ['active', '=', False]],
                    'option': {'no_create_edit': True},
                }

    # statinfo  BAR & CVR di Project management
    @api.multi
    def _get_expense_sheet_count(self):
        res = self.env['hr.expense.sheet'].search_count(['&', ('project', '=', self.name.id), (
        'state', 'not in', ['draft', 'cancel', 'reject_control', 'reject_technical', 'reject_finance'])])
        self.expense_sheet_count = res or 0

    @api.multi
    @api.depends('expense_sheet_count')
    def _get_expense_sheet_amount(self):
        data_obj = self.env['hr.expense.sheet'].search(['&', ('project', '=', self.name.id), (
        'state', 'not in', ['draft', 'cancel', 'reject_control', 'reject_technical', 'reject_finance'])])
        total_amount = sum(data_obj.mapped('total_amount'))
        for record in self:
            record.expense_sheet_amount = total_amount or False

    @api.multi
    def _get_expense_advance_count(self):
        res = self.env['hr.expense.advance'].search_count(
            ['&', ('project_id', '=', self.name.id), ('state', 'not in', ['draft', 'rejected'])])
        self.expense_advance_count = res or 0

    @api.multi
    @api.depends('expense_advance_count')
    def _get_expense_advance_amount(self):
        data_obj = self.env['hr.expense.advance'].search(
            ['&', ('project_id', '=', self.name.id), ('state', 'not in', ['draft', 'rejected'])])
        total_amount = sum(data_obj.mapped('amount_total'))
        for record in self:
            record.expense_advance_amount = total_amount or False

    # statinfo PO di Project management
    @api.multi
    def _get_purchase_order_amount(self):
        data_obj = self.env['purchase.order'].search(
            ['&', ('project', '=', self.name.id), ('state', 'not in', ['draft', 'cancel', 'refuse'])])
        total_amount = sum(data_obj.mapped('amount_total'))
        for record in self:
            record.purchase_order_amount = total_amount or False

    # open CVR
    @api.multi
    def open_expense_sheet_project(self):
        for group in self:
            return {
                'name': 'CVR',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.expense.sheet',
                'type': 'ir.actions.act_window',
                'domain': ['&', ('project', '=', group.name.id), (
                'state', 'not in', ['draft', 'cancel', 'reject_control', 'reject_technical', 'reject_finance']), ],
            }
        pass

    # open BAR
    @api.multi
    def open_expense_advance_project(self):
        for group in self:
            return {
                'name': 'BAR',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.expense.advance',
                'type': 'ir.actions.act_window',
                'domain': ['&', ('project_id', '=', group.name.id), ('state', 'not in', ['draft', 'rejected']), ],
            }
        pass

    # open PUrchase order
    @api.multi
    def open_purchase_order_project(self):
        for group in self:
            return {
                'name': 'Purchase Order',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'domain': ['&', ('project', '=', group.name.id), ('state', 'not in', ['draft', 'cancel', 'refuse']), ],
            }
        pass


class ProjectPlanCurve(models.Model):
    _name = 'project.plan.curve'

    name = fields.Float(string='Progress %')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_plan_curve_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')

    @api.depends('plan_plan_curve_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_curve_id'):
            seq = 1
            for line in order.project_plan_curve_line:
                line.seq = seq
                seq += 1


class ProjectActualCurve(models.Model):
    _name = 'project.actual.curve'

    name = fields.Float(string='Progress %')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_actual_curve_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')

    @api.depends('plan_actual_curve_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_actual_curve_id'):
            seq = 1
            for line in order.project_actual_curve_line:
                line.seq = seq
                seq += 1


class ProjectPlanCashout(models.Model):
    _name = 'project.plan.cashout'

    name = fields.Float(string='Cash Out')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal', store=True)
    plan_plan_cashout_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')

    @api.depends('plan_plan_cashout_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_cashout_id'):
            seq = 1
            for line in order.project_plan_cashout_line:
                line.seq = seq
                seq += 1


class ProjectActualCashout(models.Model):
    _name = 'project.actual.cashout'
    _description = 'Actual cashout '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Payment Date')
    actual_cashout_line_id = fields.Many2one('project.progress.plan', string='Actual Cashout', ondelete='cascade')
    code = fields.Char('Source', help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total PO & CVR")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectPlanCashin(models.Model):
    _name = 'project.plan.cashin'

    name = fields.Float(string='Cash In')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_plan_cashin_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')

    @api.depends('plan_plan_cashin_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_cashin_id'):
            seq = 1
            for line in order.project_plan_cashin_line:
                line.seq = seq
                seq += 1


class ProjectActualCashin(models.Model):
    _name = 'project.actual.cashin'
    _description = 'Actual Cash In '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Payment Date')
    actual_cashin_line_id = fields.Many2one('project.progress.plan', string='Actual Cash In ', ondelete='cascade',
                                            index=True)
    amount = fields.Float(string="Total", help="Amount of Total Cash In")
    currency_id = fields.Many2one('res.currency')
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectPlanInvoice(models.Model):
    _name = 'project.plan.invoice'

    name = fields.Float(string='Invoice')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_plan_invoice_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')

    @api.depends('plan_plan_invoice_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_invoice_id'):
            seq = 1
            for line in order.project_plan_invoice_line:
                line.seq = seq
                seq += 1


class ProjectActualInvoice(models.Model):
    _name = 'project.actual.invoice'
    _description = 'Actual Invoice '

    name = fields.Char(string='Number')
    created_date = fields.Date(string='Invoice Date')
    actual_invoice_line_id = fields.Many2one('project.progress.plan', string='Actual Invoice', ondelete='cascade',
                                             index=True)
    amount = fields.Float(string="Total", help="Amount of Total Invoice")
    amount_company_signed = fields.Float(string="Total Company Signed", help="Amount of Total Invoice")
    currency_id = fields.Many2one('res.currency')
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectPlanManhour(models.Model):
    _name = 'project.plan.manhour'

    name = fields.Float(string='Manhour')
    seq = fields.Char(string='No', compute="_compute_get_number")
    date = fields.Date(string='Tanggal')
    plan_plan_manhour_id = fields.Many2one('project.progress.plan', string='Project', ondelete='cascade')

    @api.depends('plan_plan_manhour_id')
    def _compute_get_number(self):
        for order in self.mapped('plan_plan_manhour_id'):
            seq = 1
            for line in order.project_plan_manhour_line:
                line.seq = seq
                seq += 1


class ProjectActualManhour(models.Model):
    _name = 'project.actual.manhour'
    _description = 'Actual Manhour '

    name = fields.Char(string='Name')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    actual_manhour_line_id = fields.Many2one('project.progress.plan', string='Actual Manhour', ondelete='cascade',
                                             index=True)
    total = fields.Integer(string="Total Hours", help="Amount of Total Manhour")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectEstimatedCashout(models.Model):
    _name = 'project.estimated.cashout'
    _description = 'Estimated cashout '

    name = fields.Char(string='Number')
    created_date = fields.Date(string='Created Date')
    estimated_cashout_line_id = fields.Many2one('project.progress.plan', string='Actual Cashout', ondelete='cascade',
                                                index=True)
    code = fields.Char('Source', help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total PO&CVR")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectActualPlanCashout(models.Model):
    _name = 'project.actual.plan.cashout'
    _description = 'Actual and Plan cashout '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Date')
    actual_cashout_plan_line_id = fields.Many2one('project.progress.plan', string='Actual Cashout', ondelete='cascade')
    code = fields.Char('Source', help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total PO & CVR")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectActualPlanCurve(models.Model):
    _name = 'project.actual.plan.curve'
    _description = 'Actual and Plan Curve '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Date')
    actual_curve_plan_line_id = fields.Many2one('project.progress.plan', string='Actual Curve', ondelete='cascade')
    code = fields.Char('Source', help="Testing")
    amount = fields.Float(string="Total", help="Testing")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')

class ProjectActualPlanCashin(models.Model):
    _name = 'project.actual.plan.cashin'
    _description = 'Actual and Plan Cashin '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Date')
    actual_cashin_plan_line_id = fields.Many2one('project.progress.plan', string='Actual Cashin', ondelete='cascade')
    code = fields.Char('Source', help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectActualPlanInvoice(models.Model):
    _name = 'project.actual.plan.invoice'
    _description = 'Actual and Plan invoice '

    name = fields.Char(string='Number')
    payment_date = fields.Date(string='Date')
    actual_invoice_plan_line_id = fields.Many2one('project.progress.plan', string='Actual Invoice', ondelete='cascade')
    code = fields.Char('Source', help="The code that can be used")
    amount = fields.Float(string="Total", help="Amount of Total")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')


class ProjectActualPlanManhour(models.Model):
    _name = 'project.actual.plan.manhour'
    _description = 'Actual and Plan Manhour '

    name = fields.Char(string='Number')
    date = fields.Date(string='Date')
    actual_manhour_plan_line_id = fields.Many2one('project.progress.plan', string='Actual manhour', ondelete='cascade')
    code = fields.Char('Source', help="The code that can be used")
    total = fields.Float(string="Total", help="Amount of Total")
    project = fields.Many2one('project.project', string='Project', track_visibility='onchange')
