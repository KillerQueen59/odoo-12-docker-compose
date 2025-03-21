
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import email_split, float_is_zero, pycompat
from .validator import ExpenseValidator
from datetime import date, datetime
from odoo import exceptions
from werkzeug import url_encode

class Sheet(models.Model):
    _inherit = 'hr.expense.sheet'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('cancel', 'Refused'),
        ('approve', 'Approved'),
        ('reject_control', 'Refused'),
        ('approve_cost_control', 'Checked'),
        ('approve_technical_director', 'Approved by Project Director'),
        ('approve_finance_director', 'Approved by Finance Director'),
        ('reject_technical', 'Refused'),
        ('reject_finance', 'Refused'),
        ('post', 'Posted'),
        # ('done', 'Paid'),

        

    ], string='Status', index=True, readonly=True, track_visibility='onchange', copy=False, default='draft', required=True, help='Expense Report State')

    flow_petty_cash = fields.Selection(related='state')
    flow_reimburse = fields.Selection(related='state')

    is_approve_technical = fields.Boolean('Is Approve Technical')
    is_approve_finance = fields.Boolean('Is Approve Finance')
    show_post_journal_entries = fields.Boolean('Show Post Jurnal Entries')
   

    def _default_payment_mode(self):
        transaction_type = self.env.context.get('transaction_type')
        if transaction_type == 'petty_cash' or transaction_type == 'expense_report':
            return 'company_account'
        elif transaction_type == 'hutang_usaha':
            return 'own_account'
        else:
            return None

    def _get_default_cost_control_head(self):
        job_id = self.env['hr.job'].search([('name', '=', 'Acc, Finance & Tax Head Section')])
        employee_id = self.env['hr.employee'].search([('job_id', '=', job_id.id)])
        return employee_id

    def _get_default_finance_director(self):
        job_id = self.env['hr.job'].search([('name', '=', 'Finance Director')])
        employee_id = self.env['hr.employee'].search(
            [('job_id', '=', job_id.id)])
        return employee_id

    def _get_default_technical_director(self):
        job_id = self.env['hr.job'].search([('name', '=', 'Technical Director')])
        employee_id = self.env['hr.employee'].search(
            [('job_id', '=', job_id.id)])
        return employee_id

    @api.multi
    def _compute_current_user_is_requester(self):
        for req in self:
            req.current_user_is_requester = True if req.employee_id.user_id == req.env.user else False

    @api.model
    def _default_account_journal_id(self):
        return self.env['account.journal'].search([('type', 'in', ('bank', 'cash')), ('company_id', '=', self.env.user.company_id.id)], limit=1)

    @api.model
    def _default_expense_journal_id(self):
        return self.env['account.journal'].search([('name', '=', 'CVR') ])

    @api.one
    def _default_expense_bank_journal_id(self):
        return self.env['account.journal'].search([('type', 'in', 'cash') ])
    
    journal = fields.Many2one('account.journal', string='Payment Method', domain=[('type', 'in', ('bank', 'cash'))], default=_default_account_journal_id)
    
    bank_journal_id = fields.Many2one('account.journal', required=True, string='Bank Journal', default=_default_expense_bank_journal_id, help="The payment method used when the expense is paid by the company.")
    name = fields.Char(string='CVR No.',
                     required=True, default='New', track_visibility='onchange',)
    seq = fields.Char(string='CVR seq.', track_visibility='always')
    transaction_type = fields.Selection([('petty_cash', 'Cash Advance'), ('hutang_usaha', 'Reimbursement'), ('expense_report', 'Expense Report'),],
                                        'Transaction Type')
    project = fields.Many2one('project.project', string='Project', track_visibility='always', required=True,)
    expense_advance_id = fields.Many2one('hr.expense.advance', string="BAR Expense Advance", readonly=True, states={
                                         'draft': [('readonly', False)]}, )
    returned_amount = fields.Monetary(
        string="Returned Amount", currency_field='currency_id',)
    advance_amount = fields.Monetary(
        string="Advance Amount", related='expense_advance_id.payment_id.amount', currency_field='advance_currency_id')
    balance = fields.Monetary(
        'Balance', compute='cal_return_amount', store=True, track_visibility='always')

    user_id = fields.Many2one('res.users', 'Project Manager', related='project.project_manager.user_id',
                              readonly=True, states={}, copy=False, track_visibility='onchange', oldname='responsible_id')
    project_manager_id = fields.Many2one('hr.employee', 'Project Manager', related='project.project_manager',
                              readonly=True, states={}, copy=False, track_visibility='onchange', oldname='responsible_id')
    site_manager_id = fields.Many2one('hr.employee', 'Site Manager', related='project.site_manager',
                              readonly=True, states={}, copy=False, track_visibility='onchange', oldname='responsible_id')
 
    # Payment mode aslinya (di addon odoo hr expense) adalah related field ke expense_ids.
    payment_mode = fields.Selection([("company_account", "Company"), ("own_account", "Employee (to reimburse)")],
        related="", string="Paid By", default=_default_payment_mode)

    cost_control_head_id = fields.Many2one('hr.employee', 'Cost Control Head', default=_get_default_cost_control_head)
    technical_director_id = fields.Many2one('hr.employee', 'Project Director', readonly=True, default=_get_default_technical_director)
    finance_director_id = fields.Many2one('hr.employee', 'Finance Director', readonly=True, default=_get_default_finance_director)
    current_user_is_requester = fields.Boolean(string='Current user is requester?', compute='_compute_current_user_is_requester')
    active = fields.Boolean(default=True)
    created_date = fields.Date(  help="Date when the user initiated the request.",
                             default=fields.Date.context_today,
                             track_visibility='onchange', string='Created Date')
    current_user_is_cost_control = fields.Boolean(string='Current user is cost control?', compute='_compute_current_user_is_cost_control')
    current_user_is_technical_director= fields.Boolean(string='Current user is technical director?', compute='_compute_current_user_is_technical_director')
    current_user_is_finance_director= fields.Boolean(string='Current user is finance director?', compute='_compute_current_user_is_finance_director')
    current_user_is_project_manager = fields.Boolean(string='Current user is cost control?', compute='_compute_current_user_is_project_manager')

    reject_control_reason = fields.Text(string="Rejec Reason ", readonly=True, track_visibility='always')
    reject_technical_reason = fields.Text(string="Reject Reason", readonly=True, track_visibility='always')
    reject_finance_reason = fields.Text(string="Reject Reason", readonly=True,track_visibility='always')
    paid_to = fields.Many2one('hr.employee', string="Paid To", track_visibility='always')
    journal_id = fields.Many2one('account.journal',  default=_default_expense_journal_id )
    project_seq = fields.Char( related='project.seq')
    create_date = fields.Datetime(default=datetime.now())
    accounting_date = fields.Date(default=fields.Date.context_today)
    user_ids = fields.Many2many(string='User Ids', comodel_name='res.users')
    refuse_reason = fields.Char( string='Refuse Reason')

    """
    Generate expense report no.
    """
    # @api.model
    # def create(self, values):
    #     employee_id = self.env['hr.employee'].search(
    #         [('id', '=',  values.get('employee_id'))])
    #     partner_id = employee_id.address_home_id
    #     values['journal_petty_cash'] = partner_id.journal_petty_cash.id

    #     validator = ExpenseValidator()
    #     validator.validate_pettycash(values)

        # obj = super(Sheet, self).create(values)
        # if obj.seq == 'New':
        #     seq = self.env['ir.sequence'].next_by_code('expense.no') or 'New'
        #     obj.write({'seq': seq})
        #     for exp in obj.expense_line_ids:
        #         exp.update_seq_no(seq)
        # return obj

    @api.onchange('project')
    def _onchange_expense_project_seq(self):
        seq = self.env['ir.sequence'].next_by_code('hr.expense.sheet.new')
        pro = self.project_seq or 'xxxx'
        result = pro,''.join(seq)
        res = ''.join(str(v) for v in result)
        self.name = res if res else None

