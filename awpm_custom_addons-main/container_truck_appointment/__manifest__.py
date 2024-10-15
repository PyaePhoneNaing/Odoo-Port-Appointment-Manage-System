{
    'name': 'Container Truck Appointment System',
    'version': '16.0.0.0',
    'category': 'Website',
    'license': 'AGPL-3',
    'description': """
    Container Truck Appointment System
    ========================================
    Experience a new era of efficiency in port logistics with advanced Container Truck Appointment System. 
    Seamlessly integrated into the Odoo platform, this innovative solution empowers port authorities and shipping companies alike to optimize their container truck appointment processes with ease.
    Gone are the days of manual paperwork and cumbersome procedures. 
    With Container Truck Appointment System, every aspect of container management is digitized and streamlined for maximum productivity. 
    From booking requests to vessel loading, track every container's journey effortlessly within a unified interface.
    """,
    'author': 'Mingalar Sky Co., Ltd.',
    'website': 'https://www.mingalarsky.com',
    'depends': ['base', 'web', 'mail', 'board', 'web_enterprise'],
    'data': [
        'security/awpm_security_groups.xml',
        'security/awpm_security_rules.xml',
        'security/ir.model.access.csv',
        'security/code_sequence.xml',
        'views/export.xml',
        'views/import.xml',
        'views/agent.xml',
        'views/shipping_line.xml',
        'views/country.xml',
        'views/nrc.xml',
        'views/layout.xml',
        'views/agent_login_signup.xml',
        'views/dashboard.xml',
        'views/menus.xml',
        'report/import_report.xml',
        'report/export_report.xml',
        'report/custom_template.xml',
        'data/email_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'container_truck_appointment/static/src/dashboard/*.js',
            'container_truck_appointment/static/src/dashboard/*.xml',
            'container_truck_appointment/static/src/css/main.css',
            'container_truck_appointment/static/src/js/container_truck_appointment_import_form.js',
        ],
        'web.assets_frontend': [
            'container_truck_appointment/static/src/css/bootstrap-select.min.css',
            'container_truck_appointment/static/src/css/frontend_main.css',
            'container_truck_appointment/static/src/js/bootstrap-select.min.js',
            'container_truck_appointment/static/src/js/main.js',
            'container_truck_appointment/static/src/css/announcement.css',
        ],
    },
    'installable': True,
    'active': False,
    'application': True
}
