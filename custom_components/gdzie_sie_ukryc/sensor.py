"""Small sensor states for automations; route geometries stay out of Recorder."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities(
        ShelterSensor(coordinator, zone_id, kind)
        for zone_id in coordinator.options["zones"]
        for kind in ("routes", "points", "distance", "duration")
    )


class ShelterSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, zone_id, kind):
        super().__init__(coordinator)
        self.zone_id = zone_id
        self.kind = kind
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{zone_id}_{kind}"
        labels = {
            "routes": "Trasy",
            "points": "Punkty w promieniu",
            "distance": "Najbliższa trasa",
            "duration": "Czas dojścia",
        }
        self._attr_name = labels[kind]
        self._attr_icon = (
            "mdi:map-marker-path"
            if kind in {"routes", "distance"}
            else "mdi:shield-home"
            if kind == "points"
            else "mdi:walk"
        )
        if kind == "distance":
            self._attr_native_unit_of_measurement = "m"
        elif kind == "duration":
            self._attr_native_unit_of_measurement = "min"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.entry.entry_id}_{zone_id}")},
            name=f"{NAME} · {self._zone_name()}",
            manufacturer="Integracja społecznościowa",
            model="Punkty schronienia",
        )

    def _zone_name(self):
        state = self.coordinator.hass.states.get(self.zone_id)
        return state.attributes.get("friendly_name", self.zone_id) if state else self.zone_id

    @property
    def location(self):
        return (self.coordinator.data or {}).get("locations", {}).get(self.zone_id)

    @property
    def available(self):
        return super().available and self.location is not None

    @property
    def native_value(self):
        location = self.location or {}
        routes = location.get("routes", [])
        if self.kind == "routes":
            return len(routes)
        if self.kind == "points":
            if location.get("source_status") == "error":
                return None
            return location.get("found_count", 0)
        if not routes:
            return None
        return routes[0]["distance_m"] if self.kind == "distance" else round(routes[0]["duration_s"] / 60, 1)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        location = self.location or {}
        nearest = next(iter(location.get("routes", [])), {})
        return {
            "integration": DOMAIN,
            "entry_id": self.coordinator.entry.entry_id,
            "zone_id": self.zone_id,
            "source_status": location.get("source_status", data.get("source_status")),
            "source_error": location.get("source_error", data.get("source_error")),
            "points_updated_at": location.get("points_updated_at", data.get("points_updated_at")),
            "result_limit_reached": location.get("result_limit_reached", False),
            "routes_updated_at": location.get("routes_updated_at"),
            "routing_error": location.get("routing_error"),
            "route_status": nearest.get("status"),
            "nearest_address": nearest.get("shelter", {}).get("address"),
            "nearest_name": nearest.get("shelter", {}).get("name"),
            "candidate_count": location.get("candidate_count", 0),
            "map_points": len(location.get("nearby", [])),
            "map_points_limit": location.get("nearby_limit"),
            "dataset_points": data.get("point_count", 0),
            "dataset_source": data.get("dataset", {}).get("source_url"),
            "dataset_origin": data.get("dataset", {}).get("origin"),
            "dataset_checked_at": data.get("dataset", {}).get("checked_at"),
        }
