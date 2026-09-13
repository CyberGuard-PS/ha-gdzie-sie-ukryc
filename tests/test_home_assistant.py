"""Exercise real HA config entries, entities, storage and zone-change handling."""

import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

from aiohttp.resolver import ThreadedResolver
from homeassistant import auth, bootstrap, loader
from homeassistant.config_entries import ConfigEntries, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.gdzie_sie_ukryc.api import SourceError, parse_route
from custom_components.gdzie_sie_ukryc.const import DEFAULTS, DOMAIN


async def test_real_ha_flow_import_entities_cache_and_changed_zone(tmp_path, monkeypatch):
    # The sandbox lacks interface enumeration and multicast. HA itself uses its real session.
    monkeypatch.setattr("ifaddr.get_adapters", lambda: [])

    class TestResolver(ThreadedResolver):
        async def real_close(self):
            await self.close()

    monkeypatch.setattr("homeassistant.helpers.aiohttp_client._async_make_resolver", lambda hass: TestResolver())
    shutil.copytree(Path(__file__).parents[1] / "custom_components", tmp_path / "custom_components")
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    hass.config.skip_pip = True
    hass.config.latitude = 50.296
    hass.config.longitude = 18.67
    hass.config.time_zone = "Europe/Warsaw"
    hass.config_entries = ConfigEntries(hass, {})
    try:
        assert await bootstrap.async_load_base_functionality(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
        # Sandbox cannot enumerate network interfaces; only the host adapter probe is stubbed.
        with patch("ifaddr.get_adapters", return_value=[]):
            assert await async_setup_component(hass, "websocket_api", {"http": {"server_port": 18439}})
        assert await async_setup_component(hass, "zone", {})
        await hass.async_block_till_done()
        hass.states.async_set("zone.work", "0", {"latitude": 50.31, "longitude": 18.69, "friendly_name": "Praca"})
        form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert form["type"] == "form"
        created = await hass.config_entries.flow.async_configure(
            form["flow_id"],
            {**DEFAULTS, "source_mode": "import", "zones": ["zone.home", "zone.work"], "candidate_limit": 3},
        )
        assert created["type"] == "create_entry"
        entry = created["result"]
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        coordinator = entry.runtime_data
        assert coordinator.data["source_status"] == "empty"

        async def calculate(origin, point, straight_distance):
            body = {
                "code": "Ok",
                "routes": [
                    {
                        "distance": straight_distance * 1.2,
                        "duration": straight_distance * 0.96,
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[origin.longitude, origin.latitude], [point.longitude, point.latitude]],
                        },
                    }
                ],
            }
            return parse_route(body, origin, point, straight_distance)

        router = AsyncMock()
        router.route.side_effect = calculate
        coordinator.router = router
        points = {
            "points": [
                {"id": str(i), "name": f"PS {i}", "latitude": 50.297 + i * 0.001, "longitude": 18.671 + i * 0.001}
                for i in range(3)
            ]
        }
        with patch("custom_components.gdzie_sie_ukryc.api.asyncio.sleep", new=AsyncMock()):
            result = await coordinator.async_import(points)
        await hass.async_block_till_done()
        assert result["imported"] == 3
        assert set(coordinator.data["locations"]) == {"zone.home", "zone.work"}
        assert all(len(location["routes"]) == 3 for location in coordinator.data["locations"].values())
        states = [state for state in hass.states.async_all("sensor") if state.attributes.get("integration") == DOMAIN]
        assert len(states) == 8
        assert all("geometry" not in state.attributes for state in states)
        assert any(state.state == "3" and state.attributes["zone_id"] == "zone.home" for state in states)
        saved = await coordinator.store.async_load()
        assert len(saved["dataset"]["points"]) == 3

        router.route.reset_mock()
        router.route.side_effect = SourceError("HTTP 503: nie pobrano danych")
        coordinator.force_routes = True
        await coordinator.async_refresh()
        assert all(
            route["status"] == "cached"
            for location in coordinator.data["locations"].values()
            for route in location["routes"]
        )
        assert router.route.await_count == 1

        # Changed origin coordinates must invalidate cached geometry from the previous origin.
        hass.states.async_set("zone.work", "0", {"latitude": 50.32, "longitude": 18.70, "friendly_name": "Praca"})
        await hass.async_block_till_done()
        await coordinator.async_refresh()
        assert coordinator.data["locations"]["zone.work"]["routes"] == []
        assert len(coordinator.data["locations"]["zone.home"]["routes"]) == 3

        # Real options flow must remain usable on current HA (config_entry is read-only).
        options = await hass.config_entries.options.async_init(entry.entry_id)
        assert options["type"] == "form"
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert entry.entry_id not in hass.data[DOMAIN]
        with patch("custom_components.gdzie_sie_ukryc.coordinator.WalkingRouter", return_value=router):
            assert await hass.config_entries.async_setup(entry.entry_id)
        restored = entry.runtime_data
        assert len(restored.points) == 3
        assert all(route["status"] == "cached" for route in restored.data["locations"]["zone.home"]["routes"])
        assert restored.data["locations"]["zone.work"]["routes"] == []
        assert await hass.config_entries.async_unload(entry.entry_id)
    finally:
        await hass.async_stop(force=True)