# function name jika ingin seperti no PO 
    # @api.multi
    # @api.depends('project')
    # def call_sequence_name_sheet(self):
    #         seq = self.env['ir.sequence'].next_by_code('hr.expense.sheet.new')
    #         pro = self.project_seq or 'xxxx'
    #         result = pro,''.join(seq)
    #         res = ''.join(str(v) for v in result)
    #         self.name =  res

    # @api.model
    # def create(self, vals):

    #     result = super(Sheet, self).create(vals)
    #     result.call_sequence_name_sheet()
    #     return result


    # @api.multi
    # def write(self, values):
    #     transaction_type_changed = values.get('transaction_type')

    #     # cek perubahan partner id juga.
    #     partner_id = self.employee_id.address_home_id

    #     if transaction_type_changed is not None:
    #         # field transaction_type berubah
    #         transaction_type = values.get('transaction_type')
    #     else:
    #         transaction_type = self.transaction_type

    #     values['transaction_type'] = transaction_type
    #     values['journal_petty_cash'] = partner_id.journal_petty_cash.id

    #     validator = ExpenseValidator()
    #     validator.validate_pettycash(values)

    #     del values['journal_petty_cash']
    #     return super(Sheet, self).write(values)

    # compute project, mapping dari project cash advance
    @api.multi
    def _compute_project_cash_advance(self):
        for rec in self.env['hr.expense.advance'].search([('expense_advance_id', '=', self.name)]):
            pro = rec.project_id
            self.project = pro

    @api.onchange('expense_advance_id')
    def _onchange_expense_advance_id(self):
        pro = self.expense_advance_id.project_id
        self.project = pro if pro else None

        transaction_type = self.env.context.get('transaction_type')
        if transaction_type == 'petty_cash':
            self.transaction_type = 'petty_cash'
        elif transaction_type == 'hutang_usaha':
            self.transaction_type = 'hutang_usaha'
        else:
            self.transaction_type = 'expense_report'

    def action_receive_payment(self):
        self.write({'state': 'done'})
        view_id = self.env.ref('rnet_expense.hr_expense_sheet_receive_payment_view_form').id

        return {
            'name': 'Return to Company',
            'view_type': 'form',
            'view_mode': 'tree',
            'views': [(view_id, 'form')],
            'res_model': 'account.payment',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'state': 'done',
            'context': {'receive_payment': True},
        }

    def action_register_payment(self):
        view_id = self.env.ref('account.view_account_payment_form').id
        self.write({'state': 'done'})
        return {
            'name': 'Return to Employee',
            'view_type': 'form',
            'view_mode': 'tree',
            'views': [(view_id, 'form')],
            'res_model': 'account.payment',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'register_payment': True},
        }

    @api.multi
    @api.depends('advance_amount', 'total_amount', 'expense_line_ids.total_amount_company', 'returned_amount')
    def cal_return_amount(self):
        for rec in self:
            super(Sheet, self).cal_return_amount()

            rec.return_amount = abs(rec.advance_amount - rec.total_amount - rec.returned_amount)
            rec.balance = abs(rec.advance_amount - rec.total_amount - rec.returned_amount)

            # logic dari addon bawaan
            diff = rec.total_amount - rec.advance_amount
            rec.return_to_employee = True if diff > 0 else False

# Balance di CVR
    # @api.multi
    # @api.depends('advance_amount', 'total_amount', 'expense_line_ids.total_amount_company', 'returned_amount')
    # def _cal_return_balance(self):
    #         self.balance = self.advance_amount - self.expense_line_ids.total_amount_company - self.returned_amount

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.address_id = self.employee_id.sudo().address_home_id
        self.department_id = self.employee_id.department_id
        # self.bank_journal_id = self.employee_id.sudo().address_home_id.journal_petty_cash
        # self.user_id = self.employee_id.sudo().expense_manager_id or self.employee_id.sudo().parent_id.user_id

# onchange expense journal
    # @api.onchange('paid_to')
    # def _onchange_paid_to(self):
    #     self.journal_id = self.paid_to.sudo().address_home_id.journal_petty_cash

    # set sheet_id ketika lpj di submit
    # sheet_id diperlukan untuk mengambil data rekap.
    # update visibility tombol post jurnal entries
    @api.multi
    def action_submit_sheet(self):
        res = super(Sheet, self).action_submit_sheet()
        if (self.expense_advance_id):
            advance_id = self.env['hr.expense.advance'].search(
                [('id', '=', self.expense_advance_id.id)])
            advance_id.write({
                'sheet_id': self.id
            })
        manager_mail_template = self.env.ref('rnet_expense.email_approval_project_manager_cvr')
        manager_mail_template.send_mail(self.id)
        self._update_post_button_visibility()
        return res

    # remove sheet_id ketika lpj di refuse
    # sheet = lpj
    # update visibility tombol post jurnal entries
    @api.multi
    def refuse_sheet(self, reason):
        res = super(Sheet, self).refuse_sheet(reason)
        if (self.expense_advance_id):
            advance_id = self.env['hr.expense.advance'].search(
                [('id', '=', self.expense_advance_id.id)])
            advance_id.write({
                'sheet_id': None
            })
        self.refuse_reason = reason
        self._update_post_button_visibility()
        return res

    # remove sheet id ketika lpj di reset
    # sheet = lpj
    # update visibility tombol post jurnal entries
    @api.multi
    def reset_expense_sheets(self):
        res = super(Sheet, self).reset_expense_sheets()
        if (self.expense_advance_id):
            advance_id = self.env['hr.expense.advance'].search(
                [('id', '=', self.expense_advance_id.id)])
            advance_id.write({
                'sheet_id': None,
            })
        self._update_post_button_visibility()
        return res

