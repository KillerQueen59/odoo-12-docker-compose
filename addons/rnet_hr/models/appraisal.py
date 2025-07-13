from odoo import models, api, fields

class EmployeeAppraisal(models.Model):
    _name = 'hr.employee.appraisal'

    name = fields.Char(string='Nomor Record')
    jenis_penilaian = fields.Selection([('berkala','Berkala'),('khusus','Khusus')], string="Jenis Penilaian")
    employee_id = fields.Many2one('hr.employee', string='Employee')
    nik = fields.Char(related='employee_id.gut_nik', string='NIK')
    posisi = fields.Many2one('hr.job', related='employee_id.job_id', string='Posisi Sekarang')
    department = fields.Many2one('hr.department', related='employee_id.department_id', string='Departemen')
    atasan = fields.Many2one('hr.employee', related='employee_id.parent_id', string='Atasan')
    identification_id = fields.Char( related='employee_id.identification_id', string='KTP')
    birthday = fields.Date( related='employee_id.birthday', string='Tanggal Lahir')
    periode = fields.Date(string='Periode Penilaian', default=fields.Date.context_today)
    active = fields.Boolean(default=True)
    kehadiran = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Kehadiran / Ketepatan Waktu")
    disiplin = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Disiplin")
    tingkatan_keterampilan = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Tingkat Ketrampilan")
    kuantitas_kerja = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Kuantitas Kerja")
    kualitas_kerja = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Kualitas Kerja")
    sikap_kerja = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Sikap Kerja")
    adaptasi = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Kemampuan untuk Belajar / Adaptasi terhadap Perubahan")
    tekanan = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Daya tahan terhadap stress / tekanan")
    kerjasama = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Kerjasama")
    pemahaman_tugas = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Pemahaman Tugas (Teknis / Fungsional)")
    kreativitas = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Kreativitas / Inovasi")
    kemandirian = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Kemandirian dan Inisiatif")
    kemampuan_bahasa = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Kemampuan Bahasa")
    kemampuan_analisa = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Kemampuan Analisa")
    pengambilan_keputusan = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Penilaian dan Pengambilan Keputusan")
    penilaian_safety = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Penilaian terhadap Safety")
    penilaian_quality = fields.Selection(
        [('5','5'),('4','4'),('3','3'),('2','2'),('1','1')], string="Penilaian terhadap Quality")
    komentar = fields.Text(string='Komentar')
    pelatihan = fields.Text(string='Pelatihan / Pengalaman Tambahan yang Dibutuhkan')
    kenaikan_gaji = fields.Text(string='Kenaikan Gaji / Jabaran Penambahan Tugas yang Diusulkan Mulai Tanggal')
    komentar_karyawan = fields.Text(string='Komentar Karyawan')
    komentar_atasan= fields.Text(string='Komentar Atasan')
    komentar_moderator = fields.Text(string='Komentar Moderator ( Level Manajemen yang lebih tinggi )')