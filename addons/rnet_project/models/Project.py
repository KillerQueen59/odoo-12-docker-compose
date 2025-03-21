from odoo import models, fields, api, _
from datetime import date, datetime , timedelta, time

class ProjectType(models.Model):
    _name = 'project.type'
    _description = 'Product Type'
    name = fields.Char(string='name', required=True)

class ProjectStatus(models.Model):
    _name = 'project.status'
    _description = 'Product Status'
    name = fields.Char(string='name', required=True)

# get year BY
def get_years():
    year_list = []
    for i in range(2000, 2046):
        year_list.append((i, str(i)))
    return year_list

class Project(models.Model):
    _inherit = 'project.project'


    @api.model
    def _get_default_seq_project(self):
        return self.env['ir.sequence'].next_by_code('project.seq')

    # default user finance director
    def _get_default_finance_director(self):
        job_id = self.env['hr.job'].search([('name', '=', 'Finance Director')])
        employee_id = self.env['hr.employee'].search(
            [('job_id', '=', job_id.id)])
        return employee_id

    no = fields.Char(string='Project No.')
    project_type = fields.Many2one('project.type', string='Project Type',)
    project_status = fields.Many2one('project.status', string='Project Status')
    reference_no = fields.Char(string='Reference No.')
    plan_start_date = fields.Date(string='Plan Start Date', compute="_compute_plan_start_date")
    plan_end_date = fields.Date(string='Plan End Date', compute="_compute_plan_end_date")
    actual_start_date = fields.Date(string='Actual Start Date')
    actual_end_date = fields.Date(string='Actual End Date')
    description = fields.Char(string='Description')
    parent_project = fields.Many2one('project.project', string='Parent Project')
    res_currency = fields.Many2one('res.currency', string='Currency')
    payment_term = fields.Many2one('account.payment.term', string='Term of Payment')
    customer_pic_tech = fields.Many2one('res.partner', string='Customer PIC Tech')
    customer_pic_comm = fields.Many2one('res.partner', string='Customer PIC Comm')
    project_duration = fields.Integer(string='Project Duration')
    order_date = fields.Date(string='Order Date')
    plan_delivery_date = fields.Date(string='Plan Delivery Date')
    actual_delivery_date = fields.Date(string='Actual Delivery Date')
    term_of_delivery = fields.Date(string='Term of Delivery', index=True,)
    notes = fields.Text(string='Notes')
    project_manager = fields.Many2one('hr.employee', string='Project Manager')
    project_coordinator = fields.Many2one('hr.employee', string='Project Control')
    pic_technical = fields.Many2one('hr.employee', string='PIC Technical')
    pic_project_cost = fields.Many2one('hr.employee', string='PIC Project Cost')
    team_member = fields.Many2many('hr.employee', string='Team Member')
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic Account')
    location = fields.Many2one('stock.location', string='Location', domain="[('active', '=', True), ('usage', '=', 'internal')]")
    amount = fields.Monetary(string='Amount')
    distance = fields.Boolean(string="Project lebih dari 60 km?")
    project_class_code = fields.Integer(string="Project Class Code", compute="_compute_project_class_code")
    site_manager = fields.Many2one('hr.employee', string='Site Manager')
    project_admin = fields.Many2one('hr.employee', string='Project Admin')
    # expense_count = fields.Integer( compute='_get_expense_count')
    # expense_sheet_count = fields.Integer( compute='_get_expense_sheet_count')
    # expense_sheet_amount = fields.Integer( compute='_get_expense_sheet_amount')
    # expense_advance_count = fields.Integer( compute='_get_expense_advance_count')
    # expense_advance_amount = fields.Integer( compute='_get_expense_advance_amount')
    seq = fields.Char(string='Nomor Project', track_visibility='onchange')
    purchase_order_amount = fields.Integer( compute='_get_purchase_order_amount')
    # user_ids = fields.Many2many(string='User Ids', comodel_name='res.users')
    kind_of_work = fields.Char(string='Kind of Work', track_visibility='onchange', required=True)
    project_director= fields.Many2one('hr.employee', string='Project Director')
    project_pic_warehouse = fields.Many2one('hr.employee', string='PIC Warehouse')
    customer_pic = fields.Char(string='Contact Person')
    customer_pic_division = fields.Char(string='Division')
    customer_pic_title= fields.Char(string='Tittle')
    order_value = fields.Float(string='Order Value', track_visibility='onchange')
    main_material = fields.Float(string='Main Material', track_visibility='onchange')
    man_power = fields.Float(string='Man Power', track_visibility='onchange')
    secondary_cost = fields.Float(string='Secondary Cost / Operation SIte Cost Plan', track_visibility='onchange')
    tool_cost = fields.Float(string='Tool Cost Plan', track_visibility='onchange')
    consumable_material = fields.Float(string='Consumable Material Cost Plan', track_visibility='onchange')
    other_value = fields.Float(string='Other', track_visibility='onchange')
    other_value2 = fields.Float(string='Other 2', track_visibility='onchange')
    other_value3 = fields.Float(string='Other 3', track_visibility='onchange')
    other_value4= fields.Float(string='Other 4', track_visibility='onchange')
    other_value_desc = fields.Char(string='Other Desc', track_visibility='onchange')
    other_value_desc2 = fields.Char(string='Other Desc 2', track_visibility='onchange')
    other_value_desc3 = fields.Char(string='Other Desc 3', track_visibility='onchange')
    other_value_desc4 = fields.Char(string='Other Desc 4', track_visibility='onchange')
    calculated_cost = fields.Float(string='Calculated Cost', compute='_compute_calculated_cost', track_visibility='onchange')
    gross_margin = fields.Float(string='Gross Margin ([Order Value] - [Calculated Value]', compute='_compute_gross_margin', track_visibility='onchange')
    overhead_cost = fields.Float(string='Overhead Cost', compute='_compute_overhead_cost', track_visibility='onchange')
    overhead_cost_persen = fields.Float(string='Overhead Cost %',track_visibility='onchange')
    holding_tax = fields.Float(string='With Holding Tax', compute='_compute_holding_tax', track_visibility='onchange')
    holding_tax_persen = fields.Float(string='With Holding Tax %',track_visibility='onchange')
    net_margin = fields.Float(string='Net Margin ((Gross Margin - Overhead Cost) - (With Holding Tax)', compute='_compute_net_margin')
    document_for_invoice = fields.Text(string='Document For Invoice', track_visibility='onchange')
    persentase = fields.Float('persentase', compute='_compute_persentase')
    price_condition = fields.Selection([
        ('actual_outlay', 'Actual Outlay'),
        ('fix_price', 'Fixed Price/Lumpsum'),
        ('material', 'Material/Sparepart'),
        ('service', 'Service/Training'),
        ('repair', 'Repair'),
        ('rental_tool', 'Rental Tools'),
    ], string='Price Condition',
         store=True, track_visibility='onchange',)
    reimbursement = fields.Selection([
        ('chargerable', 'Chargerable'),
        ('unchargerable', 'UnChargerable'),
        ], string='Reimbursement',
         store=True, track_visibility='onchange',)
    note = fields.Text(string='Note')

    location_longitude = fields.Float(string='Longitude', track_visibility='onchange')
    location_latitude = fields.Float(string='Latitude', track_visibility='onchange')
    location_city = fields.Char(string='City', track_visibility='onchange')
    location_state_id = fields.Char(string='State',)
    project_po_line = fields.One2many('project.po.line', 'project_id', string='Project PO Lines')
    status = fields.Selection([
    ('draft', 'Draft'),
    ('locked', 'Locked'),
    ], string='Status', track_visibility='onchange', default='draft')
    finance_director_id = fields.Many2one('hr.employee', 'Finance Director', readonly=True, default=_get_default_finance_director)
    current_user_is_finance_director= fields.Boolean(string='Current user is finance director?', compute='_check_current_user_is_finance_director')
    pm_backup_approval = fields.Many2one('hr.employee', string='PM Backup Approval')
    year_by = fields.Selection(get_years(), string='BY')
  # hidden button create & edit for group tertentu ---- adddons rp_hide_edit_btn_v12
    can_edit = fields.Selection([('yes','Yes'),('no','No')], string='Can Edit', compute='_compute_can_edit')
    can_create = fields.Selection([('yes','Yes'),('no','No')], string='Can Create', compute='_compute_can_create')


    @api.model
    def create(self, vals):
        proj = super(Project, self).create(vals)
        if not proj.no:
            no = self.env['ir.sequence'].next_by_code('project.no') or None
            proj.write({'no': no})
        return proj

    @api.multi
    def name_get(self):
        data = []
        for o in self:
            display_name = '['
            display_name += o.no or ""
            display_name += '] '
            display_name += o.name or ""
            data.append((o.id, display_name))
        return data

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('no', operator, name), ('name', operator, name)]
        project_ids = self._search(domain + args, limit=limit)
        return self.browse(project_ids).name_get()

    @api.multi
    def _compute_set_code(self):
        for pro in self:
            if pro.distance == True:
                self.code = 2
            else:
                self.code = 1

