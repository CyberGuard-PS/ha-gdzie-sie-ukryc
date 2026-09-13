import base64
import json

import pytest

from custom_components.gdzie_sie_ukryc.data import PayloadError, normalize, parse_har, parse_payload
from custom_components.gdzie_sie_ukryc.models import Origin, Shelter, candidates, distance_m


def test_geojson_uses_longitude_first_and_rejects_invalid_geometry():
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [18.67, 50.30]},
                "properties": {"id": "a", "name": "PS"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[18.67, 50.30], [18.68, 50.31]]},
                "properties": {},
            },
        ],
    }
    result = parse_payload(payload)
    assert (result.points[0].latitude, result.points[0].longitude) == (50.30, 18.67)
    assert result.skipped == 1


@pytest.mark.parametrize("bad", [None, True, "NaN", "Infinity", 91, -91])
def test_rejects_invalid_latitude(bad):
    with pytest.raises(PayloadError):
        parse_payload({"points": [{"latitude": bad, "longitude": 18.67}]})


def test_nested_feed_dedup_and_allowlist():
    point = {
        "id": "a",
        "lat": "50.30",
        "lng": "18.67",
        "address": {"street": "Próbna", "houseNumber": 1, "city": "Gliwice"},
        "token": "SECRET",
    }
    result = parse_payload({"data": {"shelters": [point, point]}})
    assert len(result.points) == 1
    assert result.points[0].address == "Próbna 1, Gliwice"
    assert "SECRET" not in json.dumps(normalize(result))


def test_unknown_wrapper_and_html_are_rejected():
    for payload in ("<html>Security Check</html>", {"weather": []}, {"data": [{"city": "Gliwice"}]}):
        with pytest.raises(PayloadError):
            parse_payload(payload)


def test_har_filters_host_and_geocoder_and_decodes_base64():
    body = {"points": [{"id": "a", "latitude": 50.30, "longitude": 18.67, "name": "PS"}]}

    def entry(url, encoding=None):
        content = json.dumps(body)
        if encoding:
            content = base64.b64encode(content.encode()).decode()
        return {
            "request": {"url": url, "headers": [{"name": "Authorization", "value": "SECRET"}]},
            "startedDateTime": "2026-09-13T07:00:00Z",
            "response": {"status": 200, "content": {"text": content, "encoding": encoding}},
        }

    result = parse_har(
        {
            "log": {
                "entries": [
                    entry("https://gdziesieukryc.pl/api/shelters", "base64"),
                    entry("https://evil.test/api/shelters"),
                    entry("https://gdziesieukryc.pl/api/geocoding"),
                ]
            }
        }
    )
    assert len(result.points) == 1
    assert result.captured_at == "2026-09-13T07:00:00Z"
    assert "SECRET" not in json.dumps(normalize(result))
    with pytest.raises(PayloadError):
        parse_har({"log": {"entries": [entry("https://evil.test/api/shelters")]}})


def test_nearest_candidates_are_radius_limited_and_deterministic():
    home = Origin("zone.home", "Dom", 50.30, 18.67)
    points = [Shelter("far", "Far", 51.3, 18.67), Shelter("b", "B", 50.301, 18.67), Shelter("a", "A", 50.30, 18.67)]
    selected, total = candidates(points, home, 5, 1)
    assert total == 2
    assert selected[0][1].id == "a"
    assert 111 < distance_m(50.30, 18.67, 50.301, 18.67) < 112
