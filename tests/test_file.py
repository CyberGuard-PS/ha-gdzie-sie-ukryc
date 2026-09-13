import json

import pytest

from custom_components.gdzie_sie_ukryc.coordinator import _load_file
from custom_components.gdzie_sie_ukryc.data import PayloadError


def test_local_source_reads_points_and_rejects_external_paths(tmp_path):
    points = {"points": [{"id": "a", "latitude": 50.30, "longitude": 18.67}]}
    config = tmp_path / "config"
    config.mkdir()
    (config / "punkty.json").write_text(json.dumps(points))
    imported, timestamp = _load_file(str(config), "punkty.json")
    assert len(imported.points) == 1
    assert timestamp
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(points))
    with pytest.raises(PayloadError):
        _load_file(str(config), "../outside.json")
    (config / "linked.json").symlink_to(outside)
    with pytest.raises(PayloadError):
        _load_file(str(config), "linked.json")
