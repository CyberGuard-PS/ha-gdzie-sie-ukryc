"""Shared configuration for Gdzie się ukryć."""

DOMAIN = "gdzie_sie_ukryc"
NAME = "Gdzie się ukryć"
VERSION = "1.5.0"
SOURCE = "https://gdziesieukryc.pl"
PSP_EXPORT_URL = f"{SOURCE}/PS_XML/punkty_schronienia.csv"
OPEN_DATA_URL = "https://dane.gov.pl/pl/dataset/28058,punkty-schronienia-w-polsce"
DATA_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
PSP_NEARBY_URL = f"{SOURCE}/api/shelters/nearby"
PSP_RESULT_LIMIT = 250
DEFAULT_ROUTER = "https://routing.openstreetmap.de/routed-foot/route/v1/foot"
DEFAULTS = {
    "source_mode": "open_data",
    "data_file": "gdzie_sie_ukryc/punkty.json",
    "feed_url": "",
    "zones": ["zone.home"],
    "radius_km": 5.0,
    "max_routes": 3,
    "candidate_limit": 12,
    "nearby_limit": 100,
    "update_hours": 24,
    "routing_url": DEFAULT_ROUTER,
}
MAX_BYTES = 8 * 1024 * 1024
MAX_CSV_BYTES = 32 * 1024 * 1024
MAX_DATASET_BYTES = 64 * 1024 * 1024
MAX_POINTS = 200_000
MAX_ZONES = 8
SNAP_RADIUS_METERS = 100


def settings(entry):
    """Merge defaults, entry data and editable options."""
    return {**DEFAULTS, **entry.data, **entry.options}
