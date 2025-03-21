from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import webbrowser

class StockLocationInherit(models.Model):
    _inherit = 'stock.location'

    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    zip = fields.Char(string='Zip')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')

    longit = fields.Float(string='Longitude')
    latit = fields.Float(string='Latitude')


    @api.multi
    def open_map(self):
        for rec in self:
            url = "http://maps.google.com/maps?oi=map&q="
        if not rec.latit:
            if rec.street:
                url += rec.street.replace(' ', '+')
            if rec.city:
                url += '+'+rec.city.replace(' ', '+')
            if rec.state_id:
                url += '+'+rec.state_id.name.replace(' ', '+')
            if rec.country_id:
                url += '+'+rec.country_id.name.replace(' ', '+')
            if rec.zip:
                url += '+'+rec.zip.replace(' ', '+')
        else:
            if rec.latit:
                lat = str(rec.latit)
                url += lat.replace(' ', '+')
            if rec.longit:
                long = str(rec.longit)
                url += '+'+long.replace(' ', '+')


        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url
        }