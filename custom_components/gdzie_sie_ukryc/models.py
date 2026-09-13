"""Validated geographic models; independent of Home Assistant."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import asin, cos, isfinite, radians, sin, sqrt


def coordinate(value, limit: float) -> float:
    """Reject missing values, booleans and non-finite coordinates."""
    if value is None or isinstance(value, bool):
        raise ValueError("Missing coordinate")
    result = float(value)
    if not isfinite(result) or not -limit <= result <= limit:
        raise ValueError("Coordinate outside WGS84 range")
    return result


@dataclass(frozen=True)
class Origin:
    id: str
    name: str
    latitude: float
    longitude: float

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Shelter:
    id: str
    name: str
    latitude: float
    longitude: float
    address: str = ""
    category: str = "Punkt schronienia"
    availability: str = "Brak informacji"
    capacity: int | None = None
    source: str = "https://gdziesieukryc.pl"

    def as_dict(self) -> dict:
        return asdict(self)


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6_371_008.8 * 2 * asin(sqrt(min(1.0, max(0.0, a))))


def candidates(points: list[Shelter], origin: Origin, radius_km: float, limit: int):
    """Return nearest geographic candidates and total known points in radius."""
    found = [(distance_m(origin.latitude, origin.longitude, p.latitude, p.longitude), p) for p in points]
    found = [pair for pair in found if pair[0] <= radius_km * 1000]
    found.sort(key=lambda pair: (pair[0], pair[1].id))
    return found[:limit], len(found)
