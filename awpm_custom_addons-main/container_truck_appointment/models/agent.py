# Import necessary modules for our coding adventure
import re

from odoo import fields, models, api, http
from odoo.exceptions import ValidationError, UserError, AccessDenied, AccessError
import secrets
import string
from odoo.tools.translate import _, _lt
from PIL import Image
import io
import base64
import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    ward_id = fields.Many2one(comodel_name='res.country.ward', string='Ward', required=False,
                              tracking=True)
    township_id = fields.Many2one(comodel_name='res.country.township', string='Township', required=False,
                                  tracking=True)

    @api.depends('township_id')
    def _compute_city(self):
        for partner in self:
            partner.city = partner.township_id.name if partner.township_id else ''

    city = fields.Char(compute=_compute_city, store=True)

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

class Agent(models.Model):
    _name = 'container.truck.appointment.agent'
    _description = 'Container Truck Appointment Agent'
    _inherits = {
        'res.partner': 'partner_id'
    }
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    login = fields.Char(string="Login Email", compute='_compute_login_email')
    code = fields.Char(string="Code", required=True,
                       tracking=True)
    partner_id = fields.Many2one('res.partner', ondelete='cascade', required=True)
    is_agent = fields.Boolean(string='Is Agent', default=True, tracking=True)
    attachments = fields.Many2many('ir.attachment', string="Attachments", tracking=True)

    channel_ids = fields.Many2many('res.partner', 'agent_channel_rel', 'agent_id', 'channel_id',
                                   string='Channel',
                                   tracking=True)
    user_id = fields.Many2one('res.users', string='User', tracking=True)
    nrc_state_id = fields.Many2one(comodel_name='nrc.state', string='NRC State No', required=False, tracking=True)
    nrc_district_id = fields.Many2one(comodel_name='nrc.district', string='NRC District Code', required=False,
                                      tracking=True)
    nrc_type_id = fields.Many2one(comodel_name='nrc.type', string='NRC Type', required=False, tracking=True)
    nrc_number = fields.Char(string='NRC Number', required=False, tracking=True)
    state = fields.Selection(
        [('draft', 'DRAFT'), ('pending', 'PENDING'), ('approved', 'APPROVED'), ('reject', 'REJECT')],
        tracking=True, help="Agent Registration Status",
        string="Status", default='pending')
    gender = fields.Selection(string='Gender', selection=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
                              required=False, tracking=True)
    password = fields.Char(string='Password', required=False)
    nrc = fields.Char(string='NRC', required=False, compute='_compute_readable_nrc')
    color = fields.Char(string='Color', required=False, tracking=True)

    @api.depends('nrc_state_id', 'nrc_district_id', 'nrc_type_id', 'nrc_number')
    def _compute_readable_nrc(self):
        for record in self:
            record.nrc = '{}/{}({}){}'.format(record.nrc_state_id.name or '', record.nrc_district_id.name or '',
                                              record.nrc_type_id.name or '', record.nrc_number or '')

    @api.constrains('name')
    def _check_duplicate(self):
        rec = self.search_count([('code', '=', self.code), ('id', '!=', self.id)])
        if rec:
            raise ValidationError('The agent code already exists.')

    @api.constrains('email')
    def _check_valid_email(self):
        for record in self:
            if record.email:
                if not re.match(r"[^@]+@[^@]+\.[^@]+", record.email):
                    raise ValidationError(
                        "The email address '%s' is not in a valid format. Please enter a valid email address." % record.email)

    @api.model
    def create(self, values):
        values['is_company'] = False
        values['is_agent'] = True
        if 'image_medium' in values:
            if values['image_medium']:
                values['image_128'] = values['image_1920'] = values['image_medium'] = self.reduce_image_size(
                    values['image_medium'])
        agent = super(Agent, self).create(values)
        return agent

    def write(self, values):
        if 'is_company' not in values:
            values['is_company'] = False
        if 'is_agent' not in values:
            values['is_agent'] = True

        if 'image_medium' in values:
            if values['image_medium']:
                values['image_128'] = values['image_1920'] = values['image_medium'] = self.reduce_image_size(
                    values['image_medium'])

        return super(Agent, self).write(values)

    # Method to override delete functionality and delete associated user
    def unlink(self):
        for agent in self:
            if agent.user_id:
                agent.user_id.unlink()
            if agent.partner_id:
                agent.partner_id.unlink()
        return super(Agent, self).unlink()

    def create_user(self):
        self.ensure_one()
        # Create a corresponding portal user
        group_awpm_user = self.env.ref('container_truck_appointment.group_awpm_user')
        user = self.with_company(company=1).env['res.users'].create({
            'partner_id': self.partner_id.id,
            'login': self.email,
            'password': self.password,
            # 'groups_id': [(4, 0, [self.env.ref('base.group_portal').id])],
            'groups_id': [(4, group_awpm_user.id)],
        })
        self.user_id = user.id

    @api.onchange('nrc_state_id')
    def onchange_nrc_state_id(self):
        if self.nrc_state_id:
            if self.nrc_district_id:
                if self.nrc_state_id.id != self.nrc_district_id.nrc_state:
                    self.nrc_district_id = False
            return {'domain': {'nrc_district_id': [('nrc_state', '=', self.nrc_state_id.id)]}}
        else:
            if not self.nrc_district_id:
                self.nrc_district_id = False
            return {'domain': {'nrc_district_id': []}}

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
            if record.state != 'approved':
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
                    existing_user = self.env['res.users'].search([('login', '=', record.email.lower())], limit=1)
                    if existing_user:
                        record.write({'state': 'approved'})
                        mail_template = self.env.ref('container_truck_appointment.email_template_agent_approved')
                        if mail_template:
                            try:
                                default_email_from = self.env['ir.config_parameter'].sudo().get_param(
                                    'mail.default.from')
                                mail_template.email_from = default_email_from or mail_template.email_from
                                mail_template.send_mail(record.id, force_send=True)
                                message = 'User with the same login already exists. Email sent successfully.'
                                message_type = 'info'
                            except Exception as e:
                                _logger.error('Failed to send approval email: %s', e)
                                message = f'User with the same login already exists. Failed to send email: {e}'
                                message_type = 'danger'
                        else:
                            message = 'Email template not found.'
                            message_type = 'danger'

                    else:
                        if not record.password:
                            record.password = record.generate_password()
                        record.create_user()
                        record.write({'state': 'approved', 'password': record.password})
                        mail_template = self.env.ref('container_truck_appointment.email_template_agent_approved')
                        if mail_template:
                            try:
                                default_email_from = self.env['ir.config_parameter'].sudo().get_param(
                                    'mail.default.from')
                                mail_template.email_from = default_email_from or mail_template.email_from
                                mail_template.send_mail(record.id, force_send=True)
                                message = 'User approved and created. Email sent successfully.'
                                message_type = 'rainbow_man'
                            except Exception as e:
                                _logger.error('Failed to send approval email: %s', e)
                                message = f'User approved and created. Failed to send email: {e}'
                                message_type = 'danger'
                        else:
                            message = 'Email template not found.'
                            message_type = 'danger'

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
                mail_template = self.env.ref('container_truck_appointment.email_template_agent_rejected')
                if mail_template:
                    try:
                        default_email_from = self.env['ir.config_parameter'].sudo().get_param('mail.default.from')
                        mail_template.email_from = default_email_from or mail_template.email_from
                        mail_template.send_mail(record.id, force_send=True)
                        message = 'The agent has been rejected. Email sent successfully.'
                        message_type = 'success'
                    except Exception as e:
                        _logger.error('Failed to send rejection email: %s', e)
                        message = f'The agent has been rejected. Failed to send email: {e}'
                        message_type = 'danger'
                else:
                    message = 'Email template not found.'
                    message_type = 'danger'

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
        # Define the pool of characters to choose from
        characters = string.ascii_letters + string.digits + string.punctuation  # You can customize this as needed
        # Generate a random password
        password = ''.join(secrets.choice(characters) for _ in range(length))
        return password

    def reduce_image_size(self, base64_image_data, max_pixels=50000000):
        # Decode base64 image data to bytes
        image_data = base64.b64decode(base64_image_data)

        # Open the image from the bytes data
        img = Image.open(io.BytesIO(image_data))

        if img.mode == 'RGBA':
            img = img.convert('RGB')

        # Get the current size of the image
        current_width, current_height = img.size

        # Calculate the current number of pixels
        current_pixels = current_width * current_height

        # If the image is already smaller than the maximum pixels, return the original image data
        if current_pixels <= max_pixels:
            return base64_image_data

        # Calculate the new width and height to fit within the maximum pixels
        ratio = (max_pixels / current_pixels) ** 0.5
        new_width = int(current_width * ratio)
        new_height = int(current_height * ratio)

        # Resize the image
        img = img.resize((new_width, new_height), Image.ANTIALIAS)

        # Save the resized image to a BytesIO buffer
        output_buffer = io.BytesIO()
        img.save(output_buffer, format='JPEG')

        # Get the image data from the buffer
        resized_image_data = output_buffer.getvalue()

        # Encode the resized image data to base64
        resized_base64_image_data = base64.b64encode(resized_image_data).decode('utf-8')

        return resized_base64_image_data


class AgentResUsers(models.Model):
    _inherit = 'res.users'

    def _check_credentials(self, password, env):

        result = super(AgentResUsers, self)._check_credentials(password, env)
        agent = self.env['container.truck.appointment.agent'].search([('user_id', '=', self.id)], limit=1)

        if agent:
            if agent.state != 'approved':
                raise AccessDenied('Your account information is waiting for approval.')

        return result
