from odoo import _, api, fields, models
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import float_compare
from datetime import date, datetime
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare, \
    pycompat, date_utils

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _get_default_seq(self):
        return self.env['ir.sequence'].next_by_code('rnet.invoice')
    
    @api.model
    def _get_default_debit_note(self):
        return self.env['ir.sequence'].next_by_code('rnet.invoice.debit.note')
    
    @api.model
    def _get_default_proforma_invoice(self):
        return self.env['ir.sequence'].next_by_code('rnet.invoice.proforma.invoice')

    date_invoice = fields.Date('Invoice Date', default=fields.Date.context_today, track_visibility='always')
    project = fields.Many2one('project.project', track_visibility='always',)
    num_word = fields.Char(string="Say:", compute='_compute_amount_in_word')
    num_word_without_tax = fields.Char(string="Say:", compute='_compute_amount_in_word')
    num_word_hyundai = fields.Char(string="Say:", compute='_compute_amount_in_word')
    num_word_rapp = fields.Char(string="Say:", compute='_compute_amount_in_word')
    po_no = fields.Many2one('project.po.line', string="PO No",)
    number = fields.Char(default=_get_default_seq)
    number_debit_note = fields.Char(default=_get_default_debit_note)
    number_proforma_invoice = fields.Char(default=_get_default_proforma_invoice)
    gut_invoice_remark = fields.Text(string="Remark")
    invoice_type = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('full_payment', 'Full Payment'),
        ('partial', 'Partial'),
        ('retention', 'Retention'), ],
        string="Invoice Type",
        track_visibility='onchange',
    )
    customer_type = fields.Selection([
        ('gut_standar', 'GUT STANDAR'),
        ('gut_rapp', 'GUT RAPP'),
        ('gut_hyundai', 'GUT HYUNDAI'),
        ('gut_donghwa', 'GUT DONGHWA'), 
        ('gut_shinbo', 'GUT SHINBO'), ],
        string="Customer Type",
        track_visibility='onchange', required=True
    )
    type_invoice = fields.Selection([
        ('type_invoice', 'Invoice'),
        ('type_debit_note', 'Debit Note'), ],
        string="Type",
        track_visibility='onchange', required=True
    )

    account_id = fields.Many2one('account.account', string='Account',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'open': [('readonly', False)]},  domain=[('user_type_id.type', 'in', ('other','receivable'))], help="The partner account used for this invoice.")

    invoice_line_ids = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines', oldname='invoice_line',
        readonly=True, states={'draft': [('readonly', False)], 'open': [('readonly', False)]}, copy=True)  
    
    active = fields.Boolean(
        default=True)

    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        for rec in self:
           if rec.type_invoice == 'type_debit_note':
                rec.number = rec.number_debit_note

        return res

# change get debit/credit account move line from inv.sub_total 
    @api.model
    def invoice_line_move_line_get(self):
        res = []
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            if line.quantity==0:
                continue
            tax_ids = []
            for tax in line.invoice_line_tax_ids:
                tax_ids.append((4, tax.id, None))
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        tax_ids.append((4, child.id, None))
            analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]

            move_line_dict = {
                'invl_id': line.id,
                'type': 'src',
                'name': line.name,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price': self.sub_total, #change this 20240715
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'analytic_tag_ids': analytic_tag_ids,
                'tax_ids': tax_ids,
                'invoice_id': self.id,
            }
            res.append(move_line_dict)
        return res
        
    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = inv.with_context(ctx).payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
                res_amount_currency = total_currency
                ctx['date'] = inv._get_currency_rate_date()
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or inv.date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
                'project': inv.project.id,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
        return True

    @api.multi
    def _compute_amount_in_word(self):
        for rec in self:
            word_total = str(rec.currency_id.amount_to_text(rec.amount_total))
            word_amount_untaxed = str(rec.currency_id.amount_to_text(rec.amount_untaxed_signed))
            word_hyundai= str(rec.currency_id.amount_to_text(rec.payable_net))
            word_rapp= str(rec.currency_id.amount_to_text(rec.payable_net))
            rec.num_word = word_total.replace(',', '')
            rec.num_word_without_tax = word_amount_untaxed.replace(',', '')
            rec.num_word_hyundai = word_hyundai.replace(',', '')
            rec.num_word_rapp = word_rapp.replace(',', '')

