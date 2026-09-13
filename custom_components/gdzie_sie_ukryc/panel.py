"""Serve the bundled card and manage its resource in storage-mode Lovelace."""

import logging
from pathlib import Path
from urllib.parse import urlsplit

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.exceptions import HomeAssistantError

from .const import VERSION

_LOGGER = logging.getLogger(__name__)
STATIC_URL = "/gdzie_sie_ukryc/frontend"
CARD_PATH = f"{STATIC_URL}/gdzie-sie-ukryc-card.js"
CARD_URL = f"{CARD_PATH}?v={VERSION}"
LEGACY_CARD_PATH = "/local/gdzie-sie-ukryc/gdzie-sie-ukryc-card.js"


def _owned_resource(item):
    parsed = urlsplit(item.get("url", ""))
    return not parsed.netloc and not parsed.scheme and parsed.path in {CARD_PATH, LEGACY_CARD_PATH}


async def async_register_frontend(hass):
    """Register only public JS/CSS assets, once in component setup (not each reload)."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), False)]
    )


async def async_register_card_resource(hass):
    """Update our resource in UI mode. YAML mode uses the documented resource URL."""
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None or lovelace.resource_mode != MODE_STORAGE:
        _LOGGER.info("Zasób karty dla panelu YAML: %s (typ: module)", CARD_URL)
        return
    resources = lovelace.resources
    try:
        await resources.async_get_info()  # Public method ensures lazy storage has loaded.
        matches = [item for item in resources.async_items() if _owned_resource(item)]
        if not matches:
            await resources.async_create_item({"url": CARD_URL, "res_type": "module"})
            return
        first, *duplicates = matches
        if first.get("url") != CARD_URL or first.get("type") != "module":
            await resources.async_update_item(first["id"], {"url": CARD_URL, "res_type": "module"})
        for duplicate in duplicates:
            await resources.async_delete_item(duplicate["id"])
    except (HomeAssistantError, OSError, ValueError):
        _LOGGER.warning("Nie dodano zasobu karty automatycznie. Dodaj %s jako moduł JavaScript", CARD_URL)


async def async_remove_card_resource(hass):
    """Remove our resource when the only integration entry is deleted."""
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None or lovelace.resource_mode != MODE_STORAGE:
        return
    resources = lovelace.resources
    await resources.async_get_info()
    for item in list(resources.async_items()):
        if _owned_resource(item):
            await resources.async_delete_item(item["id"])
