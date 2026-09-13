"""An entity action for refreshes from HA automations."""

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RefreshButton(entry.runtime_data)])


class RefreshButton(CoordinatorEntity, ButtonEntity):
    _attr_icon = "mdi:map-marker-refresh"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Gdzie się ukryć · Odśwież punkty i trasy"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_refresh"

    async def async_press(self):
        self.coordinator.force_routes = True
        await self.coordinator.async_refresh()
