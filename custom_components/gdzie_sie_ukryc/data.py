"""Import normalized JSON, GeoJSON or JSON bodies captured in a HAR file."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from urllib.parse import urlparse

from .const import MAX_POINTS, SOURCE
from .models import Shelter, coordinate


class PayloadError(ValueError):
    """The source did not provide a usable dataset."""


@dataclass
class ImportResult:
    points: list[Shelter]
    skipped: int = 0
    captured_at: str | None = None


def _value(record, *keys, default=None):
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return default


def _address(value) -> str:
    if isinstance(value, dict):
        street = _value(value, "street", "ulica", default="")
        number = _value(value, "house_number", "houseNumber", "number", "numer", default="")
        city = _value(value, "city", "miejscowosc", "town", default="")
        return ", ".join(x for x in (f"{street} {number}".strip(), str(city)) if x)[:500]
    return str(value or "")[:500]


def parse_point(record: dict) -> Shelter:
    """Only copy allowlisted public fields; never retain response credentials."""
    if not isinstance(record, dict):
        raise ValueError("Point must be an object")
    geometry = record.get("geometry") or {}
    fields = record.get("properties", record) if record.get("type") == "Feature" else record
    if not isinstance(fields, dict):
        raise ValueError("Invalid point properties")
    lat = _value(fields, "latitude", "lat", "szerokosc", "lokalizacja_lat")
    lon = _value(fields, "longitude", "lng", "lon", "dlugosc", "lokalizacja_lon")
    location = fields.get("location") or {}
    if isinstance(location, dict):
        lat = lat if lat is not None else _value(location, "latitude", "lat")
        lon = lon if lon is not None else _value(location, "longitude", "lng", "lon")
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if coords is not None:
        if geometry.get("type") != "Point" or not isinstance(coords, list) or len(coords) < 2:
            raise ValueError("Expected GeoJSON Point with [longitude, latitude]")
        lon, lat = coords[:2]
    lat, lon = coordinate(lat, 90), coordinate(lon, 180)
    address = _address(_value(fields, "address", "adres", "fullAddress", "lokalizacja_adres"))
    if not address:
        address = _address(fields)
    name = str(_value(fields, "name", "nazwa", "title", default=address or "Punkt schronienia"))[:300]
    sid = str(_value(fields, "id_publiczny", "id", "publicId", "public_id", "uuid", default=record.get("id") or ""))[
        :200
    ]
    if not sid:
        sid = hashlib.sha256(f"{lat:.7f}|{lon:.7f}|{address}|{name}".encode()).hexdigest()[:20]
    raw_capacity = _value(fields, "capacity", "pojemnosc")
    capacity = None
    try:
        if raw_capacity is not None and not isinstance(raw_capacity, bool):
            capacity = max(0, int(raw_capacity))
    except (TypeError, ValueError, OverflowError):
        pass
    return Shelter(
        id=sid,
        name=name,
        latitude=lat,
        longitude=lon,
        address=address,
        category=str(
            _value(
                fields,
                "category",
                "kategoria",
                "shelterType",
                "object_type",
                "rodzaj_obiektu",
                default="Punkt schronienia",
            )
        )[:120],
        availability=str(_value(fields, "availability", "dostepnosc", "openingHours", default="Brak informacji"))[:300],
        capacity=capacity,
        source=SOURCE,
    )


def _records(payload, depth=0):
    if depth > 6:
        raise PayloadError("Zbyt głęboko zagnieżdżony JSON")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "id_publiczny" in payload and "lokalizacja_lat" in payload and "lokalizacja_lon" in payload:
            return [payload]
        for key in ("points", "features", "shelters", "results", "items", "data"):
            if key in payload:
                try:
                    return _records(payload[key], depth + 1)
                except PayloadError:
                    continue
    raise PayloadError("Oczekiwano listy punktów, pola points/shelters/data lub GeoJSON FeatureCollection")


def parse_payload(payload) -> ImportResult:
    """Reject non-empty datasets with no valid coordinates instead of clearing cache."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError) as err:
            raise PayloadError("Nieprawidłowy JSON") from err
    records = _records(payload)
    if len(records) > MAX_POINTS:
        raise PayloadError(f"Maksymalnie {MAX_POINTS} punktów")
    points = {}
    skipped = 0
    for record in records:
        try:
            point = parse_point(record)
            points[point.id] = point
        except (TypeError, ValueError, OverflowError, AttributeError):
            skipped += 1
    if records and not points:
        raise PayloadError("Brak punktów z rozpoznanymi współrzędnymi WGS84. Użyj formatu z przykładu")
    captured_at = payload.get("captured_at") if isinstance(payload, dict) else None
    return ImportResult(list(points.values()), skipped, captured_at)


def parse_har(payload: dict) -> ImportResult:
    """Extract shelter responses from the exact official host without network calls."""
    found = {}
    skipped = 0
    capture = None
    entries = payload.get("log", {}).get("entries", [])
    for entry in entries:
        host = urlparse(entry.get("request", {}).get("url", "")).hostname
        if host not in {"gdziesieukryc.pl", "www.gdziesieukryc.pl"}:
            continue
        response = entry.get("response", {})
        if response.get("status") != 200:
            continue
        content = response.get("content", {})
        text = content.get("text", "")
        try:
            if content.get("encoding") == "base64":
                text = base64.b64decode(text, validate=True).decode("utf-8")
            decoded = json.loads(text)
            result = parse_payload(decoded)
        except (ValueError, TypeError, UnicodeError):
            continue
        # Avoid importing geocoder/weather results that also happen to have coordinates.
        path = urlparse(entry.get("request", {}).get("url", "")).path.lower()
        looks_like_shelters = any(key in path for key in ("shelter", "schron", "safe-place", "safeplace"))
        if not looks_like_shelters:
            continue
        for point in result.points:
            found[point.id] = point
        skipped += result.skipped
        timestamp = entry.get("startedDateTime")
        if isinstance(timestamp, str) and (capture is None or timestamp > capture):
            capture = timestamp
    if not found:
        raise PayloadError(
            "HAR nie zawiera rozpoznanej odpowiedzi z punktami schronienia. Zapisz samą odpowiedź JSON i sprawdź przykład formatu"
        )
    if len(found) > MAX_POINTS:
        raise PayloadError("Za dużo punktów w HAR")
    return ImportResult(list(found.values()), skipped, capture)


def normalize(result: ImportResult) -> dict:
    """Canonical output of the offline importer."""
    return {"source": SOURCE, "captured_at": result.captured_at, "points": [p.as_dict() for p in result.points]}
