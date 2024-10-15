/** @odoo-module */

import { registry } from "@web/core/registry";
import { KpiCard } from "./kpi_card";
import { ChartRenderer } from "./chart_renderer";
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart, useState } = owl;

export class ContainerDashBoard extends Component {
    setup() {
        this.state = useState({
            export_morning_appointment: { value: 0, percentage: 0 },
            export_evening_appointment: { value: 0, percentage: 0 },
            export_total_appointment: { value: 0, percentage: 0 },
            import_morning_appointment: { value: 0, percentage: 0 },
            import_evening_appointment: { value: 0, percentage: 0 },
            import_total_appointment: { value: 0, percentage: 0 },
            period: "today",
            dateStart: '',
            dateEnd: '',
            chartData: [],
        });
        this.orm = useService("orm");

        onWillStart(async () => {
            this.getDates();
            await this.getExportAppointmentData();
            await this.getImportAppointmentData();
            await this.updateChartData();
        });
    }

    clearOldData() {
        this.state.export_total_appointment.value = 0;
        this.state.export_total_appointment.percentage = 0;
        this.state.export_morning_appointment.value = 0;
        this.state.export_morning_appointment.percentage = 0;
        this.state.export_evening_appointment.value = 0;
        this.state.export_evening_appointment.percentage = 0;
        this.state.import_total_appointment.value = 0;
        this.state.import_total_appointment.percentage = 0;
        this.state.import_morning_appointment.value = 0;
        this.state.import_morning_appointment.percentage = 0;
        this.state.import_evening_appointment.value = 0;
        this.state.import_evening_appointment.percentage = 0;
        this.state.chartData = [];
    }

    getDates() {
        if (this.state.period === 'today') {
            this.state.dateStart = moment().format('YYYY-MM-DD');
            this.state.dateEnd = this.state.dateStart;
        } else if (this.state.period === 'weekly') {
            const currentDay = moment().day();
            const startDay = currentDay < 3 ? 0 : currentDay - 3;
            const endDay = currentDay > 3 ? 6 : currentDay + 3;

            this.state.dateStart = moment().day(startDay).format('YYYY-MM-DD');
            this.state.dateEnd = moment().day(endDay).format('YYYY-MM-DD');
        } else if (this.state.period === 'monthly') {
            const currentMonth = moment().month();
            this.state.dateStart = moment().month(currentMonth).startOf('month').format('YYYY-MM-DD');
            this.state.dateEnd = moment().month(currentMonth).endOf('month').format('YYYY-MM-DD');
        }
    }

    getPreviousPeriodDates() {
    let prevDateStart, prevDateEnd;

    if (this.state.period === 'today') {
        prevDateStart = moment().subtract(1, 'days').startOf('day').format('YYYY-MM-DD');
        prevDateEnd = moment().subtract(1, 'days').endOf('day').format('YYYY-MM-DD');
    } else if (this.state.period === 'weekly') {
        prevDateStart = moment().subtract(1, 'weeks').startOf('week').format('YYYY-MM-DD');
        prevDateEnd = moment().subtract(1, 'weeks').endOf('week').format('YYYY-MM-DD');
    } else if (this.state.period === 'monthly') {
        prevDateStart = moment().subtract(1, 'months').startOf('month').format('YYYY-MM-DD');
        prevDateEnd = moment().subtract(1, 'months').endOf('month').format('YYYY-MM-DD');
    }

    return { prevDateStart, prevDateEnd };
}

