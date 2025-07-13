from odoo import models, api, fields,_

STATEOFFICE = [
    ('sangat_baik', 'Sangat Baik'),
    ('baik', 'Baik'),
    ('cukup', 'Cukup'),
    ('kurang', 'Kurang'),
]

def get_years():
         year_list = [] 
         for i in range(1963, 2040): year_list.append((i, str(i))) 
         return year_list

class EmployeeCV(models.Model):
    _name = 'hr.employee.cv'

# Data Diri
    name = fields.Many2one('hr.employee', string='Employee')
    nik = fields.Char(related='name.gut_nik', string='NIK')
    foto = fields.Binary(related='name.image',  string='Foto')
    jabatan = fields.Many2one('hr.job', related='name.job_id', string='Jabatan Sekarang')
    status_karyawan = fields.Many2one('hr.contract.type', related='name.status_karyawan', string='Status Karyawan')
    department = fields.Many2one('hr.department', related='name.department_id', string='Departemen')
    atasan = fields.Many2one('hr.employee', related='name.parent_id', string='Atasan Langsung')
    identification_id = fields.Char( related='name.identification_id', string='KTP')
    gut_npwp = fields.Char( related='name.gut_npwp', string='NPWP')
    passport_id = fields.Char( related='name.passport_id', string='Passport')
    street = fields.Char(related='name.address_home_id.street')
    city = fields.Char(related='name.address_home_id.city', string='Kota')
    state = fields.Many2one('res.partner', related='name.address_home_id', string='Provinsi')
    phone = fields.Many2one('res.partner', related='name.address_home_id', string='Phone')
    mobile = fields.Many2one('res.partner', related='name.address_home_id', string='Mobile')
    email = fields.Many2one('res.partner', related='name.address_home_id', string='Email',)
    birthday = fields.Date( related='name.birthday', string='Tanggal Lahir')
    place_of_birth = fields.Char(related='name.place_of_birth', string='Tempat Lahir')
    gender = fields.Selection(related='name.gender', string='Jenis Kelamin')
    marital = fields.Selection(related='name.marital', string='Status Pernikahan')
    region = fields.Selection(related='name.region', string='Agama')
    emergency_contact = fields.Char(related='name.emergency_contact', string='Kontak Darurat')
    emergency_phone = fields.Char(related='name.emergency_phone', string='Nomor HP Darurat')
    akun_fb = fields.Char( string='Akun Facebook')
    akun_ig = fields.Char( string='Akun Instagram')
    ms_office = fields.Selection(STATEOFFICE, string="Ms. Office")
    internet = fields.Selection(STATEOFFICE, string="Internet")
    active = fields.Boolean(default=True)
    employee_location_line_ids = fields.One2many('hr.employee.location.line', 'employee_location', string='Location Lines')


# Pendidikan
    nama_kampus = fields.Char( string='Nama Kampus')
    lokasi_kampus = fields.Char( string='Lokasi Kampus')
    jurusan_kuliah = fields.Char( string='Jurusan Kuliah')
    jenjang_kuliah = fields.Char( string='Jenjang Kuliah')
    tahun_lulus_kuliah = fields.Selection(get_years(), string='Tahun Lulus Kuliah')
    ipk = fields.Float( string='IPK')
    judul_ta = fields.Char( string='Judul Tugas AKhir')
    nama_sma = fields.Char( string='Nama SMA')
    lokasi_sma = fields.Char( string='Kota SMA')
    jurusan_sma = fields.Char( string='Jurusan SMA')
    tahun_lulus_sma = fields.Selection(get_years(), string='Tahun Lulus SMA')
    nama_smp = fields.Char( string='Nama SMP')
    lokasi_smp = fields.Char( string='Kota SMP')
    tahun_lulus_smp = fields.Selection(get_years(), string='Tahun Lulus SMP')
    nama_sd = fields.Char( string='Nama SD')
    lokasi_sd = fields.Char( string='Kota SD')
    tahun_lulus_sd = fields.Selection(get_years(),  string='Tahun Lulus SD')
    organisasi_line_ids = fields.One2many('hr.employee.cv.organisasi.line', 'cv_organisasi_id', string='Organisasi Lines')
    seminar_line_ids = fields.One2many('hr.employee.cv.seminar.line', 'cv_seminar_id', string='Seminar Lines')
    spesialisasi_line_ids = fields.One2many('hr.employee.cv.spesialisasi.line', 'cv_spesialisasi_id', string='Spesialisasi Lines')
    pengalaman_line_ids = fields.One2many('hr.employee.cv.pengalaman.line', 'cv_pengalaman_id', string='Pengalaman Lines')
    pengalaman_gut_line_ids = fields.One2many('hr.employee.cv.project.line', 'cv_pengalaman_gut_id', string='Pengalaman Proyek GUT Lines')
    pendidikan_line_ids = fields.One2many('hr.employee.cv.pendidikan.line', 'cv_pendidikan_id', string='Pendidikan Lines')