# action butten reset to draft
    @api.multi
    def reset_expense_sheets(self):
        self.create_revision()
        return self.write({'state': 'cancel'})


    # update visibility tombol post jurnal entries
    @api.multi
    def approve_expense_sheets(self):
        res = super(Sheet, self).approve_expense_sheets()
        manager_mail_template = self.env.ref('rnet_expense.email_approval_cost_control_cvr')
        manager_mail_template.send_mail(self.id)
        self.write({'state': 'approve'})
        self._update_post_button_visibility()
        return res

    def approve_cost_control(self):
        transaction_type = self.env.context.get('transaction_type')
        if transaction_type == 'petty_cash':
            manager_mail_template = self.env.ref('rnet_expense.email_approval_technical_director_cvr')
            manager_mail_template.send_mail(self.id)
            self.write({'state': 'approve'})
        else:
            manager_mail_template = self.env.ref('rnet_expense.email_approval_finance_director_cvr')
            manager_mail_template.send_mail(self.id)
        self.write({'state': 'approve_cost_control'})
        self._update_post_button_visibility()

    def approve_technical_director(self):
        self.write({'state': 'approve_technical_director'})
        self._update_post_button_visibility()

    def approve_finance_director(self):
        self.write({'state': 'approve_finance_director'})
        self._update_post_button_visibility()

    @api.multi
    def action_sheet_move_create(self):
        # if any(sheet.state != 'approve' for sheet in self):
        #     raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Expenses must have an expense journal specified to generate accounting entries."))

        expense_line_ids = self.mapped('expense_line_ids')\
            .filtered(lambda r: not float_is_zero(r.total_amount, precision_rounding=(r.currency_id or self.env.user.company_id.currency_id).rounding))
        res = expense_line_ids.action_move_create()
        

        if not self.accounting_date:
            self.accounting_date = self.account_move_id.date

        if self.payment_mode == 'own_account' and expense_line_ids:
            self.write({'state': 'post'})
        else:
            self.write({'state': 'post'})
        self.activity_update()
        self._update_post_button_visibility()
        return res

    
    def _update_post_button_visibility(self):
        transaction_type = self.env.context.get('transaction_type')

        if transaction_type == 'expense_report' and self.state == 'approve':
            self.show_post_journal_entries = True
        elif transaction_type == 'petty_cash' and self.state == 'approve_technical_director':
            self.show_post_journal_entries = True
        elif transaction_type == 'hutang_usaha' and self.state == 'approve_finance_director':
            self.show_post_journal_entries = True
        elif transaction_type == 'hutang_usaha' and self.state == 'approve' and self.project.id == False:
            self.show_post_journal_entries = True
        else:
            self.show_post_journal_entries = False

    @api.onchange('project')
    def _is_approve_technical(self):
        transaction_type = self.env.context.get('transaction_type')

        #if transaction_type == 'petty_cash' and self.project:
        if transaction_type == 'petty_cash':
            self.is_approve_technical = True
        else:
            self.is_approve_technical = False

    @api.onchange('project')
    def _is_approve_finance(self):
        transaction_type = self.env.context.get('transaction_type')

        if transaction_type == 'hutang_usaha' and self.project:
            self.is_approve_finance = True
        else:
            self.is_approve_finance = False

# tombol wizard refuse untuk user cost control
    @api.multi
    def action_refuse_control(self):
        view_id = self.env.ref('rnet_expense.expense_sheet_reject_control_wizard').id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet.control.reject.wizard',
            'target': 'new',
            'state': 'reject_control',
            'type': 'ir.actions.act_window',
            'name': 'CVR',
            'views': [[view_id, 'form']],
            'context': {'expense_sheet_control_id': self.id}
        }

# tombol wizard refuse untuk user technical director di CVR
    @api.multi
    def action_refuse_technical_director(self):
        view_id = self.env.ref('rnet_expense.expense_sheet_reject_technical_wizard').id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet.technical.reject.wizard',
            'target': 'new',
            'state': 'reject_technical',
            'type': 'ir.actions.act_window',
            'name': 'CVR',
            'views': [[view_id, 'form']],
            'context': {'expense_sheet_technical_id': self.id}
        }

# tombol wizard refuse untuk user finance director di Reimbursment
    @api.multi
    def action_refuse_finance_director(self):
        view_id = self.env.ref('rnet_expense.expense_sheet_reject_finance_wizard').id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet.finance.reject.wizard',
            'target': 'new',
            'state': 'reject_finance',
            'type': 'ir.actions.act_window',
            'name': 'CVR',
            'views': [[view_id, 'form']],
            'context': {'expense_sheet_finance_id': self.id}
        }

    @api.multi
    def _compute_current_user_is_cost_control(self):
        for req in self:
            req.current_user_is_cost_control = True if req.cost_control_head_id.user_id == req.env.user and req.state == "approve" else False
    
    @api.multi
    def _compute_current_user_is_project_manager(self):
        for req in self:
            req.current_user_is_project_manager = True if req.project_manager_id.user_id == req.env.user or req.site_manager_id.user_id == req.env.user and req.state == "submit" else False
    

    @api.multi
    def _compute_current_user_is_technical_director(self):
        for req in self:
            req.current_user_is_technical_director = True if req.technical_director_id.user_id == req.env.user and req.state == "approve_cost_control" else False
    
    @api.multi
    def _compute_current_user_is_finance_director(self):
        for req in self:
            req.current_user_is_finance_director = True if req.finance_director_id.user_id == req.env.user and req.state == "approve_cost_control" else False
    

    # validasi date sheet dan  expense harus sama
    # @api.multi
    # def _my_check_method(self):
    #      for rec in self.expense_line_ids:
    #         if rec.date == self.created_date:
    #             return True or False
    # _constraints = [(_my_check_method, 'Created Date dan Date  Tidak Sama! please check again', ['created_date']),]

# validate duplicate no CVR
    @api.constrains('name')
    def _check_name_bar(self):
        if self.name:
            existing_name = self.env['hr.expense.sheet'].search([('id','!=', self.id),('name','=', self.name)])
            if existing_name:
                raise UserError(_("CVR No. is Already Taken " + self.name + ''))

# report expense sheet PCR
    @api.model
    def get_expense_line_cost_category_group(self):

        query = """SELECT  em.name as employee, cc.code as code, cc.name as cost_category,COALESCE(SUM(ex.total_amount),0) as total
                        FROM hr_expense ex 
												LEFT JOIN hr_employee em ON (ex.employee_id=em.id)
												LEFT JOIN product_cost_category cc ON (ex.cost_category=cc.id)
                                                INNER JOIN hr_expense_sheet AS st ON st.id = ex.sheet_id
												WHERE ex.sheet_id = %s 
												GROUP BY employee, cc.name, cc.code ORDER BY cost_category ASC"""
        params = (self.id,)
        self._cr.execute(query, params)
        dat = self._cr.fetchall()
        data = []
        for i in range(0, len(dat)):
            data.append({'code': dat[i][1],
                        'label': dat[i][2], 
                        'total': dat[i][3],
                        })
        return data

