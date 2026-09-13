"""Actual map entities: no router, overlapping zones, changes and removals."""

import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

from aiohttp.resolver import ThreadedResolver
from homeassistant import auth, bootstrap, loader
from homeassistant.config_entries import ConfigEntries, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.setup import async_setup_component

from custom_components.gdzie_sie_ukryc.api import SourceError
from custom_components.gdzie_sie_ukryc.const import DEFAULTS, DOMAIN


async def test_map_entities_without_routes_deduplicate_update_move_restore_and_remove(tmp_path, monkeypatch):
    monkeypatch.setattr("ifaddr.get_adapters", lambda: [])

    class TestResolver(ThreadedResolver):
        async def real_close(self):
            await self.close()

    monkeypatch.setattr("homeassistant.helpers.aiohttp_client._async_make_resolver", lambda hass: TestResolver())
    shutil.copytree(Path(__file__).parents[1] / "custom_components", tmp_path / "custom_components")
    points = [
        {
            "id": f"TEST-HOME-{index}",
            "name": f"DANE TESTOWE — punkt {index}",
            "address": f"Fikcyjna {index}, Miasto Testowe",
            "latitude": 50.3 + index * 0.00001,
            "longitude": 18.67,
        }
        for index in range(80)
    ] + [
        {
            "id": f"TEST-WORK-{index}",
            "name": f"DANE TESTOWE — praca {index}",
            "address": f"Fikcyjna {index}, Drugie Miasto Testowe",
            "latitude": 52.2 + index * 0.00001,
            "longitude": 21.0,
        }
        for index in range(3)
    ]
    path = tmp_path / "nearby.json"
    path.write_text(json.dumps({"points": points}), encoding="utf-8")
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    hass.config.skip_pip = True
    hass.config.latitude, hass.config.longitude = 50.3, 18.67
    hass.config.time_zone = "Europe/Warsaw"
    hass.config_entries = ConfigEntries(hass, {})

    def map_states():
        return {
            state.attributes["point_id"]: state
            for state in hass.states.async_all("geo_location")
            if state.attributes.get("integration") == DOMAIN and "latitude" in state.attributes
        }

    def registered_points():
        return {
            entry.entity_id
            for entry in entity_registry.async_get(hass).entities.values()
            if entry.domain == "geo_location" and entry.platform == DOMAIN
        }

    try:
        assert await bootstrap.async_load_base_functionality(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
        assert await async_setup_component(hass, "websocket_api", {"http": {"server_port": 18442}})
        assert await async_setup_component(hass, "zone", {})
        await hass.async_block_till_done()
        hass.states.async_set("zone.same", "0", {"latitude": 50.3, "longitude": 18.67, "friendly_name": "Druga strefa"})
        hass.states.async_set("zone.work", "0", {"latitude": 52.2, "longitude": 21.0, "friendly_name": "Praca testowa"})
        with patch(
            "custom_components.gdzie_sie_ukryc.api.WalkingRouter.route",
            new=AsyncMock(side_effect=SourceError("HTTP 503")),
        ) as router:
            form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
            created = await hass.config_entries.flow.async_configure(
                form["flow_id"],
                {
                    **DEFAULTS,
                    "source_mode": "file",
                    "data_file": "nearby.json",
                    "zones": ["zone.home", "zone.same", "zone.work"],
                    "radius_km": 1,
                    "candidate_limit": 2,
                    "max_routes": 2,
                    "nearby_limit": 30,
                },
            )
            entry = created["result"]
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
            coordinator = entry.runtime_data
            assert coordinator.data["point_count"] == 83
            assert coordinator.data["locations"]["zone.home"]["found_count"] == 80
            assert coordinator.data["locations"]["zone.home"]["nearby_truncated"] is True
            assert len(coordinator.export()["locations"]["zone.home"]["nearby"]) == 30
            assert not any(location["routes"] for location in coordinator.data["locations"].values())
            assert router.await_count == 1  # one failed request; no route dependency for map points
            states = map_states()
            assert len(states) == 33  # same points in two zones, not 63 separate entities
            assert registered_points() == {state.entity_id for state in states.values()}
            first = states["TEST-HOME-0"]
            assert first.attributes["source"] == DOMAIN
            assert first.attributes["zone_ids"] == ["zone.home", "zone.same"]
            assert first.attributes["latitude"] == 50.3
            assert first.attributes["longitude"] == 18.67
            assert points[0]["name"] in first.attributes["friendly_name"]
            assert points[0]["address"] in first.attributes["friendly_name"]
            assert states["TEST-WORK-0"].attributes["distance_to_zone_m"] == 0
            assert float(states["TEST-WORK-0"].state) > 100  # geo state measures distance from HA's home

            # Updates keep the public point identity while refreshing both labels and coordinates.
            points[0].update(name="DANE TESTOWE — zmieniona nazwa", address="Fikcyjna 99, Nowy Adres Testowy")
            path.write_text(json.dumps({"points": points}), encoding="utf-8")
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            first_after = map_states()["TEST-HOME-0"]
            assert first_after.entity_id == first.entity_id
            assert points[0]["name"] in first_after.attributes["friendly_name"]
            assert first_after.attributes["address"] == points[0]["address"]

            # All three zones now overlap in the second city; old map entities and registry rows disappear.
            for zone in ("zone.home", "zone.same"):
                hass.states.async_set(zone, "0", {"latitude": 52.2, "longitude": 21.0})
            await hass.async_block_till_done()
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            states = map_states()
            assert set(states) == {f"TEST-WORK-{index}" for index in range(3)}
            assert registered_points() == {state.entity_id for state in states.values()}
            assert all(
                state.attributes["zone_ids"] == ["zone.home", "zone.same", "zone.work"] for state in states.values()
            )

            # Source failure leaves known map points; reload uses the persisted dataset.
            path.write_text('{"invalid": true}', encoding="utf-8")
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            assert len(map_states()) == 3
            assert all(state.attributes["source_status"] == "cached" for state in map_states().values())
            old_ids = {state.entity_id for state in map_states().values()}
            assert await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert not map_states()
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert {state.entity_id for state in map_states().values()} == old_ids

            # A valid empty source deliberately clears all point entities and registrations.
            path.write_text('{"points": []}', encoding="utf-8")
            await entry.runtime_data.async_refresh()
            await hass.async_block_till_done()
            assert entry.runtime_data.data["source_status"] == "empty"
            assert not map_states()
            assert not registered_points()
            assert await hass.config_entries.async_unload(entry.entry_id)
    finally:
        await hass.async_stop(force=True)
