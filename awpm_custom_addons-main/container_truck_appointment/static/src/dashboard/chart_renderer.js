/** @odoo-module */

import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
const { Component, onWillStart, onWillUpdateProps, useRef, onMounted } = owl;

export class ChartRenderer extends Component {
    setup() {
        this.ChartRef = useRef("chart");
        this.chartInstance = null;

        onWillStart(async () => {
            await loadJS("container_truck_appointment/static/src/dashboard/chart.umd.min.js");
        });

        onMounted(() => {
            this.renderChart();
        });

        onWillUpdateProps(nextProps => {
            if (nextProps.data !== this.props.data) {
                this.updateChart(nextProps.data);
            }
        });
    }

    renderChart() {
        if (!this.props.data) return;

        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        const labels = this.props.data.map(row => row.label);
        const data = this.props.data.map(row => row.count);

        this.chartInstance = new Chart(this.ChartRef.el, {
            type: this.props.type,
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Appointments',
                        data: data,
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                plugins: {
                    title: {
                        display: true,
                        text: this.props.title,
                        position: 'bottom'
                    },
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    updateChart(newData) {
        if (!newData) return;

        if (this.chartInstance) {
            this.chartInstance.data.labels = newData.map(row => row.label);
            this.chartInstance.data.datasets[0].data = newData.map(row => row.count);
            this.chartInstance.update();
        } else {
            this.renderChart();
        }
    }
}

ChartRenderer.template = "owl.ChartRenderer";
registry.category("actions").add("owl.chart_renderer", ChartRenderer);