# report expense sheet CVR Journal
    @api.model
    def get_expense_line_account_name_group(self):
        account = self.bank_journal_id.default_credit_account_id.id
        query = """ SELECT aa.code as code,  aa.name as account, COALESCE(SUM(debit), 0) as debit,COALESCE(SUM(credit), 0) as credit, COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance,am.ref as refere
                            FROM account_move_line ml
                            LEFT JOIN account_move am ON (ml.move_id=am.id)
                            LEFT JOIN account_account aa ON (ml.account_id=aa.id)
                            WHERE  am.ref like '%s' AND account_id != %s
                        GROUP BY code, account,refere 
                        union all
                            select null, 'TOTAL', sum(debit), sum(credit),null ,null from account_move_line ml
                            LEFT JOIN account_move am ON (ml.move_id=am.id)
                            LEFT JOIN account_account aa ON (ml.account_id=aa.id)
                            WHERE  am.ref like '%s' AND account_id != %s
                            ORDER BY code ASC """ % (str(self.name), account, str(self.name),account)

        params = (self.name)
        self._cr.execute(query)
        dat = self._cr.fetchall()
        data = []
        for i in range(0, len(dat)):
            data.append({'code': dat[i][0],
                            'label': dat[i][1], 
                            'debit': dat[i][2],
                            'credit': dat[i][3],
                        })
        return data

# attachment dokumen pdf CVR
    @api.multi
    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense.sheet') ,('res_name', 'in', [self.name, self.unrevisioned_name])]
        res['context'] = {'default_res_model': 'hr.expense.sheet', 'default_res_id': self.id}
        return res

    @api.multi
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.expense.sheet'),('res_name', 'in', [self.name, self.unrevisioned_name])], ['res_name'], ['res_name'])
        # attachment = dict((data['res_name'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = len(attachment_data)

    @api.multi
    def check_consistency(self):
        for rec in self:
            expense_lines = rec.expense_line_ids
            if not expense_lines:
                continue
            if any(expense.employee_id != rec.employee_id for expense in expense_lines):
                raise UserError(_("Expenses must belong to the same Employee."))
            if any(expense.payment_mode != expense_lines[0].payment_mode for expense in expense_lines):
                None


