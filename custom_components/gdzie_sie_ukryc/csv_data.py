"""Stream records from the officially published full-country PSP CSV, offline."""

import csv
import io
import unicodedata
from dataclasses import dataclass

from .const import MAX_CSV_BYTES, MAX_POINTS
from .data import PayloadError, parse_point
from .models import Shelter


@dataclass
class CSVResult:
    points: list[Shelter]
    total_rows: int
    skipped: int
    duplicates: int


def _header(value):
    plain = unicodedata.normalize("NFKD", value.strip().lower().replace("ł", "l"))
    return " ".join("".join(c for c in plain if not unicodedata.combining(c)).replace("_", " ").split())


def parse_csv(body: bytes) -> CSVResult:
    """Keep public IDs, validate WGS84, report invalid records and duplicate IDs."""
    if len(body) > MAX_CSV_BYTES:
        raise PayloadError("Eksport CSV przekracza 32 MiB")
    try:
        text = body.decode("utf-8-sig")
    except UnicodeError as err:
        raise PayloadError("Eksport CSV PSP nie jest poprawnym plikiem UTF-8") from err
    aliases = {
        "id_publiczny": {"identyfikator publiczny", "id publiczny"},
        "nazwa": {"nazwa", "name"},
        "rodzaj_obiektu": {"rodzaj obiektu"},
        "lokalizacja_lat": {"szerokosc geograficzna", "lokalizacja lat", "latitude"},
        "lokalizacja_lon": {"dlugosc geograficzna", "lokalizacja lon", "longitude"},
        "lokalizacja_adres": {"adres", "lokalizacja adres", "address"},
        "dostepnosc": {"dostepnosc", "availability"},
    }
    points, total, skipped, duplicates = {}, 0, 0, 0
    try:
        # The published export uses commas; also accept semicolon-separated UTF-8 CSV.
        first_line = text.split("\n", 1)[0]
        delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
        reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        if not reader.fieldnames:
            raise PayloadError("Eksport CSV PSP jest pusty")
        mapping = {
            field: next((name for name in reader.fieldnames if _header(name) in names), None)
            for field, names in aliases.items()
        }
        if any(mapping[key] is None for key in ("id_publiczny", "lokalizacja_lat", "lokalizacja_lon")):
            raise PayloadError("Eksport CSV PSP: nieznany format nagłówka (możliwa odpowiedź HTML)")
        for row in reader:
            total += 1
            if total > MAX_POINTS:
                raise PayloadError(f"Eksport CSV przekracza {MAX_POINTS} rekordów")
            try:
                if None in row or not row.get(mapping["id_publiczny"], "").strip():
                    raise ValueError("Invalid CSV row or missing public ID")
                record = {key: row[name] for key, name in mapping.items() if name is not None}
                point = parse_point(record)
                if point.id in points:
                    duplicates += 1
                    if points[point.id] != point:
                        raise PayloadError("Eksport CSV PSP zawiera sprzeczne rekordy dla tego samego identyfikatora")
                points[point.id] = point
            except (ValueError, TypeError, OverflowError, AttributeError) as err:
                if isinstance(err, PayloadError):
                    raise
                skipped += 1
    except csv.Error as err:
        raise PayloadError("Niepoprawna struktura eksportu CSV PSP") from err
    if not points:
        raise PayloadError("Eksport CSV PSP nie zawiera poprawnych punktów")
    return CSVResult(list(points.values()), total, skipped, duplicates)
