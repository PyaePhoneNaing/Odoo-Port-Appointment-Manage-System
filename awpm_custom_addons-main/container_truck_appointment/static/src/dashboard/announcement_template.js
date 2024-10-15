/** @odoo-module **/
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { markup } from "@odoo/owl";  // Import the markup function

const { onMounted } = owl;

patch(HomeMenu.prototype, "container_truck_appointment.HomeMenu", {
    setup() {
        this._super();
        this.orm = useService("orm");
        this.state = useState({
            announcements: []
        });

        onMounted(() => {
            this.loadAnnouncements();
        });
    },

    async loadAnnouncements() {
        try {
            const result = await this.orm.searchRead(
                "announcement",
                [['active', '=', true]],
                ['name', 'message'],
                { order: 'id DESC' }
            );

            const announcements = result.map(announcement => {
                return {
                    ...announcement,
                    message: markup(announcement.message)
                };
            });

            this.state.announcements = announcements;
        } catch (error) {
            console.error("Failed to load announcements", error);
        }
    },
});
