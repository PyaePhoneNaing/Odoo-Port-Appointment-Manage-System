from odoo import fields, models

class ResAbstractCountry(models.AbstractModel):
    _name = 'res.abstract.country'
    _description = "Abstract Country"

    # Common fields for country-related models
    name = fields.Char(string="Name", required=True)
    burmese_name = fields.Char(string='Burmese Name')
    active = fields.Boolean(string='Active', default=True)
    country_id = fields.Many2one('res.country', string='Country', store=True)


class ResCountryTownship(models.Model):
    _name = 'res.country.township'
    _description = "Township"
    _inherit = ['res.abstract.country']

    # Specific field for township
    state_id = fields.Many2one('res.country.state', string='State')


class ResCountryWard(models.Model):
    _name = 'res.country.ward'
    _description = "Ward"
    _inherit = ['res.abstract.country']

    # Specific field for ward
    township_id = fields.Many2one('res.country.township', string='Township')


class ResCountry(models.Model):
    _name = 'res.country'
    _description = "Country"
    _inherit = ['res.country', 'res.abstract.country']

    # Additional fields for country
    burmese_name = fields.Char(string='Burmese Name')
    township_ids = fields.One2many('res.country.township', 'country_id', string='Townships')


class ResCountryState(models.Model):
    _name = 'res.country.state'
    _description = "State"
    _inherit = ['res.country.state', 'res.abstract.country']

    # Additional fields for state
    township_ids = fields.One2many('res.country.township', 'state_id', string='Townships')
    ward_ids = fields.One2many('res.country.ward', 'township_id', string='Wards')
