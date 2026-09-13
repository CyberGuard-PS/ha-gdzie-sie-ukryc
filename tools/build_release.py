#!/usr/bin/env python3
"""Build an installable release ZIP containing the entire integration and card."""

import argparse
import zipfile
from pathlib import Path

from check_repository import DOMAIN, ROOT, check_repository


def build_release(output: Path, tag=None):
    version = check_repository()
    if tag and tag != f"v{version}":
        raise ValueError(f"Tag wydania musi odpowiadać manifestowi: v{version}")
    integration = ROOT / "custom_components" / DOMAIN
    output = output.resolve()
    if output.is_relative_to(integration):
        raise ValueError("ZIP nie może znajdować się wewnątrz integracji")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(integration.rglob("*")):
            if not path.is_file() or any(
                part.startswith(".") or part == "__pycache__" for part in path.relative_to(integration).parts
            ):
                continue
            if path.suffix in {".pyc", ".har"}:
                continue
            archive.write(path, path.relative_to(ROOT))
    print(f"Wydanie {version}: {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description="Zbuduj ZIP do dołączenia do GitHub Release.")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/gdzie_sie_ukryc.zip")
    parser.add_argument("--tag", help="Opcjonalna kontrola zgodności tagu, np. v1.2.0")
    args = parser.parse_args()
    try:
        build_release(args.output, args.tag)
    except (ValueError, KeyError, OSError, AttributeError) as err:
        parser.exit(1, f"Błąd: {err}\n")


if __name__ == "__main__":
    main()
