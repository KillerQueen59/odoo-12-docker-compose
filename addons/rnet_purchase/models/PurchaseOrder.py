

import logging
from odoo import api, fields, models, SUPERUSER_ID, _
_logger = logging.getLogger(__name__)
from datetime import date, datetime , timedelta
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Received GR'),
        ('cancel', 'Cancelled'),
        ('finance_approval', 'Waiting Finance Approval'),
        ('director_approval', 'Waiting Director Approval'),
        ('refuse', 'Refused'),
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

    project = fields.Many2one('project.project', string='Project')
    gut_qty_total = fields.Integer('Quantity Ordered', compute='_get_qty_total')
    gut_qty_received = fields.Integer('Quantity Received', compute='_get_qty_received')
    gut_qty_billed = fields.Integer('Quantity Billed', compute='_get_qty_billed')
    gut_receive_status = fields.Selection([
        ('open','Open'),
        ('close','Close'),
        ('over','Over'),
    ], string='Receive Status', default='open', compute='_get_receive_status', store=True)
    gut_qc = fields.Selection([ 
        ('Yes','Yes'),
        ('No','No'),
    ], string='Quality Control', default='Yes', required=True)
    gut_term_of_delivery = fields.Selection([
        ('allowed','Partial Delivery Allowed'),
        ('not allowed', 'Partial Delivery Not Allowed'),
    ], string='Term of Delivery', default='allowed', required=True)
    num_word = fields.Char(string="Say:", compute='_compute_amount_in_word')
    gut_description = fields.Text(string='Description')
    total_purchase_product = fields.Integer(string='Total Products:',compute='_total_purchase_product',help="total Products")
    total_purchase_quantity = fields.Integer(string='Total Quantities:',compute='_total_purchase_product_qty',help="total Quantity")
    is_product_category_service = fields.Boolean(string='Is product category Service?', compute='_compute_is_product_category_service')

    @api.one
    def _get_qty_total(self):
        total = 0
        for rec in self:
            for line in self.order_line:
                total = total + line.product_qty
            rec.gut_qty_total = total


    @api.one
    def _get_qty_received(self):
        total = 0
        for line in self.order_line:
            total = total + line.qty_received
        self.gut_qty_received = total

    @api.one
    def _get_qty_billed(self):
        total = 0
        for line in self.order_line:
            total = total + line.qty_invoiced
        self.gut_qty_billed = total

    @api.multi
    @api.depends('order_line.product_qty', 'order_line.qty_received')
    def _get_receive_status(self):
        for rec in self:
            if rec.gut_qty_received < rec.gut_qty_total:
                rec.gut_receive_status = 'open'
            elif rec.gut_qty_received == rec.gut_qty_total:
                rec.gut_receive_status = 'close'
            elif rec.gut_qty_received > rec.gut_qty_total:
                rec.gut_receive_status = 'over'
            else:
                rec.gut_receive_status = None

    @api.multi
    def _compute_amount_in_word(self):
        for rec in self:
            rec.num_word = str(rec.currency_id.amount_to_text(rec.amount_total))

    def _total_purchase_product(self):
            for record in self:
                list_of_product=[]
                for line in record.order_line:
                    list_of_product.append(line.product_id)
                record.total_purchase_product = len(set(list_of_product))

    def _total_purchase_product_qty(self):
            for record in self:
                total_qty = 0
                for line in record.order_line:
                    total_qty = total_qty + line.product_qty
                record.total_purchase_quantity = total_qty


# line untuk notifikasi email reciept PO 
    email_date = fields.Date()
    recipient = fields.Many2one('hr.employee', string='Recipient',  compute='_compute_nama_employee_pr')
    subject = fields.Char('Subject')
    email_content = fields.Text('Email Content')

# compute nama employee receipt notifikasi
    @api.one
    def _compute_nama_employee_pr(self):
        for rec in self:
            pr_obj = self.env['material.purchase.requisition'].search([('name', '=' , rec.origin)])
            reprentative = self.env['hr.employee'].search([('user_id', '=', rec.user_id.id)])
            if rec.origin:  
                rec.recipient = pr_obj.employee_id
            else:
                rec.recipient = reprentative
   
   #scheduler function
    @api.model
    def send_email_to_issued_by(self):
        today_date = date.today() - timedelta(days=1)
        current_date = str(today_date)

        obj = self.env['purchase.order'].search(['|',('state','=','purchase'), ('gut_receive_status','=','open')])
        if obj:
            for order in obj:

                tgl =  datetime.strptime(str(order.date_planned), "%Y-%m-%d %H:%M:%S").date()
                order_date = str(order.email_date)

                if order and order_date > current_date:
                    manager_mail_template = self.env.ref('rnet_purchase.email_receipt_confirmation_purchase')
                    manager_mail_template.send_mail(self.id)

    #scheduler function
    @api.model
    def send_receipt_purchase_notification(self):
        today_date = date.today() - timedelta(days=5)
        today_datetime = datetime.now() - timedelta(days=5)

        for po in self.env['purchase.order'].search(['&','&',('state','=','purchase'), ('gut_receive_status','in',('open', 'over')), ('date_order', '>', today_datetime)]):
            if po:
                template_id = self.env.ref('rnet_purchase.receipt_purchase_notification_template')
                template_id.send_mail(po.id, force_send=True)

