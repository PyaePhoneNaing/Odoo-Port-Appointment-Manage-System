# Import necessary modules from Odoo
import base64
from io import BytesIO
from odoo.exceptions import ValidationError
from datetime import datetime
import qrcode
import logging
_logger = logging.getLogger(__name__)
from odoo import fields, models, api, _
from odoo.exceptions import UserError


# Define the ContainerTruckAppointmentImport class, representing the container truck appointment import model
class ContainerTruckAppointmentImport(models.Model):
    _name = 'container.truck.appointment.import'
    _description = 'Container Truck Appointment Import'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Appointment No', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    appointment_date = fields.Date(string='Appointment Date', required=True, tracking=True)
    shipper_id = fields.Many2one(comodel_name='res.partner', string='Consignee', required=True, tracking=True,
                                 domain="[('is_company', '=', True)]")  # Filter to show only companies
    vessel_id = fields.Many2one(comodel_name='vessel', string='Vessel', required=True)
    voyage_id = fields.Many2one(comodel_name='voyage', string='Voyage', required=False)
    time = fields.Many2one(comodel_name='shift', string='Time', required=True,
                           domain=lambda self: self._get_shift_domain())
    agent_id = fields.Many2one(comodel_name='container.truck.appointment.agent', string='Agent',
                               default=lambda self: self._get_default_agent_id(), required=True)
    import_line_ids = fields.One2many(comodel_name='container.truck.appointment.import.line', string='Import Line',
                                      inverse_name='import_id', required=False)
    qr_code = fields.Binary("QR Code", compute='generate_qr_code')
    bill_of_landing = fields.Many2one(comodel_name='bill.of.landing', string='Bill of Landing (BL)', required=True)
    import_declaration = fields.Char(string='Import Declaration (ID)', required=False)
    delivery_order = fields.Char(string='Delivery Order (DO)', required=False)
    release_order_number = fields.Char(string='Release Order Number', required=False)
    receipt_order = fields.Char(string='Receipt Order', required=False)
    physical_sheet = fields.Char(string='Physical Sheet', required=False)
    gate_information = fields.Selection(string='Gate Information',
                                        selection=[('gate_one', 'Gate 1'), ('gate_two', 'Gate 2'),
                                                   ('gate_three', 'Gate 3')])
    state = fields.Selection(string='State',
                             selection=[('draft', 'Draft'), ('request', 'Request'), ('approve', 'Approved'),
                                        ('cancel', 'Cancel')],
                             default='draft', required=False)
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

    @api.onchange('bill_of_landing')
    def _onchange_bill_of_landing(self):
        if self.bill_of_landing:
            # Get related containers
            container_ids = self.env['container'].search([('bill_of_landing_id', '=', self.bill_of_landing.id)])

            # Clear existing lines and set new lines
            self.import_line_ids = [(5, 0, 0)]
            lines = [(0, 0, {'container_id': container.id}) for container in container_ids]
            self.import_line_ids = lines

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

    def action_request(self):
        return self.write({'state': 'request'})

    def action_approve(self):
        self.write({'state': 'approve'})

        mail_template = self.env.ref('container_truck_appointment.email_template_import_approved')
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
        action = self.env['ir.actions.act_window'].search([('name', '=', 'Container Truck Appointment (Import)')],
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

    @api.onchange('vessel_id')
    def get_voyage(self):
        domain = []
        if self.vessel_id:
            domain = [('vessel_id', '=', self.vessel_id.id), ('voyage_type', '=', 'import')]
        return {'domain': {'voyage_id': domain}}

    @api.model
    def create(self, vals):
        if not vals.get('import_line_ids'):
            raise ValidationError(_("You must add at least one Import Line."))

        if vals.get('name', _('New')) == _('New'):
            seq = self.env['ir.sequence'].next_by_code('container.truck.import')
            vals['name'] = "IM/" + f'{seq:0>6}'

        return super(ContainerTruckAppointmentImport, self).create(vals)

    def write(self, vals):
        if 'export_line_ids' in vals and not vals['export_line_ids']:
            raise ValidationError(_("You must add at least one Export Line."))

        return super(ContainerTruckAppointmentImport, self).write(vals)


class ContainerTruckAppointmentImportLine(models.Model):
    _name = 'container.truck.appointment.import.line'
    _description = 'Container Truck Appointment Import Line'

    import_id = fields.Many2one(comodel_name='container.truck.appointment.import', string='Import Id', required=True)
    container_id = fields.Many2one(comodel_name='container', string='Container', required=True,
                                   domain="[('bill_of_landing_id', '=', parent.bill_of_landing)]")
    state = fields.Selection(
        string='Status',
        selection=[('draft', 'Draft'),
                   ('done', 'Done')],
        default='draft',
        required=False
    )
    can_print = fields.Boolean(compute='_compute_can_print', store=True)

    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_done(self):
        return self.write({'state': 'done'})

    @api.depends('import_id.state')
    def _compute_can_print(self):
        for record in self:
            record.can_print = record.import_id.state == 'approve'

    def action_generate_report(self):
        return self.env.ref(
            'container_truck_appointment.action_container_truck_appointment_import_report').report_action(self)

    @api.model
    def create(self, vals):
        # Ensure container_name is explicitly passed
        container_name = vals.get('container_name', 'New Container')

        # Get import and voyage details
        import_id = vals.get('import_id')
        if import_id:
            import_ = self.env['container.truck.appointment.import'].browse(import_id)
            voyage_id = import_.voyage_id.id if import_.voyage_id else False

            # Create the container with correct name and voyage_id if not already linked
            if 'container_id' not in vals or not vals['container_id']:
                container_vals = {
                    'name': container_name,
                    'voyage_id': voyage_id,
                }
                container = self.env['container'].create(container_vals)
                vals['container_id'] = container.id
            else:
                # Ensure the container's voyage_id is updated if it already exists
                container = self.env['container'].browse(vals['container_id'])
                if container and voyage_id and container.voyage_id.id != voyage_id:
                    container.write({'voyage_id': voyage_id})

        return super(ContainerTruckAppointmentImportLine, self).create(vals)


class BillOfLanding(models.Model):
    _name = 'bill.of.landing'
    _description = 'Bill of Landing'

    name = fields.Char(string='Name', required=True)
    container_ids = fields.One2many(comodel_name='container', inverse_name='bill_of_landing_id',
                                    string='Containers')
