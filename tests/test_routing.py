from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession, web

from custom_components.gdzie_sie_ukryc.api import (
    JsonClient,
    SourceError,
    WalkingRouter,
    parse_route,
    plan_routes,
    validate_url,
)
from custom_components.gdzie_sie_ukryc.models import Origin, Shelter

HOME = Origin("zone.home", "Dom", 50.296, 18.670)
PS = Shelter("a", "PS", 50.298, 18.672)


def payload(distance=325, duration=260):
    return {
        "code": "Ok",
        "routes": [
            {
                "distance": distance,
                "duration": duration,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[18.670, 50.296], [18.671, 50.297], [18.672, 50.298]],
                },
            }
        ],
    }


@pytest.mark.parametrize("body", [{"code": "NoRoute"}, payload(float("nan")), payload(duration=-1)])
def test_invalid_routes_do_not_turn_into_straight_lines(body):
    with pytest.raises(SourceError):
        parse_route(body, HOME, PS, 263)


def test_route_validates_snapping_and_keeps_units():
    route = parse_route(payload(), HOME, PS, 263)
    assert route["distance_m"] == 325
    assert route["duration_s"] == 260
    assert route["status"] == "fresh"
    assert route["end_gap_m"] == 0
    bad = payload()
    bad["routes"][0]["geometry"]["coordinates"][-1] = [19.0, 51.0]
    with pytest.raises(SourceError):
        parse_route(bad, HOME, PS, 263)


async def test_router_unavailable_preserves_valid_cache_and_opens_circuit():
    router = AsyncMock()
    router.route.side_effect = SourceError("Nie udało się połączyć z usługą")
    previous = parse_route(payload(), HOME, PS, 263)
    other = Shelter("b", "B", 50.299, 18.673)
    routes, missing, error, opened = await plan_routes(router, HOME, [(263, PS), (300, other)], 3, [previous])
    assert len(routes) == 1 and routes[0]["status"] == "cached"
    assert routes[0]["calculated_at"] == previous["calculated_at"]
    assert len(missing) == 1
    assert opened and error
    assert router.route.await_count == 1


async def test_cache_is_not_reused_when_shelter_moves():
    router = AsyncMock()
    router.route.side_effect = SourceError("HTTP 503")
    previous = parse_route(payload(), HOME, PS, 263)
    moved = Shelter("a", "Moved", 50.31, 18.69)
    routes, missing, _, _ = await plan_routes(router, HOME, [(1300, moved)], 3, [previous])
    assert routes == [] and len(missing) == 1


async def test_point_specific_no_route_does_not_stop_other_routes():
    router = AsyncMock()
    router.route.side_effect = [
        SourceError("Brak poprawnej trasy pieszej między punktami"),
        parse_route(payload(), HOME, PS, 263),
    ]
    with patch("custom_components.gdzie_sie_ukryc.api.asyncio.sleep", new=AsyncMock()):
        routes, missing, _, opened = await plan_routes(router, HOME, [(263, PS), (300, PS)], 3, [])
    assert len(routes) == 1 and len(missing) == 1 and not opened
    assert router.route.await_count == 2


async def test_http_client_and_router_handle_403_html_and_no_route():
    async def response(request):
        if request.path.startswith("/blocked"):
            return web.Response(status=403, text="Security Check")
        if request.path.startswith("/html"):
            return web.Response(text="<html>Security Check</html>")
        if request.path.startswith("/missing"):
            return web.json_response({"code": "NoRoute"}, status=400)
        assert request.query["geometries"] == "geojson"
        assert request.query["radiuses"] == "100;100"
        assert "18.6700000,50.2960000;18.6720000,50.2980000" in request.path
        return web.json_response(payload())

    app = web.Application()
    app.router.add_get("/{tail:.*}", response)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    try:
        async with ClientSession() as session:
            for path in ("blocked", "html"):
                with pytest.raises(SourceError):
                    await JsonClient(session).get(f"{base}/{path}")
            with pytest.raises(SourceError, match="Brak poprawnej trasy"):
                await WalkingRouter(session, f"{base}/missing").route(HOME, PS, 263)
            route = await WalkingRouter(session, f"{base}/foot").route(HOME, PS, 263)
            assert route["distance_m"] == 325
    finally:
        await runner.cleanup()


@pytest.mark.parametrize(
    "url",
    ["file:///etc/passwd", "https://user:pass@example.org", "javascript:alert(1)", "https://example.org/#fragment"],
)
def test_invalid_feed_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)
