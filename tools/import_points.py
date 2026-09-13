#!/usr/bin/env python3
"""Offline converter; Python 3.10+, standard library only, no network access."""

import argparse
import importlib
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Load the pure-Python parser without executing the HA-specific package __init__.
package = types.ModuleType("gsu_import")
package.__path__ = [str(ROOT / "custom_components" / "gdzie_sie_ukryc")]
sys.modules[package.__name__] = package
data = importlib.import_module("gsu_import.data")


def main():
    parser = argparse.ArgumentParser(
        description="Przetwórz odpowiedź JSON/GeoJSON lub HAR z gdziesieukryc.pl do punktów dla HA. Bez dostępu do sieci."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("Plik wejściowy i wyjściowy muszą być różne")
        if args.input.stat().st_size > 256 * 1024 * 1024:
            raise ValueError("Plik wejściowy przekracza 256 MiB; zapisz pojedynczą odpowiedź JSON")
        payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
        result = (
            data.parse_har(payload) if isinstance(payload, dict) and "log" in payload else data.parse_payload(payload)
        )
        if not result.points:
            raise ValueError("Brak punktów do importu")
        output = json.dumps(data.normalize(result), ensure_ascii=False, indent=2)
        if len(output.encode()) > 8 * 1024 * 1024:
            # Compact JSON lets a country-wide dataset fit where possible.
            output = json.dumps(data.normalize(result), ensure_ascii=False, separators=(",", ":"))
        if len(output.encode()) > 8 * 1024 * 1024:
            raise ValueError("Wynik przekracza 8 MiB. Zapisz dane ograniczone do obszarów wybranych lokalizacji")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
        print(f"Zapisano {len(result.points)} punktów do {args.output}. Pominięto: {result.skipped}.")
    except (OSError, ValueError, TypeError) as err:
        print(f"Błąd: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
