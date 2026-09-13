# Weryfikacja wersji 1.5.0

Wykonano 13.09.2026. Zakres: trasa z bieżącej pozycji urządzenia, pełny eksport PSP, integracja, zapis lokalny, importer i karta. Nie wykonywano zmian w instalacji HA użytkownika ani pushu do jego repozytorium.

## Trasa z urządzenia — wersja 1.5

Nowe testy użyły rzeczywistego serwera HTTP i WebSocket HA 2026.9.2, prawdziwego uwierzytelniania i dwóch użytkowników bez praw administratora. Potwierdzono:

- Żądanie bez uwierzytelnienia jest odrzucone, a zwykli zalogowani użytkownicy otrzymują trasę do wybranego punktu. Serwer pobiera cel z aktualnego zbioru po publicznym identyfikatorze.
- Dwa jednoczesne żądania mają różne pozycje początku i otrzymują odpowiadające im geometrie. Można wskazać punkt z pełnej bazy, także poza obecnym obszarem domu.
- Wyniki i sensory stref, encje mapy, eksport karty i zawartość pliku Store integracji pozostają identyczne po wyznaczeniu jednorazowych tras. Pozycja urządzenia nie staje się wspólną lokalizacją HA.
- Nieprawidłowe współrzędne, wartości logiczne, brak punktu, brak wpisu i próba podania innego adresu silnika lub własnych współrzędnych celu są odrzucane. Błąd silnika HTTP 503 zwraca błąd trasy i zachowuje trasy stref.
- Test lokalnego serwera z dwoma równoczesnymi klientami `WalkingRouter` na wspólnej sesji potwierdził odstęp co najmniej sekundy między próbami do tego samego hosta.

Testy DOM rzeczywistej karty i dołączonego Leaflet potwierdziły przycisk w dymku i na liście, użycie współrzędnych przeglądarki zamiast strefy, `maximumAge: 0`, wysoką dokładność i timeout 20 s. Nie ma żądania położenia przy samym otwarciu karty. Trasa z urządzenia działa także bez gotowych tras strefy.

Sprawdzono różowy przebieg SVG, marker J, dokładność i jej okrąg, czas odczytu, długość i czas dojścia, ponowny odczyt pozycji, poprawne początki i cele Google Maps / Apple Maps, osobne przerywane odcinki dojścia do sieci dróg i brak podwójnego markera celu. Odmowa dostępu, niedostępna lokalizacja, timeout, niezaufany kontekst HTTP, brak Geolocation API i awaria silnika pozostawiają punkty i trasy stref. Linki awaryjne przekazują cel i tryb pieszy, bez narzucenia strefy jako początku.

Starsze odpowiedzi GPS i WebSocket po zmianie celu są ignorowane. Zamknięcie, odłączenie karty i zmiana strefy usuwają trasę urządzenia; odświeżenie danych zachowuje własny pomiar z jego czasem. Dwa widoki karty mają niezależne początki i przebiegi.

