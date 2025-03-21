# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from io import BytesIO
import pytz
import xlsxwriter
import base64
from datetime import datetime, date
from pytz import timezone

class FakturPajakInvoice(models.Model):
    _inherit = 'faktur.pajak.invoice'

    @api.model
    def get_default_date_model(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone('Asia/Jakarta'))

    file_data = fields.Binary('File', readonly=True)
    
    def cell_format(self, workbook):
        cell_format = {}
        cell_format['title'] = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 20,
            'font_name': 'Arial',
        })
        cell_format['no'] = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': True,
        })
        cell_format['header'] = workbook.add_format({
            'align': 'left',
            'border': True,
            'font_name': 'Arial',
        })

        cell_format['content'] = workbook.add_format({
            'font_size': 11,
            'align': 'left',
            'border': True,
            'font_name': 'Arial',
        })
        cell_format['content_float'] = workbook.add_format({
            'font_size': 11,
            'border': True,
            'num_format': '#,##0.00',
            'font_name': 'Arial',
        })
        cell_format['total'] = workbook.add_format({
            'bold': True,
            'bg_color': '#d9d9d9',
            'num_format': '#,##0.00',
            'border': True,
            'font_name': 'Arial',
        })
        return cell_format, workbook

    def action_export_faktur_to_excel(self):
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        cell_format, workbook = self.cell_format(workbook)
        report_name = 'Faktur Pajak'
        invoice_ids = self.mapped('invoice_id')
        for invoice_id in invoice_ids:
            worksheet = workbook.add_worksheet(invoice_id.number)

            columns = [
                'FK',
                'KD_JENIS_TRANSAKSI',
                'FG_PENGGANTI',
                'NOMOR_FAKTUR',
                'MASA_PAJAK',
                'TAHUN_PAJAK',
                'TANGGAL_FAKTUR',
                'NPWP',
                'NAMA',
                'ALAMAT_LENGKAP',
                'JUMLAH_DPP',
                'JUMLAH_PPN',
                'JUMLAH_PPNBM',
                'ID_KETERANGAN_TAMBAHAN',
                'FG_UANG_MUKA',
                'UANG_MUKA_DPP',
                'UANG_MUKA_PPN',
                'UANG_MUKA_PPNBM',
                'REFERENSI',
                'KODE_DOKUMEN_PENDUKUNG',
            ]
            columns2 = [
                'LT',
                'NPWP',
                'NAMA',
                'JALAN',
                'BLOK',
                'NOMOR',
                'RT',
                'RW',
                'KECAMATAN',
                'KELURAHAN',
                'KABUPATEN',
                'PROPINSI',
                'KODE_POS',
                'NOMOR_TELEPON',
            ]
            columns3 = [
                'OF',
                'KODE_OBJEK',
                'NAMA',
                'HARGA_SATUAN',
                'JUMLAH_BARANG',
                'HARGA_TOTAL',
                'DISKON',
                'DPP',
                'PPN',
                'TARIF_PPNBM',
                'PPNBM',
            ]

            column_length = len(columns)
            if not column_length:
                return False
            no = 1
            column = 1
            column2 = 1
            column3 = 1

            worksheet.set_column('A:A', 5)
            worksheet.set_column('B:B', 10)
            worksheet.set_column('C:C', 20)
            worksheet.set_column('D:G', 20)
            worksheet.write('A1', 'No', cell_format['header'])
            worksheet.write('A2', '', cell_format['header'])
            worksheet.write('A3', '', cell_format['header'])

            for col in columns:
                worksheet.write(0, column, col, cell_format['header'])
                column += 1
            for col2 in columns2:
                worksheet.write(1, column2, col2, cell_format['header'])
                column2 += 1
            for col3 in columns3:
                worksheet.write(2, column3, col3, cell_format['header'])
                column3 += 1


            data_list = []
            for rec in self:
                data_list.append([
                    rec.fk or '',
                    rec.kd_jenis_transaksi or '',
                    format(rec.fg_pengganti,'.0f') or '',
                    rec.name or '',
                    rec.masa_faktur or '',
                    rec.tahun_pajak or '',
                    rec.tgl_faktur.strftime("%d/%m/%Y") or '',
                    rec.customer_npwp or '',
                    rec.customer_id.name or '',
                    rec.customer_alamat or '',
                    format(rec.jumlah_dpp,'.0f') or '',
                    format(rec.jumlah_ppn,'.0f') or '',
                    format(rec.jumlah_ppnbm,'.0f') or '',
                    round(rec.id_keterangan_tambahan) or '',
                    format(rec.fg_uang_muka,'.0f') or '',
                    format(rec.uang_muka_dpp,'.0f') or '',
                    format(rec.uang_muka_ppn,'.0f') or '',
                    format(rec.uang_muka_ppnbm,'.0f') or '',
                    rec.referensi or '',
                    rec.kode_dokumen_pendukung or '',
                ])
            data_list2 = []
            for rec in self.invoice_id:
                data_list2.append([
                    'FAPR',
                    rec.company_id.name,
                    self.company_alamat or '',
                ])
            
            data_list3 = []
            for rec in self.invoice_id.invoice_line_ids:
                data_list3.append([
                    'OF',
                    rec.no_site or '',
                    rec.name,
                    format(rec.price_unit,'.0f') or '',
                    self.jumlah_barang or '',
                    format(rec.price_unit,'.0f') or '',
                    format(rec.discount,'.0f') or '',
                    format(rec.price_subtotal,'.0f') or '',
                    format(rec.price_subtotal / 100 * 11,'.0f') or '',
                    format(self.tarif_ppnbm,'.0f') or '',
                    format(self.ppnbm,'.0f') or '',
                ])

            row = 4
            column_float_number = {}
            for data in data_list:
                column = 1
                for value in data:
                    if type(value) is int or type(value) is float:
                        content_format = 'content_float'
                        column_float_number[column] = column_float_number.get(column, 0) + value
                    else:
                        content_format = 'content'
                    if isinstance(value, datetime):
                        value = pytz.UTC.localize(value).astimezone(timezone(self.env.user.tz or 'UTC'))
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date):
                        value = value.strftime('%Y-%m-%d')
                    worksheet.write(row - 1, column, value, cell_format[content_format])
                    column += 1
                row += 1

            row = 5
            column_float_number = {}
            for data in data_list2:
                column = 1
                for value in data:
                    if type(value) is int or type(value) is float:
                        content_format = 'content_float'
                        column_float_number[column] = column_float_number.get(column, 0) + value
                    else:
                        content_format = 'content'
                    if isinstance(value, datetime):
                        value = pytz.UTC.localize(value).astimezone(timezone(self.env.user.tz or 'UTC'))
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date):
                        value = value.strftime('%Y-%m-%d')
                    worksheet.write(row - 1, column, value, cell_format[content_format])
                    column += 1
                row += 1

            row = 6
            column_float_number = {}
            for data in data_list3:
                column = 1
                for value in data:
                    if type(value) is int or type(value) is float:
                        content_format = 'content_float'
                        column_float_number[column] = column_float_number.get(column, 0) + value
                    else:
                        content_format = 'content'
                    if isinstance(value, datetime):
                        value = pytz.UTC.localize(value).astimezone(timezone(self.env.user.tz or 'UTC'))
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date):
                        value = value.strftime('%Y-%m-%d')
                    worksheet.write(row - 1, column, value, cell_format[content_format])
                    column += 1
                row += 1

# row total
            # row -= 1
            # for x in range(column_length + 1):
            #     if x == 0:
            #         worksheet.write('A%s' % (row + 1), '', cell_format['header'])
            #     elif x not in column_float_number:
            #         worksheet.write(row, x, '', cell_format['header'])
            #     else:
            #         worksheet.write(row, x, column_float_number[x], cell_format['total'])

        workbook.close()
        result = base64.encodestring(fp.getvalue())
        project = self.invoice_id.project.name or ''
        faktur = self.name or ''
        date_string = self.tgl_faktur.strftime("%Y-%m-%d")
        filename = '%s %s %s %s' % (report_name, faktur, project, date_string)
        filename += '%2Ecsv'
        self.write({'file_data': result})
        url = "web/content/?model=" + self._name + "&id=" + str(
            self[:1].id) + "&field=file_data&download=true&filename=" + filename
        return {
            'name': 'Generic Excel Report',
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
