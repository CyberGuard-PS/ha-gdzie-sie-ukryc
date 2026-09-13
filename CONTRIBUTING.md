# Współtworzenie

Do uruchomienia integracji nie instaluj narzędzi deweloperskich na produkcyjnym HA.

Testy wykorzystują Core 2026.9.2 i Python 3.14. W osobnym środowisku:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff check custom_components tools tests
ruff format --check custom_components tools tests
PYTHONPATH=. python -m pytest -q
npm ci
npm run test:card
```

Przed pierwszą publikacją uzupełnij repozytorium przez `tools/prepare_repository.py` według `docs/PUBLIKACJA_GITHUB.md`. Następnie uruchom `python tools/check_repository.py`.

Testy nie łączą się z produkcyjnym PSP. Zachowaj tę zasadę w nowych testach, korzystając z fikcyjnych punktów o takim samym schemacie. Nie zapisuj w repozytorium adresów domowych, pełnych HAR ani tokenów.

Zmianę wersji zastosuj w `manifest.json`, `const.py`, `package.json`, komentarzu karty i przykładach zasobów. Wydanie GitHub ma tag `vX.Y.Z` zgodny z manifestem. Zachowaj licencję biblioteki Leaflet i jej atrybucję.
