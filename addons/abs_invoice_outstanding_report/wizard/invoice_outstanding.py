# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2019-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class InvoiceOutstanding(models.TransientModel):
    _name = "invoice.outstanding"

    start_date = fields.Date(string='Cut-off Date', required='1', help='select start date', default=fields.Date.context_today,)
    end_date = fields.Date(string='To Due Date', help='select end date')
    customer = fields.Many2one('res.partner', string='Customer', domain=[('customer','=',True)] )
    total_amount_due = fields.Integer(string='Total Outstanding Amount')
    total_amount_pph = fields.Integer(string='Total Outstanding Amount PPh')
    currency = fields.Char(string='currency')

    @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['start_date', 'end_date','customer'])[0]
        if not self.check_outstanding_customer():
            raise UserError("There is not any Outstanding invoice. Please check cut-off date or invoice status is 'Open'")
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['start_date', 'end_date','customer'])[0])
        return self.env.ref('abs_invoice_outstanding_report.action_customer_invoice_outstanding').report_action(self, data=data, config=False)


    def check_outstanding_customer(self):
        for rec in self:
            invoices = self.env['account.invoice'].search([('date_due', '<=', rec.start_date),('partner_id', 'in', [rec.customer.id]),('type','=', 'out_invoice'),('state','=','open')])
        return invoices