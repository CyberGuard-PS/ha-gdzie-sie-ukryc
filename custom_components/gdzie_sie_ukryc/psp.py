"""The website's nearby query, verified against its 1.3.74 HAR and frontend.

This is an undocumented website endpoint. No browser cookies, login tokens,
or whole-country database download are needed for the captured request.
"""

from dataclasses import dataclass

from .api import JsonClient, SourceError
from .const import PSP_NEARBY_URL, PSP_RESULT_LIMIT
from .data import parse_point
from .models import Origin, Shelter


@dataclass
class NearbyResult:
    points: list[Shelter]
    returned_count: int
    skipped: int

    @property
    def result_limit_reached(self):
        return self.returned_count >= PSP_RESULT_LIMIT


def parse_nearby(payload) -> NearbyResult:
    """Accept the observed data/count envelope; never interpret an error as no points."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise SourceError("PSP: nieznany format odpowiedzi listy punktów")
    records = payload["data"]
    count = payload.get("count")
    if type(count) is not int or count != len(records) or count > PSP_RESULT_LIMIT:
        raise SourceError("PSP: nieprawidłowa liczba punktów w odpowiedzi")
    points = {}
    skipped = 0
    for record in records:
        try:
            if not isinstance(record, dict) or not record.get("id_publiczny"):
                raise ValueError("Missing public ID")
            if "lokalizacja_lat" not in record or "lokalizacja_lon" not in record:
                raise ValueError("Missing PSP coordinates")
            point = parse_point(record)
            points[point.id] = point
        except (TypeError, ValueError, OverflowError, AttributeError):
            skipped += 1
    if records and not points:
        raise SourceError("PSP: brak punktów z poprawnymi współrzędnymi")
    return NearbyResult(list(points.values()), count, skipped)


class PSPClient(JsonClient):
    async def nearby(self, origin: Origin, radius_km: float) -> NearbyResult:
        payload = await self.get(
            PSP_NEARBY_URL,
            params={
                "lat": f"{origin.latitude:.7f}",
                "lng": f"{origin.longitude:.7f}",
                "radius": str(round(radius_km * 1000)),
                "limit": str(PSP_RESULT_LIMIT),
            },
        )
        return parse_nearby(payload)
