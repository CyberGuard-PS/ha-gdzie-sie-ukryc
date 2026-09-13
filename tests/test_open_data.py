"""Public national export contract, bounds and conditional HTTP requests."""

import csv
import io
from unittest.mock import patch

import pytest
from aiohttp import ClientSession, web

from custom_components.gdzie_sie_ukryc.api import SourceError
from custom_components.gdzie_sie_ukryc.csv_data import parse_csv
from custom_components.gdzie_sie_ukryc.data import PayloadError


def csv_payload(count=301):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Identyfikator publiczny",
            "Nazwa",
            "Rodzaj obiektu",
            "Szerokosc geograficzna",
            "Dlugosc geograficzna",
            "Adres",
            "Dostepnosc",
        ]
    )
    for index in range(count):
        writer.writerow(
            [
                f"TEST-{index}",
                "Punkt fikcyjny",
                "DANE TESTOWE",
                50.3 + index * 0.00001,
                18.67,
                f"Adres testowy {index}, Polska",
                "Nie dotyczy",
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def test_national_csv_has_no_250_limit_and_keeps_public_fields():
    result = parse_csv(csv_payload())
    assert result.total_rows == len(result.points) == 301
    assert result.skipped == result.duplicates == 0
    assert result.points[0].id == "TEST-0"
    assert result.points[0].address == "Adres testowy 0, Polska"
    assert result.points[0].category == "DANE TESTOWE"


@pytest.mark.parametrize("body", [b"", b"<html>challenge</html>", b"lat,lon\n50,18", b"\xff", csv_payload(0)])
def test_invalid_or_empty_export_is_an_error(body):
    with pytest.raises(PayloadError):
        parse_csv(body)


def test_invalid_coordinates_and_duplicate_ids_are_reported():
    body = csv_payload(3).decode("utf-8-sig")
    body += 'TEST-0,Punkt fikcyjny,DANE TESTOWE,50.3,18.67,"Adres testowy 0, Polska",Nie dotyczy\r\n'
    body += "TEST-BAD,Punkt fikcyjny,DANE TESTOWE,NaN,18.67,Test,Nie dotyczy\r\n"
    result = parse_csv(body.encode())
    assert result.total_rows == 5 and len(result.points) == 3
    assert result.skipped == result.duplicates == 1
    with pytest.raises(PayloadError, match="sprzeczne"):
        parse_csv((body + "TEST-0,Inny punkt,DANE TESTOWE,52,21,Test,Nie dotyczy\r\n").encode())


async def test_csv_http_200_304_and_403_without_query_credentials_or_redirects():
    from custom_components.gdzie_sie_ukryc.open_data import OpenDataClient

    calls = []

    async def export(request):
        calls.append(request)
        assert not request.query
        assert "Cookie" not in request.headers and "Authorization" not in request.headers
        if len(calls) == 2:
            assert request.headers["If-None-Match"] == '"fixture"'
            return web.Response(status=304, headers={"ETag": '"fixture"'})
        if len(calls) == 3:
            return web.Response(status=403)
        if len(calls) == 4:
            return web.Response(status=302, headers={"Location": "/must-not-follow"})
        return web.Response(body=csv_payload(), content_type="text/csv", headers={"ETag": '"fixture"'})

    app = web.Application()
    app.router.add_get("/PS_XML/punkty_schronienia.csv", export)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with ClientSession() as session:
            with patch(
                "custom_components.gdzie_sie_ukryc.open_data.PSP_EXPORT_URL",
                f"http://127.0.0.1:{port}/PS_XML/punkty_schronienia.csv",
            ):
                client = OpenDataClient(session)
                fresh = await client.fetch()
                assert len(parse_csv(fresh.body).points) == 301
                assert (await client.fetch(fresh.etag)).body is None
                with pytest.raises(SourceError, match="403"):
                    await client.fetch()
                with pytest.raises(SourceError, match="302"):
                    await client.fetch()
        assert len(calls) == 4
    finally:
        await runner.cleanup()


async def test_csv_download_is_bounded():
    from custom_components.gdzie_sie_ukryc.open_data import OpenDataClient

    async def handler(request):
        return web.Response(body=csv_payload())

    app = web.Application()
    app.router.add_get("/csv", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with ClientSession() as session:
            with (
                patch("custom_components.gdzie_sie_ukryc.open_data.PSP_EXPORT_URL", f"http://127.0.0.1:{port}/csv"),
                patch("custom_components.gdzie_sie_ukryc.open_data.MAX_CSV_BYTES", 100),
            ):
                with pytest.raises(SourceError, match="32 MiB"):
                    await OpenDataClient(session).fetch()
    finally:
        await runner.cleanup()
