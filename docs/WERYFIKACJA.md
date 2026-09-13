# Weryfikacja wersji 1.2.0

Wykonano 13.09.2026. Weryfikacja obejmuje automatyczne źródło, integrację, importer i kartę. Nie potwierdza fizycznej dostępności obiektów ani tras z rzeczywistego domu użytkownika.

## Dane potwierdzone na zapisie działania strony

- Aplikacja PSP: wersja 1.3.74, zapisana odpowiedź `/api/version`.
- `GET /api/shelters/nearby`: HTTP 200, odpowiedź `application/json`, 250 elementów w `data`, `count: 250`, `source: local`.
- Zaobserwowane parametry: `lat`, `lng`, `radius=12000`, `limit=250`. Dokładnych współrzędnych środka wyszukiwania nie umieszczono w dokumentacji ani kodzie.
- W żądaniu listy brak cookies i nagłówka `Authorization`; kod integracji nie kopiuje nagłówków z HAR.
- Zapisany JavaScript buduje ten sam GET przez `URLSearchParams`. Kod wersji mobilnej stosuje m.in. promienie 3000 i 5000 metrów, a wersji desktopowej 12000 metrów z limitem 250. Potwierdza to jednostkę promienia i znaczenie parametrów.
- Odczytano pola `id_publiczny`, `nazwa`, `lokalizacja_lat`, `lokalizacja_lon`, `lokalizacja_adres`, `rodzaj_obiektu`, `dostepnosc`. Lista i szczegóły pojedynczego punktu są zgodne po identyfikatorze publicznym.
- Parser odczytał wszystkie 250 rzeczywistych punktów; 0 rekordów pominiętych. Oddzielnie sprawdzono zarówno dedykowany parser automatycznego źródła, jak i importer całego HAR.
- Zapytanie strony zwróciło wyniki w kolejności rosnącej według `dystans_metry`. Integracja niezależnie wylicza i sortuje odległości od stref HA.

To obserwacja konkretnego działania strony, a nie gwarantowany kontrakt publicznego API. Nie ustalono mechanizmu stronicowania ani nie pobierano całej bazy. Limit 250 w integracji wynika z obserwowanego żądania; nie jest deklaracją maksymalnego limitu po stronie PSP.

## Testy kodu

| Element | Wynik i zakres |
| --- | --- |
| Home Assistant | Rzeczywisty Core 2026.9.2, Python 3.14.7 w oddzielnym środowisku |
| Testy Python | 39 przechodzących testów |
| Automatyczna konfiguracja HA | Domyślne źródło PSP, utworzenie wpisu i encji, pobranie dla dwóch odległych stref, po 2 trasy z 3 kandydatów |
| Trwały zapis | Odładowanie i ponowne załadowanie wpisu przywraca punkty i geometrie; przed terminem odświeżenia nie powtarza zapytań |
| Awaria PSP i silnika tras | Kontrolowane 403/503 zachowują poprzednie dane; po jednym błędzie usługi dalsze zapytania w cyklu są wstrzymane |
| Zmiana miejsca | Przeniesienie strefy przy niedostępnym PSP nie używa punktów ani tras poprzedniego obszaru; druga strefa zachowuje własne dane |
| Strefy HA | Zmiana liczby osób bez zmiany współrzędnych nie wywołuje odświeżenia |
| Pusta odpowiedź | Poprawne `data: []`, `count: 0` usuwa stare punkty; nieznany format odpowiedzi jest błędem, a nie pustym wynikiem |
| Klient HTTP PSP | Lokalny serwer aiohttp potwierdza ścieżkę, kolejność lat/lng, promień w metrach, limit 250 i brak cookies/autoryzacji |
| Limit i uszkodzone dane | Test 250 rekordów z jednym błędnym ujawnia osiągnięcie limitu i liczbę pominiętych punktów |
| Dotychczasowe funkcje | Import JSON/GeoJSON/HAR, lokalny plik, 8 sensorów dla 2 stref, opcje, zapis i przywrócenie tras |
| Karta mapy | 6 testów DOM z jsdom 30.0.1 i rzeczywistą biblioteką Leaflet 1.9.4 |
| Zasoby HTTP HA | Rzeczywisty serwer HA zwraca kartę JS, Leaflet JS i CSS; nie udostępnia plików integracji spoza katalogu frontend |
| Zasoby Lovelace | Rzeczywista kolekcja HA: nowy wpis, migracja starego URL, brak duplikatów, zachowanie innych kart i usunięcie zasobu przy usunięciu integracji |
| Tryb YAML | Integracja nie zmienia zasobów YAML; przykład nowego URL dołączono w repozytorium |
| Narzędzia publikacji | Skrypt przygotowania metadanych, lokalna walidacja struktury i budowa ZIP wydania sprawdzone w osobnej kopii repozytorium |
| Tryb automatyczny karty | Osobne statusy i daty stref, brak daty przy błędzie nowego obszaru, limit 250, brak przycisku importu, pusta odpowiedź i ręczne odświeżenie |
| Trasy i karta | Ścieżki SVG, wybór stref, przybliżenie trasy, nawigacja piesza Apple/Google, cache, bezpieczne wyświetlanie tekstu i ponowne podłączenie karty |
| Kontrole statyczne | Ruff, składnia JavaScript, składnia Python i pliki JSON |
| Importer samodzielny | Python bez HA: konwersja przesłanego HAR do 250 datowanych punktów |

