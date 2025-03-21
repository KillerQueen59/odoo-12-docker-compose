# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from werkzeug import url_encode

class HrExpenseAdvanceRegisterPaymentWizard(models.TransientModel):

    _name = "hr.expense.advance.register.payment.wizard"
    _description = "Expense Advance Register Payment Wizard"

    @api.model
    def _default_partner_id(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_advance = self.env['hr.expense.advance'].browse(active_ids)
        return expense_advance.address_id.id or expense_advance.employee_id.id and expense_advance.employee_id.address_home_id.id

    @api.model
    def _default_project(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_advance = self.env['hr.expense.advance'].browse(active_ids)
        return expense_advance.project_id.id

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, default=_default_partner_id)
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account")
    journal_id = fields.Many2one('account.journal', string='Payment Method', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True, required=True)
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Type', required=True)
    amount = fields.Monetary(string='Payment Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)

    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True)
    communication = fields.Char(string='Memo')
    hide_payment_method = fields.Boolean(compute='_compute_hide_payment_method',
        help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")
    show_partner_bank_account = fields.Boolean(compute='_compute_show_partner_bank', help='Technical field used to know whether the field `partner_bank_account_id` needs to be displayed or not in the payments form views')

    payment_difference = fields.Monetary(string='Difference Amount', compute='_compute_payment_difference', readonly=True)
    payment_difference_handling = fields.Selection([ ('full', 'Mark as fully paid'),('partial', 'Mark as Partial Payment')], default="full", string="Payment Difference Handling", copy=False)
    project = fields.Many2one('project.project', 'Project', default=_default_project)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        active_ids = self._context.get('active_ids', [])
        expense_advance = self.env['hr.expense.advance'].browse(active_ids)
        if expense_advance.employee_id.id and expense_advance.employee_id.sudo().bank_account_id.id:
            self.partner_bank_account_id = expense_advance.employee_id.sudo().bank_account_id.id
        elif self.partner_id and len(self.partner_id.bank_ids) > 0:
            self.partner_bank_account_id = self.partner_id.bank_ids[0]
        else:
            self.partner_bank_account_id = False

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        if not self.amount > 0.0:
            raise ValidationError(_('The payment amount must be strictly positive.'))

    @api.depends('payment_method_id')
    def _compute_show_partner_bank(self):
        """ Computes if the destination bank account must be displayed in the payment form view. By default, it
        won't be displayed but some modules might change that, depending on the payment type."""
        for payment in self:
            payment.show_partner_bank_account = payment.payment_method_id.code in self.env['account.payment']._get_method_codes_using_bank_account()

    @api.one
    @api.depends('journal_id')
    def _compute_hide_payment_method(self):
        if not self.journal_id:
            self.hide_payment_method = True
            return
        journal_payment_methods = self.journal_id.outbound_payment_method_ids
        self.hide_payment_method = len(journal_payment_methods) == 1 and journal_payment_methods[0].code == 'manual'

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.journal_id.outbound_payment_method_ids
            self.payment_method_id = payment_methods and payment_methods[0] or False
            # Set payment method domain (restrict to methods enabled for the journal and to selected payment type)
            return {'domain': {'payment_method_id': [('payment_type', '=', 'outbound'), ('id', 'in', payment_methods.ids)]}}
        return {}

    def _get_payment_vals(self):
        """ Hook for extension """
        return {
            'partner_type': 'supplier',
            'payment_type': 'outbound',
            'partner_id': self.partner_id.id,
            'partner_bank_account_id': self.partner_bank_account_id.id,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'payment_method_id': self.payment_method_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'payment_date': self.payment_date,
            'communication': self.communication,
            'project': self.project.id,
        }

    @api.multi
    def expense_advance_post_payment(self):
        self.ensure_one()
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_advance = self.env['hr.expense.advance'].browse(active_ids)

        # Create payment and post it
        payment = self.env['account.payment'].create(self._get_payment_vals())
        payment.post()

        if self.payment_difference_handling == 'full':
            expense_advance.write({'state': 'paid', 'payment_id': payment.id})
        else:
             expense_advance.write({'state': 'partial', 'payment_id': payment.id})

        # Log the payment in the chatter
        body = (_("A payment of %s %s with the reference <a href='/mail/view?%s'>%s</a> related to your expense advance %s has been made.") %
                (payment.amount, payment.currency_id.symbol, url_encode({'model': 'account.payment', 'res_id': payment.id}), payment.name, expense_advance.name))
        expense_advance.message_post(body=body)
        return {'type': 'ir.actions.act_window_close'}

    @api.one
    @api.depends('amount','payment_date')
    def _compute_payment_difference(self):
            self.payment_difference = self._compute_total_advance_amount() - self.amount

    def _compute_total_advance_amount(self):
        """ Compute the sum of the residual of Aadvance, expressed in the payment currency """
        expense_advance = self._get_expense_advance()

        total = 0
        for inv in expense_advance:
            total += inv.residual_amount
        return abs(total)

    def _get_expense_advance(self):
        return self.env['hr.expense.advance'].browse(self._context.get('active_ids'))