#   onchange gut code di project
    @api.multi
    def _compute_project_class_code(self):
        if  self.no == '0000MG-0001' :
                self.project_class_code = 0
        elif self.no != '0000MG-0001' and self.distance == True:
                self.project_class_code = 2
        elif self.no != '0000MG-0001' and self.distance == False:
               self.project_class_code  = 1


# statinfo  BAR & CVR di Project
#     @api.multi
#     def _get_expense_count(self):
#             res = self.env['hr.expense'].search_count([('project', '=', self.id),('state', '=', 'approved')])
#             self.expense_count = res or 0

    # @api.multi
    # def _get_expense_sheet_count(self):
    #         res = self.env['hr.expense.sheet'].search_count(['&', ('project', '=', self.id), ('state', 'not in', ['draft', 'cancel', 'reject_control', 'reject_technical', 'reject_finance'])])
    #         self.expense_sheet_count = res or 0

    @api.multi
    @api.depends('expense_sheet_count')
    def _get_expense_sheet_amount(self):
        data_obj = self.env['hr.expense.sheet'].search(['&', ('project', '=', self.id), ('state', 'not in', ['draft', 'cancel', 'reject_control', 'reject_technical', 'reject_finance'])])
        total_amount = sum(data_obj.mapped('total_amount'))
        for record in self:
            record.expense_sheet_amount = total_amount or False

    # @api.multi
    # def _get_expense_advance_count(self):
    #         res = self.env['hr.expense.advance'].search_count(['&', ('project_id', '=', self.id), ('state', 'not in', ['draft', 'rejected'])])
    #         self.expense_advance_count = res or 0
            
    @api.multi
    @api.depends('expense_advance_count')
    def _get_expense_advance_amount(self):
        data_obj = self.env['hr.expense.advance'].search(['&', ('project_id', '=', self.id), ('state', 'not in', ['draft', 'rejected'])])
        total_amount = sum(data_obj.mapped('amount_total'))
        for record in self:
            record.expense_advance_amount = total_amount or False

    @api.multi
    def open_expense_project(self):
        for group in self:
            return {
                    'name': 'Expenses',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'hr.expense',
                    'type': 'ir.actions.act_window',
                    'domain': [('project', '=', group.id),('state', '=', 'approved')],
                }
        pass

    @api.multi
    def open_expense_sheet_project(self):
        for group in self:
            return {
                    'name': 'CVR',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'hr.expense.sheet',
                    'type': 'ir.actions.act_window',
                    'domain': ['&', ('project', '=', group.id), ('state', 'not in', ['draft', 'cancel', 'reject_control', 'reject_technical', 'reject_finance']),],
                }
        pass

    @api.multi
    def open_expense_advance_project(self):
        for group in self:
            return {
                    'name': 'BAR',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'hr.expense.advance',
                    'type': 'ir.actions.act_window',
                    'domain': ['&', ('project_id', '=', group.id), ('state', 'not in', ['draft', 'rejected']),],
                }
        pass

    # statinfo PO di Project

    @api.multi
    def _get_purchase_order_amount(self):
        data_obj = self.env['purchase.order'].search(['&', ('project', '=', self.id), ('state', 'not in', ['draft', 'cancel', 'refuse'])])
        total_amount = sum(data_obj.mapped('amount_total'))
        for record in self:
            record.purchase_order_amount = total_amount or False


    @api.multi
    def open_purchase_order_project(self):
        for group in self:
            return {
                    'name': 'Purchase Order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'purchase.order',
                    'type': 'ir.actions.act_window',
                    'domain': ['&', ('project', '=', group.id), ('state', 'not in', ['draft', 'cancel', 'refuse']),],
                }
        pass

    @api.onchange('partner_id')
    def onchange_partner_id(self):

        for rec in self:
            for cust in rec.partner_id.child_ids:
                self.customer_pic = cust.name
                self.customer_pic_division = cust.function
                self.customer_pic_title = cust.title.name


    @api.onchange('payment_term')
    def onchange_payment_term(self):

        for rec in self:
            for pay in rec.payment_term.line_ids:
                if rec.order_date:
                    due = pay.days 
                    term = rec.order_date + timedelta(days=due)
                    self.term_of_delivery = term

    # @api.onchange('payment_term')
    # def _onchange_payment_term(self):
    #     delivery_date = self.plan_delivery_date
    #     if not delivery_date:
    #         delivery_date = fields.Date.context_today(self)
    #     if not self.payment_term:
    #         # When no payment term defined
    #         self.term_of_delivery = self.term_of_delivery or self.plan_delivery_date
    #     else:
    #         pterm = self.payment_term
    #         pterm_list = pterm.with_context(currency_id=self.currency_id.id).compute(value=1, date_ref=delivery_date)[0]
    #         self.term_of_delivery = max(line[0] for line in pterm_list)

    @api.multi
    @api.depends('main_material', 'man_power','secondary_cost', 'tool_cost', 'consumable_material', 'other_value', 'other_value2', 'other_value3', 'other_value4')
    def _compute_calculated_cost(self):
        for rec in self:
            total = rec.main_material + rec.man_power + rec.secondary_cost + rec.tool_cost + rec.consumable_material + rec.other_value + rec.other_value2 + rec.other_value3 + rec.other_value4
            rec.calculated_cost = total or 0

    @api.multi
    @api.depends('calculated_cost', 'order_value')
    def _compute_gross_margin(self):
        total = 0
        for rec in self:
            if rec.order_value:
                total = rec.order_value - rec.calculated_cost
                rec.gross_margin = total

    @api.multi
    @api.depends('gross_margin')
    def _compute_overhead_cost(self):
        total = 0
        for rec in self:
            total = rec.gross_margin / 100 * rec.overhead_cost_persen
            rec.overhead_cost = total

    @api.multi
    @api.depends('gross_margin','overhead_cost')
    def _compute_holding_tax(self):
        total = 0
        for rec in self:
            total = rec.gross_margin / 100 * rec.holding_tax_persen
            rec.holding_tax = total

    @api.multi
    @api.depends('gross_margin','order_value','holding_tax')
    def _compute_net_margin(self):
        total = 0
        for rec in self:
            total = rec.gross_margin - rec.overhead_cost - rec.holding_tax
            rec.net_margin = total

    @api.multi
    @api.depends('net_margin','order_value')
    def _compute_persentase(self):
        for rec in self:
            if rec.net_margin:
                persen = rec.net_margin / rec.order_value * 100
                self.persentase = persen

    @api.onchange('location')
    def onchange_location(self):
        for rec in self:
            self.location_latitude = rec.location.latit 
            self.location_longitude = rec.location.longit
            self.location_city = rec.location.city
            self.location_state_id = rec.location.state_id.name

