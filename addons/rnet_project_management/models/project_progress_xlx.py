# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from io import BytesIO
import pytz
import xlsxwriter
import base64
from datetime import datetime, date
from pytz import timezone

class FakturPajakInvoice(models.Model):
    _inherit = 'project.progress.plan'

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

    def action_export_progress_to_excel(self):
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        cell_format, workbook = self.cell_format(workbook)
        report_name = 'Project Progress'

        worksheet = workbook.add_worksheet(self.name.no)

        columns = [
                'External Id',
                'Project',
                'Project Plan Curve/Tanggal',
                'Project Plan Curve/Progress %',
                'Project Plan Cash Out/Tanggal',
                'Project Plan Cash Out/Cash Out',
                'Project Plan Cash In/Tanggal',
                'Project Plan Cash In/Cash In',
                'Project Plan Invoice/Tanggal',
                'Project Plan Invoice/Invoice',
                'Project Plan Manhour/Tanggal',
                'Project Plan Manhour/Manhour',
                'Project Actual Curve/Tanggal',
                'Project Actual Curve/Progress %',
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
        worksheet.set_column('D:O', 35)
        worksheet.write('A2', '', cell_format['header'])
        worksheet.write('A3', '', cell_format['header'])

        for col in columns:
            worksheet.write(0, column, col, cell_format['header'])
            column += 1


        data_list = []
        for rec in self:
            external_id = rec.get_metadata()[0].get('xmlid')
            data_list.append([
                    external_id,
                    rec.name.no or '',
                ])

        

        row = 2
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

        workbook.close()
        result = base64.encodestring(fp.getvalue())
        project = self.name.no or ''
        filename = '%s %s ' % (report_name,  project,)
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
