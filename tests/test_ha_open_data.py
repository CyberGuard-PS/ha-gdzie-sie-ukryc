"""Actual HA setup, whole-country selection, cold fallback and persisted cache."""

import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

from aiohttp.resolver import ThreadedResolver
from homeassistant import auth, bootstrap, loader
from homeassistant.config_entries import ConfigEntries, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from test_open_data import csv_payload

from custom_components.gdzie_sie_ukryc.api import SourceError, parse_route
from custom_components.gdzie_sie_ukryc.const import DEFAULTS, DOMAIN
from custom_components.gdzie_sie_ukryc.open_data import CSVDownload


async def test_national_source_bundle_refresh_move_304_failure_and_reload(tmp_path, monkeypatch):
    monkeypatch.setattr("ifaddr.get_adapters", lambda: [])

    class TestResolver(ThreadedResolver):
        async def real_close(self):
            await self.close()

    monkeypatch.setattr("homeassistant.helpers.aiohttp_client._async_make_resolver", lambda hass: TestResolver())
    shutil.copytree(Path(__file__).parents[1] / "custom_components", tmp_path / "custom_components")
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    hass.config.skip_pip = True
    hass.config.latitude, hass.config.longitude = 50.3, 18.67
    hass.config.time_zone = "Europe/Warsaw"
    hass.config_entries = ConfigEntries(hass, {})

    async def calculate(origin, point, straight):
        return parse_route(
            {
                "code": "Ok",
                "routes": [
                    {
                        "distance": straight * 1.2,
                        "duration": straight,
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[origin.longitude, origin.latitude], [point.longitude, point.latitude]],
                        },
                    }
                ],
            },
            origin,
            point,
            straight,
        )

    source = AsyncMock(side_effect=SourceError("Eksport CSV PSP: HTTP 403"))
    try:
        assert await bootstrap.async_load_base_functionality(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
        assert await async_setup_component(hass, "websocket_api", {"http": {"server_port": 18441}})
        assert await async_setup_component(hass, "zone", {})
        await hass.async_block_till_done()
        hass.states.async_set("zone.work", "0", {"latitude": 52.2, "longitude": 21.0, "friendly_name": "Praca testowa"})
        with (
            patch("custom_components.gdzie_sie_ukryc.open_data.OpenDataClient.fetch", new=source),
            patch(
                "custom_components.gdzie_sie_ukryc.psp.PSPClient.nearby",
                new=AsyncMock(side_effect=AssertionError("Unexpected nearby query")),
            ) as nearby,
            patch("custom_components.gdzie_sie_ukryc.api.WalkingRouter.route", new=AsyncMock(side_effect=calculate)),
            patch("custom_components.gdzie_sie_ukryc.coordinator.asyncio.sleep", new=AsyncMock()),
        ):
            form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
            created = await hass.config_entries.flow.async_configure(
                form["flow_id"],
                {
                    **DEFAULTS,
                    "zones": ["zone.home", "zone.work"],
                    "radius_km": 50,
                    "max_routes": 2,
                    "candidate_limit": 2,
                },
            )
            entry = created["result"]
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
            assert entry.version == 2
            coordinator = entry.runtime_data
            # Real bundled national CSV remains usable when the first network request fails.
            assert coordinator.data["point_count"] > 85000
            assert coordinator.data["source_status"] == "cached"
            assert coordinator.data["dataset"]["origin"] == "bundled"
            assert source.await_count == 1
            nearby.assert_not_awaited()

            country = csv_payload() + b"TEST-WORK,Punkt fikcyjny,DANE TESTOWE,52.2,21.0,Test,Nie dotyczy\r\n"
            source.side_effect = None
            source.return_value = CSVDownload(country, '"test"', None)
            coordinator.force_routes = True
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            assert coordinator.data["point_count"] == 302
            assert coordinator.data["source_status"] == "ok"
            assert coordinator.data["dataset"]["origin"] == "live"
            assert coordinator.data["locations"]["zone.home"]["found_count"] == 301
            assert coordinator.data["locations"]["zone.work"]["found_count"] == 1
            assert len(coordinator.data["locations"]["zone.home"]["routes"]) == 2
            assert source.await_count == 2  # one national download, even with two zones
            sensors = [s for s in hass.states.async_all("sensor") if s.attributes.get("integration") == DOMAIN]
            assert len(sensors) == 8
            assert all(s.attributes["dataset_points"] == 302 for s in sensors)
            assert any(s.state == "301" for s in sensors)

            # Moving the origin uses the already downloaded national dataset.
            source.reset_mock()
            hass.states.async_set(
                "zone.home", "0", {"latitude": 52.2, "longitude": 21.0, "friendly_name": "Dom testowy"}
            )
            await hass.async_block_till_done()
            await coordinator.async_refresh()
            assert coordinator.data["locations"]["zone.home"]["found_count"] == 1
            source.assert_not_awaited()

            old_date = coordinator.points_updated_at
            source.return_value = CSVDownload(None, '"test"', None)
            coordinator.force_routes = True
            await coordinator.async_refresh()
            assert coordinator.points_updated_at == old_date
            assert coordinator.data["point_count"] == 302
            assert source.call_args.args == ('"test"', None)

            source.side_effect = SourceError("Eksport CSV PSP: HTTP 503")
            coordinator.force_routes = True
            await coordinator.async_refresh()
            assert coordinator.data["source_status"] == "cached"
            assert coordinator.data["point_count"] == 302
            source.reset_mock()
            assert await hass.config_entries.async_unload(entry.entry_id)
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.runtime_data.data["source_status"] == "cached"
            assert entry.runtime_data.data["point_count"] == 302
            source.assert_not_awaited()
            nearby.assert_not_awaited()
            assert await hass.config_entries.async_unload(entry.entry_id)
    finally:
        await hass.async_stop(force=True)


async def test_old_psp_entry_migrates_preserving_zone_and_radius(tmp_path):
    from homeassistant.config_entries import ConfigEntry

    from custom_components.gdzie_sie_ukryc import async_migrate_entry

    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = ConfigEntries(hass, {})
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test",
        data={**DEFAULTS, "source_mode": "psp"},
        options={"source_mode": "psp", "radius_km": 50, "zones": ["zone.home"]},
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data=[],
    )
    # Register the stored entry without starting its platforms or network clients.
    hass.config_entries._entries[entry.entry_id] = entry
    try:
        assert await async_migrate_entry(hass, entry)
        assert entry.version == 2
        assert entry.options["source_mode"] == entry.data["source_mode"] == "open_data"
        assert entry.options["radius_km"] == 50
        assert entry.options["zones"] == ["zone.home"]
    finally:
        await hass.async_stop(force=True)