W testach cyklu życia użyto rzeczywistych obiektów HA, platform i plików Store. Wyliczanie interfejsów i multicast DNS hosta testowego zastąpiono atrapami. Odpowiedzi PSP oraz geometrię tras kontrolują testy, aby sprawdzić również awarie i zmiany obszaru. Test klienta HTTP uruchamia lokalny serwer. Żaden test automatyczny nie łączy się z produkcyjnym PSP ani instalacją użytkownika.

W poprzednim etapie wykonano rzeczywiste próbne zapytania do publicznego silnika pieszych tras FOSSGIS: HTTP 200 / `Ok`, m.in. 324,4 m i 259,6 s. Plik podglądu zawiera geometrię próbnych tras i jawnie oznaczone fikcyjne punkty. Przy tej zmianie dostawcy punktów nie powtarzano zapytań OSRM, ponieważ implementacja obliczania tras nie uległa zmianie.

GitHub Actions są przygotowane do uruchomienia po publikacji. Nie wykonano ich w zdalnym repozytorium ani oficjalnej walidacji HACS, ponieważ adres repozytorium i jego właściciel zostaną uzupełnione przez wydawcę. Sprawdzono składnię YAML workflowów lokalnie.

## Granice weryfikacji

- Dostęp bezpośrednio z hosta HA użytkownika nie został sprawdzony. Wcześniejsze połączenia z tego środowiska były blokowane kodem 403. Udane żądanie potwierdzone jest w przesłanym HAR; nie odtwarzano cookies ani weryfikacji bezpieczeństwa.
- Wyglądu w rzeczywistej przeglądarce HA i aplikacji iOS nie zweryfikowano wizualnie. Dostępna przeglądarka odrzucała lokalny podgląd (`ERR_BLOCKED_BY_CLIENT`). Testy DOM sprawdzają zawartość i geometrię SVG, nie układ pikseli.
- Nie zainstalowano paczki w HA użytkownika ani nie ustawiono jego lokalizacji domu.
- Deklaracje dostępności obiektu są przepisywane ze źródła, a nie sprawdzane w terenie. Pin nie musi wskazywać wejścia.
- Punkty i geometrie tras są zapisywane na restart; pełny podkład mapy offline nie jest funkcją paczki.

## Powtórzenie testów

W oddzielnym środowisku z Pythonem wymaganym przez Core 2026.9.2:

```bash
python -m pip install homeassistant==2026.9.2 pytest pytest-asyncio ruff
PYTHONPATH=. python -m pytest -q
ruff check custom_components tools tests
node --check custom_components/gdzie_sie_ukryc/frontend/gdzie-sie-ukryc-card.js
npm ci
npm run test:card
```

Ręczny podgląd karty: uruchom `python3 -m http.server 8765` z katalogu paczki i otwórz `http://localhost:8765/tests/browser_fixture.html`. Dane podglądu są testowe. Publiczne repozytorium nie zawiera HAR ani rzeczywistych danych punktów.