# get plan start date dari PO start date
    def _compute_plan_start_date(self):
        for record in self:
            obj = self.env['project.po.line'].search([('project_id', 'in', [record.id])], limit=1, order='po_start_date ASC')
            for rec in  obj:
                    record.plan_start_date = rec.po_start_date

# get plan end date dari PO end date
    def _compute_plan_end_date(self):
        for record in self:
            obj = self.env['project.po.line'].search([('project_id', 'in', [record.id])], limit=1, order='po_end_date DESC')
            for rec in  obj:
                    record.plan_end_date = rec.po_end_date

    @api.multi
    def button_lock(self):
        for rec in self:
            return self.write({'status': 'locked'})

    @api.multi
    def button_reset(self):
        for rec in self:
            return self.write({'status': 'draft'})

# check  user is finance director
    @api.multi
    def _check_current_user_is_finance_director(self):
        for req in self:
            req.current_user_is_finance_director = True if req.finance_director_id.user_id == req.env.user  else False

# check jika user bisa create project
    @api.depends('name')
    def _compute_can_create(self):
        if  self.user_has_groups('rnet_project.can_create_edit_project_group'): # you can check weather user has particular group or not.
            self.can_create = 'yes'
        else:
            self.can_create = 'no'

# check jika user bisa edit project
    @api.depends('name','project_manager')
    def _compute_can_edit(self):
        if  self.project_manager.user_id == self.env.user or self.user_has_groups('rnet_project.can_create_edit_project_group'):
            self.can_edit = 'yes'
        else:
            self.can_edit = 'no'

