from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import date, datetime


class FakturPajak(models.Model):
    _name = "faktur.pajak.invoice"


# prevent duplicat name nomor faktur
    @api.constrains('name')
    def _check_name(self):
        if self.name:
            faktur = self.env['faktur.pajak.invoice'].search(
                [('name', '=', self.name), ('id', '!=', self.id)])
            if faktur:
                raise UserError(_('Nomor Faktur Sudah Ada !'))

# get default nama company
    @api.model
    def _default_faktur_company_id(self):
        return self.env['res.partner'].search([('name', '=ilike', 'PT Graha Usaha Teknik') ])

    name = fields.Char(string="Nomor Faktur", required=True)
    fk = fields.Char(string="FK", default="FK")
    kd_jenis_transaksi = fields.Char(string="KD Jenis Transaksi", default=1)
    fg_pengganti = fields.Float(string="FG Pengganti", default=0)
    tgl_faktur = fields.Date(string="Created Date")
    masa_faktur = fields.Char(string="Masa Faktur")
    tahun_pajak = fields.Char(string="Tahun Pajak")
    invoice_id = fields.Many2one('account.invoice',
                                   string='Referensi (Invoice)',
                                   store=True, domain=[('state','!=','draft'),('type', 'in', ('out_invoice','out_refund'))])
    customer_id = fields.Many2one('res.partner',string="Customer", domain=[('customer','=',True)] )
    customer_npwp = fields.Char(string="NPWP",)
    customer_alamat = fields.Text(string="Alamat Customer")
    company_id = fields.Many2one('res.partner', string="Company", default=_default_faktur_company_id)
    company_alamat = fields.Text(string="Company Address", default="GED. OFFICE 8 LEVEL 18-A SCBD, JL. JEND. SUDIRMAN KAV.52-53 , JAKARTA SELATAN")
    jumlah_dpp = fields.Float(string="Jumlah DPP", default=0)
    jumlah_ppn = fields.Float(string="Jumlah PPN", default=0)
    jumlah_ppnbm = fields.Float(string="Jumlah PPNBM", default=0)
    id_keterangan_tambahan= fields.Char(string="Id Keterangan Tambahan",)
    fg_uang_muka = fields.Float(string="FG Uang Muka", default=0)
    uang_muka_dpp = fields.Float(string="Uang Muka DPP", default=0)
    uang_muka_ppn = fields.Float(string="Uang Muka PPN", default=0)
    uang_muka_ppnbm = fields.Float(string="Uang Muka PPNBM", default=0)
    referensi  = fields.Char(string="Referensi")
    kode_dokumen_pendukung  = fields.Char(string="Kode Dokumen Pendukung")

    kode_objek  = fields.Char(string="Kode Objek")
    harga_satuan = fields.Float(string="Harga Satuan", default=0)
    jumlah_barang  = fields.Char(string="Jumlah Barang", default=1)
    harga_total = fields.Float(string="Harga Total", default=0)
    dpp = fields.Float(string="DPP", default=0)
    ppn = fields.Float(string="PPN", default=0)
    tarif_ppnbm = fields.Float(string="Tarif PPNBM", default=0)
    ppnbm = fields.Float(string="PPNBM", default=0)

 
    @api.onchange('customer_id')
    def onchange_customer_id(self):
        for rec in self:
            alamat =  str(rec.customer_id.street or '') + ' ' + str(rec.customer_id.city or '') + ' ' + str(rec.customer_id.state_id.name or '') + ' ' + str(rec.customer_id.zip or '') + ' ' + str(rec.customer_id.country_id.name or '')
            npwp = rec.customer_id.vat
            self.customer_alamat = alamat
            self.customer_npwp = npwp

    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        for rec in self:
            if rec.invoice_id:
                self.customer_id = rec.invoice_id.partner_id.id
                self.tgl_faktur = rec.invoice_id.date_invoice
                self.masa_faktur = rec.invoice_id.date_invoice.strftime("%m")
                self.tahun_pajak = rec.invoice_id.date_invoice.strftime("%Y")
                self.jumlah_dpp = rec.invoice_id.amount_untaxed
                self.jumlah_ppn = rec.invoice_id.amount_tax