  async getExportAppointmentData() {
    const { dateStart, dateEnd } = this.state;
    const { prevDateStart, prevDateEnd } = this.getPreviousPeriodDates();
    const approvedStateCondition = ['state', '=', 'approve'];
    const dateConditionStart = ['appointment_date', '>=', dateStart];
    const dateConditionEnd = ['appointment_date', '<=', dateEnd];
    const prevDateConditionStart = ['appointment_date', '>=', prevDateStart];
    const prevDateConditionEnd = ['appointment_date', '<=', prevDateEnd];
    const morningCondition = ['time', '=', 'Morning'];
    const eveningCondition = ['time', '=', 'Evening'];

    try {
        const exportTotalAppointment = await this.orm.searchCount(
            "container.truck.appointment.export",
            [approvedStateCondition, dateConditionStart, dateConditionEnd]
        );

        const prevExportTotalAppointment = await this.orm.searchCount(
            "container.truck.appointment.export",
            [approvedStateCondition, prevDateConditionStart, prevDateConditionEnd]
        );

        const morningAppointmentData = await this.orm.searchCount(
            "container.truck.appointment.export",
            [approvedStateCondition, dateConditionStart, dateConditionEnd, morningCondition]
        );

        const prevMorningAppointmentData = await this.orm.searchCount(
            "container.truck.appointment.export",
            [approvedStateCondition, prevDateConditionStart, prevDateConditionEnd, morningCondition]
        );

        const eveningAppointmentData = await this.orm.searchCount(
            "container.truck.appointment.export",
            [approvedStateCondition, dateConditionStart, dateConditionEnd, eveningCondition]
        );

        const prevEveningAppointmentData = await this.orm.searchCount(
            "container.truck.appointment.export",
            [approvedStateCondition, prevDateConditionStart, prevDateConditionEnd, eveningCondition]
        );

        console.log('Export Total Appointment:', exportTotalAppointment);
        console.log('Previous Export Total Appointment:', prevExportTotalAppointment);
        console.log('Morning Appointment Data:', morningAppointmentData);
        console.log('Previous Morning Appointment Data:', prevMorningAppointmentData);
        console.log('Evening Appointment Data:', eveningAppointmentData);
        console.log('Previous Evening Appointment Data:', prevEveningAppointmentData);

        this.state.export_total_appointment.value = exportTotalAppointment;
        this.state.export_total_appointment.percentage = this.calculatePercentageChange(exportTotalAppointment, prevExportTotalAppointment);
        this.state.export_morning_appointment.value = morningAppointmentData;
        this.state.export_morning_appointment.percentage = this.calculatePercentageChange(morningAppointmentData, prevMorningAppointmentData);
        this.state.export_evening_appointment.value = eveningAppointmentData;
        this.state.export_evening_appointment.percentage = this.calculatePercentageChange(eveningAppointmentData, prevEveningAppointmentData);
    } catch (error) {
        console.error('Error fetching export appointment data:', error);
    }
}

async getImportAppointmentData() {
    const { dateStart, dateEnd } = this.state;
    const { prevDateStart, prevDateEnd } = this.getPreviousPeriodDates();
    const approvedStateCondition = ['state', '=', 'approve'];
    const dateConditionStart = ['appointment_date', '>=', dateStart];
    const dateConditionEnd = ['appointment_date', '<=', dateEnd];
    const prevDateConditionStart = ['appointment_date', '>=', prevDateStart];
    const prevDateConditionEnd = ['appointment_date', '<=', prevDateEnd];
    const morningCondition = ['time', '=', 'Morning'];
    const eveningCondition = ['time', '=', 'Evening'];

    try {
        const importTotalAppointment = await this.orm.searchCount(
            "container.truck.appointment.import",
            [approvedStateCondition, dateConditionStart, dateConditionEnd]
        );

        const prevImportTotalAppointment = await this.orm.searchCount(
            "container.truck.appointment.import",
            [approvedStateCondition, prevDateConditionStart, prevDateConditionEnd]
        );

        const morningAppointmentData = await this.orm.searchCount(
            "container.truck.appointment.import",
            [approvedStateCondition, dateConditionStart, dateConditionEnd, morningCondition]
        );

        const prevMorningAppointmentData = await this.orm.searchCount(
            "container.truck.appointment.import",
            [approvedStateCondition, prevDateConditionStart, prevDateConditionEnd, morningCondition]
        );

        const eveningAppointmentData = await this.orm.searchCount(
            "container.truck.appointment.import",
            [approvedStateCondition, dateConditionStart, dateConditionEnd, eveningCondition]
        );

        const prevEveningAppointmentData = await this.orm.searchCount(
            "container.truck.appointment.import",
            [approvedStateCondition, prevDateConditionStart, prevDateConditionEnd, eveningCondition]
        );

        console.log('Import Total Appointment:', importTotalAppointment);
        console.log('Previous Import Total Appointment:', prevImportTotalAppointment);
        console.log('Morning Appointment Data:', morningAppointmentData);
        console.log('Previous Morning Appointment Data:', prevMorningAppointmentData);
        console.log('Evening Appointment Data:', eveningAppointmentData);
        console.log('Previous Evening Appointment Data:', prevEveningAppointmentData);

        this.state.import_total_appointment.value = importTotalAppointment;
        this.state.import_total_appointment.percentage = this.calculatePercentageChange(importTotalAppointment, prevImportTotalAppointment);
        this.state.import_morning_appointment.value = morningAppointmentData;
        this.state.import_morning_appointment.percentage = this.calculatePercentageChange(morningAppointmentData, prevMorningAppointmentData);
        this.state.import_evening_appointment.value = eveningAppointmentData;
        this.state.import_evening_appointment.percentage = this.calculatePercentageChange(eveningAppointmentData, prevEveningAppointmentData);
    } catch (error) {
        console.error('Error fetching import appointment data:', error);
    }
}