class ProjectPo(models.Model):
    _name = 'project.po.line'
    _inherit = ['mail.thread']
    _description = 'Project PO Line'

    name = fields.Char(string='SPK.PO No./Contract', required=True)
    po_code = fields.Char(string='PO Code')
    po_amount = fields.Float(string='PO Amount')
    po_date = fields.Date(string='SPK.PO Date/Contract Date')
    po_start_date = fields.Date(string='Plan Start Date')
    po_end_date = fields.Date(string='Plan End Date')
    po_desc = fields.Text(string='PO Description')
    project_id = fields.Many2one('project.project',
                                   string='Project',
                                   store=True,)
    po_no_site =  fields.Char(string='No Site')

    @api.onchange('project_id')
    def _onchange_project_no_site(self):
        if self.number:
            seq = self.env['ir.sequence'].next_by_code('project.no.site') or 'New'
            sq = self.number
            number = '{:0>4}'.format(sq)
            pro = self.project_id.seq or 'xxxx'
            result = pro, ''.join(number)
            res = ''.join(str(v) for v in result)
            self.po_no_site = res if res else None

    number = fields.Char(
        compute='_compute_get_number',
        store=True,)

    @api.depends('project_id')
    def _compute_get_number(self):
        for order in self.mapped('project_id'):
            number = 1
            for line in order.project_po_line:
                line.number = number
                number += 1



