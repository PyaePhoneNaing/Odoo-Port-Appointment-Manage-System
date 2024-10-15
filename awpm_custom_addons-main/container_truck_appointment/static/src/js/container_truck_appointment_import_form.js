odoo.define('container_truck_appointment.container_truck_appointment_import_form1', function (require) {
    "use strict";

    var core = require('web.core');
    var FormController = require('web.FormController');

    FormController.include({
        events: _.extend({}, FormController.prototype.events, {
            'view_content_has_displayed': '_onViewContentHasDisplayed',
        }),

        _onViewContentHasDisplayed: function () {
            var currentUrl = window.location.href;
            this.updateRecord({ current_url: currentUrl });
        },
    });
});