# Revisi CVR
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
        comodel_name='hr.expense.sheet',
        string='Current revision',
        readonly=True,
        copy=True
    )
    old_revision_ids = fields.One2many(
        comodel_name='hr.expense.sheet',
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
    unrevisioned_name = fields.Char(
        string='Original Plan Reference',
        copy=True,
        readonly=True,
    )
    has_old_revisions = fields.Boolean(
        compute='_compute_has_old_revisions')

    revision_count = fields.Integer(compute='_compute_revision_count')


    @api.model
    def create(self, values):
        if 'unrevisioned_name' not in values:
            values['unrevisioned_name'] = values['name']
        return super(Sheet, self).create(values)

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        return super(Sheet, self).copy(default=default)


    def copy_revision_with_context(self):
        default_data = self.default_get([])
        new_rev_number = self.revision_number + 1
        default_data.update({
            'revision_number': new_rev_number,
            'unrevisioned_name': self.unrevisioned_name,
            'name': '%s(REV-%02d)' % (self.unrevisioned_name, new_rev_number),
            'old_revision_ids': [(4, self.id, False)],
        })

        expense_line =  []
        for line in self.expense_line_ids:
                expense_line.append([0, False, 
                                    {   'seq' : line.seq,
                                        'name' : line.name,
                                        'employee_id' : line.employee_id.id,
                                        'date' : line.date,
                                        'payment_mode' : line.payment_mode,
                                        'project' : line.project.id,
                                        'cost_category' : line.cost_category.id,
                                        'account_id' : line.account_id.id,
                                        'alokasi_biaya' : line.alokasi_biaya.id,
                                        'expense_direct' : line.expense_direct.id,
                                        'unit_amount' : line.unit_amount,
                                        'quantity' : line.quantity,

                                    }])
                                    
        default_data['expense_line_ids'] = expense_line

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
        for rec in self:
            # Calling  Copy method
            copied_rec = rec.copy_revision_with_context()

            msg = _('New revision created: %s') % copied_rec.seq
            copied_rec.message_post(body=msg)
            rec.message_post(body=msg)

            revision_ids.append(copied_rec.id)

        res = {
            'type': 'ir.actions.act_window',
            'name': _('Revisions'),
            'res_model': 'hr.expense.sheet',
            'domain': "[('id', 'in', %s)]" % revision_ids,
            'auto_search': True,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'target': 'new',
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
                    'res_model': 'hr.expense.sheet',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': ['&', ['current_revision_id', '=', rec.id], ['active', '=', False]],
                    'option': {'no_create_edit': True},
                }

# override compute total amount. ignore negative value (hutang pph 21 & 23)
    @api.one
    @api.depends('expense_line_ids', 'expense_line_ids.total_amount', 'expense_line_ids.currency_id')
    def _compute_amount(self):
        total_amount = 0.0
        for expense in self.expense_line_ids.filtered(lambda r: r.account_id.user_type_id.name not in ('OCLY','Current Liabilities')):
            total_amount += expense.currency_id.with_context(
                date=expense.date,
                company_id=expense.company_id.id
            ).compute(expense.total_amount, self.currency_id)
        self.total_amount = total_amount


    def activity_update(self):
        # for expense_report in self.filtered(lambda hol: hol.state == 'submit'):
        #     self.activity_schedule(
        #         'hr_expense.mail_act_expense_approval',
        #         user_id=expense_report.sudo()._get_responsible_for_approval().id or self.env.user.id)
        # self.filtered(lambda hol: hol.state == 'approve').activity_feedback(['hr_expense.mail_act_expense_approval'])
        # self.filtered(lambda hol: hol.state == 'cancel').activity_unlink(['hr_expense.mail_act_expense_approval'])
        return
        
# trigger open link in mail template
    @api.multi
    def get_url_view_CVR(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        url_params = {
            'id': self.id,
            'view_type': 'form',
            'model': 'hr.expense.sheet',
            'menu_id': self.env.ref('rnet_expense.menu_cvr_report').id,
            'action': self.env.ref('rnet_expense.action_hr_expense_cvr_report').id,
        }
        params = '/web?#%s' % url_encode(url_params)
        return base_url + params
class Expense(models.Model):
    _inherit = 'hr.expense'
    _order = 'seq ASC'

    @api.model
    def _get_default_seq(self):
        return self.env['ir.sequence'].next_by_code('hr.expense')

        
    @api.multi
    def _default_project_expense(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)

        return expense_sheet.project.id

    @api.multi
    def _default_payment_mode_expense(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)

        return expense_sheet.payment_mode


    seq = fields.Integer(string='No Urut', track_visibility='onchange')
    project = fields.Many2one('project.project', string='Project',track_visibility='always')
    payment_mode = fields.Selection([("own_account", "Employee (to reimburse)"), ("company_account", "Company")], default=_default_payment_mode_expense, string="Payment By")
    expensed_by_id = fields.Many2one('hr.employee', string='Expensed By',track_visibility='always' )
    partner_id = fields.Many2one('res.partner', string='Vendor', domain="[('supplier','=',True)]", track_visibility='always')
    cost_category = fields.Many2one('product.cost.category', string='Cost Category', track_visibility='always')
    active = fields.Boolean(default=True)
    product_id = fields.Many2one('product.product', required=False)
    account_id = fields.Many2one('account.account', string='Account', default=None, states={'post': [('readonly', True)], 'done': [('readonly', True)]},
        help="An expense account is expected")

    @api.onchange('product_id')
    def _onchange_product(self):
        self.cost_category = self.product_id.product_cost_category

    @api.multi
    def paid_expense_sheets(self):
        self.write({'state': 'done'})

    @api.multi
    def _prepare_move_values(self):
        """
        This function prepares move values related to an expense
        """
        for expense in self:
            self.ensure_one()
            journal = expense.sheet_id.bank_journal_id
            account_date = expense.sheet_id.accounting_date or expense.date
            move_values = {
                'journal_id': journal.id,
                'company_id': expense.env.user.company_id.id,
                'date': account_date,
                'ref':  'CVR ' + str(expense.sheet_id.name),
                'project': expense.project.id,
                # force the name to the default value, to avoid an eventual 'default_name' in the context
                # to set it to '' which cause no number to be given to the account.move when posted.
                'name': '/',
            }
        return move_values

    @api.multi
    def _get_account_move_by_sheet(self):
        """ Return a mapping between the expense sheet of current expense and its account move
            :returns dict where key is a sheet id, and value is an account move record
        """
        move_grouped_by_sheet = {}
        for expense in self:
            # create the move that will contain the accounting entries
            if expense.sheet_id.id not in move_grouped_by_sheet:
                move = self.env['account.move'].create(expense._prepare_move_values())
                move_grouped_by_sheet[expense.sheet_id.id] = move
            else:
                move = move_grouped_by_sheet[expense.sheet_id.id]
        return move_grouped_by_sheet

    @api.multi
    def _get_account_move_line_values(self):
        move_line_values_by_expense = {}
        for expense in self:
            move_line_name = expense.employee_id.name + ': ' + expense.name.split('\n')[0][:64]
            account_src = expense._get_expense_account_source()
            account_dst = expense.sheet_id.bank_journal_id.default_credit_account_id.id
            account_date = expense.sheet_id.accounting_date or expense.date or fields.Date.context_today(expense)

            company_currency = expense.company_id.currency_id
            different_currency = expense.currency_id and expense.currency_id != company_currency

            move_line_values = []
            taxes = expense.tax_ids.with_context(round=True).compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id)
            total_amount = 0.0
            total_amount_currency = 0.0
            partner_id = expense.employee_id.address_home_id.commercial_partner_id.id

            # source move line
            amount = taxes['total_excluded']
            amount_currency = False
            if different_currency:
                amount = expense.currency_id._convert(amount, company_currency, expense.company_id, account_date)
                amount_currency = taxes['total_excluded']
            move_line_src = {
                'name': move_line_name,
                'quantity': expense.quantity or 1,
                'debit': amount < 0 and - amount if expense.account_id.user_type_id.name in ('OCLY','Current Liabilities') else amount > 0 and  amount,
                'credit': amount > 0 and amount if expense.account_id.user_type_id.name in ('OCLY','Current Liabilities') else amount < 0 and - amount,
                # 'debit': amount if amount > 0 else 0,
                # 'credit': -amount if amount < 0 else 0,
                'amount_currency': amount_currency if different_currency else 0.0,
                'account_id': account_src.id,
                'product_id': expense.product_id.id,
                'product_uom_id': expense.product_uom_id.id,
                'analytic_account_id': expense.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)],
                'expense_id': expense.id,
                'partner_id': partner_id,
                'tax_ids': [(6, 0, expense.tax_ids.ids)],
                'currency_id': expense.currency_id.id if different_currency else False,
                'project': expense.project.id,
            }
            move_line_values.append(move_line_src)
            total_amount += -move_line_src['debit'] or move_line_src['credit']
            total_amount_currency += -move_line_src['amount_currency'] if move_line_src['currency_id'] else (-move_line_src['debit'] or move_line_src['credit'])

            # taxes move lines
            for tax in taxes['taxes']:
                amount = tax['amount']
                amount_currency = False
                if different_currency:
                    amount = expense.currency_id._convert(amount, company_currency, expense.company_id, account_date)
                    amount_currency = tax['amount']
                move_line_tax_values = {
                    'name': tax['name'],
                    'quantity': 1,
                    'debit': amount if amount > 0 else 0,
                    'credit': -amount if amount < 0 else 0,
                    'amount_currency': amount_currency if different_currency else 0.0,
                    'account_id': tax['account_id'] or move_line_src['account_id'],
                    'tax_line_id': tax['id'],
                    'expense_id': expense.id,
                    'partner_id': partner_id,
                    'currency_id': expense.currency_id.id if different_currency else False,
                    'analytic_account_id': expense.analytic_account_id.id if tax['analytic'] else False,
                    'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)] if tax['analytic'] else False,
                }
                total_amount -= amount
                total_amount_currency -= move_line_tax_values['amount_currency'] or amount
                move_line_values.append(move_line_tax_values)

            # destination move line
            move_line_dst = {
                'name': move_line_name,
                'debit': total_amount > 0 and total_amount,
                'credit': total_amount < 0 and -total_amount,
                'account_id': account_dst,
                'date_maturity': account_date,
                'amount_currency': total_amount_currency if different_currency else 0.0,
                'currency_id': expense.currency_id.id if different_currency else False,
                'expense_id': expense.id,
                'partner_id': partner_id,
                'project': expense.project.id,
            }
            move_line_values.append(move_line_dst)

            move_line_values_by_expense[expense.id] = move_line_values
        return move_line_values_by_expense

    @api.multi
    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        move_group_by_sheet = self._get_account_move_by_sheet()

        move_line_values_by_expense = self._get_account_move_line_values()

        for expense in self:
            company_currency = expense.company_id.currency_id
            different_currency = expense.currency_id != company_currency

            # get the account move of the related sheet
            move = move_group_by_sheet[expense.sheet_id.id]

            # get move line values
            move_line_values = move_line_values_by_expense.get(expense.id)
            move_line_dst = move_line_values[-1]
            total_amount = move_line_dst['debit'] or -move_line_dst['credit']
            total_amount_currency = move_line_dst['amount_currency']

            # create one more move line, a counterline for the total on payable account
            if expense.payment_mode == 'company_account':
                if not expense.sheet_id.bank_journal_id.default_credit_account_id:
                    raise UserError(_("No credit account found for the %s journal, please configure one.") % (expense.sheet_id.bank_journal_id.name))
                journal = expense.sheet_id.bank_journal_id
                # create payment
                payment_methods = journal.outbound_payment_method_ids if total_amount < 0 else journal.inbound_payment_method_ids
                journal_currency = journal.currency_id or journal.company_id.currency_id
                payment = self.env['account.payment'].create({
                    'payment_method_id': payment_methods and payment_methods[0].id or False,
                    'payment_type': 'outbound' if total_amount < 0 else 'inbound',
                    'partner_id': expense.employee_id.address_home_id.commercial_partner_id.id,
                    'partner_type': 'supplier',
                    'journal_id': journal.id,
                    'payment_date': expense.date,
                    'state': 'reconciled',
                    'currency_id': expense.currency_id.id if different_currency else journal_currency.id,
                    'amount': abs(total_amount_currency) if different_currency else abs(total_amount),
                    'name': expense.name,
                })
                move_line_dst['payment_id'] = payment.id

            # link move lines to move, and move to expense sheet
            move.with_context(dont_create_taxes=True).write({
                'line_ids': [(0, 0, line) for line in move_line_values]
            })
            expense.sheet_id.write({'account_move_id': move.id})

            if expense.payment_mode == 'company_account':
                expense.sheet_id.paid_expense_sheets()

        # post the moves
        for move in move_group_by_sheet.values():
            move.post()

        return move_group_by_sheet