class EmployeeCVPendidikanLine(models.Model):
    _name = 'hr.employee.cv.pendidikan.line'

    cv_pendidikan_id = fields.Many2one('hr.employee.cv')
    name = fields.Char(string='Tingkat')
    nama_sekolah = fields.Char(string='Nama Sekolah')
    lokasi_sekolah = fields.Char(string='Lokasi')
    tahun_lulus = fields.Char(string='Tahun Lulus')
    jurusan = fields.Char(string='Jurusan')
    jenjang = fields.Char(string='Jenjang Kuliah')
    ipk = fields.Char(string='IPK')
    judul_ta = fields.Char(string='Judul Tugas Akhir')

class EmployeeCVOrganisasiLine(models.Model):
    _name = 'hr.employee.cv.organisasi.line'

    cv_organisasi_id = fields.Many2one('hr.employee.cv')
    name = fields.Char(string='Nama Organisasi', )
    jabatan = fields.Char(string='Jabatan', )
    tahun_aktif = fields.Selection(get_years(),  string='Tahun Aktif')

class EmployeeCVSeminarLine(models.Model):
    _name = 'hr.employee.cv.seminar.line'

    cv_seminar_id = fields.Many2one('hr.employee.cv')
    name = fields.Char(string='Tema' )
    lembaga_penyenggara = fields.Char(string='Lembaga Penyelenggara', )
    tahun_pelatihan = fields.Selection(get_years(),  string='Tahun Pelatihan')

class EmployeeCVSpesialisasiLine(models.Model):
    _name = 'hr.employee.cv.spesialisasi.line'

    cv_spesialisasi_id = fields.Many2one('hr.employee.cv')
    name = fields.Char(string='Bidang' )
    deskripsi = fields.Char(string='Deskripsi', )

class EmployeeCVPenglamanLine(models.Model):
    _name = 'hr.employee.cv.pengalaman.line'

    cv_pengalaman_id = fields.Many2one('hr.employee.cv')
    name = fields.Char(string='Jabatan', )
    nama_perusahaan = fields.Char(string='Nama Perusahaan' )
    nama_atasan = fields.Char(string='Nama Atasan') 
    nama_proyek= fields.Char(string='Nama Proyek')
    area = fields.Char(string='Area / Wilayah')
    tahun_masuk = fields.Selection(get_years(),  string='Tahun Masuk')
    tahun_keluar = fields.Selection(get_years(),  string='Tahun Keluar')

    
class EmployeeCVPenglamanGutLine(models.Model):
    _name = 'hr.employee.cv.project.line'

    cv_pengalaman_gut_id = fields.Many2one('hr.employee.cv')
    name = fields.Many2one('project.project', string='Nama Proyek')
    jabatan = fields.Char(string='Jabatan')
    nama_atasan_gut = fields.Many2one('hr.employee', string='Nama Atasan')
    tahun = fields.Selection(get_years(),  string='Tahun')
    work_date = fields.Date(string='Work Date')

    @api.onchange('name')
    def onchange_project(self):
        for rec in self:
            self.nama_atasan_gut = rec.name.project_manager

class EmployeeLocationLine(models.Model):
    _name = "hr.employee.location.line"

    employee_location = fields.Many2one('hr.employee.cv')
    name = fields.Many2one('project.project', string='Project')
    project_manager = fields.Many2one('hr.employee', string='Project Manager', compute='_compute_project_manager', store=True)
    jabatan_project = fields.Char(string='Jabatan')
    work_date = fields.Date(string='Work Date')

    @api.depends('name')
    def _compute_project_manager(self):
        for record in self:
            record.project_manager = record.name.project_manager if record.name else None

    @api.depends('name', 'work_date')
    def name_get(self):
        res = []
        for rec in self:
            tgl = rec.work_date.strftime('%b' ' ' '%Y')
            project = rec.name.name[:20]
            name = _('%s - %s') % (project, tgl)
            res.append((rec.id, name))
        return res

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # get name alamat dan phone
    def name_get(self):
        result = []
        for record in self:
            if self.env.context.get('hp', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id," "+str(record.mobile)))
            elif self.env.context.get('phone', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.phone)))
            elif self.env.context.get('email', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.email)))
            elif self.env.context.get('street', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.street)))
            elif self.env.context.get('kota', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.city)))
            elif self.env.context.get('provinsi', False):
                # Only goes off when the custom_search is in the context values.
                result.append((record.id, " "+str(record.state_id.name)))
            else:
                result.append((record.id, record.name))
        return result
    



