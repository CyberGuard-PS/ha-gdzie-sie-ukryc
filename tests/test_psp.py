"""PSP 1.3.74 response contract; all fixture coordinates and names are synthetic."""

from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession, web

from custom_components.gdzie_sie_ukryc.api import SourceError
from custom_components.gdzie_sie_ukryc.data import parse_payload
from custom_components.gdzie_sie_ukryc.models import Origin
from custom_components.gdzie_sie_ukryc.psp import PSPClient, parse_nearby


def psp_record(index=0, latitude=50.3, longitude=18.67):
    return {
        "id": 123 + index,
        "id_publiczny": f"TEST-{latitude}-{index}",
        "nazwa": "DANE TESTOWE — obiekt fikcyjny",
        "rodzaj_obiektu": "Obiekt ochrony ludności",
        "opis_ogolny": None,
        "gmina": "Miasto testowe",
        "lokalizacja_lat": latitude + index * 0.001,
        "lokalizacja_lon": longitude + index * 0.001,
        "lokalizacja_adres": f"Adres testowy {index}",
        "dostepnosc": "Całodobowa",
        "dystans_metry": 123,
    }


def psp_payload(records):
    return {"data": records, "count": len(records), "source": "local"}


def test_psp_fields_and_public_id_match_list_and_detail():
    record = psp_record()
    point = parse_nearby(psp_payload([record])).points[0]
    assert point.id == record["id_publiczny"]
    assert (point.latitude, point.longitude) == (50.3, 18.67)
    assert point.address == "Adres testowy 0"
    assert point.category == "Obiekt ochrony ludności"
    assert point.availability == "Całodobowa"
    assert parse_payload({"data": record, "source": "local"}).points == [point]
    assert "dystans_metry" not in point.as_dict()


def test_limit_and_corrupt_records_are_visible():
    records = [psp_record(i) for i in range(250)]
    records[8]["lokalizacja_lat"] = "NaN"
    result = parse_nearby(psp_payload(records))
    assert result.result_limit_reached and result.returned_count == 250
    assert len(result.points) == 249 and result.skipped == 1
    assert parse_nearby(psp_payload([])).points == []


@pytest.mark.parametrize(
    "body",
    [
        {"message": "Challenge"},
        {"data": [], "count": True},
        {"data": [], "count": 4},
        {"data": None, "count": 0},
        psp_payload([{"lat": 50.3, "lng": 18.67}]),
    ],
)
def test_changed_schema_is_an_error_not_a_valid_empty_result(body):
    with pytest.raises(SourceError):
        parse_nearby(body)


async def test_real_http_query_has_meters_limit_and_no_browser_credentials():
    requests = []

    async def nearby(request):
        requests.append(request)
        assert dict(request.query) == {"lat": "50.3000000", "lng": "18.6700000", "radius": "5000", "limit": "250"}
        assert "Cookie" not in request.headers and "Authorization" not in request.headers
        return web.json_response(psp_payload([psp_record()]))

    app = web.Application()
    app.router.add_get("/api/shelters/nearby", nearby)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with ClientSession() as session:
            with patch(
                "custom_components.gdzie_sie_ukryc.psp.PSP_NEARBY_URL", f"http://127.0.0.1:{port}/api/shelters/nearby"
            ):
                result = await PSPClient(session).nearby(Origin("zone.home", "Dom", 50.3, 18.67), 5)
        assert len(result.points) == 1 and len(requests) == 1
    finally:
        await runner.cleanup()


async def test_psp_403_is_not_retried_by_the_client():
    client = PSPClient(None)
    client.get = AsyncMock(side_effect=SourceError("HTTP 403"))
    with pytest.raises(SourceError, match="403"):
        await client.nearby(Origin("zone.home", "Dom", 50.3, 18.67), 5)
    assert client.get.await_count == 1