class ExpenseAdvance(models.Model):
    _inherit = 'hr.expense.advance'

    state = fields.Selection(
        [('draft', 'Draft'),
         ('submitted', 'Submitted'),
         ('approved', 'Approved'),
         ('approved_commercial', 'Approved by Commercial'),
         ('processed', 'Processed'),
         ('reported', 'Reported'),
         ('partial', 'Partial Pay'),
         ('paid', 'Full Paid'),
         ('rejected', 'Rejected'),
         ('rejected_commercial', 'Rejected'),],
        string='Status', index=True, readonly=True, copy=False, track_visibility='onchange',
        default='draft', required=True, help='Expense Request State')

    def _default_finance_director(self):
        job_id = self.env['hr.job'].search([('name', '=', 'Finance Director')])
        employee_id = self.env['hr.employee'].search(
            [('job_id', '=', job_id.id)])
        return employee_id

    def _default_processed_by_bar(self):
        employee_id = self.env['hr.employee'].search(
            [('name', '=', 'ASIH RAMANTO')])
        return employee_id

    def _default_transaction_type(self):
        return 'petty_cash'

    @api.model
    def _get_default_name(self):
        return self.env['ir.sequence'].next_by_code('hr.expense.advance')

    transaction_type = fields.Selection([('petty_cash', 'Cash Advance'), ('hutang_usaha', 'Reimbursement'), ('expense_report', 'Expense Report'),],
                                        'Transaction Type', readonly=True, default=_default_transaction_type)

    gut_expense_report_count = fields.Integer(compute='_expense_report_count')
    expense_journal_count = fields.Integer(compute='_expense_journal_count')

    user_id = fields.Many2one(
        'res.users', related='project_id.project_manager.user_id', track_visibility='always')

    due_date_payment = fields.Date('Due Date Payment', default=fields.Date.context_today, track_visibility='always')

    site_manager = fields.Many2one(
         'hr.employee', related='project_id.site_manager', track_visibility='always')

    seq_num = fields.Char(
        'BAR No.', Readonly=False, track_visibility='always')

    active = fields.Boolean(default=True)
    name = fields.Char('BAR No.', size=32, default='New', required=True, track_visibility='onchange')

    # --- Tambahan field buat form BAR --- #
    project_manager = fields.Many2one(
        'hr.employee', related='project_id.project_manager', track_visibility='always')

    commercial_id = fields.Many2one('hr.employee', 'Commercial', copy=False, readonly=True, states={
                                    'draft': [('readonly', False)]}, default=_default_finance_director)

    processed_by = fields.Many2one('hr.employee', 'Processed By', states={
                                    'draft': [('readonly', False)]}, default=_default_processed_by_bar)
    current_user_is_approver = fields.Boolean(string='Current user is approver?', compute='_compute_current_user_is_approver')
    current_user_is_finance_director= fields.Boolean(string='Current user is finance director?', compute='_compute_current_user_is_finance_director')
    current_user_is_processed_by= fields.Boolean(string='Current user is Processed By?', compute='_compute_current_user_is_processed_by')
    
    reject_reason = fields.Text(string="Reject Reason", readonly=True, track_visibility='always')
    
    # --- Visit plan --- #
    purpose = fields.Selection([('project', 'Project'), ('non_project', 'Non Project')],
                               string='Purpose', default='project', readonly=True, states={'draft': [('readonly', False)]})
    project_id = fields.Many2one('project.project', states={
                                 'draft': [('readonly', False)]}, readonly=True, track_visibility='always')
    kind_of_work = fields.Char(
        'Kind of Work', related='project_id.project_type.name')
    customer_id = fields.Many2one(
        'res.partner', string='Customer', related='project_id.partner_id')
    workplace = fields.Many2one(
        'stock.location', string='Workplace', related='project_id.location')
    job_order_no = fields.Char(string='Job Order No.', related='project_id.no')
    location_id = fields.Selection([('onshore', 'On Shore'), ('offshore', 'Off Shore')], default="onshore", string="Location")
    visit_plan_from = fields.Date(
        'From', related='project_id.plan_start_date')
    visit_plan_to = fields.Date('To', related='project_id.plan_end_date')

    # --- Allowance --- #
    est_visit_days = fields.Integer(string='Est. Visit Days', default=0, readonly=True, states={
                                    'draft': [('readonly', False)]}, track_visibility='always')
    allowance_per_day = fields.Monetary(
        string='Allowance per Day', default=0, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    total_allowance = fields.Monetary(
        string='Total Allowance', default=0, track_visibility='always', compute="_compute_sum_allowance_line")
    # --- --- #

    # --- Other expense --- #
    transport_expense = fields.Monetary(
        string='Transportation', default=0, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always', compute="_compute_sum_transportasi_line")
    transport_expense_note = fields.Char(
        readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    material_expense = fields.Monetary(string='Material', default=0, readonly=True, states={
                                       'draft': [('readonly', False)]}, track_visibility='always', compute="_compute_sum_material_line")
    material_expense_note = fields.Char(
        readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    other_expense = fields.Monetary(string='Other', default=0, readonly=True, states={
                                    'draft': [('readonly', False)]}, track_visibility='always', compute="_compute_sum_akomodasi_line")
    other_expense_note = fields.Char(
        readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    total_other_expense = fields.Monetary(
        string='Total Other Expenses', default=0, compute='_compute_total_other_expense', track_visibility='always')
    # --- --- #

    # --- Non project expense --- #
    private_expense = fields.Monetary(string='Private', default=0, readonly=True, states={
                                      'draft': [('readonly', False)]})
    private_expense_note = fields.Char(
        readonly=True, states={'draft': [('readonly', False)]})
    office_expense = fields.Monetary(string='Office', default=0, readonly=True, states={
                                     'draft': [('readonly', False)]})
    office_expense_note = fields.Char(
        readonly=True, states={'draft': [('readonly', False)]})
    other_nonproject_expense = fields.Monetary(
        string='Other', default=0, readonly=True, states={'draft': [('readonly', False)]})
    other_nonproject_note = fields.Char(
        readonly=True, states={'draft': [('readonly', False)]})
    total_nonproject_expense = fields.Monetary(
        string='Total Non Project Expenses', default=0, compute='_compute_sum_non_project_line')
    # --- --- #

    # --- Total & remark --- #
    remark = fields.Text('Remark', readonly=True, states={
                         'draft': [('readonly', False)]}, track_visibility='always')
    amount_total = fields.Monetary(
        string='Total', default=0, compute='_compute_amount_total', track_visibility='always', store=True)
    # --- --- #

    # --- LPJ buat rekap --- #
    sheet_id = fields.Many2one('hr.expense.sheet', string='Expense Sheet', readonly=True)
    sheet_balance = fields.Monetary(related='sheet_id.balance', store=True)
    sheet_total_amount = fields.Monetary(related='sheet_id.total_amount')
    total_paid = fields.Monetary('Total Paid',  compute='_compute_total_paid', store=True)
    residual_amount = fields.Monetary('Residual Amount', compute='_compute_residual_amount',)
    sheet_return_amount = fields.Monetary(related='sheet_id.return_amount')
    sheet_returned_amount = fields.Monetary(related='sheet_id.returned_amount')
    # --- --- #
    
    # rincian expense line
    transportasi_line = fields.One2many('hr.expense.advance.transportasi.line', 'transportasi_line_ids', string='Transportasi')
    material_line = fields.One2many('hr.expense.advance.material.line', 'material_line_ids', string='Material & Tools')
    allowance_line = fields.One2many('hr.expense.advance.allowance.line', 'allowance_line_ids', string='Gaji + Allowance')
    akomodasi_line = fields.One2many('hr.expense.advance.akomodasi.line', 'akomodasi_line_ids', string='Akomodasi')
    non_project_line = fields.One2many('hr.expense.advance.nonproject.line', 'non_project_line_ids', string='Non Project Expenses')


    @api.onchange('purpose')
    def _onchange_purpose(self):
        if self.purpose == 'non_project':
            self.project_id = None

    # modif logic bawaan addon, user id ga usah
    # berubah kalau employee berubah, karena sekarang
    # user id adalah project manager.
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.department_id = self.employee_id.department_id.id
        self.job_id = self.employee_id.job_id.id
        # self.user_id = self.employee_id.sudo().expense_manager_id or self.employee_id.sudo().parent_id.user_id
        self.address_id = self.employee_id.sudo().address_home_id

# total advance
    @api.multi
    @api.depends('total_allowance', 'total_other_expense', 'other_expense', 'transport_expense', 'material_expense', 'total_nonproject_expense')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.total_allowance + rec.transport_expense + rec.material_expense + rec.other_expense + rec.total_nonproject_expense

# compute total paid
    @api.multi
    @api.depends('residual_amount','amount_total')
    def _compute_total_paid(self):
        for rec in self:
            move = self.env['account.move'].search([('ref', '=', rec.name)])
            amount = sum([p.amount for p in move])
            total = amount / 2
            rec.total_paid = total 

# compute residual amount due
    @api.multi
    @api.depends('amount_total','state')
    def _compute_residual_amount(self):
        for rec in self:
            if rec.state == 'paid':
                rec.residual_amount = 0.0
            else:
                 rec.residual_amount = rec.amount_total - rec.total_paid

    @api.multi
    @api.depends('est_visit_days', 'allowance_per_day')
    def _compute_total_allowance(self):
        for rec in self:
            rec.total_allowance = rec.allowance_per_day * rec.est_visit_days

    @api.multi
    @api.depends('transport_expense', 'material_expense', 'other_expense')
    def _compute_total_other_expense(self):
        for rec in self:
            rec.total_other_expense = rec.transport_expense + \
                rec.material_expense + rec.other_expense

    @api.multi
    @api.depends('private_expense', 'office_expense', 'other_nonproject_expense')
    def _compute_total_nonproject_expense(self):
        for rec in self:
            rec.total_nonproject_expense = rec.private_expense + \
                rec.office_expense + rec.other_nonproject_expense

    # @api.model
    # def create(self, values):
    #     employee_id = self.env['hr.employee'].search(
    #         [('id', '=',  values.get('employee_id'))])
    #     partner_id = employee_id.address_home_id
    #     values['journal_petty_cash'] = partner_id.journal_petty_cash.id

    #     validator = ExpenseValidator()
    #     validator.validate_pettycash(values)

    #     return super(ExpenseAdvance, self).create(values)

    # @api.multi
    # def write(self, values):
    #     transaction_type_changed = values.get('transaction_type')
    #     partner_id = self.employee_id.address_home_id

    #     if transaction_type_changed is not None:
    #         # field transaction_type berubah
    #         transaction_type = values.get('transaction_type')
    #     else:
    #         transaction_type = self.transaction_type

    #     if transaction_type == 'petty_cash' and partner_id.journal_petty_cash.id is False:
    #         raise ValidationError(
    #             'Untuk tipe transaksi cash advance, jurnal cash advance employee harus dipilih')

    #     return super(ExpenseAdvance, self).write(values)

    @api.multi
    def open_expense_report(self):
        for rec in self:
            return {
                'name': _('Expense Report'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.expense.sheet',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('expense_advance_id', '=', rec.name)],
                'option': {'no_create_edit': True}
            }

    def open_expense_journal(self):
        if self.sheet_id.name:
            domain = ['|', '|',('ref', '=', self.name),('ref', '=', self.sheet_id.name),('ref', '=', self.sheet_id.seq)]
        else:
            domain = [('ref', '=', self.name)]
        return {
            'name': _('Expense Journal'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': domain, #['|',('ref', '=', self.seq_num),('ref', '=', self.sheet_id.name)],
            'option': {'no_create_edit': True}
        }

    @api.multi
    def _expense_report_count(self):
        res = self.env['hr.expense.sheet'].search_count(
            [('expense_advance_id', '=', self.name)])
        self.gut_expense_report_count = res or 0

    def _expense_journal_count(self):
        if self.sheet_id.name:
            self.expense_journal_count = self.env['account.move'].search_count(['|', '|',('ref', '=', self.name), (
                'ref', '=', self.sheet_id.name),('ref', '=', self.sheet_id.seq)])
        else:
            self.expense_journal_count = self.env['account.move'].search_count([('ref', '=', self.name)])

    @api.multi
    def action_submit(self):
        super(ExpenseAdvance, self).action_submit()
        manager_mail_template = self.env.ref('rnet_expense.email_approval_site_manager_bar')
        manager_mail_template.send_mail(self.id)
        self.activity_update()
        self.write({'state': 'submitted'})
        self.activity_update()

    @api.multi
    def action_approve_commercial(self):
        manager_mail_template = self.env.ref('rnet_expense.email_processed_by_bar')
        manager_mail_template.send_mail(self.id)
        self.activity_update()
        self.write({'state': 'approved_commercial'})
   
    @api.multi
    def action_processed(self):
        self.write({'state': 'processed'})
        self.activity_update()

        
    @api.multi
    def action_approve(self):
        super(ExpenseAdvance, self).action_approve()
        manager_mail_template = self.env.ref('rnet_expense.email_approval_commercial_bar')
        manager_mail_template.send_mail(self.id)
        self.write({'state': 'approved'})

    @api.multi
    def _compute_current_user_is_approver(self):
        for req in self:
            req.current_user_is_approver = True if req.site_manager.user_id == req.env.user or req.project_manager.user_id == req.env.user and req.state == "submitted" else False
    
    @api.multi
    def action_refuse_commercial(self):
        view_id = self.env.ref('rnet_expense.expense_advance_reject_wizard').id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.expense.advance.reject.wizard',
            'target': 'new',
            'state': 'rejected',
            'type': 'ir.actions.act_window',
            'name': 'BAR',
            'views': [[view_id, 'form']],
            'context': {'expense_advance_id': self.id}
        }

    @api.multi
    def _compute_current_user_is_finance_director(self):
        for req in self:
            req.current_user_is_finance_director = True if req.commercial_id.user_id == req.env.user and req.state == "approved" else False
    
    @api.multi
    def _compute_current_user_is_processed_by(self):
        for req in self:
            req.current_user_is_processed_by = True if req.processed_by.user_id == req.env.user and req.state == "approved_commercial" else False
    

    @api.onchange('project_id')
    def _onchange_expense_advance_project_seq(self):
        seq = self.env['ir.sequence'].next_by_code('hr.expense.advance.new')
        # num = 0
        # num += 1
        # seq = "{0:04d}".format(num)
        current_year = date.today().year
        current_month = date.today().strftime('%m')
        pro = self.job_order_no or 'xxxx'
        result = seq, ''.join(pro),'/', current_month, '/', current_year
        res = ''.join(str(v) for v in result)
        self.name = res if res else None

# check jika nomor bar sudah digunakan
    @api.constrains('name')
    def _check_name_bar(self):
        if self.name:
            existing_name = self.env['hr.expense.advance'].search([('id','!=', self.id),('name','=', self.name)])
            if existing_name:
                raise UserError(_("BAR No. is Already Taken " + self.name + ''))

# mapping transportasi dari line
    @api.depends('transportasi_line')
    def _compute_sum_transportasi_line(self):
        for pr in self:
            total = sum(pr.transportasi_line.mapped('biaya'))
            pr.transport_expense = total

# mapping material dari line
    @api.depends('material_line')
    def _compute_sum_material_line(self):
        for pr in self:
            total = sum(pr.material_line.mapped('biaya'))
            pr.material_expense = total

# mapping allowance dari line
    @api.depends('allowance_line')
    def _compute_sum_allowance_line(self):
        for pr in self:
            total = sum(pr.allowance_line.mapped('biaya'))
            pr.total_allowance = total

# mapping akomodasi dari line
    @api.depends('akomodasi_line')
    def _compute_sum_akomodasi_line(self):
        for pr in self:
            total = sum(pr.akomodasi_line.mapped('biaya'))
            pr.other_expense = total

# mapping non project dari line
    @api.depends('non_project_line')
    def _compute_sum_non_project_line(self):
        for pr in self:
            total = sum(pr.non_project_line.mapped('biaya'))
            pr.total_nonproject_expense = total

# trigger open link in mail template
    @api.multi
    def get_url_view_BAR(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        url_params = {
            'id': self.id,
            'view_type': 'form',
            'model': 'hr.expense.advance',
            'menu_id': self.env.ref('hr_expense_request_advance.menu_hr_expense_advance_my_requests').id,
            'action': self.env.ref('rnet_expense.action_hr_expense_BAR').id,
        }
        params = '/web?#%s' % url_encode(url_params)
        return base_url + params

    def activity_update(self):
        # for expense_advance in self.filtered(lambda req: req.state == 'submitted'):
        #     self.activity_schedule(
        #         'hr_expense_request_advance.mail_act_expense_advance_approval',
        #         user_id=expense_advance.sudo()._get_responsible_for_approval().id or self.env.user.id)

        # self.filtered(lambda req: req.state == 'approved').activity_feedback(
        #         ['hr_expense_request_advance.mail_act_expense_advance_approval'])

        # self.filtered(lambda req: req.state == 'rejected').activity_unlink(
        #         ['hr_expense_request_advance.mail_act_expense_advance_approval'])
        return

    # Mail Thread
    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'approved':
            return 
        elif 'state' in init_values and self.state == 'rejected':
            return 'hr_expense_request_advance.mt_expense_advance_rejected'
        elif 'state' in init_values and self.state in ['paid','partial']:
            return 'hr_expense_request_advance.mt_expense_advance_paid'
        return super(ExpenseAdvance, self)._track_subtype(init_values)


# function name jika ingin seperti no PO 
    # @api.multi
    # @api.depends('project_id')
    # def call_sequence_name_advance(self):
    #         seq = self.env['ir.sequence'].next_by_code('hr.expense.advance.new')
    #         pro = self.job_order_no or 'xxxx'
    #         current_year = date.today().year
    #         current_month = date.today().strftime('%m')
    #         result = seq,''.join(pro),'/', current_month, '/', current_year
    #         res = ''.join(str(v) for v in result)
    #         self.name =  res

    # @api.model
    # def create(self, values):

    #     record = super(ExpenseAdvance, self).create(values)
    #     record.call_sequence_name_advance()
    #     return record


class ExpenseAdvanceTransportasi(models.Model):
    _name = 'hr.expense.advance.transportasi.line'

    name = fields.Char(string="Uraian")
    biaya = fields.Float('Total Biaya')
    Keterangan = fields.Text('Keterangan')
    transportasi_line_ids = fields.Many2one('hr.expense.advance')

class ExpenseAdvanceMaterial(models.Model):
    _name = 'hr.expense.advance.material.line'

    name = fields.Char(string="Uraian")
    biaya = fields.Float('Total Biaya')
    Keterangan = fields.Text('Keterangan')
    material_line_ids = fields.Many2one('hr.expense.advance')


class ExpenseAdvanceAllowance(models.Model):
    _name = 'hr.expense.advance.allowance.line'

    name = fields.Char(string="Uraian")
    biaya = fields.Float('Total Biaya')
    Keterangan = fields.Text('Keterangan')
    allowance_line_ids = fields.Many2one('hr.expense.advance')


class ExpenseAdvanceAkomodasi(models.Model):
    _name = 'hr.expense.advance.akomodasi.line'

    name = fields.Char(string="Uraian")
    biaya = fields.Float('Total Biaya')
    Keterangan = fields.Text('Keterangan')
    akomodasi_line_ids = fields.Many2one('hr.expense.advance')

class ExpenseAdvanceNonProject(models.Model):
    _name = 'hr.expense.advance.nonproject.line'

    name = fields.Char(string="Uraian")
    biaya = fields.Float('Total Biaya')
    Keterangan = fields.Text('Keterangan')
    non_project_line_ids = fields.Many2one('hr.expense.advance')

