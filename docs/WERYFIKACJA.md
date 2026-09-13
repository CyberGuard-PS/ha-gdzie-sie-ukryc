# Weryfikacja wersji 1.3.0

Wykonano 13.09.2026. Zakres: pełny eksport PSP, integracja, zapis lokalny, importer i karta. Nie wykonywano zmian w instalacji HA użytkownika ani pushu do jego repozytorium.

## Pełne opublikowane dane

Źródło potwierdzono w oficjalnych metadanych [zbioru PSP, ID 28058](https://api.dane.gov.pl/1.4/datasets/28058,punkty-schronienia-w-polsce) oraz [zasobu CSV, ID 1393918](https://api.dane.gov.pl/1.4/resources/1393918,punkty-schronienia-dane-csv). Wydawca: Komenda Główna PSP; licencja CC BY 4.0; deklarowana aktualizacja co tydzień. Końcowy, opublikowany URL: `https://gdziesieukryc.pl/PS_XML/punkty_schronienia.csv`.

Wykonano zwykłe pobranie opublikowanego CSV oraz próbę nowym `OpenDataClient` z sesją utworzoną przez Home Assistant 2026.9.2. Obie próby zwróciły **HTTP 200** i identyczną treść. Sesja HA zachowała standardowy User-Agent Home Assistant. Środowisko testowe wymaga sieciowego proxy, dlatego w tej jednorazowej próbie włączono odczyt ustawień proxy środowiska; kod integracji korzysta ze zwykłej wspólnej sesji HA. Nie kopiowano cookies ani nagłówków z HAR i nie odtwarzano CAPTCHA.

| Właściwość CSV | Wynik |
| --- | --- |
| Rozmiar | 15 077 217 bajtów |
| Format | UTF-8 z BOM, przecinki, 11 kolumn |
| Wiersze danych | 85 739 |
| Poprawne, unikalne punkty | 85 739 |
| Pominięte rekordy | 0 |
| Powtórzone identyfikatory | 0 |
| ETag w próbie sesji HA | `W/"e60f61-1a096acda20"` |
| Last-Modified w próbie sesji HA | `Sat, 12 Sep 2026 17:31:45 GMT` |

Suma SHA-256 oraz atrybucja są w `datasets/snapshot.json` i `DATA_LICENSE.md`. Opis katalogu podaje 85 853 rekordy i datę danych 07.09.2026; faktyczny pobrany CSV ma 85 739. Parser nie pominął żadnego rekordu. Nie zakładamy, że eksport jest w każdej chwili identyczny z wewnętrzną bazą mapy strony.

## Testy

| Element | Wynik i zakres |
| --- | --- |
| Home Assistant | Rzeczywisty Core 2026.9.2, Python 3.14.7 |
| Testy Python | **50 przechodzących testów** |
| Karta mapy | **7 przechodzących testów DOM**, jsdom 30.0.1, dołączony Leaflet 1.9.4 |
| Pierwsze uruchomienie z błędem eksportu | Kontrolowane 403: rzeczywisty dołączony CSV z ponad 85 tys. punktów pozostaje dostępny |
| Cała baza i wiele stref | Jeden pobrany zbiór dla dwóch odległych stref; 301 znalezionych punktów przy domu testowym i 1 w drugiej strefie; 8 sensorów |
| Zmiana lokalizacji | Przeniesienie strefy wyszukuje w pełnym zbiorze bez nowego pobrania przed okresem odświeżania |
| 304 i błędy | 304 zachowuje bazę i datę jej pozyskania; 503 zachowuje ostatni pełny zbiór |
| Trwały zapis | Odładowanie i ponowne załadowanie wpisu przywraca pełny zbiór oraz błąd bez przedwczesnego pobierania |
| Migracja | Wpis starego trybu PSP przechodzi do pełnego CSV, zachowując strefy i promień 50 km |
| HTTP eksportu | Lokalny serwer: 200 / 304 / 403 / 302, nagłówki warunkowe, limit rozmiaru, brak parametrów lokalizacji, brak cookies i Authorization |
| CSV | Ponad 250 punktów, zaobserwowane nagłówki, BOM, pola z przecinkiem; błędne UTF-8, HTML, współrzędne, sprzeczne i identyczne duplikaty |
| Pełny JSON | Rzeczywisty loader lokalnego pliku HA wczytał wszystkie 85 739 punktów z pliku około 23 MB; wszystkie równe wynikowi CSV |
| Karta pełnej bazy | Licznik całego zbioru i okolicy, atrybucja CC BY 4.0, częstotliwość publikacji, dane dołączone i błąd bez ukrywania zapisanych tras |
| Dotychczasowe funkcje | Import JSON / GeoJSON / HAR, plik, opcje, trasy, sensory, stary klient nearby i osobne zapisy obszarów |
| Zasoby HA i Lovelace | Rzeczywisty HTTP HA, karta JS, Leaflet JS/CSS, ograniczenie do katalogu frontend; migracja zasobu UI, brak duplikatów i tryb YAML |
| Kontrole statyczne | Ruff check i format, składnia JavaScript, struktura repozytorium, JSON i 8 plików YAML |

Testy automatyczne używają rzeczywistych obiektów HA, platform i plików Store. Sieć, odpowiedzi źródła i geometrie tras są kontrolowane, aby sprawdzić błędy i przeładowania bez ruchu do publicznych usług. Wyliczanie interfejsów i mDNS hosta testowego zastąpiono atrapami. Pobranie produkcyjnego CSV było osobną, opisaną powyżej próbą.

W poprzednim etapie sprawdzono prawdziwe zapytania do pieszej usługi FOSSGIS: HTTP 200 / Ok. Przy zmianie źródła danych nie powtarzano zapytań OSRM, ponieważ kod wyznaczania tras pozostał bez zmian. Podgląd `tests/browser_fixture.html` zawiera jawnie oznaczone fikcyjne punkty i geometrię wcześniejszych próbnych tras.

## Granice weryfikacji

- Nie sprawdzono połączenia z hosta HA użytkownika. Udane pobranie w środowisku testowym nie gwarantuje dostępu z każdego adresu IP; pełna dołączona baza jest dostępna także wtedy, gdy pobranie się nie powiedzie.
- Nie potwierdzono opublikowania plików na GitHubie ani wyniku zdalnego walidatora HACS. Workflowy i metadane są gotowe dla repozytorium CyberGuard-PS/ha-gdzie-sie-ukryc.
- Testy DOM sprawdzają zawartość i geometrie SVG, bez wizualnej oceny panelu HA lub aplikacji iOS.
- Nie potwierdzono dostępności obiektów, wejść ani bezpieczeństwa dojścia w terenie. Zbiór opisuje punkty schronienia, nie wyłącznie formalne schrony.
- Zapis punktów i tras nie zapewnia kafelkowego podkładu offline.

## Powtórzenie testów

W oddzielnym środowisku Python 3.14:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
ruff check custom_components tools tests
ruff format --check custom_components tools tests
python tools/check_repository.py
node --check custom_components/gdzie_sie_ukryc/frontend/gdzie-sie-ukryc-card.js
npm ci
npm run test:card
```

Podgląd z danymi testowymi: uruchom `python3 -m http.server 8765` z katalogu repozytorium i otwórz `http://localhost:8765/tests/browser_fixture.html`.
