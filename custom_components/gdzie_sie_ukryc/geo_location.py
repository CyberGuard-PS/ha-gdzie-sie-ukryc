"""Nearby shelter points on Home Assistant's built-in map, without routing."""

import asyncio

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.const import UnitOfLength
from homeassistant.core import callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_platform import async_get_current_platform

from .const import DOMAIN
from .models import distance_m

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    manager = ShelterMapManager(hass, entry, async_get_current_platform())
    entry.async_on_unload(entry.runtime_data.async_add_listener(manager.schedule_sync))
    entry.async_on_unload(manager.stop)
    await manager.async_sync()


class ShelterMapManager:
    """Add, update and remove map entities as points enter or leave the area."""

    def __init__(self, hass, entry, platform):
        self.hass = hass
        self.entry = entry
        self.coordinator = entry.runtime_data
        self.platform = platform
        self.entities = {}
        self.lock = asyncio.Lock()
        self.tasks = set()
        self.stopped = False

    @callback
    def schedule_sync(self):
        if not self.stopped:
            task = self.hass.async_create_task(self.async_sync())
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)

    @callback
    def stop(self):
        self.stopped = True
        for task in self.tasks:
            task.cancel()

    def current_points(self):
        by_point = {}
        for location in (self.coordinator.data or {}).get("locations", {}).values():
            for point in location.get("nearby", []):
                by_point.setdefault(point["shelter"]["id"], []).append((location, point))
        current = {}
        for point_id, entries in by_point.items():
            location, point = min(entries, key=lambda pair: pair[1]["straight_distance_m"])
            current[point_id] = {
                **point,
                "zone_ids": sorted({loc["origin"]["id"] for loc, _ in entries}),
                "nearest_zone": location["origin"]["id"],
                "source_status": location.get("source_status"),
                "source_error": location.get("source_error"),
                "points_updated_at": location.get("points_updated_at"),
            }
        return current

    async def async_sync(self):
        async with self.lock:
            if self.stopped:
                return
            current = self.current_points()
            registry = entity_registry.async_get(self.hass)
            for point_id in set(self.entities) - current.keys():
                entity = self.entities.pop(point_id)
                await entity.async_remove(force_remove=True)
                if entity.entity_id in registry.entities:
                    registry.async_remove(entity.entity_id)
            added = []
            for point_id, point in current.items():
                if entity := self.entities.get(point_id):
                    entity.update_point(point)
                    entity.async_write_ha_state()
                else:
                    entity = ShelterMapPoint(self.hass, self.entry, point)
                    self.entities[point_id] = entity
                    added.append(entity)
            if added:
                # Await platform registration before a subsequent refresh can remove a point.
                await self.platform.async_add_entities(added)


class ShelterMapPoint(GeolocationEvent):
    """One public point; overlapping zones share the same entity."""

    _attr_should_poll = False
    _attr_source = DOMAIN
    _attr_icon = "mdi:shield-home"
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS

    def __init__(self, hass, entry, point):
        self.map_hass = hass
        self.entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_point_{point['shelter']['id']}"
        self.update_point(point)

    def update_point(self, point):
        self.point = point
        shelter = point["shelter"]
        self._attr_name = " — ".join(filter(None, (shelter["name"], shelter.get("address"))))
        self._attr_latitude = shelter["latitude"]
        self._attr_longitude = shelter["longitude"]
        self._attr_distance = (
            distance_m(
                self.map_hass.config.latitude,
                self.map_hass.config.longitude,
                self._attr_latitude,
                self._attr_longitude,
            )
            / 1000
        )

    @property
    def extra_state_attributes(self):
        shelter = self.point["shelter"]
        return {
            "integration": DOMAIN,
            "entry_id": self.entry_id,
            "point_id": shelter["id"],
            "point_name": shelter["name"],
            "address": shelter.get("address", ""),
            "category": shelter.get("category"),
            "availability": shelter.get("availability"),
            "source_url": shelter.get("source"),
            "zone_ids": self.point["zone_ids"],
            "nearest_zone": self.point["nearest_zone"],
            "distance_to_zone_m": self.point["straight_distance_m"],
            "points_updated_at": self.point["points_updated_at"],
            "source_status": self.point["source_status"],
            "source_error": self.point["source_error"],
        }
