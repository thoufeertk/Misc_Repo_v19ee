/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS, loadCSS } from "@web/core/assets";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

export class PropertyMap extends Component {
    static template = "msr_property_management.PropertyMap";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.mapRef = useRef("map");
        this.state = useState({
            loading: true,
            buildings: [],
        });
        this.leafletMap = null;

        onWillStart(async () => {
            await Promise.all([
                loadJS("/msr_property_management/static/lib/leaflet/leaflet.js"),
                loadCSS("/msr_property_management/static/lib/leaflet/leaflet.css"),
            ]);
            await this.loadData();
        });

        onMounted(() => this._renderMap());
        onWillUnmount(() => {
            if (this.leafletMap) {
                this.leafletMap.remove();
            }
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.buildings = await this.orm.call("property.building", "get_map_data", []);
        this.state.loading = false;
    }

    _renderMap() {
        if (!this.mapRef.el || typeof L === "undefined") {
            return;
        }
        const buildings = this.state.buildings;
        const center = buildings.length ? [buildings[0].latitude, buildings[0].longitude] : [20.5937, 78.9629];
        this.leafletMap = L.map(this.mapRef.el).setView(center, buildings.length ? 12 : 5);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap contributors",
            maxZoom: 19,
        }).addTo(this.leafletMap);

        const markers = [];
        for (const building of buildings) {
            const marker = L.marker([building.latitude, building.longitude]).addTo(this.leafletMap);
            marker.bindPopup(this._buildPopup(building));
            markers.push(marker);
        }
        if (markers.length > 1) {
            const group = L.featureGroup(markers);
            this.leafletMap.fitBounds(group.getBounds().pad(0.2));
        }
    }

    _buildPopup(building) {
        const popup = document.createElement("div");
        popup.className = "o_property_map_popup";

        const title = document.createElement("div");
        title.className = "o_property_map_popup_title";
        title.textContent = building.name;
        popup.appendChild(title);

        if (building.address) {
            const address = document.createElement("div");
            address.className = "o_property_map_popup_address";
            address.textContent = building.address;
            popup.appendChild(address);
        }

        const stats = document.createElement("div");
        stats.className = "o_property_map_popup_stats";
        stats.textContent = `${building.room_count} rooms · ${Math.round(building.occupancy_rate)}% occupied`;
        popup.appendChild(stats);

        const button = document.createElement("button");
        button.className = "btn btn-sm btn-primary mt-1";
        button.textContent = "Open Building";
        button.addEventListener("click", () => this.openBuilding(building.id));
        popup.appendChild(button);

        return popup;
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

registry.category("actions").add("msr_property_management_map", PropertyMap);
