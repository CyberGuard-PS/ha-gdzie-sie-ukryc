"""Actual authenticated HA WebSockets, client origins and unchanged persisted zone data."""

import copy
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp.resolver import ThreadedResolver
from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth, bootstrap, loader
from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.gdzie_sie_ukryc.api import SourceError, parse_route
from custom_components.gdzie_sie_ukryc.const import DEFAULTS, DOMAIN
from custom_components.gdzie_sie_ukryc.data import PayloadError


@pytest.fixture
async def device_hass(tmp_path, monkeypatch):
    monkeypatch.setattr("ifaddr.get_adapters", lambda: [])

    class TestResolver(ThreadedResolver):
        async def real_close(self):
            await self.close()

    monkeypatch.setattr("homeassistant.helpers.aiohttp_client._async_make_resolver", lambda hass: TestResolver())
    shutil.copytree(Path(__file__).parents[1] / "custom_components", tmp_path / "custom_components")
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    hass.config.skip_pip = True
    hass.config.latitude = 50.3
    hass.config.longitude = 18.67
    hass.config.time_zone = "Europe/Warsaw"
    hass.config_entries = ConfigEntries(hass, {})

    async def calculate(origin, point, straight):
        return parse_route(
            {
                "code": "Ok",
                "routes": [
                    {
                        "distance": straight * 1.2,
                        "duration": straight * 0.96,
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

    router = AsyncMock(side_effect=calculate)
    monkeypatch.setattr("custom_components.gdzie_sie_ukryc.coordinator.WalkingRouter.route", router)
    try:
        assert await bootstrap.async_load_base_functionality(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
        # HA automatically makes its first user the owner. Test clients are subsequent users.
        await hass.auth.async_create_user("DANE TESTOWE właściciel instalacji")
        assert await async_setup_component(hass, "websocket_api", {"http": {"server_port": 18443}})
        assert await async_setup_component(hass, "zone", {})
        form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        created = await hass.config_entries.flow.async_configure(
            form["flow_id"], {**DEFAULTS, "source_mode": "import", "candidate_limit": 1, "max_routes": 1}
        )
        entry = created["result"]
        await hass.async_block_till_done()
        with patch("custom_components.gdzie_sie_ukryc.api.asyncio.sleep", new=AsyncMock()):
            await entry.runtime_data.async_import(
                {
                    "points": [
                        {"id": "near", "name": "DANE TESTOWE przy domu", "latitude": 50.301, "longitude": 18.671},
                        {"id": "far", "name": "DANE TESTOWE inne miasto", "latitude": 51.2, "longitude": 20.5},
                    ]
                }
            )
        await hass.async_block_till_done()
        router.reset_mock()
        yield hass, entry, router
        await hass.config_entries.async_unload(entry.entry_id)
    finally:
        await hass.async_stop(force=True)


async def connect_user(hass, client, name):
    user = await hass.auth.async_create_user(name, group_ids=[GROUP_ID_USER])
    assert not user.is_admin
    token = await hass.auth.async_create_refresh_token(user, client_id="https://ha.test/")
    socket = await client.ws_connect("/api/websocket")
    assert (await socket.receive_json())["type"] == "auth_required"
    await socket.send_json({"type": "auth", "access_token": hass.auth.async_create_access_token(token)})
    assert (await socket.receive_json())["type"] == "auth_ok"
    return socket


async def test_current_device_origins_are_authenticated_independent_and_not_persisted(device_hass):
    hass, entry, router = device_hass
    coordinator = entry.runtime_data
    before = copy.deepcopy(coordinator.export())
    saved = await coordinator.store.async_load()
    states = [(state.entity_id, state.state, dict(state.attributes)) for state in hass.states.async_all()]
    assert [point["shelter"]["id"] for point in before["locations"]["zone.home"]["nearby"]] == ["near"]
    async with TestClient(TestServer(hass.http.app)) as client:
        unauthenticated = await client.ws_connect("/api/websocket")
        await unauthenticated.receive_json()
        await unauthenticated.send_json({"id": 1, "type": f"{DOMAIN}/route_from_device", "entry_id": entry.entry_id})
        assert (await unauthenticated.receive_json())["type"] == "auth_invalid"
        await unauthenticated.close()
        router.assert_not_awaited()
        first = await connect_user(hass, client, "DANE TESTOWE użytkownik telefonu")
        second = await connect_user(hass, client, "DANE TESTOWE użytkownik tabletu")
        command = {"id": 1, "type": f"{DOMAIN}/route_from_device", "entry_id": entry.entry_id, "point_id": "far"}
        await first.send_json({**command, "latitude": 51.201, "longitude": 20.499})
        await second.send_json({**command, "latitude": 51.198, "longitude": 20.503})
        one = await first.receive_json(timeout=5)
        two = await second.receive_json(timeout=5)
        assert one["success"] and two["success"]
        for result, latitude, longitude in [(one["result"], 51.201, 20.499), (two["result"], 51.198, 20.503)]:
            assert result["origin"]["latitude"] == latitude
            assert result["origin"]["longitude"] == longitude
            assert result["origin"]["id"] == "device"
            assert result["route"]["geometry"]["coordinates"][0] == [longitude, latitude]
            assert result["route"]["shelter"]["id"] == "far"
            assert result["route"]["mode"] == "foot"
        await first.close()
        await second.close()
    assert router.await_count == 2
    assert coordinator.export() == before
    assert await coordinator.store.async_load() == saved
    assert [(state.entity_id, state.state, dict(state.attributes)) for state in hass.states.async_all()] == states


async def test_device_route_rejects_invalid_positions_and_targets_and_preserves_zone_routes(device_hass):
    hass, entry, router = device_hass
    coordinator = entry.runtime_data
    before = copy.deepcopy(coordinator.export())
    async with TestClient(TestServer(hass.http.app)) as client:
        socket = await connect_user(hass, client, "DANE TESTOWE zwykły użytkownik")
        command = {
            "type": f"{DOMAIN}/route_from_device",
            "entry_id": entry.entry_id,
            "point_id": "near",
            "latitude": 50.302,
            "longitude": 18.673,
        }
        invalid = [
            ({"latitude": True}, "invalid_route_request"),
            ({"latitude": 91}, "invalid_route_request"),
            ({"longitude": -181}, "invalid_route_request"),
            ({"latitude": None}, "invalid_format"),
            ({"longitude": "18.67"}, "invalid_format"),
            ({"point_id": "missing"}, "invalid_route_request"),
            ({"point_id": ""}, "invalid_format"),
            ({"entry_id": "unloaded"}, "not_loaded"),
            ({"routing_url": "https://unexpected.test/"}, "invalid_format"),
            ({"shelter": {"id": "near", "latitude": 0, "longitude": 0}}, "invalid_format"),
        ]
        for identifier, (changes, code) in enumerate(invalid, 1):
            await socket.send_json({**command, **changes, "id": identifier})
            response = await socket.receive_json(timeout=5)
            assert not response["success"]
            assert response["error"]["code"] == code
        router.assert_not_awaited()
        # Non-JSON infinities are rejected at the coordinator boundary too.
        for latitude, longitude in [(float("nan"), 18.67), (50.3, float("inf"))]:
            with pytest.raises(PayloadError):
                await coordinator.async_route_from_device("near", latitude, longitude)
        router.side_effect = SourceError("HTTP 503: silnik tras niedostępny")
        await socket.send_json({**command, "id": len(invalid) + 1})
        response = await socket.receive_json(timeout=5)
        assert not response["success"]
        assert response["error"]["code"] == "route_failed"
        assert "503" in response["error"]["message"]
        await socket.close()
    assert coordinator.export() == before
