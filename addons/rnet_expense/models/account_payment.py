from odoo import _, api, fields, models


class account_payment(models.Model):
    _inherit = 'account.payment'

    @api.onchange('currency_id')
    def _onchange_currency(self):
        super(account_payment, self)._onchange_currency()

        context = self.env.context
        if context.get('receive_payment') or context.get('register_payment'):
            lpj = self.env['hr.expense.sheet'].search(
                [('id', '=', context.get('active_id'))])
            self.amount = abs(lpj.return_amount)

    @api.multi
    def post(self):
        res = super(account_payment, self).post()

        context = self.env.context
        active_id = context.get('active_id')
        lpj = self.env['hr.expense.sheet'].search([('id', '=', active_id)])

        if lpj:
            if context.get('receive_payment'):
                lpj.write({'returned_amount': lpj.returned_amount + self.amount, })
            elif context.get('register_payment'):
                lpj.write({'returned_amount': lpj.returned_amount + (-abs(self.amount)), })
                # lpj.write({'returned_amount': -abs(self.amount), })
            else:
                lpj.write({'returned_amount': lpj.returned_amount + (-abs(self.amount)), })

        return res

    @api.model
    def default_get(self, _fields):
        rec = super(account_payment, self).default_get(_fields)
        context = self.env.context

        if context.get('receive_payment'):
            lpj = self.env['hr.expense.sheet'].search(
                [('id', '=', context.get('active_id'))])
            payment_method_id = self.env['account.payment.method'].search(
                [('code', '=', 'manual'), ('payment_type', '=', 'outbound')])

            rec['communication'] = "Return " + lpj.name
            rec['payment_type'] = 'transfer'
            rec['payment_method_id'] = payment_method_id.id
            rec['payment_date'] = fields.date.today()
            rec['journal_id'] = lpj.employee_id.address_home_id.journal_petty_cash.id
            # rec['destination_journal_id'] = lpj.bank_journal_id.id
            rec['currency_id'] = lpj.currency_id.id
            rec['amount'] = lpj.return_amount
        elif context.get('register_payment'):
            lpj = self.env['hr.expense.sheet'].search(
                [('id', '=', context.get('active_id'))])
            payment_method_id = self.env['account.payment.method'].search(
                [('code', '=', 'manual'), ('payment_type', '=', 'outbound')])

            rec['communication'] = lpj.expense_advance_id.seq_num
            rec['payment_type'] = 'transfer'
            rec['payment_method_id'] = payment_method_id.id
            rec['payment_date'] = fields.date.today()
            rec['journal_id'] = lpj.bank_journal_id.id
            rec['destination_journal_id'] = lpj.employee_id.address_home_id.journal_petty_cash.id
            rec['currency_id'] = lpj.currency_id.id
            rec['amount'] = lpj.return_amount
        return rec