        calculatePercentageChange(current, previous) {
            if (previous === 0) return current > 0 ? 100 : 0;
            const percentageChange = ((current - previous) / previous) * 100;
            return parseFloat(percentageChange.toFixed(2));
            }

async updateChartData() {
    const { period } = this.state;
    let dateStart, dateEnd;

    if (period === 'today') {
        dateStart = moment().startOf('day').format('YYYY-MM-DD');
        dateEnd = moment().endOf('day').format('YYYY-MM-DD');
    } else if (period === 'weekly') {
        dateStart = moment().subtract(1, 'month').startOf('month').format('YYYY-MM-DD');
        dateEnd = moment().add(1, 'month').endOf('month').format('YYYY-MM-DD');
    } else if (period === 'monthly') {
        dateStart = moment().subtract(1, 'year').startOf('year').format('YYYY-MM-DD');
        dateEnd = moment().add(1, 'year').endOf('year').format('YYYY-MM-DD');
    }

    const dateRangeCondition = [
        ['appointment_date', '>=', dateStart],
        ['appointment_date', '<=', dateEnd],
        ['state', '=', 'approve']
    ];

    try {
        const exportAppointments = await this.orm.searchRead(
            "container.truck.appointment.export",
            dateRangeCondition,
            ['appointment_date', 'time']
        );

        const importAppointments = await this.orm.searchRead(
            "container.truck.appointment.import",
            dateRangeCondition,
            ['appointment_date', 'time']
        );

        const exportDataMap = new Map();
        const importDataMap = new Map();

        if (period === 'weekly') {
            for (let i = 1; i <= 4; i++) {
                exportDataMap.set(`Week ${i}`, 0);
                importDataMap.set(`Week ${i}`, 0);
            }
        } else if (period === 'monthly') {
            for (let i = 1; i <= 12; i++) {
                exportDataMap.set(moment().month(i - 1).format('MMMM'), 0);
                importDataMap.set(moment().month(i - 1).format('MMMM'), 0);
            }
        }

        for (const appointment of exportAppointments) {
            if (period === 'today') {
                const weekday = moment(appointment.appointment_date).format('dddd');
                exportDataMap.set(weekday, (exportDataMap.get(weekday) || 0) + 1);
            } else if (period === 'weekly') {
                const weekNumber = Math.ceil(moment(appointment.appointment_date).date() / 7);
                const weekLabel = `Week ${weekNumber}`;
                exportDataMap.set(weekLabel, (exportDataMap.get(weekLabel) || 0) + 1);
            } else if (period === 'monthly') {
                const monthLabel = moment(appointment.appointment_date).format('MMMM');
                exportDataMap.set(monthLabel, (exportDataMap.get(monthLabel) || 0) + 1);
            }
        }

        for (const appointment of importAppointments) {
            if (period === 'today') {
                const weekday = moment(appointment.appointment_date).format('dddd');
                importDataMap.set(weekday, (importDataMap.get(weekday) || 0) + 1);
            } else if (period === 'weekly') {
                const weekNumber = Math.ceil(moment(appointment.appointment_date).date() / 7);
                const weekLabel = `Week ${weekNumber}`;
                importDataMap.set(weekLabel, (importDataMap.get(weekLabel) || 0) + 1);
            } else if (period === 'monthly') {
                const monthLabel = moment(appointment.appointment_date).format('MMMM');
                importDataMap.set(monthLabel, (importDataMap.get(monthLabel) || 0) + 1);
            }
        }

        const exportChartData = Array.from(exportDataMap.entries()).map(([label, count]) => ({
            label: label,
            count: count,
        })).sort((a, b) => {
            if (period === 'weekly') {
                return parseInt(a.label.split(' ')[1]) - parseInt(b.label.split(' ')[1]);
            } else if (period === 'monthly') {
                return moment(a.label, 'MMMM').month() - moment(b.label, 'MMMM').month();
            }
            return 0;
        });

        const importChartData = Array.from(importDataMap.entries()).map(([label, count]) => ({
            label: label,
            count: count,
        })).sort((a, b) => {
            if (period === 'weekly') {
                return parseInt(a.label.split(' ')[1]) - parseInt(b.label.split(' ')[1]);
            } else if (period === 'monthly') {
                return moment(a.label, 'MMMM').month() - moment(b.label, 'MMMM').month();
            }
            return 0;
        });

        this.state.exportChartData = exportChartData;
        this.state.importChartData = importChartData;

        console.log('Export Chart Data:', exportChartData);
        console.log('Import Chart Data:', importChartData);
    } catch (error) {
        console.error('Error updating chart data:', error);
    }
}

    async onChangePeriod() {
        this.clearOldData();
        this.getDates();
        try {
            await Promise.all([
                this.getExportAppointmentData(),
                this.getImportAppointmentData(),
            ]);
            await this.updateChartData();
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    }

    onPeriodChange(event) {
        this.state.period = event.target.value;
        this.onChangePeriod();
    }
}

ContainerDashBoard.template = "owl.ContainerDashBoard";
ContainerDashBoard.components = { KpiCard, ChartRenderer };
registry.category("actions").add("owl.container_dashboard", ContainerDashBoard);