# onchange project
    @api.onchange('project')
    def on_change_project(self):
        for rec in self:

            return {'domain': {'po_no': [('project_id', '=', rec.project.id)]}}


    # @api.depends('project',)       
    # def compute_project_po_no(self):
    #     for rec in self:
    #         data_obj = self.env['project.po.line'].search([('project_id', '=', rec.project.id), ])
    #         for record in data_obj:
    #             if rec.project:
    #                 rec.po_no = record[:1]

# copy dari addons sale_discount_total
    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'amount_tax','ap_deduction','retention_deduction', 'less_dp_amount','sub_total', 'discount_rate','amount_discount',
                 'currency_id','customer_type')
    def _compute_amount(self):
        for order in self:
            for line in order.invoice_line_ids:
                if line.price_unit > 0.00:
                    if order.less_dp_amount > 0.00:
                        round_curr = self.currency_id.round
                        self.amount_discount = order.discount_rate
                        self.amount_less_dp= order.less_dp_amount
                        self.amount_pph = (line.price_subtotal - order.less_dp_amount) * sum(round_curr(line.amount) for line in line.invoice_line_tax_ids.filtered(lambda x: x.name != '11%')) / 100  if line.invoice_line_tax_ids else False
                        self.direct_amount = order.amount_direct
                        self.indirect_amount = order.amount_indirect
                        self.ap_deduction_amount = order.ap_deduction
                        self.retention_deduction_amount = order.retention_deduction
                        self.other_deduction_amount = order.other_deduction
                        self.subtotal_invoice_shinbo = line.price_subtotal - (order.ap_deduction + order.retention_deduction + order.other_deduction)
                        self.amount_untaxed += line.price_subtotal
                        self.amount_after_disc = order.amount_untaxed - order.amount_discount
                        self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids.filtered(lambda x: x.name == '11%')) if line.invoice_line_tax_ids else False
                    else:
                        round_curr = self.currency_id.round
                        self.amount_discount = order.discount_rate
                        self.amount_less_dp= order.less_dp_amount
                        self.amount_pph = sum(round_curr(line.amount) for line in self.tax_line_ids.filtered(lambda x: x.name != '11%')) if line.invoice_line_tax_ids else False
                        self.direct_amount = order.amount_direct
                        self.indirect_amount = order.amount_indirect
                        self.ap_deduction_amount = order.ap_deduction
                        self.retention_deduction_amount = order.retention_deduction
                        self.other_deduction_amount = order.other_deduction
                        self.subtotal_invoice_shinbo = line.price_subtotal - (order.ap_deduction + order.retention_deduction + order.other_deduction)
                        self.amount_untaxed += line.price_subtotal
                        self.amount_after_disc = order.amount_untaxed - order.amount_discount
                        self.amount_tax = sum(round_curr(line.amount) for line in self.tax_line_ids.filtered(lambda x: x.name == '11%')) if line.invoice_line_tax_ids and order.type in ('out_invoice','out_refund') else sum(round_curr(line.amount) for line in self.tax_line_ids)

        if order.customer_type == 'gut_standar':
            self.amount_total = self.sub_total + self.amount_tax - self.amount_pph
        elif order.customer_type == 'gut_shinbo':
            self.amount_total = self.subtotal_invoice_shinbo - self.amount_pph
        elif order.type in ('in_invoice','in_refund'):
            self.amount_total = self.amount_untaxed + self.amount_tax
        else:
            self.amount_total = self.sub_total + self.amount_tax - self.amount_pph - self.retention_5

        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed

        if self.currency_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date_invoice or fields.Date.today())
            amount_untaxed_signed = currency_id._convert(self.amount_untaxed, self.company_id.currency_id,  self.company_id, self.date_invoice or fields.Date.today())
            self.amount_total = self.amount_untaxed
            self.amount_tax = 0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign
       



    discount_type = fields.Selection([('amount', 'Amount'),('percent', 'Percentage')], string='Discount Type',
                                     readonly=True, states={'draft': [('readonly', False)]}, default='amount')
    discount_rate = fields.Monetary('Discount', readonly=True, states={'draft': [('readonly', False)], 'open': [('readonly', False)]})
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_compute_amount',
                                      track_visibility='always')
    amount_after_disc = fields.Monetary(string='Total after disc', store=True, readonly=True, compute='_compute_amount',
                                     track_visibility='always')
    paid_amount = fields.Monetary(string='Paid Amount', compute="_get_paid_amount_invoice")

    work_value = fields.Monetary(string='Work Value', compute="_compute_get_value_hyundai")
    advance_paymnet = fields.Monetary(string='Advacne Payment Deduction', compute="_compute_get_value_hyundai")
    retention_hyundai = fields.Monetary(string='Retention', compute="_compute_get_value_hyundai")
    work_value_net = fields.Monetary(string='Work Value Net', compute="_compute_get_value_hyundai")
    vat_hyundai = fields.Monetary(string='VAT 11% Hyundai', compute="_compute_get_value_hyundai")
    with_holding = fields.Monetary(string='WithHolding Tax', compute="_compute_get_value_hyundai")
    payable_net = fields.Monetary(string='Payable Net', compute="_compute_get_value_hyundai")
    sub_total = fields.Monetary(string='Sub Total', compute="_compute_get_subtotal")
    sub_total_2 = fields.Monetary(string='Sub Total II', compute="_compute_get_subtotal")
    less_dp_persen = fields.Float(string="%")
    less_dp_amount = fields.Monetary(string="Less DP")
    amount_less_dp = fields.Monetary(string='Less DP', store=True, readonly=True, compute='_compute_amount',
                                      track_visibility='always')
    pph_265 = fields.Monetary(string="pph 2,65%", states={'draft': [('readonly', False)], 'open': [('readonly', False)]})
    pph_265_persen = fields.Float(string="%", default="2.65")
    amount_pph = fields.Monetary(string='PPh', store=True, readonly=True, compute='_compute_amount',
                                      track_visibility='always')
    retention_5 = fields.Monetary(string="Retention 5%", compute="_compute_pph_retention")
    amount_direct = fields.Monetary(string="Direct Amount")
    direct_amount = fields.Monetary(string="Direct Amount", compute='_compute_amount')
    amount_indirect = fields.Monetary(string="indirect Amount")
    indirect_amount = fields.Monetary(string="Indirect Amount",compute='_compute_amount')
    ap_deduction = fields.Monetary(string="AP Deduction")
    ap_deduction_amount = fields.Monetary(string="AP Deduction", compute='_compute_amount')
    retention_deduction = fields.Monetary(string="Retention Deduction")
    retention_deduction_amount = fields.Monetary(string="Retention Deduction", compute='_compute_amount')
    other_deduction = fields.Monetary(string="Other Deduction")
    other_deduction_amount = fields.Monetary(string="Other Deduction", compute='_compute_amount')
    subtotal_invoice_shinbo = fields.Monetary(string="Subtotal Invoice", compute='_compute_amount')
    rounded_total_rapp = fields.Monetary(string="Rounded Total")


    @api.one
    @api.depends('amount_untaxed', 'amount_total_signed', 'amount_tax', 'amount_after_disc','amount_discount','less_dp_amount')
    def _compute_get_subtotal(self):
        for rec in self:
            total = rec.amount_untaxed - rec.less_dp_amount
            total_2 = total + rec.amount_tax
            rec.sub_total = total
            rec.sub_total_2 = total_2
            

    @api.multi
    def _compute_get_value_hyundai(self):
        for rec in self:
            total = rec.project.amount / 100 * 6.66
            rec.work_value = total
            rec.advance_paymnet = total / 100 * 10
            rec.retention_hyundai = total / 100 * 10
            rec.work_value_net = total - rec.advance_paymnet - rec.retention_hyundai
            rec.vat_hyundai = rec.work_value_net / 100 * 11
            rec.with_holding = rec.work_value_net / 100 * 2.65
            rec.payable_net = rec.work_value_net - rec.vat_hyundai -  rec.with_holding


    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=self.date or self.date_invoice or fields.Date.context_today(self))
                line['currency_id'] = currency.id
                line['amount_currency'] = currency.round(line['price'])
                line['price'] = currency.compute(line['price'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = line['price']
            if self.type in ('out_invoice', 'in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, invoice_move_lines
    
    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in self._get_aml_for_amount_residual():
            residual_company_signed += line.amount_residual 
            if line.currency_id == self.currency_id:
                residual += line.amount_residual_currency - self.amount_pph if line.currency_id else line.amount_residual
            else:
                if line.currency_id:
                    residual += line.currency_id._convert(line.amount_residual_currency, self.currency_id, line.company_id, line.date or fields.Date.today()) - self.amount_pph
                else:
                    residual += line.company_id.currency_id._convert(line.amount_residual, self.currency_id, line.company_id, line.date or fields.Date.today()) - self.amount_pph
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        self.residual = abs(residual)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False

# get retention
    @api.one
    @api.depends('amount_untaxed', 'amount_tax', 'amount_after_disc','amount_discount','sub_total',)
    def _compute_pph_retention(self):
        for order in self:
            total_retention = 0.0

            total_retention= order.amount_after_disc / 100 * 5
            order.retention_5 = total_retention

# paid amount invoice
    def _get_paid_amount_invoice(self):
        for inv in self:
            inv.paid_amount = 0.0
            if inv.state != 'draft' and inv.residual <= inv.amount_total:
                inv.paid_amount = inv.amount_total - inv.residual

#override onchnage partner_id account_id  
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        bank_id = False
        warning = {}
        domain = {}
        company_id = self.company_id.id
        p = self.partner_id if not company_id else self.partner_id.with_context(force_company=company_id)
        type = self.type
        if p:
            rec_account = p.property_account_receivable_id
            pay_account = p.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('out_invoice', 'out_refund'):
                account_id = rec_account.id
                payment_term_id = p.property_payment_term_id.id
            else:
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term_id.id

            delivery_partner_id = self.get_delivery_partner_id()
            fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id, delivery_id=delivery_partner_id)

            # If partner has no warning, check its company
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                # if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                #     p = p.parent_id
                # warning = {
                #     'title': _("Warning for %s") % p.name,
                #     'message': p.invoice_warn_msg
                #     }
                if p.invoice_warn == 'block':
                    self.partner_id = False

        self.account_id = False
        self.payment_term_id = payment_term_id
        self.date_due = False
        self.fiscal_position_id = fiscal_position

        if type in ('in_invoice', 'out_refund'):
            bank_ids = p.commercial_partner_id.bank_ids
            bank_id = bank_ids[0].id if bank_ids else False
            self.partner_bank_id = bank_id
            domain = {'partner_bank_id': [('id', 'in', bank_ids.ids)]}

        res = {}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    project_id = fields.Many2one('project.project',
                                   string='Project',
                                   store=True,)
    po_line_id = fields.Many2one('project.po.line',
                                   string='PO',
                                   store=True, )
    name = fields.Text(default="Description")
    no_site = fields.Char(default="No Site", required=True)

    discount = fields.Monetary(string='Discount')

# override compute price subtotal
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * self.quantity
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = price - self.discount
        if self.invoice_id.currency_id and self.invoice_id.company_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign


# onchange project PO
    @api.onchange('po_line_id')
    def on_change_project_po_no(self):
        for order in self:
            pro = order.po_line_id.project_id
            site = order.po_line_id.po_no_site
            desc = order.po_line_id.po_desc
            order.project_id = pro if pro else None 
            order.no_site = site if site else None
            order.name = desc if desc else None