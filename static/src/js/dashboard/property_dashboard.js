/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { Component, onWillStart, onWillUnmount, useRef, useState, useEffect } from "@odoo/owl";

// Validated categorical palette (fixed order - see dataviz skill palette.md)
const SERIES = { blue: "#2a78d6", orange: "#eb6834" };
const STATUS = { good: "#0ca30c", warning: "#fab219", serious: "#ec835a" };

export class PropertyDashboard extends Component {
    static template = "msr_property_management.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            data: null,
            loading: true,
        });
        this.occupancyChartRef = useRef("occupancyChart");
        this.revenueChartRef = useRef("revenueChart");
        this.charts = {};

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.loadData();
        });

        useEffect(
            () => {
                this._renderCharts();
            },
            () => [this.state.loading, this.state.data]
        );

        onWillUnmount(() => {
            Object.values(this.charts).forEach((chart) => chart && chart.destroy());
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call("property.building", "get_dashboard_data", []);
        this.state.loading = false;
    }

    _renderCharts() {
        const data = this.state.data;
        if (!data || typeof Chart === "undefined") {
            return;
        }

        if (this.charts.occupancy) {
            this.charts.occupancy.destroy();
        }
        if (this.occupancyChartRef.el) {
            const rest = Math.max(
                data.total_rooms - data.occupied_rooms - data.vacant_rooms - data.maintenance_rooms,
                0
            );
            const labels = ["Occupied", "Vacant", "Maintenance"];
            const values = [data.occupied_rooms, data.vacant_rooms, data.maintenance_rooms];
            const colors = [STATUS.good, STATUS.warning, STATUS.serious];
            if (rest) {
                labels.push("Other");
                values.push(rest);
                colors.push("#c3c2b7");
            }
            this.charts.occupancy = new Chart(this.occupancyChartRef.el, {
                type: "doughnut",
                data: {
                    labels,
                    datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: "#fcfcfb" }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "68%",
                    plugins: { legend: { position: "bottom", labels: { boxWidth: 10, padding: 14 } } },
                },
            });
        }

        if (this.charts.revenue) {
            this.charts.revenue.destroy();
        }
        if (this.revenueChartRef.el) {
            const buildings = data.buildings.slice(0, 8);
            this.charts.revenue = new Chart(this.revenueChartRef.el, {
                type: "bar",
                data: {
                    labels: buildings.map((b) => b.name),
                    datasets: [
                        {
                            label: "Expected Monthly Revenue",
                            data: buildings.map((b) => b.monthly_expected_revenue),
                            backgroundColor: SERIES.blue,
                            borderRadius: 4,
                            maxBarThickness: 28,
                        },
                        {
                            label: "Total Invoiced (Posted)",
                            data: buildings.map((b) => b.total_invoiced_amount),
                            backgroundColor: SERIES.orange,
                            borderRadius: 4,
                            maxBarThickness: 28,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { display: false } },
                        y: { beginAtZero: true, grid: { color: "rgba(137,135,129,0.2)" } },
                    },
                    plugins: { legend: { position: "bottom", labels: { boxWidth: 10, padding: 14 } } },
                },
            });
        }
    }

    formatMoney(value) {
        const data = this.state.data;
        const amount = (Math.round((value || 0) * 100) / 100).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        if (!data) {
            return amount;
        }
        return data.currency_position === "before"
            ? `${data.currency_symbol} ${amount}`
            : `${amount} ${data.currency_symbol}`;
    }

    formatPercent(value) {
        return `${(Math.round((value || 0) * 10) / 10).toLocaleString()}%`;
    }

    async openBuildings() {
        await this.actionService.doAction("msr_property_management.action_property_building");
    }

    async openRooms(domain) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Rooms",
            res_model: "property.room",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
        });
    }

    async openTenancies() {
        await this.actionService.doAction("msr_property_management.action_property_tenancy");
    }

    async openDocuments() {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Expiring Documents",
            res_model: "property.document",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["expiring", "expired"]]],
        });
    }

    get maxRevenue() {
        if (!this.state.data || !this.state.data.buildings.length) {
            return 0;
        }
        return Math.max(...this.state.data.buildings.map((b) => b.total_invoiced_amount), 1);
    }

    revenueBarWidth(building) {
        const max = this.maxRevenue;
        return max ? Math.round((building.total_invoiced_amount / max) * 100) : 0;
    }

    async openBuilding(buildingId) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "property.building",
            res_id: buildingId,
            views: [[false, "form"]],
            view_mode: "form",
        });
    }
}

registry.category("actions").add("msr_property_management_dashboard", PropertyDashboard);
