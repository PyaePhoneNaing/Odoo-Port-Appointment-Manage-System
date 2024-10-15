odoo.define('container_truck_appointment.agent', function (require) {
    "use strict";

    var publicWidget = require('web.public.widget');
    var FileReader = window.FileReader;
    var rpc = require('web.rpc');
    var session = require('web.session');

    publicWidget.registry.AgentRegistration = publicWidget.Widget.extend({
        selector: '.oe_signup_form', // define which part of the DOM this widget will be applied to

        events: {
            'change.bs.select select[name="nrc_state_id"]': '_onChangeNRCState',
            'change.bs.select select[name="state_id"]': '_onChangeState',
            'change.bs.select select[name="township_id"]': '_onChangeTownship',
            'change.bs.select select[name="country_id"]': '_onChangeCountry',
            'change #attachments': '_onImageChange',
            'dragover #imageUploadArea': '_onDragOver',
            'dragleave #imageUploadArea': '_onDragLeave',
            'drop #imageUploadArea': '_onDrop',
            'click #imageUploadArea': '_onClick',
            'change #image': '_onFileInputChange',
        },

        init: function() {
            this._super.apply(this, arguments);

            $('.selectpicker').selectpicker('render');
            this._initSelectors(); // Geeky naming convention for clarity
        },

        _initSelectors: function() { // Renamed function for clarity
            this._onChangeNRCState();
            this._onChangeState();
            this._onChangeTownship();
            this._onChangeCountry();
        },

        _onImageChange: function (ev) {
            var file = ev.target.files[0];
            this._handleImageUpload(file);
        },

        _onChangeNRCState: function() {
            var nrc_state = $('#nrc_state_id').val();
            var nrc_district = $('select[name="nrc_district_id"]');
            if (!nrc_state) {
                this._resetSelector(nrc_district);
                return;
            }

            this._rpc({
                route: '/nrc_state_infos/' + nrc_state
            }).then((data) => { // Arrow function to maintain scope
                if (data.nrc_districts.length) {
                    this._populateSelector(nrc_district, data.nrc_districts);
                } else {
                    this._resetSelector(nrc_district);
                }   
            });
        },

        _onChangeTownship: function() {
            var township = $('#township_id').val();
            var ward = $('select[name="ward_id"]');
            if (!township) {
                this._resetSelector(ward);
                return;
            }

            this._rpc({
                route: '/ward_infos/' + township
            }).then((data) => { // Arrow function to maintain scope
                if (data.wards.length) {
                    this._populateSelector(ward, data.wards);
                } else {
                    this._resetSelector(ward);
                }
            });
        },

        _onChangeState: function() {
            var state = $('#state_id').val();
            var township = $('select[name="township_id"]');
            if (!state) {
                this._resetSelector(township);
                return;
            }

            this._rpc({
                route: '/township_infos/' + state
            }).then((data) => { // Arrow function to maintain scope
                if (data.townships.length) {
                    this._populateSelector(township, data.townships);
                } else {
                    this._resetSelector(township);
                }
            });
        },

        _onChangeCountry: function() {
            var country = $('#country_id').val();
            var state = $('select[name="state_id"]');
            if (!country) {
                this._resetSelector(state);
                return;
            }

            this._rpc({
                route: '/state_infos/' + country
            }).then((data) => { // Arrow function to maintain scope
                if (data.states.length) {
                    this._populateSelector(state, data.states);
                } else {
                    this._resetSelector(state);
                }
            });
        },

        _populateSelector: function(selector, data) { // Geeky function for populating selector
            selector.html('<option value=""></option>');
            _.each(data, function(x) {
                var opt = $('<option>').text(x[1])
                    .attr('value', x[0])
                    .attr('data-code', x[2]);
                selector.append(opt);
            });
            selector.prop('disabled', false);
            selector.selectpicker('destroy');
            selector.selectpicker('refresh');
        },

        _resetSelector: function(selector) { // Geeky function for resetting selector
            selector.val('');
            selector.html('<option value=""></option>');
            selector.prop('disabled', true);
            selector.selectpicker('refresh');
        },

        _onDragOver: function (ev) {
            ev.preventDefault();
            $('#imageUploadArea').addClass('border-primary');
        },

        _onDragLeave: function () {
            $('#imageUploadArea').removeClass('border-primary');
        },

        _onDrop: function (ev) {
            ev.preventDefault();
            $('#imageUploadArea').removeClass('border-primary');
            var file = ev.originalEvent.dataTransfer.files[0];
            this._handleImageUpload(file);
        },

        _onClick: function () {
            $('#attachments').click();
        },

        _handleImageUpload: function (file) {
            var self = this;
            if (file) {
                var reader = new FileReader();
                reader.onload = function () {
                    $('#displayedImage').attr('src', reader.result);
                    $('#displayedImage').removeClass('d-none');
                };
                reader.readAsDataURL(file);
            }
        },
        _onFileInputChange: function (ev) {
            var file = ev.target.files[0];
            if (file) {
                var reader = new FileReader();
                var self = this;
                reader.onload = function () {
                    self.$('#selectedAvatar').attr('src', reader.result);
                    self.$('#image_medium').val(reader.result.split(',')[1]);
                };

                reader.readAsDataURL(file);
            }
        },
    });

    publicWidget.registry.FormValidation = publicWidget.Widget.extend({
        selector: '.o_form_validation',

        events: {
            'submit .o_form_validation': '_setupFormValidation',
        },

         init: function() {
            this._super.apply(this, arguments);
            this._setupFormValidation();
        },

        _setupFormValidation: function () {
    document.querySelectorAll('.o_form_validation').forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }


            const validateField = (fieldId, pattern = null) => {
                const field = form.querySelector(fieldId);
                if (!pattern) {
                    if (!Number.isInteger(Number(field.value))) {
                        field.classList.add('is-invalid');
                    } else {
                        field.classList.remove('is-invalid');
                    }
                } else {
                    const fieldValue = field.value;
                    if (!pattern.test(fieldValue)) {
                        field.classList.add('is-invalid');
                    } else {
                        field.classList.remove('is-invalid');
                    }
                }
            };

            ['#code', '#nrc_number'].forEach(fieldId => validateField(fieldId));
            validateField('#email', /\S+@\S+\.\S+/);
            validateField('#phone', /^\d{8}$|^\d{10}$/);
            const passwordField = form.querySelector('#password').value;
            const confirmPasswordField = form.querySelector('#confirm_password').value;
            ['#password', '#confirm_password'].forEach(fieldId => validateField(fieldId));
            form.classList.add('was-validated');
        });
    });
},

    });


});
