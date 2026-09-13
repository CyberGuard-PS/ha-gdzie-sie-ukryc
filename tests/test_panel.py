"""Real HA resource storage and static HTTP serving of the HACS-installed assets."""

from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth, bootstrap, loader
from homeassistant.components.lovelace import LovelaceData
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceStorage
from homeassistant.components.lovelace.resources import ResourceStorageCollection, ResourceYAMLCollection
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.gdzie_sie_ukryc.panel import (
    CARD_PATH,
    CARD_URL,
    LEGACY_CARD_PATH,
    async_register_card_resource,
    async_register_frontend,
    async_remove_card_resource,
)


@pytest.fixture
async def panel_hass(tmp_path, monkeypatch):
    monkeypatch.setattr("ifaddr.get_adapters", lambda: [])
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    hass.config.skip_pip = True
    hass.config_entries = ConfigEntries(hass, {})
    try:
        assert await bootstrap.async_load_base_functionality(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
        assert await async_setup_component(hass, "http", {"http": {"server_port": 18441}})
        yield hass
    finally:
        await hass.async_stop(force=True)


async def test_card_resource_migration_is_idempotent_and_keeps_unrelated_resources(panel_hass):
    hass = panel_hass
    resources = ResourceStorageCollection(hass, LovelaceStorage(hass, None))
    hass.data[LOVELACE_DATA] = LovelaceData("storage", {}, resources, {})
    old = await resources.async_create_item({"url": f"{LEGACY_CARD_PATH}?v=1.1.0", "res_type": "module"})
    await resources.async_create_item({"url": f"{CARD_PATH}?v=1.1.0", "res_type": "module"})
    unrelated = await resources.async_create_item({"url": "/local/other-card.js", "res_type": "module"})
    await async_register_card_resource(hass)
    await async_register_card_resource(hass)
    items = resources.async_items()
    assert len(items) == 2
    assert {**old, "url": CARD_URL} in items
    assert unrelated in items
    await async_remove_card_resource(hass)
    assert resources.async_items() == [unrelated]


async def test_new_card_resource_is_created_and_yaml_resources_are_untouched(panel_hass):
    hass = panel_hass
    resources = ResourceStorageCollection(hass, LovelaceStorage(hass, None))
    hass.data[LOVELACE_DATA] = LovelaceData("storage", {}, resources, {})
    await async_register_card_resource(hass)
    assert len(resources.async_items()) == 1
    assert resources.async_items()[0]["url"] == CARD_URL
    yaml_items = [{"url": "/local/my-card.js", "type": "module"}]
    yaml_resources = ResourceYAMLCollection(yaml_items)
    hass.data[LOVELACE_DATA] = LovelaceData("yaml", {}, yaml_resources, {})
    await async_register_card_resource(hass)
    await async_remove_card_resource(hass)
    assert yaml_resources.async_items() == yaml_items


async def test_static_http_serves_all_bundled_assets_without_exposing_integration_files(panel_hass):
    hass = panel_hass
    await async_register_frontend(hass)
    async with TestClient(TestServer(hass.http.app)) as client:
        for name, marker in [
            ("gdzie-sie-ukryc-card.js", "class GdzieSieUkrycCard"),
            ("vendor/leaflet.js", "Leaflet 1.9.4"),
            ("vendor/leaflet.css", ".leaflet-container"),
        ]:
            response = await client.get(f"/gdzie_sie_ukryc/frontend/{name}")
            assert response.status == 200
            assert marker in await response.text()
        for path in ["manifest.json", "../manifest.json", "../../coordinator.py"]:
            response = await client.get(f"/gdzie_sie_ukryc/frontend/{path}")
            assert response.status == 404


async def test_resource_failure_keeps_integration_setup_usable(panel_hass):
    hass = panel_hass
    resources = AsyncMock()
    resources.async_get_info.side_effect = OSError("disk unavailable")
    hass.data[LOVELACE_DATA] = LovelaceData("storage", {}, resources, {})
    await async_register_card_resource(hass)
    resources.async_create_item.assert_not_awaited()
