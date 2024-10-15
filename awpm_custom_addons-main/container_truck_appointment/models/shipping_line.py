from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessDenied
import re
import string
import secrets
import logging

_logger = logging.getLogger(__name__)

class ShippingLine(models.Model):
    _name = 'shipping.line'
    _description = 'Shipping Line'
    _inherits = {
        'res.partner': 'partner_id'
    }
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    is_shipping_line = fields.Boolean(string='Is Shipping Line', default=True)
    company_id = fields.Many2one('res.company', string='Company')
    password = fields.Char(string='Password')
    vessel_ids = fields.One2many(
        comodel_name='vessel',
        inverse_name='shipping_line_id',
        string='Vessels'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('request', 'Request'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    partner_id = fields.Many2one('res.partner', ondelete='cascade', required=True)

    @api.constrains('email')
    def _check_valid_email(self):
        for record in self:
            if record.email:
                if not re.match(r"[^@]+@[^@]+\.[^@]+", record.email):
                    raise ValidationError(
                        "The email address '%s' is not in a valid format. Please enter a valid email address." % record.email)

    def create_user(self):
        self.ensure_one()

        group_awpm_shipping = self.env.ref('container_truck_appointment.group_awpm_shipping')

        user = self.env['res.users'].search([('login', '=', self.email.lower())], limit=1)

        if not user:
            user = self.env['res.users'].create({
                'partner_id': self.partner_id.id,
                'login': self.email,
                'password': self.password,
                'groups_id': [(4, group_awpm_shipping.id)],
            })
        else:
            user.write({
                'password': self.password,
                'groups_id': [(4, group_awpm_shipping.id)],
            })

        self.user_id = user.id

    @api.onchange('ward_id')
    def onchange_ward(self):
        if self.ward_id:
            self.township_id = self.ward_id.township_id.id if self.ward_id.township_id else False
            self.state_id = self.township_id.state_id.id if self.township_id else False
            self.country_id = self.state_id.country_id.id if self.state_id else False
            return {'domain': {'township_id': [('state_id', '=', self.state_id.id)]}}
        else:
            if not self.township_id:
                self.township_id = False
            else:
                return {'domain': {'ward_id': [('township_id', '=', self.township_id.id)]}}

            if not self.state_id:
                self.state_id = False

            if not self.country_id:
                self.country_id = False

            return {'domain': {'township_id': []}}

    @api.onchange('township_id')
    def onchange_township(self):
        if self.township_id:
            if self.township_id != self.ward_id.township_id:
                self.ward_id = False
            self.state_id = self.township_id.state_id.id
            self.country_id = self.state_id.country_id.id
            return {'domain': {'ward_id': [('township_id', '=', self.township_id.id)]}}
        else:
            if not self.state_id:
                self.state_id = False
            else:
                return {'domain': {'township_id': [('state_id', '=', self.state_id.id)]}}

            if not self.country_id:
                self.country_id = False
            return {'domain': {'ward_id': []}}

    @api.onchange('state_id')
    def onchange_state(self):
        if self.state_id:
            if self.township_id.state_id != self.state_id:
                self.township_id = False
                self.ward_id = False

            self.country_id = self.state_id.country_id.id

            return {'domain': {'township_id': [('state_id', '=', self.state_id.id)]}}

        else:
            self.country_id = False
            return {'domain': {'township_id': []}}

    @api.onchange('country_id')
    def onchange_country(self):
        if self.country_id:
            if self.country_id != self.state_id.country_id:
                self.state_id = False
                self.township_id = False
                self.ward_id = False
            return {'domain': {'state_id': [('country_id', '=', self.country_id.id)]}}
        else:
            return {'domain': {'state_id': []}}

    def action_approve(self):
        for record in self:
            if record.state != 'approve':
                if not record.email:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Warning'),
                            'type': 'warning',
                            'message': 'User must have an email address.',
                            'sticky': True,
                        }
                    }
                else:
                    existing_user = self.env['res.users'].with_context(active_test=False).search(
                        [('login', '=', record.email.lower())], limit=1)
                    if existing_user:
                        if not existing_user.active:
                            existing_user.active = True
                        record.write({'state': 'approve'})
                        message = 'User with the same login already exists and has been reactivated.'
                        message_type = 'info'
                    else:
                        if not record.password:
                            record.password = record.generate_password()
                        record.create_user()
                        record.write({'state': 'approve'})
                        message = 'User approved and created successfully.'
                        message_type = 'rainbow_man'

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Information'),
                            'type': message_type,
                            'message': message,
                            'sticky': True,
                            'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                        }
                    }

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_reject(self):
        for record in self:
            if record.state != 'reject':
                record.write({'state': 'reject'})

                if record.email:
                    user = self.env['res.users'].search([('login', '=', record.email.lower())], limit=1)
                    if user:
                        user.active = False

                message = 'The shipping line has been rejected successfully and cannot log in until approved.'
                message_type = 'success'

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Information'),
                        'type': message_type,
                        'message': message,
                        'sticky': False,
                        'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                    }
                }

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def generate_password(self, length=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(characters) for i in range(length))


