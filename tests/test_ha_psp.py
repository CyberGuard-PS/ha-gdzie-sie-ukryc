"""Real Home Assistant setup using the automatic source, with controlled services."""

import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

from aiohttp.resolver import ThreadedResolver
from homeassistant import auth, bootstrap, loader
from homeassistant.config_entries import ConfigEntries, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from test_psp import psp_payload, psp_record

from custom_components.gdzie_sie_ukryc.api import SourceError, parse_route
from custom_components.gdzie_sie_ukryc.const import DEFAULTS, DOMAIN
from custom_components.gdzie_sie_ukryc.psp import parse_nearby


async def test_automatic_setup_per_zone_cache_failure_moved_origin_and_empty_result(tmp_path, monkeypatch):
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

    async def nearby(origin, radius):
        assert radius == 5
        return parse_nearby(
            psp_payload([psp_record(i, origin.latitude + 0.001, origin.longitude + 0.001) for i in range(3)])
        )

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

    source = AsyncMock(side_effect=nearby)
    router = AsyncMock(side_effect=calculate)
    try:
        assert await bootstrap.async_load_base_functionality(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
        assert await async_setup_component(hass, "websocket_api", {"http": {"server_port": 18440}})
        assert await async_setup_component(hass, "zone", {})
        await hass.async_block_till_done()
        hass.states.async_set("zone.work", "0", {"latitude": 52.2, "longitude": 21.0, "friendly_name": "Praca testowa"})
        with (
            patch("custom_components.gdzie_sie_ukryc.psp.PSPClient.nearby", new=source),
            patch("custom_components.gdzie_sie_ukryc.api.WalkingRouter.route", new=router),
            patch("custom_components.gdzie_sie_ukryc.coordinator.asyncio.sleep", new=AsyncMock()),
        ):
            form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
            assert DEFAULTS["source_mode"] == "open_data"
            created = await hass.config_entries.flow.async_configure(
                form["flow_id"],
                {
                    **DEFAULTS,
                    "source_mode": "psp",
                    "zones": ["zone.home", "zone.work"],
                    "max_routes": 2,
                    "candidate_limit": 3,
                },
            )
            entry = created["result"]
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
            coordinator = entry.runtime_data
            assert source.await_count == 2 and router.await_count == 6
            assert coordinator.data["point_count"] == 6
            assert all(len(item["routes"]) == 2 for item in coordinator.data["locations"].values())
            sensors = [
                state for state in hass.states.async_all("sensor") if state.attributes.get("integration") == DOMAIN
            ]
            assert len(sensors) == 8 and all(state.attributes["source_status"] == "ok" for state in sensors)

            # Cache survives unload/setup; no network calls until the interval expires.
            source.reset_mock()
            router.reset_mock()
            assert await hass.config_entries.async_unload(entry.entry_id)
            assert await hass.config_entries.async_setup(entry.entry_id)
            coordinator = entry.runtime_data
            await coordinator.async_refresh()
            assert source.await_count == 0 and router.await_count == 0
            old_date = coordinator.data["locations"]["zone.home"]["points_updated_at"]

            # Home occupancy changes must not start a source or route refresh.
            with patch.object(coordinator, "async_request_refresh", new=AsyncMock()) as refresh:
                hass.states.async_set("zone.home", "1", dict(hass.states.get("zone.home").attributes))
                await hass.async_block_till_done()
                refresh.assert_not_awaited()

            # A global service failure stops subsequent queries, retains every area's cache.
            source.side_effect = SourceError("HTTP 403: dostęp odrzucony")
            router.side_effect = SourceError("HTTP 503")
            coordinator.force_routes = True
            await coordinator.async_refresh()
            assert source.await_count == 1 and router.await_count == 1
            assert coordinator.data["source_status"] == "cached"
            assert coordinator.data["locations"]["zone.home"]["points_updated_at"] == old_date
            assert all(
                route["status"] == "cached" for loc in coordinator.data["locations"].values() for route in loc["routes"]
            )

            # Move Home far away while PSP is unavailable. Work remains usable; Home has no false coverage.
            hass.states.async_set(
                "zone.home", "0", {"latitude": 53.5, "longitude": 16.5, "friendly_name": "Nowy dom testowy"}
            )
            await hass.async_block_till_done()
            await coordinator.async_refresh()
            home = coordinator.data["locations"]["zone.home"]
            assert home["routes"] == [] and home["found_count"] == 0
            assert home["source_status"] == "error" and home["points_updated_at"] is None
            assert len(coordinator.data["locations"]["zone.work"]["routes"]) == 2

            # A successful empty reply intentionally removes prior points/routes.
            source.side_effect = None
            source.return_value = parse_nearby(psp_payload([]))
            router.reset_mock()
            coordinator.force_routes = True
            await coordinator.async_refresh()
            assert coordinator.data["source_status"] == "empty" and coordinator.data["point_count"] == 0
            assert all(not loc["routes"] for loc in coordinator.data["locations"].values())
            router.assert_not_awaited()
            assert await hass.config_entries.async_unload(entry.entry_id)
    finally:
        await hass.async_stop(force=True)
