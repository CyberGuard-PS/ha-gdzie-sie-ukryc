"""Home Assistant entry points for Gdzie się ukryć."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .coordinator import ShelterCoordinator
from .panel import async_register_card_resource, async_register_frontend, async_remove_card_resource
from .websocket import async_register_commands

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async_register_commands(hass)
    await async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ShelterCoordinator(hass, entry)
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_card_resource(hass)

    async def zone_changed(event):
        before = event.data.get("old_state")
        after = event.data.get("new_state")
        keys = ("latitude", "longitude", "friendly_name")
        if before and after and all(before.attributes.get(key) == after.attributes.get(key) for key in keys):
            return
        await coordinator.async_request_refresh()

    entry.async_on_unload(async_track_state_change_event(hass, coordinator.options["zones"], zone_changed))
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True
    return False


async def async_remove_entry(hass, entry):
    from homeassistant.helpers.storage import Store

    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
    await async_remove_card_resource(hass)
