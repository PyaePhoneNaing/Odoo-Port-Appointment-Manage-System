from odoo import fields, models, api
from odoo.exceptions import ValidationError


# Define the abstract model to encapsulate common attributes and constraints for NRC-related models
class NRCCommon(models.AbstractModel):
    _name = 'nrc.common'
    _description = 'NRC Common'

    # Common fields for all NRC-related models
    name = fields.Char('Burmese Name', required=True)
    eng_name = fields.Char('English Name', required=True)

    # Constraint to ensure uniqueness of names across records
    @api.constrains('name')
    def _check_duplicate(self):
        # Count the number of records with the same name
        rec = self.search_count([('name', '=', self.name), ('id', '!=', self.id)])
        # Raise a validation error if duplicates are found
        if rec:
            raise ValidationError('The name already exists.')


# Define the model for NRC State
class NRCState(NRCCommon, models.Model):
    _name = "nrc.state"
    _description = 'NRC State Number'

    # Additional field specific to NRC State
    description = fields.Char('Description', required=True)

    # Constraint to ensure uniqueness of names across records
    @api.constrains('name')
    def _check_duplicate(self):
        # Count the number of records with the same name
        rec = self.search_count([('name', '=', self.name), ('id', '!=', self.id)])
        # Raise a validation error if duplicates are found
        if rec:
            raise ValidationError('The name already exists.')


# Define the model for NRC District
class NRCDistrict(NRCCommon, models.Model):
    _name = "nrc.district"
    _description = 'NRC District'

    # Additional field specific to NRC District
    nrc_state = fields.Many2one('nrc.state', string='NRC State Number', required=True)

    # Constraint to ensure uniqueness of names within the same NRC State
    @api.constrains('name', 'nrc_state')
    def _check_duplicate(self):
        # Count the number of records with the same name and NRC State
        rec = self.search_count(
            [('nrc_state', '=', self.nrc_state.id), ('name', '=', self.name), ('id', '!=', self.id)])
        # Raise a validation error if duplicates are found
        if rec:
            raise ValidationError('The NRC District already exists.')


# Define the model for NRC Type
class NRCType(NRCCommon, models.Model):
    _name = "nrc.type"
    _description = 'NRC Type'
