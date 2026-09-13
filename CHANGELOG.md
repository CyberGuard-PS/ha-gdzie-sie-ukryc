# Historia zmian

## 1.3.0 — 2026-09-13

- Domyślne automatyczne pobieranie pełnego, oficjalnie opublikowanego eksportu CSV PSP.
- Jedno pobranie dla wszystkich stref i wyszukiwanie lokalne bez limitu 250 punktów.
- Dołączona pełna baza 85 739 punktów, używana także przy pierwszym uruchomieniu bez dostępu do eksportu.
- Okresowe sprawdzanie eksportu, obsługa ETag / Last-Modified i zachowanie ostatniej poprawnej pełnej bazy przy błędach.
- Migracja wpisów korzystających ze starego trybu PSP, z zachowaniem stref i promienia.
- Karta i sensory pokazują rozmiar pełnej bazy, jej pochodzenie i czas sprawdzenia.
- Pełny JSON w `export`, konwerter CSV i samodzielny skrypt pobierania dla wydawcy.
- Limit lokalnego JSON zwiększony do 64 MiB; dane PSP na CC BY 4.0 z atrybucją.
- Metadane repozytorium przygotowane dla CyberGuard-PS/ha-gdzie-sie-ukryc.

## 1.2.0 — 2026-09-13

- Układ repozytorium przeznaczony do instalacji jako integracja HACS.
- Karta i lokalna biblioteka Leaflet w katalogu integracji.
- Udostępnianie zasobów przez HA i automatyczne dodawanie lub aktualizowanie zasobu Lovelace w trybie UI.
- Migracja adresu karty z wcześniejszych wersji; osobny przykład zasobu dla YAML.
- Ikona, licencje, instrukcje publikacji, GitHub Actions i narzędzia przygotowania metadanych oraz wydania.
- Publiczna paczka zawiera wyłącznie fikcyjne dane testowe.

## 1.1.0 — 2026-09-13

- Automatyczne pobieranie pobliskich punktów przez wewnętrzne żądanie serwisu PSP.
- Osobny zapis punktów dla każdej strefy, kontrola limitu wyników i obsługa awarii.
- Odczyt pól punktów potwierdzonych w zapisie działania aplikacji PSP 1.3.74.

## 1.0.0 — 2026-09-13

- Integracja wielu stref, trasy piesze, karta mapy, sensory i pamięć tras.
- Import JSON/GeoJSON, lokalnego pliku lub feedu.