# check jika product category PO line "service"
    @api.multi
    def _compute_is_product_category_service(self):
        for order in self:
               order.is_product_category_service = True if any([ptype in ['service'] for ptype in order.order_line.mapped('product_id.type')]) else False


# override create picking Purchase original source
    @api.model
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
        }

    @api.multi
    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            if any([ptype in ['product', 'consu', 'service'] for ptype in order.order_line.mapped('product_id.type')]):
                pickings = order.picking_ids.filtered(lambda x: x.state not in ('done','cancel'))
                if not pickings:
                    res = order._prepare_picking()
                    picking = StockPicking.create(res)
                else:
                    picking = pickings[0]
                moves = order.order_line._create_stock_moves(picking)
                moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                seq = 0
                for move in sorted(moves, key=lambda move: move.date_expected):
                    seq += 5
                    move.sequence = seq
                moves._action_assign()
                picking.message_post_with_view('mail.message_origin_link',
                    values={'self': picking, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return True

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    gut_remark = fields.Char('Remark')
    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)])
    asset_category_id = fields.Many2one('account.asset.category.custom', string='Asset Category')

# override create picking Purchase original source
    @api.multi
    def _create_or_update_picking(self):
        for line in self:
            if line.product_id.type in ('product', 'consu','service'):
                # Prevent decreasing below received quantity
                if float_compare(line.product_qty, line.qty_received, line.product_uom.rounding) < 0:
                    raise UserError('You cannot decrease the ordered quantity below the received quantity.\n'
                                    'Create a return first.')

                if float_compare(line.product_qty, line.qty_invoiced, line.product_uom.rounding) == -1:
                    # If the quantity is now below the invoiced quantity, create an activity on the vendor bill
                    # inviting the user to create a refund.
                    activity = self.env['mail.activity'].sudo().create({
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'note': _('The quantities on your purchase order indicate less than billed. You should ask for a refund. '),
                        'res_id': line.invoice_lines[0].invoice_id.id,
                        'res_model_id': self.env.ref('account.model_account_invoice').id,
                    })
                    activity._onchange_activity_type_id()

                # If the user increased quantity of existing line or created a new line
                pickings = line.order_id.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.location_dest_id.usage in ('internal', 'transit'))
                picking = pickings and pickings[0] or False
                if not picking:
                    res = line.order_id._prepare_picking()
                    picking = self.env['stock.picking'].create(res)
                move_vals = line._prepare_stock_moves(picking)
                for move_val in move_vals:
                    self.env['stock.move']\
                        .create(move_val)\
                        ._action_confirm()\
                        ._action_assign()



    @api.depends('order_id.state', 'move_ids.state', 'move_ids.product_uom_qty')
    def _compute_qty_received(self):
        for line in self:
            if line.order_id.state not in ['purchase', 'done']:
                line.qty_received = 0.0
                continue
            if line.product_id.type not in ['consu', 'product', 'service']:
                line.qty_received = line.product_qty
                continue
            total = 0.0
            for move in line.move_ids:
                if move.state == 'done':
                    if move.location_dest_id.usage == "supplier":
                        if move.to_refund:
                            total -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                    else:
                        total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
            line.qty_received = total

    @api.multi
    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu','service']:
            return res
        qty = 0.0
        price_unit = self._get_stock_move_price_unit()
        for move in self.move_ids.filtered(lambda x: x.state != 'cancel' and not x.location_dest_id.usage == "supplier"):
            qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
        template = {
            'name': self.name or '',
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'date': self.order_id.date_order,
            'date_expected': self.date_planned,
            'location_id': self.order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': self.order_id._get_destination_location(),
            'picking_id': picking.id,
            'partner_id': self.order_id.dest_address_id.id,
            'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.order_id.picking_type_id.id,
            'group_id': self.order_id.group_id.id,
            'origin': self.order_id.name, 
            'route_ids': self.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.order_id.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
        }
        diff_quantity = self.product_qty - qty
        if float_compare(diff_quantity, 0.0,  precision_rounding=self.product_uom.rounding) > 0:
            quant_uom = self.product_id.uom_id
            get_param = self.env['ir.config_parameter'].sudo().get_param
            if self.product_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
                product_qty = self.product_uom._compute_quantity(diff_quantity, quant_uom, rounding_method='HALF-UP')
                template['product_uom'] = quant_uom.id
                template['product_uom_qty'] = product_qty
            else:
                template['product_uom_qty'] = diff_quantity
            res.append(template)
        return res

    @api.model
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
        }

# onchange product_id order line
    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.product_qty = 0.0
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = '%s %s %s' % (self.product_id.name, self.product_id.brand.name or '', self.product_id.brand_type or '')
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase
        fpos = self.order_id.fiscal_position_id
        if self.env.uid == SUPERUSER_ID:
            company_id = self.env.user.company_id.id
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
        else:
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id)

        self._suggest_quantity()
        self._onchange_quantity()

        return result

# batas overide