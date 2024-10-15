from odoo import http
from odoo.http import request
from werkzeug.utils import redirect

class MyController(http.Controller):

    @http.route('/my/signup/route', type='http', auth='public', website=True, methods=['GET', 'POST'])
    def signup_form(self, **kwargs):
        if request.httprequest.method == 'POST':
            # Process form submission logic here
            return redirect('/some/other/route')
        else:
            # Handle GET request to render the signup form
            return http.request.render('container_truck_appointment.agent_signup', {})
