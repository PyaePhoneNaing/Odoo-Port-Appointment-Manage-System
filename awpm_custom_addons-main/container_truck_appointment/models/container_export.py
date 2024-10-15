# Import necessary modules from Odoo
from odoo import fields, models, api, _
from datetime import date
from datetime import datetime
from odoo.exceptions import ValidationError
import qrcode
import base64
import logging
_logger = logging.getLogger(__name__)
from io import BytesIO
from odoo.http import request



# Define the ContainerTruckAppointmentExport class, representing the container truck appointment export model
class ContainerTruckAppointmentExport(models.Model):
    _name = 'container.truck.appointment.export'
    _description = 'Container Truck Appointment Export'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Appointment No', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    booking_no = fields.Many2one(comodel_name='booking.reference', string='Booking Reference', required=True)
    appointment_date = fields.Date(string='Appointment Date', required=True, tracking=True)
    shipper_id = fields.Many2one(comodel_name='res.partner', string='Consignee', required=True, tracking=True,
                                 domain="[('is_company', '=', True)]")  # Filter to show only companies
    vessel_id = fields.Many2one(comodel_name='vessel', string='Vessel', required=True)
    voyage_id = fields.Many2one(comodel_name='voyage', string='Voyage', required=False)
    control_no = fields.Char(string='Export Control No.', required=False)
    time = fields.Many2one(comodel_name='shift', string='Time', required=True, domain=lambda self: self._get_shift_domain())
    agent_id = fields.Many2one(comodel_name='container.truck.appointment.agent', string='Agent',
                               default=lambda self: self._get_default_agent_id(), required=True)
    export_line_ids = fields.One2many(comodel_name='container.truck.appointment.export.line', string='Export Line',
                                      inverse_name='export_id', required=True)
    export_declaration_no = fields.Char(string='Declaration No.', required=False)
    qr_code = fields.Binary("QR Code", compute='generate_qr_code')
    state = fields.Selection(string='State',
                             selection=[('draft', 'Draft'), ('request', 'Request'), ('approve', 'Approved'),
                                        ('cancel', 'Cancel')],
                             default='draft', required=False)
    commodity = fields.Char(string='Commodity', required=True)
    voyage_readonly = fields.Boolean(compute='_compute_voyage_readonly')
    can_print = fields.Boolean(compute='_compute_can_print', store=True)
    agent_email = fields.Char(string="Agent Email", compute='_compute_agent_email')

    @api.model
    def _get_shift_domain(self):
        now = datetime.now()
        current_date = now.date()
        current_time = now.hour + now.minute / 60.0

        domain = [
            ('start_date', '<=', current_date),
            ('end_date', '>=', current_date),
            '|',
            '&', ('start_time', '<=', current_time), ('end_time', '>=', current_time),
            '&', ('start_time', '>=', 0.0), ('end_time', '<=', 24.0)
        ]

        return domain

    @api.onchange('booking_no')
    def _onchange_booking_no(self):
        if self.booking_no:
            # Get related containers
            container_ids = self.env['container'].search([('booking_reference_id', '=', self.booking_no.id)])

            # Clear existing lines and set new lines
            self.export_line_ids = [(5, 0, 0)]
            lines = [(0, 0, {'container_id': container.id}) for container in container_ids]
            self.export_line_ids = lines

            # Set voyage and vessel
            if container_ids:
                # Assuming all containers have the same voyage
                first_container = container_ids[0]
                self.voyage_id = first_container.voyage_id

                # Set vessel based on voyage
                if self.voyage_id:
                    self.vessel_id = self.voyage_id.vessel_id

    @api.depends('agent_id')
    def _compute_agent_email(self):
        for record in self:
            record.agent_email = record.agent_id.email if record.agent_id else ''

    @api.depends('state')
    def _compute_can_print(self):
        for record in self:
            record.can_print = record.state == 'approve'

    @api.depends('export_line_ids.container_id')
    def _compute_voyage_readonly(self):
        for record in self:
            record.voyage_readonly = any(line.container_id for line in record.export_line_ids)

    def action_request(self):
        return self.write({'state': 'request'})

    def action_approve(self):
        self.write({'state': 'approve'})

        # Send approval email
        mail_template = self.env.ref('container_truck_appointment.email_template_export_approved')
        if mail_template:
            try:
                default_email_from = self.env['ir.config_parameter'].sudo().get_param('mail.default.from')
                mail_template.email_from = default_email_from or mail_template.email_from
                mail_template.send_mail(self.id, force_send=True)
                message = 'Approval email sent successfully.'
                message_type = 'info'
            except Exception as e:
                _logger.error('Failed to send approval email: %s', e)
                message = f'Failed to send approval email: {e}'
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

    def action_cancel(self):
        return self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        return self.write({'state': 'draft'})

    @api.onchange('vessel_id')
    def get_voyage(self):
        domain = []
        if self.vessel_id:
            domain = [('vessel_id', '=', self.vessel_id.id), ('voyage_type', '=', 'export')]
        return {'domain': {'voyage_id': domain}}

    @api.model
    def create(self, vals):
        if not vals.get('export_line_ids'):
            raise ValidationError(_("You must add at least one Export Line."))

        if vals.get('name', _('New')) == _('New'):
            seq = self.env['ir.sequence'].next_by_code('container.truck.export')
            vals['name'] = "EX/" + f'{seq:0>6}'

        return super(ContainerTruckAppointmentExport, self).create(vals)

    def write(self, vals):
        if 'export_line_ids' in vals and not vals['export_line_ids']:
            raise ValidationError(_("You must add at least one Export Line."))

        return super(ContainerTruckAppointmentExport, self).write(vals)

    def generate_qr_code(self):
        for rec in self:
            if qrcode and base64:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=3,
                    border=4,
                )
                form_url = rec._get_form_url()
                qr.add_data(form_url)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                rec.update({'qr_code': qr_image})

    def _get_form_url(self):
        action = self.env['ir.actions.act_window'].search([('name', '=', 'Container Truck Appointment (Export)')],
                                                          limit=1)
        menu_item = self.env['ir.ui.menu'].search([('name', '=', 'Container Truck')], limit=1)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        record_id = self.id
        form_url = f"{base_url}/web?debug=1#menu_id={menu_item.id}&cids=1&action={action.id}&model=container.truck.appointment.import&view_type=form&id={record_id}"
        return form_url

    def _get_default_agent_id(self):
        current_user = self.env.user
        agent = self.env['container.truck.appointment.agent'].search([('user_id', '=', current_user.id)], limit=1)
        return agent.id if agent else False


