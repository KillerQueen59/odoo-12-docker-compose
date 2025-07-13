from odoo import models, api, fields


class HrEmployeeCertificate(models.Model):
    _name = "hr.employee.certificate"

    name = fields.Many2one('hr.employee', string="Employee")
    certificate_line_ids = fields.One2many('hr.employee.certificate.line', 'certificate_id', string='Certificate Lines')
    jabatan = fields.Many2one('hr.job', related='name.job_id', string='Jabatan Sekarang')
    gut_nik = fields.Char(related='name.gut_nik', string='NIK')

class HrEmployeeCertificateLine(models.Model):
    _name = "hr.employee.certificate.line"

    certificate_id = fields.Many2one('hr.employee.certificate')
    seq = fields.Char('No')
    name = fields.Char('Sertifikasi')
    deskripsi = fields.Text('Deskripsi')
    badan_penerbit = fields.Char('Badan Penerbit')
    tanggal_sertifikasi = fields.Date('Tanggal Sertifikasi')
    bidang_sertifikasi = fields.Char('Bidang Sertifikasi')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachment',)
 