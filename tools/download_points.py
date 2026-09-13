#!/usr/bin/env python3
"""Download the public PSP CSV and convert it with Python 3.10+ standard library."""

import argparse
import hashlib
import importlib
import json
import sys
import types
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("gsu_download")
package.__path__ = [str(ROOT / "custom_components/gdzie_sie_ukryc")]
sys.modules[package.__name__] = package
const = importlib.import_module("gsu_download.const")
data = importlib.import_module("gsu_download.data")
csv_data = importlib.import_module("gsu_download.csv_data")


def main():
    parser = argparse.ArgumentParser(
        description="Pobierz pełny publiczny eksport CSV PSP. Bez przeglądarki i logowania."
    )
    parser.add_argument("output", type=Path, nargs="?", default=ROOT / "export/punkty-schronienia.json")
    parser.add_argument(
        "--update-bundled", action="store_true", help="Zaktualizuj także CSV i metadane bazy dołączonej do integracji"
    )
    args = parser.parse_args()
    try:
        with urllib.request.urlopen(const.PSP_EXPORT_URL, timeout=45) as response:
            body = response.read(const.MAX_CSV_BYTES + 1)
            if len(body) > const.MAX_CSV_BYTES:
                raise ValueError("Eksport przekracza 32 MiB")
        imported = csv_data.parse_csv(body)
        metadata = {
            "provider": "psp_open_data",
            "publisher": "Komenda Główna Państwowej Straży Pożarnej",
            "source_url": const.PSP_EXPORT_URL,
            "catalog_url": const.OPEN_DATA_URL,
            "license": "CC BY 4.0",
            "license_url": const.DATA_LICENSE_URL,
            "update_frequency": "Co tydzień",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(body).hexdigest(),
            "point_count": len(imported.points),
            "total_rows": imported.total_rows,
            "skipped_points": imported.skipped,
            "duplicate_ids": imported.duplicates,
        }
        output = data.normalize(data.ImportResult(imported.points, imported.skipped, metadata["captured_at"]))
        output["attribution"] = {
            **metadata,
            "changes": "Normalizacja pól i walidacja współrzędnych na potrzeby mapy Home Assistant.",
        }
        encoded = json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n"
        if len(encoded.encode()) > const.MAX_DATASET_BYTES:
            raise ValueError("Wynik JSON przekracza 64 MiB")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        if args.update_bundled:
            directory = ROOT / "custom_components/gdzie_sie_ukryc/datasets"
            directory.mkdir(exist_ok=True)
            (directory / "psp-punkty.csv").write_bytes(body)
            (directory / "snapshot.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(
            f"Zapisano {len(imported.points)} punktów. Wiersze: {imported.total_rows}; błędne: {imported.skipped}; duplikaty ID: {imported.duplicates}."
        )
    except (OSError, urllib.error.URLError, ValueError, TimeoutError) as err:
        parser.exit(1, f"Błąd: {err}\n")


if __name__ == "__main__":
    main()