class ContainerTruckAppointmentExportLine(models.Model):
    _name = 'container.truck.appointment.export.line'
    _description = 'Container Truck Appointment Export Line'

    export_id = fields.Many2one(comodel_name='container.truck.appointment.export', string='Export Id', required=True)
    container_id = fields.Many2one(comodel_name='container', string='Container', required=True,
                                   domain="[('booking_reference_id', '=', parent.booking_no)]")
    state = fields.Selection(
        string='Status',
        selection=[('draft', 'Draft'), ('done', 'Done')],
        default="draft",
    )
    can_print = fields.Boolean(compute='_compute_can_print', store=True)

    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_done(self):
        return self.write({'state': 'done'})

    @api.depends('export_id.state')
    def _compute_can_print(self):
        for record in self:
            record.can_print = record.export_id.state == 'approve'

    def action_generate_report(self):
        return self.env.ref(
            'container_truck_appointment.action_container_truck_appointment_export_report').report_action(self)

    @api.model
    def create(self, vals):
        container_name = vals.get('container_name', 'New Container')
        export_id = vals.get('export_id')
        if export_id:
            export = self.env['container.truck.appointment.export'].browse(export_id)
            voyage_id = export.voyage_id.id if export.voyage_id else False

            if 'container_id' not in vals or not vals['container_id']:
                container_vals = {
                    'name': container_name,
                    'voyage_id': voyage_id,
                }
                container = self.env['container'].create(container_vals)
                vals['container_id'] = container.id
            else:
                container = self.env['container'].browse(vals['container_id'])
                if container and voyage_id and container.voyage_id.id != voyage_id:
                    container.write({'voyage_id': voyage_id})

        return super(ContainerTruckAppointmentExportLine, self).create(vals)


