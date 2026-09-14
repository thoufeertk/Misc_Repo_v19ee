/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formatCurrency } from "@web/core/currency";
import { Component } from "@odoo/owl";

export class PropertyBuildingOverview extends Component {
    static template = "msr_property_management.BuildingOverviewWidget";
    static props = { ...Component.props, record: { type: Object } };

    get data() {
        return this.props.record.data;
    }

    get currencyId() {
        const currency = this.data.currency_id;
        return Array.isArray(currency) ? currency[0] : currency?.id;
    }

    formatMoney(value) {
        return formatCurrency(value || 0, this.currencyId);
    }

    formatPercent(value) {
        return `${(Math.round((value || 0) * 1000) / 10).toLocaleString()}%`;
    }
}

registry.category("view_widgets").add("property_building_overview", {
    component: PropertyBuildingOverview,
});
