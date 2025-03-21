from odoo import models, fields, api, _
from odoo.exceptions import UserError
from werkzeug import url_encode

class HrExpenseAdvanceRegisterPaymentWizard(models.TransientModel):
    _inherit = 'hr.expense.advance.register.payment.wizard'

    @api.model
    def _default_transfer_to(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_advance = self.env['hr.expense.advance'].browse(active_ids)
        return expense_advance.address_id.journal_petty_cash or expense_advance.employee_id.id and expense_advance.employee_id.address_home_id.journal_petty_cash

    @api.model
    def _default_journal_id(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_advance = self.env['hr.expense.advance'].browse(active_ids)
        return expense_advance.journal_id

    @api.model
    def _default_memo(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        advance_id = self.env['hr.expense.advance'].browse(active_ids)
        return advance_id.name or None

    transfer_to = fields.Many2one('account.journal', string='Transfer To', default=_default_transfer_to,
                                  domain="['|',('type', '=', 'bank'), ('type', '=', 'cash')]")

    journal_id = fields.Many2one('account.journal', string='Payment Method', required=True, domain=[('type', '=', 'bank')])
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    hide_transfer_to = fields.Boolean(compute='_compute_hide_transfer_to', default=True)
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Type', required=True)
    communication = fields.Char(string='Memo', default=_default_memo)

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        cur = self.journal_id.bank_account_id.currency_id

        self.currency_id = cur if cur else None


    @api.depends('transfer_to')
    def _compute_hide_transfer_to(self):
        context = dict(self._context or {})
        transaction_type = context.get('transaction_type', None)
        if transaction_type == 'petty_cash':
            self.hide_transfer_to = False
        else:
            self.hide_transfer_to = True

    def _get_payment_vals(self):
        vals = super(HrExpenseAdvanceRegisterPaymentWizard, self)._get_payment_vals()
        if self._context.get('transaction_type', None) == 'petty_cash':
            vals['payment_type'] = 'transfer'
            vals['destination_journal_id'] = self.transfer_to.id
        return vals


class HrExpenseReimbursmentRegisterPaymentWizard(models.TransientModel):
    _inherit = 'hr.expense.sheet.register.payment.wizard'

    @api.model
    def _default_transfer_to(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)

        return expense_sheet.address_id.journal_petty_cash or expense_sheet.employee_id.id and expense_sheet.employee_id.address_home_id.journal_petty_cash



    @api.model
    def _default_sheet_journal_id(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)
        return expense_sheet.bank_journal_id


    transfer_to = fields.Many2one('account.journal', string='Transfer To', 
                                  domain="['|',('type', '=', 'bank'), ('type', '=', 'cash')]")
    journal_id = fields.Many2one('account.journal', string='Payment Method', required=True, default=_default_sheet_journal_id, domain=[('type', 'in', ('bank', 'cash'))])
    paid_to = fields.Many2one('hr.employee', string="Paid To")
    rekening_no = fields.Char(string="Rekenig No")
    bank_name = fields.Char(string="Bank")

    @api.onchange('transfer_to')
    def _onchange_transfer_to(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)
        self.paid_to = expense_sheet.paid_to.id
        self.transfer_to = expense_sheet.paid_to.address_home_id.journal_petty_cash
        self.rekening_no = expense_sheet.paid_to.address_home_id.journal_petty_cash.bank_account_id.acc_number
        self.bank_name = expense_sheet.paid_to.address_home_id.journal_petty_cash.bank_id.name
    

    # @api.onchange('partner_id')
    # def _onchange_partner(self):
    #     self.journal_id = self.partner_id.journal_petty_cash

    @api.model
    def _default_memo(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        sheet = self.env['hr.expense.sheet'].browse(active_ids)
        return sheet.name or None

    communication = fields.Char(string='Memo', default=_default_memo)

    @api.multi
    def expense_post_payment(self):
        self.ensure_one()
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)

        if not expense_sheet.return_to_employee:
            raise UserError(_("Employee need to payback to company, no payment will be created."))

        # Create payment and post it
        payment = self.env['account.payment'].create(self._get_payment_vals())
        payment.post()

        expense_sheet.write({'state': 'done'})
        
        # Log the payment in the chatter
        body = (_(
            "A payment of %s %s with the reference <a href='/mail/view?%s'>%s</a> related to your expense %s has been made.") % (
                payment.amount, payment.currency_id.symbol,
                url_encode({'model': 'account.payment', 'res_id': payment.id}), payment.name, expense_sheet.name))
        expense_sheet.message_post(body=body)

        # Reconcile the payment and the expense, i.e. lookup on the payable account move lines
        account_move_lines_to_reconcile = self.env['account.move.line']
        for line in payment.move_line_ids + expense_sheet.expense_advance_id.payment_id.move_line_ids + expense_sheet.account_move_id.line_ids:
            if line.account_id.internal_type == 'payable' and not line.reconciled:
                account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.reconcile()
        return {'type': 'ir.actions.act_window_close'}