class vessel(models.Model):
    _name = 'vessel'
    _description = 'Vessel Information'

    name = fields.Char(string='Name', required=True)
    built = fields.Integer(string='Built', required=False)
    flag_id = fields.Many2one(comodel_name='res.country', string='Flag', required=False)
    gross_tonnage = fields.Integer(string='Gross Tonnage (GT)', required=False)
    deadweight_tonnage = fields.Integer(string='Deadweight Tonnage (DWT)', required=False)
    size = fields.Char(string='Size (m)', required=False)
    voyage_ids = fields.One2many(comodel_name='voyage', string='Voyage', required=False, inverse_name='vessel_id')
    external_id = fields.Integer(string='External ID')

    shipping_line_id = fields.Many2one(
        comodel_name='shipping.line',
        string='Shipping Line',
        required=False,
        ondelete='cascade'
    )

    @api.onchange('name')
    def get_voyage_ids(self):
        for rec in self:
            return {'domain': {'voyage_ids': [('vessel_id', '=', rec.vessel_id.id)]}}


class Voyage(models.Model):
    _name = 'voyage'
    _description = 'Voyage Information'

    name = fields.Char(string='Name', required=True)
    vessel_id = fields.Many2one(comodel_name='vessel', string='Vessel', required=True)
    container_ids = fields.One2many(comodel_name='container', inverse_name='voyage_id', string='Containers')
    voyage_type = fields.Selection([
        ('export', 'Export'),
        ('import', 'Import'),
    ], string='Voyage Type', required=True)
    external_id = fields.Integer(string='External ID')

    @api.model
    def create(self, vals):
        if 'name' not in vals or not vals['name']:
            vals['name'] = self.env['ir.sequence'].next_by_code('voyage') or _('New Voyage')

        return super(Voyage, self).create(vals)


class Container(models.Model):
    _name = 'container'
    _description = 'Container Information'

    name = fields.Char(string='Name', required=True)
    voyage_id = fields.Many2one(comodel_name='voyage', string='Voyage')
    booking_reference_id = fields.Many2one(comodel_name='booking.reference', string='Booking Reference')
    bill_of_landing_id = fields.Many2one(comodel_name='bill.of.landing', string='Bill of Landing')
    external_id = fields.Integer(string='External ID')

    @api.model
    def create(self, vals):
        if 'name' not in vals or not vals['name']:
            vals['name'] = self.env['ir.sequence'].next_by_code('container') or _('New Container')
        return super(Container, self).create(vals)

class Shift(models.Model):
    _name = 'shift'
    _description = 'Shift Configuration'
    _order = "sequence asc"

    name = fields.Char(string='Name')
    start_time = fields.Float(string='Start Time', help='Please use 24 hours Format')
    end_time = fields.Float(string='End Time', help='Please use 24 hours Format')
    containers = fields.Integer(string='Container (Approx)')
    sequence = fields.Integer(string="Sequence")
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')


class BookingReference(models.Model):
    _name = 'booking.reference'
    _description = 'Booking Reference'

    name = fields.Char(string='Name', required=True)
    container_ids = fields.One2many(comodel_name='container', inverse_name='booking_reference_id', string='Containers')


class Announcement(models.Model):
    _name = 'announcement'
    _description = 'Announcement'

    name = fields.Char(string='Title', required=True)
    message = fields.Char(string='Message', required=True)
    active = fields.Boolean(string='Active', default=True)
