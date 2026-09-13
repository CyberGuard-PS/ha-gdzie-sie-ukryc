"""Full national PSP export, optional sources and persisted walking routes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import JsonClient, SourceError, WalkingRouter, plan_routes, utcnow
from .const import DATA_LICENSE_URL, DOMAIN, MAX_DATASET_BYTES, MAX_ZONES, OPEN_DATA_URL, PSP_EXPORT_URL, settings
from .csv_data import parse_csv
from .data import ImportResult, PayloadError, normalize, parse_payload
from .models import Origin, candidates, coordinate, distance_m
from .open_data import OpenDataClient
from .psp import PSPClient

_LOGGER = logging.getLogger(__name__)


def _load_file(config_dir: str, relative_path: str):
    root = Path(config_dir).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() not in {".json", ".geojson"}:
        raise PayloadError("Plik JSON musi znajdować się w katalogu konfiguracji HA")
    if path.stat().st_size > MAX_DATASET_BYTES:
        raise PayloadError("Plik przekracza 64 MiB")
    result = parse_payload(json.loads(path.read_text(encoding="utf-8")))
    timestamp = result.captured_at or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    return result, timestamp


def _load_bundled():
    directory = Path(__file__).parent / "datasets"
    body = (directory / "psp-punkty.csv").read_bytes()
    metadata = json.loads((directory / "snapshot.json").read_text(encoding="utf-8"))
    if hashlib.sha256(body).hexdigest() != metadata.get("sha256"):
        raise PayloadError("Nieprawidłowa suma kontrolna dołączonej bazy PSP")
    result = parse_csv(body)
    if result.total_rows != metadata.get("total_rows") or len(result.points) != metadata.get("point_count"):
        raise PayloadError("Niezgodna liczba rekordów dołączonej bazy PSP")
    return result, metadata


def valid_timestamp(value) -> str | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed > datetime.now(timezone.utc) + timedelta(minutes=5):
            return None
        return parsed.isoformat()
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


class ShelterCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.entry = entry
        self.options = settings(entry)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(hours=self.options["update_hours"]),
        )
        self.session = async_get_clientsession(hass)
        self.router = WalkingRouter(self.session, self.options["routing_url"])
        self.psp = PSPClient(self.session)
        self.open_data = OpenDataClient(self.session)
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.points = []
        self.points_updated_at = None
        self.saved_locations = {}
        self.nearby_snapshots = {}
        self.source_metadata = {}
        self.source_attempted_at = None
        self.export_error = None
        self.force_routes = False
        self.import_lock = asyncio.Lock()

    async def async_route_from_device(self, point_id: str, latitude, longitude):
        """Return a one-off route without changing zone routes, entities or the Store."""
        try:
            origin = Origin("device", "Moja aktualna lokalizacja", coordinate(latitude, 90), coordinate(longitude, 180))
        except (ValueError, TypeError, OverflowError) as err:
            raise PayloadError("Urządzenie podało nieprawidłowe współrzędne lokalizacji") from err
        if not isinstance(point_id, str) or not point_id:
            raise PayloadError("Wybierz punkt schronienia z mapy lub listy")
        shelter = next((point for point in self.points if point.id == point_id), None)
        if shelter is None:
            raise PayloadError("Punkt nie istnieje w aktualnej bazie. Odśwież kartę i wybierz go ponownie")
        straight = distance_m(origin.latitude, origin.longitude, shelter.latitude, shelter.longitude)
        route = await self.router.route(origin, shelter, straight)
        return {
            "origin": origin.as_dict(),
            "route": route,
            "points_updated_at": self.points_updated_at,
            "source_status": (self.data or {}).get("source_status"),
        }

    async def _async_setup(self):
        saved = await self.store.async_load()
        if saved:
            try:
                imported = parse_payload(saved.get("dataset", {"points": []}))
                self.points = imported.points
                self.points_updated_at = valid_timestamp(saved.get("points_updated_at"))
                self.saved_locations = saved.get("locations", {})
                snapshots = saved.get("nearby_snapshots", {})
                self.nearby_snapshots = snapshots if isinstance(snapshots, dict) else {}
                metadata = saved.get("source_metadata", {})
                self.source_metadata = metadata if isinstance(metadata, dict) else {}
                self.source_attempted_at = valid_timestamp(saved.get("source_attempted_at"))
                self.export_error = saved.get("export_error")
            except (PayloadError, AttributeError, TypeError):
                _LOGGER.warning("Nie udało się odczytać zapisanych punktów schronienia")
        if self.options["source_mode"] != "open_data":
            self.source_metadata, self.source_attempted_at, self.export_error = {}, None, None
        elif self.source_metadata.get("provider") != "psp_open_data" or self.source_metadata.get("point_count") != len(
            self.points
        ):
            # A previous nearby/import dataset must never be labelled as the full national export.
            self.points, self.points_updated_at = [], None
            self.source_metadata, self.source_attempted_at, self.export_error = {}, None, None
            try:
                result, metadata = await self.hass.async_add_executor_job(_load_bundled)
                self.points = result.points
                self.points_updated_at = valid_timestamp(metadata.get("captured_at"))
                self.source_metadata = {**metadata, "origin": "bundled"}
            except (OSError, ValueError, TypeError) as err:
                _LOGGER.warning("Nie udało się odczytać dołączonej bazy PSP: %s", err)

    async def _read_open_data(self):
        """Refresh once for all zones; an outage retains the last complete export."""
        now = datetime.now(timezone.utc)
        attempted = valid_timestamp(self.source_attempted_at)
        recent = attempted and now - datetime.fromisoformat(attempted) < timedelta(hours=self.options["update_hours"])
        if not self.force_routes and recent:
            return ("cached" if self.points else "error", self.export_error) if self.export_error else ("ok", None)
        self.source_attempted_at = utcnow()
        try:
            downloaded = await self.open_data.fetch(
                self.source_metadata.get("etag") if self.points else None,
                self.source_metadata.get("last_modified") if self.points else None,
            )
            if downloaded.body is None:
                if not self.points:
                    raise SourceError("Eksport CSV PSP: HTTP 304 bez lokalnej bazy")
            else:
                digest = hashlib.sha256(downloaded.body).hexdigest()
                if not self.points or digest != self.source_metadata.get("sha256"):
                    result = await self.hass.async_add_executor_job(parse_csv, downloaded.body)
                    self.points = result.points
                    self.points_updated_at = utcnow()
                    self.source_metadata = {
                        "provider": "psp_open_data",
                        "source_url": PSP_EXPORT_URL,
                        "catalog_url": OPEN_DATA_URL,
                        "publisher": "Komenda Główna Państwowej Straży Pożarnej",
                        "license": "CC BY 4.0",
                        "license_url": DATA_LICENSE_URL,
                        "update_frequency": "Co tydzień",
                        "sha256": digest,
                        "point_count": len(result.points),
                        "total_rows": result.total_rows,
                        "skipped_points": result.skipped,
                        "duplicate_ids": result.duplicates,
                        "captured_at": self.points_updated_at,
                    }
            self.source_metadata.update(origin="live", checked_at=utcnow())
            if downloaded.etag is not None:
                self.source_metadata["etag"] = downloaded.etag
            if downloaded.last_modified is not None:
                self.source_metadata["last_modified"] = downloaded.last_modified
            self.export_error = None
            return "ok", None
        except (SourceError, PayloadError) as err:
            self.export_error = str(err)
            _LOGGER.warning("Nie udało się odświeżyć pełnej bazy PSP: %s", err)
            return "cached" if self.points else "error", self.export_error

    def origins(self) -> tuple[list[Origin], list[str]]:
        origins, errors = [], []
        for zone_id in self.options["zones"][:MAX_ZONES]:
            state = self.hass.states.get(zone_id)
            attrs = state.attributes if state else {}
            try:
                lat = attrs.get("latitude", self.hass.config.latitude if zone_id == "zone.home" else None)
                lon = attrs.get("longitude", self.hass.config.longitude if zone_id == "zone.home" else None)
                origins.append(
                    Origin(
                        zone_id,
                        attrs.get("friendly_name", "Dom" if zone_id == "zone.home" else zone_id),
                        coordinate(lat, 90),
                        coordinate(lon, 180),
                    )
                )
            except (TypeError, ValueError):
                errors.append(f"Brak współrzędnych strefy {zone_id}")
        return origins, errors

    def _signature(self, origin):
        value = {
            "origin": origin.as_dict(),
            "router": self.options["routing_url"],
            "radius": self.options["radius_km"],
            "max_routes": self.options["max_routes"],
            "candidate_limit": self.options["candidate_limit"],
            "source_mode": self.options["source_mode"],
        }
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    async def _read_psp(self, origins):
        """Keep each response tied to its query area, including empty and failed responses."""
        now = datetime.now(timezone.utc)
        interval = timedelta(hours=self.options["update_hours"])
        snapshots, per_zone = {}, {}
        service_error = None
        requested = False
        for origin in origins:
            signature = [origin.latitude, origin.longitude, self.options["radius_km"]]
            saved = self.nearby_snapshots.get(origin.id, {})
            if not isinstance(saved, dict) or saved.get("signature") != signature:
                saved = {}
            snapshot = dict(saved)
            try:
                points = parse_payload({"points": snapshot.get("points", [])}).points
            except PayloadError:
                snapshot, points = {}, []
            attempted = valid_timestamp(snapshot.get("attempted_at"))
            recent = attempted and now - datetime.fromisoformat(attempted) < interval
            if self.force_routes or not recent:
                error = service_error
                if error is None:
                    try:
                        if requested:
                            await asyncio.sleep(1.05)
                        requested = True
                        result = await self.psp.nearby(origin, self.options["radius_km"])
                        points = result.points
                        snapshot = {
                            "points": [point.as_dict() for point in points],
                            "points_updated_at": utcnow(),
                            "returned_count": result.returned_count,
                            "result_limit_reached": result.result_limit_reached,
                            "skipped": result.skipped,
                        }
                    except SourceError as err:
                        error = service_error = str(err)
                        _LOGGER.warning("Nie udało się odświeżyć punktów PSP: %s", err)
                snapshot.update(signature=signature, attempted_at=utcnow(), source_error=error)
            snapshot.setdefault("signature", signature)
            error = snapshot.get("source_error")
            timestamp = valid_timestamp(snapshot.get("points_updated_at"))
            # A cached empty successful response is also a known dataset, not a network failure.
            status = ("cached" if timestamp else "error") if error else ("ok" if points else "empty")
            per_zone[origin.id] = {
                "points": points,
                "source_status": status,
                "source_error": error,
                "points_updated_at": timestamp,
                "returned_count": snapshot.get("returned_count", 0),
                "result_limit_reached": snapshot.get("result_limit_reached", False),
                "skipped_points": snapshot.get("skipped", 0),
            }
            snapshots[origin.id] = snapshot
        self.nearby_snapshots = snapshots
        self.points = list({point.id: point for value in per_zone.values() for point in value["points"]}.values())
        dates = [value["points_updated_at"] for value in per_zone.values() if value["points_updated_at"]]
        self.points_updated_at = min(dates) if dates else None
        statuses = {value["source_status"] for value in per_zone.values()}
        errors = [f"{key}: {value['source_error']}" for key, value in per_zone.items() if value["source_error"]]
        if statuses & {"error", "cached"}:
            status = "partial" if statuses & {"ok", "empty"} else "cached" if dates else "error"
        else:
            status = "ok" if self.points else "empty"
        return per_zone, status, "; ".join(errors) or None

    async def _read_source(self):
        mode = self.options["source_mode"]
        if mode == "open_data":
            return await self._read_open_data()
        if mode == "import":
            return "imported" if self.points else "empty", None
        try:
            if mode == "file":
                result, timestamp = await self.hass.async_add_executor_job(
                    _load_file, self.hass.config.config_dir, self.options["data_file"]
                )
            else:
                payload = await JsonClient(self.session).get(self.options["feed_url"])
                result = await self.hass.async_add_executor_job(parse_payload, payload)
                timestamp = result.captured_at or utcnow()
            self.points = result.points
            self.points_updated_at = valid_timestamp(timestamp) or utcnow()
            if result.skipped:
                _LOGGER.warning("Pominięto %s punktów z nieprawidłowymi danymi", result.skipped)
            return "ok" if self.points else "empty", None
        except (SourceError, PayloadError, OSError, ValueError) as err:
            _LOGGER.warning("Źródło punktów schronienia: %s", err)
            return "cached" if self.points else "error", str(err)

    async def _async_update_data(self):
        async with self.import_lock:
            origins, origin_errors = self.origins()
            per_zone = {}
            if self.options["source_mode"] == "psp":
                per_zone, source_status, source_error = await self._read_psp(origins)
            else:
                source_status, source_error = await self._read_source()
            locations = {}
            dataset = self.source_metadata if self.options["source_mode"] == "open_data" else {}
            circuit_open = False
            now = datetime.now(timezone.utc)
            for origin in origins:
                signature = self._signature(origin)
                previous = self.saved_locations.get(origin.id, {})
                if previous.get("signature") != signature:
                    previous = {}
                zone_source = per_zone.get(origin.id, {})
                nearby, found_count = await self.hass.async_add_executor_job(
                    candidates,
                    zone_source.get("points", self.points),
                    origin,
                    self.options["radius_km"],
                    max(self.options["candidate_limit"], self.options["nearby_limit"]),
                )
                selected = nearby[: self.options["candidate_limit"]]
                nearby_points = [
                    {"shelter": point.as_dict(), "straight_distance_m": round(distance, 1)}
                    for distance, point in nearby[: self.options["nearby_limit"]]
                ]
                selected_ids = [point.id for _, point in selected]
                selected_keys = [f"{point.id}|{point.latitude}|{point.longitude}" for _, point in selected]
                calculated = valid_timestamp(previous.get("routes_updated_at"))
                recent = calculated and now - datetime.fromisoformat(calculated) < timedelta(
                    hours=self.options["update_hours"]
                )
                reuse = (
                    not self.force_routes
                    and recent
                    and previous.get("selected_keys") == selected_keys
                    and not previous.get("routing_error")
                    and previous.get("routes")
                )
                if reuse:
                    point_map = {p.id: p.as_dict() for _, p in selected}
                    routes = [{**r, "shelter": point_map[r["shelter"]["id"]]} for r in previous["routes"]]
                    unrouted = previous.get("unrouted", [])
                    routing_error = None
                    routes_updated_at = previous["routes_updated_at"]
                else:
                    routes, unrouted, routing_error, circuit_open = await plan_routes(
                        self.router,
                        origin,
                        selected,
                        self.options["max_routes"],
                        previous.get("routes", []),
                        circuit_open,
                    )
                    routes_updated_at = (
                        utcnow() if any(r["status"] == "fresh" for r in routes) else previous.get("routes_updated_at")
                    )
                locations[origin.id] = {
                    "source_status": source_status,
                    "source_error": source_error,
                    "points_updated_at": self.points_updated_at,
                    "result_limit_reached": False,
                    "skipped_points": dataset.get("skipped_points", 0),
                    **{key: value for key, value in zone_source.items() if key != "points"},
                    "origin": origin.as_dict(),
                    "signature": signature,
                    "selected_ids": selected_ids,
                    "selected_keys": selected_keys,
                    "found_count": found_count,
                    "nearby": nearby_points,
                    "nearby_limit": self.options["nearby_limit"],
                    "nearby_truncated": found_count > len(nearby_points),
                    "candidate_count": len(selected),
                    "routes": routes,
                    "unrouted": unrouted,
                    "routing_error": routing_error,
                    "routes_updated_at": routes_updated_at,
                }
            self.force_routes = False
            self.saved_locations = locations
            await self._save()
            return {
                "entry_id": self.entry.entry_id,
                "updated_at": utcnow(),
                "points_updated_at": self.points_updated_at,
                "point_count": len(self.points),
                "source_status": source_status,
                "source_error": source_error,
                "origin_errors": origin_errors,
                "source_mode": self.options["source_mode"],
                "dataset": dataset,
                "locations": locations,
            }

    async def _save(self):
        await self.store.async_save(
            {
                "dataset": normalize(ImportResult(self.points, captured_at=self.points_updated_at)),
                "points_updated_at": self.points_updated_at,
                "locations": self.saved_locations,
                "nearby_snapshots": self.nearby_snapshots,
                "source_metadata": self.source_metadata if self.options["source_mode"] == "open_data" else {},
                "source_attempted_at": self.source_attempted_at if self.options["source_mode"] == "open_data" else None,
                "export_error": self.export_error if self.options["source_mode"] == "open_data" else None,
            }
        )

    async def async_import(self, payload):
        if self.options["source_mode"] != "import":
            raise PayloadError("Import w karcie wymaga wybrania źródła: Import w karcie")
        result = await self.hass.async_add_executor_job(parse_payload, payload)
        if not result.points:
            raise PayloadError("Import musi zawierać co najmniej jeden punkt")
        async with self.import_lock:
            self.points = result.points
            self.points_updated_at = valid_timestamp(result.captured_at) or utcnow()
            await self._save()
        self.force_routes = True
        await self.async_refresh()
        return {"imported": len(result.points), "skipped": result.skipped}

    def export(self):
        data = self.data or {}
        locations = {
            key: {k: v for k, v in value.items() if k not in {"signature", "selected_ids", "selected_keys"}}
            for key, value in data.get("locations", {}).items()
        }
        return {**data, "locations": locations}
