"""Bounded asynchronous JSON feed and walking OSRM client."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from math import isfinite
from urllib.parse import urlparse

import aiohttp

from .const import MAX_BYTES, SNAP_RADIUS_METERS
from .models import Origin, Shelter, coordinate, distance_m


class SourceError(Exception):
    """A feed or routing service failed."""


def validate_url(value: str) -> str:
    """Allow explicit HTTPS and LAN HTTP services; reject embedded credentials."""
    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError("Podaj pełny URL HTTP/HTTPS bez loginu, hasła i fragmentu")
    return value.rstrip("/")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class JsonClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def get(self, url: str, params: dict | None = None, route_response: bool = False):
        try:
            async with asyncio.timeout(20):
                async with self.session.get(
                    url, params=params, headers={"Accept": "application/json"}, allow_redirects=False
                ) as response:
                    if response.status in (403, 429):
                        raise SourceError(f"HTTP {response.status}: dostęp odrzucony lub limit zapytań")
                    if response.status != 200 and not (route_response and response.status == 400):
                        raise SourceError(f"HTTP {response.status}: nie pobrano danych")
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise SourceError("Odpowiedź przekracza 8 MiB")
                    try:
                        return json.loads(body)
                    except (ValueError, UnicodeError) as err:
                        raise SourceError("Odpowiedź nie jest JSON (możliwa weryfikacja bezpieczeństwa)") from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SourceError("Nie udało się połączyć z usługą") from err


class WalkingRouter(JsonClient):
    def __init__(self, session: aiohttp.ClientSession, base_url: str):
        super().__init__(session)
        self.base_url = validate_url(base_url)

    async def route(self, origin: Origin, shelter: Shelter, straight_distance: float) -> dict:
        coordinates = f"{origin.longitude:.7f},{origin.latitude:.7f};{shelter.longitude:.7f},{shelter.latitude:.7f}"
        payload = await self.get(
            f"{self.base_url}/{coordinates}",
            {
                "overview": "simplified",
                "geometries": "geojson",
                "steps": "false",
                "alternatives": "false",
                "radiuses": f"{SNAP_RADIUS_METERS};{SNAP_RADIUS_METERS}",
            },
            route_response=True,
        )
        return parse_route(payload, origin, shelter, straight_distance)


def parse_route(payload, origin: Origin, shelter: Shelter, straight_distance: float) -> dict:
    """Validate geometry and expose snapping gaps separately from the walking route."""
    try:
        if not isinstance(payload, dict) or payload.get("code") != "Ok" or not payload.get("routes"):
            raise ValueError("No route")
        first = payload["routes"][0]
        distance, duration = float(first["distance"]), float(first["duration"])
        if not all(isfinite(n) and n >= 0 for n in (distance, duration)):
            raise ValueError("Invalid distance or time")
        geometry = first["geometry"]
        coords = geometry["coordinates"]
        if (
            geometry.get("type") != "LineString"
            or not isinstance(coords, list)
            or len(coords) < 2
            or len(coords) > 10000
        ):
            raise ValueError("Invalid route geometry")
        validated = [[coordinate(pair[0], 180), coordinate(pair[1], 90)] for pair in coords]
        start_gap = distance_m(origin.latitude, origin.longitude, validated[0][1], validated[0][0])
        end_gap = distance_m(shelter.latitude, shelter.longitude, validated[-1][1], validated[-1][0])
        if max(start_gap, end_gap) > SNAP_RADIUS_METERS + 10:
            raise ValueError("Route endpoints too far from points")
    except (KeyError, ValueError, TypeError, IndexError, OverflowError) as err:
        raise SourceError("Brak poprawnej trasy pieszej między punktami") from err
    return {
        "shelter": shelter.as_dict(),
        "distance_m": round(distance, 1),
        "duration_s": round(duration, 1),
        "straight_distance_m": round(straight_distance, 1),
        "geometry": {"type": "LineString", "coordinates": validated},
        "start_gap_m": round(start_gap, 1),
        "end_gap_m": round(end_gap, 1),
        "calculated_at": utcnow(),
        "status": "fresh",
        "mode": "foot",
    }


async def plan_routes(
    router: WalkingRouter, origin: Origin, selected, max_routes: int, cached: list[dict], circuit_open=False
):
    """Refresh candidates sequentially; a failed service never erases a last known route."""
    old = {r["shelter"]["id"]: r for r in cached if isinstance(r, dict) and "shelter" in r}
    routes = []
    unrouted = []
    error = None
    failed = circuit_open
    for index, (straight_distance, point) in enumerate(selected):
        try:
            if failed:
                raise SourceError("Obliczanie tras wstrzymane po błędzie usługi")
            route = await router.route(origin, point, straight_distance)
            routes.append(route)
        except SourceError as err:
            error = str(err)
            # NoSegment/NoRoute may be point-specific; a connection/HTTP error opens the circuit.
            if "Brak poprawnej trasy" not in error:
                failed = True
            previous = old.get(point.id)
            if previous and any(
                previous["shelter"].get(key) != getattr(point, key) for key in ("latitude", "longitude")
            ):
                previous = None
            if previous:
                routes.append({**previous, "shelter": point.as_dict(), "status": "cached"})
            else:
                unrouted.append({"shelter": point.as_dict(), "straight_distance_m": round(straight_distance, 1)})
        if not failed and index + 1 < len(selected):
            await asyncio.sleep(1.05)
    routes.sort(key=lambda r: (r["distance_m"], r["shelter"]["id"]))
    return routes[:max_routes], unrouted, error, failed
