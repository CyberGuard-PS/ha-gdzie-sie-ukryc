"""Shared configuration for Gdzie się ukryć."""

DOMAIN = "gdzie_sie_ukryc"
NAME = "Gdzie się ukryć"
VERSION = "1.2.0"
SOURCE = "https://gdziesieukryc.pl"
PSP_NEARBY_URL = f"{SOURCE}/api/shelters/nearby"
PSP_RESULT_LIMIT = 250
DEFAULT_ROUTER = "https://routing.openstreetmap.de/routed-foot/route/v1/foot"
DEFAULTS = {
    "source_mode": "psp",
    "data_file": "gdzie_sie_ukryc/punkty.json",
    "feed_url": "",
    "zones": ["zone.home"],
    "radius_km": 5.0,
    "max_routes": 3,
    "candidate_limit": 12,
    "update_hours": 24,
    "routing_url": DEFAULT_ROUTER,
}
MAX_BYTES = 8 * 1024 * 1024
MAX_POINTS = 100_000
MAX_ZONES = 8
SNAP_RADIUS_METERS = 100


def settings(entry):
    """Merge defaults, entry data and editable options."""
    return {**DEFAULTS, **entry.data, **entry.options}
