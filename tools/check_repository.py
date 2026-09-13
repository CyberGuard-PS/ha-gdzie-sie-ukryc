#!/usr/bin/env python3
"""Check local publication structure, metadata and bundled assets without network access."""

import argparse
import ast
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "gdzie_sie_ukryc"


def check_repository(root=ROOT, allow_template=False):
    integration = root / "custom_components" / DOMAIN
    manifest = json.loads((integration / "manifest.json").read_text(encoding="utf-8"))
    hacs = json.loads((root / "hacs.json").read_text(encoding="utf-8"))
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    const = (integration / "const.py").read_text(encoding="utf-8")
    version = re.search(r'^VERSION = "([^"]+)"$', const, re.MULTILINE).group(1)
    if manifest["domain"] != DOMAIN or manifest["version"] != version or package["version"] != version:
        raise ValueError("Niezgodna domena lub wersje w manifest.json, const.py i package.json")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Wersja musi mieć format X.Y.Z")
    required = {"domain", "documentation", "issue_tracker", "codeowners", "name", "version"}
    if not required.issubset(manifest) or not hacs.get("name"):
        raise ValueError("Brak metadanych wymaganych przez HACS")
    if "http" not in manifest["dependencies"] or "websocket_api" not in manifest["dependencies"]:
        raise ValueError("Brak wymaganych zależności HA")
    if not allow_template and "REPLACE_ME" in json.dumps(manifest):
        raise ValueError("Uzupełnij dane projektu: python3 tools/prepare_repository.py TWOJ_LOGIN")
    if manifest["issue_tracker"] != manifest["documentation"].rstrip("/") + "/issues":
        raise ValueError("Adres zgłoszeń nie odpowiada repozytorium dokumentacji")
    if not manifest["codeowners"] or any(not item.startswith("@") for item in manifest["codeowners"]):
        raise ValueError("Brak opiekuna kodu GitHub")
    directories = sorted(
        p.name for p in (root / "custom_components").iterdir() if p.is_dir() and not p.name.startswith("_")
    )
    if directories != [DOMAIN]:
        raise ValueError("HACS wymaga jednej integracji w custom_components")
    for relative in [
        "frontend/gdzie-sie-ukryc-card.js",
        "frontend/vendor/leaflet.js",
        "frontend/vendor/leaflet.css",
        "frontend/vendor/LICENSE",
        "brand/icon.svg",
        "LICENSE",
    ]:
        if not (integration / relative).is_file():
            raise ValueError(f"Brak dołączonego zasobu: {relative}")
    for filename, size in [("icon.png", 256), ("icon@2x.png", 512)]:
        image = (integration / "brand" / filename).read_bytes()
        if image[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack(">II", image[16:24]) != (size, size):
            raise ValueError(f"Nieprawidłowa ikona: {filename}")
    for path in root.rglob("*.py"):
        if not any(item in path.parts for item in ("node_modules", ".venv", "venv")):
            ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 12))
    for path in integration.rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    if json.loads((integration / "strings.json").read_text(encoding="utf-8")) != json.loads(
        (integration / "translations/pl.json").read_text(encoding="utf-8")
    ):
        raise ValueError("Niezgodne polskie tłumaczenia")
    for path in root.rglob("*"):
        if path.is_file() and (path.suffix.lower() == ".har" or path.name.startswith("punkty-z-har")):
            raise ValueError("Usuń prywatne dane HAR z katalogu repozytorium")
    return version


def main():
    parser = argparse.ArgumentParser(description="Sprawdź pliki i metadane przed publikacją na GitHubie.")
    parser.add_argument(
        "--allow-template", action="store_true", help="Sprawdź szablon bez ustalonego jeszcze loginu GitHub"
    )
    args = parser.parse_args()
    try:
        version = check_repository(allow_template=args.allow_template)
    except (ValueError, KeyError, OSError, AttributeError) as err:
        parser.exit(1, f"Błąd: {err}\n")
    print(f"Struktura repozytorium {version}: OK")


if __name__ == "__main__":
    main()