Zasady odczytu pozycji sprawdzono w [dokumentacji Geolocation API](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition), uwierzytelnianie w [dokumentacji WebSocket HA](https://developers.home-assistant.io/docs/api/websocket/), a limit i logowanie żądań w [zasadach FOSSGIS](https://routing.openstreetmap.de/about.html).

## Punkty na mapie HA i lista okolicy

Zrzut dostarczony przy zgłoszeniu pokazuje wybraną wbudowaną zakładkę Mapa HA. Wersja 1.3 udostępniała sensory i własną kartę, ale nie tworzyła encji punktów `geo_location` dla tej mapy.

W 1.4 dodano platformę `geo_location`, osobne pobliskie punkty w danych karty i listę nazw oraz adresów. Domyślnie widocznych jest 100 najbliższych punktów na strefę, z opcją 30–500. Pełny zbiór i licznik wszystkich punktów w promieniu nie są ograniczane przez tę opcję.

Nowy test z rzeczywistym HA potwierdził:

- Przy 83 fikcyjnych punktach, 3 strefach i awarii silnika tras HTTP 503 powstały **33 encje mapy**: 30 wspólnych dla dwóch nakładających się stref i 3 w drugim mieście. Geometrie tras były puste, a punkty pozostały dostępne.
- Encje mają numeryczne współrzędne, źródło `gdzie_sie_ukryc`, nazwę i adres, stabilny identyfikator i informacje o strefach. Stan geolokalizacji mierzy odległość od domu HA, osobny atrybut mierzy odległość od najbliższej wybranej strefy.
- Zmiana nazwy i adresu aktualizuje istniejącą encję bez zmiany jej tożsamości.
- Przeniesienie stref usuwa stare punkty ze stanów i rejestru encji; wspólne punkty w nowym obszarze nie są duplikowane.
- Błąd źródła zachowuje znane punkty; odładowanie i ponowne załadowanie przywraca aktualny widok z zapisanej bazy. Poprawne puste źródło usuwa punkty oraz ich rejestracje.

Nowe testy DOM rzeczywistej karty i Leaflet potwierdziły **45 markerów punktów bez żadnej trasy**, nazwy i adresy w liście oraz dymkach, bezpieczne wyświetlanie tekstu, przybliżanie punktu, nawigację, rozwijanie listy 20 / 40 / 45 pozycji oraz zmianę strefy. Oddzielny przypadek z trasami potwierdził brak podwójnych markerów dla punktów występujących także w liście.

Sprawdzono również zachowanie oryginalnych bajtów CSV po `git add` i odtworzeniu z indeksu przy `core.autocrlf=true`. Reguła binarna w `.gitattributes` zachowała sumę SHA-256 i 85 740 zakończeń CRLF, w tym wiersz nagłówka.

Zasady mapy oraz platformy potwierdzono w [oficjalnej dokumentacji mapy HA](https://www.home-assistant.io/dashboards/map/) i [encjach geolokalizacji](https://developers.home-assistant.io/docs/core/entity/geo-location/). Wbudowana mapa wyświetla markery; geometrie pieszych tras i listę okolicy udostępnia własna karta integracji.

## Pełne opublikowane dane

Źródło potwierdzono w oficjalnych metadanych [zbioru PSP, ID 28058](https://api.dane.gov.pl/1.4/datasets/28058,punkty-schronienia-w-polsce) oraz [zasobu CSV, ID 1393918](https://api.dane.gov.pl/1.4/resources/1393918,punkty-schronienia-dane-csv). Wydawca: Komenda Główna PSP; licencja CC BY 4.0; deklarowana aktualizacja co tydzień. Końcowy, opublikowany URL: `https://gdziesieukryc.pl/PS_XML/punkty_schronienia.csv`.

W etapie 1.3 tego samego dnia wykonano zwykłe pobranie opublikowanego CSV oraz próbę nowym `OpenDataClient` z sesją utworzoną przez Home Assistant 2026.9.2. Obie próby zwróciły **HTTP 200** i identyczną treść. Sesja HA zachowała standardowy User-Agent Home Assistant. Środowisko testowe wymaga sieciowego proxy, dlatego w tej jednorazowej próbie włączono odczyt ustawień proxy środowiska; kod integracji korzysta ze zwykłej wspólnej sesji HA. Nie kopiowano cookies ani nagłówków z HAR i nie odtwarzano CAPTCHA.

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
| Testy Python | **54 przechodzące testy** |
| Karta mapy | **13 przechodzących testów DOM**, jsdom 30.0.1, dołączony Leaflet 1.9.4 |
| Trasa urządzenia 1.5 | Rzeczywiste uwierzytelnione WebSockety, zwykli użytkownicy, niezależne początki, niezmieniony Store i sensory, błędne dane i 503 |
| Położenie i karta 1.5 | Odczyt na kliknięcie, wymaganie HTTPS, zgoda, błędy, wyścigi odpowiedzi, geometria i dokładność, nawigacja, ponowny odczyt i zamknięcie |
| Pierwsze uruchomienie z błędem eksportu | Kontrolowane 403: rzeczywisty dołączony CSV z ponad 85 tys. punktów pozostaje dostępny |
| Cała baza i wiele stref | Jeden pobrany zbiór dla dwóch odległych stref; 301 znalezionych punktów przy domu testowym i 1 w drugiej strefie; 8 sensorów |
| Zmiana lokalizacji | Przeniesienie strefy wyszukuje w pełnym zbiorze bez nowego pobrania przed okresem odświeżania |
| 304 i błędy | 304 zachowuje bazę i datę jej pozyskania; 503 zachowuje ostatni pełny zbiór |
| Trwały zapis | Odładowanie i ponowne załadowanie wpisu przywraca pełny zbiór oraz błąd bez przedwczesnego pobierania |
| Migracja | Wpis starego trybu PSP przechodzi do pełnego CSV, zachowując strefy i promień 50 km |
| HTTP eksportu | Lokalny serwer: 200 / 304 / 403 / 302, nagłówki warunkowe, limit rozmiaru, brak parametrów lokalizacji, brak cookies i Authorization |
| CSV | Ponad 250 punktów, zaobserwowane nagłówki, BOM, pola z przecinkiem; błędne UTF-8, HTML, współrzędne, sprzeczne i identyczne duplikaty |
| Pełny JSON | Rzeczywisty loader lokalnego pliku HA wczytał wszystkie 85 739 punktów z pliku około 23 MB; wszystkie równe wynikowi CSV |
| Punkty i karta 1.4 | Encje mapy bez tras, deduplikacja i usuwanie punktów, lista nazw i adresów, dymki i nawigacja niezależne od OSRM |
| Karta pełnej bazy | Licznik całego zbioru i okolicy, atrybucja CC BY 4.0, częstotliwość publikacji, dane dołączone i błąd bez ukrywania zapisanych tras |
| Dotychczasowe funkcje | Import JSON / GeoJSON / HAR, plik, opcje, trasy, sensory, stary klient nearby i osobne zapisy obszarów |
| Zasoby HA i Lovelace | Rzeczywisty HTTP HA, karta JS, Leaflet JS/CSS, ograniczenie do katalogu frontend; migracja zasobu UI, brak duplikatów i tryb YAML |
| Kontrole statyczne | Ruff check i format, składnia JavaScript, struktura repozytorium, JSON i 9 plików YAML |

Testy automatyczne używają rzeczywistych obiektów HA, platform i plików Store. Sieć, odpowiedzi źródła i geometrie tras są kontrolowane, aby sprawdzić błędy i przeładowania bez ruchu do publicznych usług. Wyliczanie interfejsów i mDNS hosta testowego zastąpiono atrapami. Pobranie produkcyjnego CSV było osobną, opisaną powyżej próbą.

W poprzednim etapie sprawdzono prawdziwe zapytania do pieszej usługi FOSSGIS: HTTP 200 / Ok. W wersji 1.5 dodano wspólną kolejkę i obsługę początku z urządzenia; parametry żądania oraz walidacja odpowiedzi OSRM pozostały zgodne z dotychczasowym klientem. Nową kolejkę sprawdzono lokalnym serwerem, a pozycje urządzeń kontrolowanymi odpowiedziami, bez powtarzania zapytań do publicznej usługi. Podgląd `tests/browser_fixture.html` zawiera jawnie oznaczone fikcyjne punkty, wcześniejsze próbne geometrie i symulację położenia oraz trasy urządzenia; nie odczytuje prawdziwej pozycji odwiedzającego.

## Granice weryfikacji

- Nie sprawdzono połączenia z hosta HA użytkownika. Udane pobranie w środowisku testowym nie gwarantuje dostępu z każdego adresu IP; pełna dołączona baza jest dostępna także wtedy, gdy pobranie się nie powiedzie.
- Nie potwierdzono opublikowania plików na GitHubie ani wyniku zdalnego walidatora HACS. Workflowy i metadane są gotowe dla repozytorium CyberGuard-PS/ha-gdzie-sie-ukryc.
- Testy DOM sprawdzają zawartość i geometrie SVG, bez wizualnej oceny panelu HA lub aplikacji iOS.
- Nie wykonano odczytu rzeczywistej pozycji telefonu w Safari ani widoku Companion. Testy kontrolują Geolocation API; dostęp na urządzeniu wymaga odpowiedniego kontekstu, zgody dla strony lub aplikacji i systemowych usług lokalizacji.
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
