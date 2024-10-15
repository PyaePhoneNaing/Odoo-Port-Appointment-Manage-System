from odoo.tools.misc import file_open, str2bool
from lxml import html

from odoo.addons.base.models.ir_qweb import render as qweb_render
from odoo import http
from odoo.http import request
from odoo.tools import config
from odoo.addons.web.controllers import utils


class ContainerTruckAppointmentExport(http.Controller):

    @http.route('/web/container_truck_appointment_export', type='http', auth='public', csrf=False, website=True)
    def container_booking_export(self):
        values = {}
        return http.request.render("container_truck_appointment.container_truck_appointment_export", values)

    # TODO: Update information when there is already in agent data
    # Check by agent name and code for existing
    # If not create agent data
    @http.route(['/web/agent_registration/save'], type='http', auth="none", methods=['POST'], csrf=False, website=True)
    def agent_save_data(self, **kwargs):
        # main_database = config.get('main_database')
        # request.db = http.request.session.db = main_database
        # User = http.request.env['res.users']
        # user_sudo = User.sudo().search(
        #     User._get_login_domain('cto@mingalarsky.com'), order=User._get_login_order(), limit=1
        # )
        # Agent = http.request.env['container.truck.appointment.agent']
        # agent_sudo = Agent.sudo().search([])
        # Agent.sudo().create(kwargs)
        # agent = http.request.env['container.truck.appointment.agent'].search([])
        # print(agent_sudo)
        data = kwargs

        int_keys = ['ward_id', 'township_id', 'state_id', 'nrc_state_id', 'nrc_district_id', 'nrc_type_id', 'country_id', 'company_id']

        exclude_keys = ['name', 'code', 'confirm_password', 'image']
        create_exclude_keys = ['confirm_password', 'image']

        agentObj = request.env['container.truck.appointment.agent'].sudo()
        agent = agentObj.search(['&', ('code', '=', data.get('code').strip()), ('name', '=', data.get('name').strip())])
        write_keys = {key for key in kwargs.keys() if key not in exclude_keys}
        write_data = {key: int(kwargs.get(key)) if key in int_keys else kwargs.get(key) for key in write_keys}
        create_keys = {key for key in kwargs.keys() if key not in create_exclude_keys}
        create_data = {key: kwargs.get(key) for key in create_keys}

        if agent:
            agent.write(write_data)
            agent.action_approve()
        else:
            agentObj.create(create_data)


    @http.route('/web/agent_registration', type='http', auth='public', csrf=False, website=True)
    def agent_register(self, **kw):
        # db = con  fig.get('main_database')
        # request.session.db = db
        # utils.ensure_db()
        # convert eng_name as integer and sort to avoid 12,1,2
        nrc_states = sorted(request.env['nrc.state'].sudo().search([]), key=lambda state: int(state.eng_name))
        nrc_types = request.env['nrc.type'].sudo().search([])
        countries = request.env['res.country'].sudo().search([])
        parent_companies = request.env['res.partner'].sudo().search([('is_company', '=', 1)])
        values = {
            'nrc_states': nrc_states,
            'nrc_types': nrc_types,
            'countries': countries,
            'parent_companies': parent_companies
        }

        return http.request.render("container_truck_appointment.agent_registration", values)

    @http.route(['/nrc_state_infos/<model("nrc.state"):state>'], type='json', auth="public", methods=['post'],
                website=True)
    def division_infos(self, state, **kwargs):
        nrc_districts = request.env['nrc.district'].sudo().search([('nrc_state', '=', state.id)], order="name asc")
        return dict(
            nrc_districts=[(dst.id, dst.name) for dst in nrc_districts]
        )

    @http.route(['/state_infos/<model("res.country"):country>'], type='json', auth="public", methods=['post'],
                website=True)
    def state_infos(self, country, **kwargs):
        states = http.request.env['res.country.state'].sudo().search([('country_id', '=', country.id)], order="name asc")
        return dict(
            states=[(state.id, state.name) for state in states]
        )

    @http.route(['/township_infos/<model("res.country.state"):state>'], type='json', auth="public", methods=['post'],
                website=True)
    def township_infos(self, state, **kwargs):
        townships = http.request.env['res.country.township'].sudo().search([('state_id', '=', state.id)], order="name asc")
        return dict(
            townships=[(tsp.id, tsp.name) for tsp in townships]
        )

    @http.route(['/ward_infos/<model("res.country.township"):township>'], type='json', auth="public", methods=['post'],
                website=True)
    def ward_infos(self, township, **kwargs):
        wards = http.request.env['res.country.ward'].sudo().search([('township_id', '=', township.id)], order="name asc")
        return dict(
            wards=[(wrd.id, wrd.name) for wrd in wards]
        )
