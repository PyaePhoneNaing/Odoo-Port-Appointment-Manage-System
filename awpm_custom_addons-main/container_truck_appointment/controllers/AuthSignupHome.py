# -*- coding: utf-8 -*-
import base64
from odoo import _, http
from odoo.exceptions import UserError
from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from werkzeug.exceptions import NotFound
from odoo.http import request

class AuthSignupAgent(Home):

    def get_auth_signup_qcontext(self):
        qcontext = super(AuthSignupAgent, self).get_auth_signup_qcontext()
        qcontext.update(
            {k: v for (k, v) in http.request.params.items() if k in ['image_medium', 'code', 'name', 'nrc_state_id',
                                                                     'nrc_district_id', 'nrc_type_id', 'nrc_number',
                                                                     'gender', 'phone', 'street',
                                                                     'ward_id', 'township_id', 'state_id',
                                                                     'country_id', 'parent_id', 'attachments']})
        nrc_states = sorted(http.request.env['nrc.state'].sudo().search([]), key=lambda state: int(state.eng_name))
        nrc_types = http.request.env['nrc.type'].sudo().search([])
        countries = http.request.env['res.country'].sudo().search([])
        parent_companies = http.request.env['res.partner'].sudo().search([('is_company', '=', True)])

        qcontext["nrc_states"] = nrc_states
        qcontext["nrc_types"] = nrc_types
        qcontext['countries'] = countries
        qcontext['parent_companies'] = parent_companies

        return qcontext

    def _signup_with_values(self, token, values):
        login, password = request.env['res.users'].sudo().signup(values, token)
        groups_user = request.env.ref('base.group_user')
        groups_portal = request.env.ref('base.group_portal')
        awpm_user = request.env.ref('container_truck_appointment.group_awpm_user')
        request.env.cr.commit()

        userObj = http.request.env['res.users'].sudo()
        context = self.get_auth_signup_qcontext()

        agentObj = http.request.env['container.truck.appointment.agent'].sudo()

        agent_fields = ['image_medium', 'code', 'name', 'nrc_state_id', 'nrc_district_id', 'nrc_type_id', 'nrc_number',
                        'gender', 'phone', 'street', 'ward_id', 'township_id', 'state_id', 'country_id', 'parent_id',
                        'password']

        user = userObj.search([('login', '=', values['login'])])

        if user:
            agent_data = {'user_id': user.id, 'email': context['login']}
            for field in agent_fields:
                if field in context:
                    agent_data.update({field: context[field]})

            # Check if agent exists with the same name and code
            agent = agentObj.search([('name', '=', context['name']), ('code', '=', context['code'])])

            if agent:
                # Update agent data and set state to approved
                agent_data.update({'state': 'approved'})
                agent.write(agent_data)
            else:
                # Create new agent
                agent = agentObj.create(agent_data)

            if 'attachments' in context:
                file_name = context.get('attachments').filename
                file = context.get('attachments')
                attachment_id = http.request.env['ir.attachment'].sudo().create({
                    'name': file_name,
                    'type': 'binary',
                    'datas': base64.b64encode(file.read()),
                    'res_model': agent._name,
                    'res_id': agent.id
                })
                agent.update({
                    'attachments': [(4, attachment_id.id)],
                })

            user_data = {'state': 'new', 'commercial_partner_id': agent.partner_id.id,
                         'partner_id': agent.partner_id.id}

            if context['image_medium']:
                user_data.update({'image_medium': context['image_medium']})

            # Get auto-created res_partner
            old_partner_id = user.partner_id

            # Update user with new data
            user.write(user_data)
            user.write({'groups_id': [(3, groups_portal.id)]})
            user.update({'groups_id': [(4, groups_user.id), (4, awpm_user.id)]})

            # Delete old res_partner which created along with user
            old_partner_id.sudo().unlink()

            # Find and delete the old user account
            old_user = userObj.search([('login', '!=', values['login']), ('partner_id', '=', agent.partner_id.id)])
            if old_user:
                old_user.unlink()

    @http.route('/web/signup', type='http', auth='public', website=True, methods=['GET', 'POST'], csrf=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise NotFound()

        try:
            self.do_signup(qcontext)
            return http.request.redirect('/web/login')
        except UserError as e:
            qcontext['error'] = e.args[0]

        return http.request.render('auth_signup.signup', qcontext)

    def do_signup(self, qcontext):
        """ Shared helper that creates a res.partner out of a token """
        values = {key: qcontext.get(key) for key in ('login', 'name', 'password')}
        assert values, "The form was not properly filled in."
        if not values.get('login'):
            raise UserError(_('Please provide an email address.'))

        if values.get('password') != qcontext.get('confirm_password'):
            raise UserError(_('Passwords do not match; please retype them.'))

        # prevent passing through the optional 'token' field, could be used to forge account
        token = qcontext.get('token')
        if token:
            values.pop('token')

        self._signup_with_values(token, values)
        http.request.env.cr.commit()
