#!/usr/bin/env python3
"""Set the future GitHub repository identity without using the network."""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components/gdzie_sie_ukryc/manifest.json"


def github_owner(value):
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", value):
        raise argparse.ArgumentTypeError("Podaj login lub nazwę organizacji GitHub, bez URL i znaku @")
    return value


def repository_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
        raise argparse.ArgumentTypeError("Podaj samą nazwę repozytorium GitHub")
    return value


def configure(owner, repository, codeowner):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    old_url = manifest["documentation"].rstrip("/")
    new_url = f"https://github.com/{owner}/{repository}"
    old_repo = old_url.removeprefix("https://github.com/")
    new_repo = f"{owner}/{repository}"
    manifest.update(documentation=new_url, issue_tracker=f"{new_url}/issues", codeowners=[f"@{codeowner}"])
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for relative in ("README.md", ".github/ISSUE_TEMPLATE/config.yml"):
        path = ROOT / relative
        path.write_text(path.read_text(encoding="utf-8").replace(old_repo, new_repo), encoding="utf-8")
    (ROOT / ".github/CODEOWNERS").write_text(f"* @{codeowner}\n", encoding="utf-8")
    return new_url


def main():
    parser = argparse.ArgumentParser(
        description="Uzupełnij login GitHub, adresy projektu i CODEOWNERS przed publikacją."
    )
    parser.add_argument("owner", type=github_owner, help="Twój login lub organizacja GitHub")
    parser.add_argument("--repository", default="ha-gdzie-sie-ukryc", type=repository_name)
    parser.add_argument("--codeowner", type=github_owner, help="Login opiekuna kodu (domyślnie owner)")
    args = parser.parse_args()
    print("Repozytorium przygotowane:", configure(args.owner, args.repository, args.codeowner or args.owner))
    print("Sprawdź instrukcję docs/PUBLIKACJA_GITHUB.md i prześlij pliki do tego repozytorium.")


if __name__ == "__main__":
    main()
