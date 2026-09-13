# Gdzie się ukryć — Home Assistant 1.5.0

Mapa tras pieszych z domu (`zone.home`), dodatkowych stref i bieżącego położenia urządzenia do wybranego punktu schronienia. Domyślnie: promień 5 km, 3 trasy z 12 kandydatów, odświeżanie co 24 godziny. Przycisk **Trasa z mojej lokalizacji** odczytuje położenie telefonu, tabletu lub komputera używanego do otwarcia karty.

**Integracja pobiera automatycznie całą opublikowaną bazę PSP**, korzystając z [oficjalnego eksportu CSV](https://gdziesieukryc.pl/PS_XML/punkty_schronienia.csv) wskazanego w [katalogu dane.gov.pl](https://dane.gov.pl/pl/dataset/28058,punkty-schronienia-w-polsce). Nie wymaga klucza API ani importowania HAR. Jeden plik obsługuje wszystkie strefy; wyszukiwanie w promieniu odbywa się lokalnie, bez limitu 250 wyników.

Dołączona baza pobrana 13.09.2026 zawiera **85 739 poprawnych, unikalnych punktów**. Jest używana również przy pierwszym uruchomieniu, jeśli pobieranie się nie powiedzie. Ostatnia pełna pobrana baza i trasy przetrwają restart HA.

To automatyczne pobieranie aktualnego **eksportu**, a nie natychmiastowa synchronizacja z wewnętrzną bazą strony. PSP deklaruje aktualizację zbioru **co tydzień**; HA domyślnie sprawdza plik co 24 godziny. Opis katalogowy podaje 85 853 rekordy, ale sam pobrany CSV ma 85 739 — wszystkie zostały odczytane, bez odrzuconych rekordów. Szczegóły i atrybucja: [DATA_LICENSE.md](DATA_LICENSE.md).

[Zgłoszenia błędów](https://github.com/CyberGuard-PS/ha-gdzie-sie-ukryc/issues) · [Historia zmian](CHANGELOG.md) · [Publikacja i aktualizacja GitHub](docs/PUBLIKACJA_GITHUB.md) · [Weryfikacja](docs/WERYFIKACJA.md)

## Aktualizacja z 1.0 / 1.1 / 1.2 / 1.3 / 1.4

1. Zaktualizuj przez HACS albo zastąp **cały** katalog `/config/custom_components/gdzie_sie_ukryc` katalogiem z paczki. Musi zawierać również `datasets/psp-punkty.csv` i `datasets/snapshot.json`.
2. Uruchom ponownie Home Assistant.
3. W **Ustawienia → Urządzenia i usługi → Gdzie się ukryć → opcje** wybierz źródło **Cała baza PSP — automatyczny eksport CSV**. Pozostaw wybrane strefy i swój promień, np. 50 km.
4. Ponownie wczytaj panel lub aplikację HA. Wbudowana zakładka **Mapa** pokaże pobliskie punkty. Własna karta poniżej udostępnia także trasy i listę nazw oraz adresów.
5. W opcjach jest nowe pole **Liczba punktów na mapie i liście (na strefę)**. Domyślnie pokazuje 100 najbliższych punktów w Twoim promieniu; zakres 30–500. Pobierana baza i licznik punktów w promieniu pozostają pełne.

Wpis korzystający ze starego trybu PSP jest migrowany automatycznie do pełnego CSV. Import, plik lokalny i własny URL zachowują dotychczasowy wybór; w tych przypadkach przełącz źródło ręcznie. Nie trzeba usuwać wpisu integracji. Stary zapis 250 punktów nie jest używany jako pełna baza Polski.

W zasobach Lovelace zarządzanych przez UI adres karty aktualizuje się automatycznie. Przy zasobach YAML ustaw wersję URL na `v=1.5.0`, jak poniżej. Jeśli aktualizujesz z wersji używającej `/local/gdzie-sie-ukryc/`, zmień także ścieżkę zasobu.

## Instalacja przez HACS

Wymagany Home Assistant **2026.9.0 lub nowszy**. Testy wykonano na rzeczywistym Core 2026.9.2.

1. W **HACS → ⋮ → Repozytoria niestandardowe** dodaj `https://github.com/CyberGuard-PS/ha-gdzie-sie-ukryc`, typ **Integration / Integracja**.
2. Pobierz **Gdzie się ukryć** i uruchom HA ponownie.
3. W **Ustawienia → Urządzenia i usługi → Dodaj integrację** wyszukaj **Gdzie się ukryć**.
4. Pozostaw źródło **Cała baza PSP — automatyczny eksport CSV**, wybierz Dom i ewentualnie inne strefy.
5. Dodaj do panelu kartę:

```yaml
type: custom:gdzie-sie-ukryc-card
title: Gdzie się ukryć
zone: zone.home
map_height: 420
```

Karta i Leaflet są częścią integracji. W trybie zasobów UI moduł Lovelace dodawany jest automatycznie. Po instalacji ponownie wczytaj panel. Nie trzeba osobno instalować karty ani kopiować katalogu `www`.

Gdy zasoby są utrzymywane w YAML, połącz poniższy fragment z istniejącą sekcją `lovelace` w `configuration.yaml`:

```yaml
lovelace:
  resource_mode: yaml
  resources:
    - url: /gdzie_sie_ukryc/frontend/gdzie-sie-ukryc-card.js?v=1.5.0
      type: module
```

Jeśli automatyczne dodanie zasobu UI się nie powiedzie, dodaj ten URL w **Ustawienia → Panele → ⋮ → Zasoby**, typ **Moduł JavaScript**. Nie dodawaj modułu dwukrotnie.

## Instalacja ręczna

Z repozytorium lub paczki skopiuj **cały** `custom_components/gdzie_sie_ukryc` do `/config/custom_components/gdzie_sie_ukryc`. Uruchom HA ponownie i dodaj integrację oraz kartę jak wyżej. `/config` oznacza katalog zawierający `configuration.yaml`. Pozostałych plików repozytorium nie trzeba kopiować do HA. Node.js ani narzędzia deweloperskie nie są wymagane do instalacji.

## Punkty na mapie i nazwy oraz adresy

Od wersji 1.4 integracja tworzy encje **`geo_location`** dla pobliskich punktów. Ich współrzędne pozwalają wyświetlić je we wbudowanej zakładce **Mapa** HA. Nazwa encji łączy nazwę punktu z adresem; informacje są też osobnymi atrybutami `point_name` i `address`. Markery nie wymagają udanej odpowiedzi silnika tras.

Domyślnie publikowanych jest **100 najbliższych punktów na strefę** w ustawionym promieniu. W opcjach możesz wybrać 30–500. Przy nakładających się strefach ten sam publiczny identyfikator tworzy jedną encję. Zmiana strefy, promienia lub bazy aktualizuje punkty i usuwa te, które opuściły wybrany obszar. Ta liczba dotyczy widoku mapy i listy, a nie wielkości pobieranej bazy ani sensora liczby wszystkich punktów w promieniu.

W standardowej karcie HA możesz wskazać źródło:

```yaml
type: map
title: Punkty schronienia
geo_location_sources:
  - gdzie_sie_ukryc
entities:
  - zone.home
auto_fit: true
```

We własnej karcie `custom:gdzie-sie-ukryc-card` dostępne są punkty **oraz geometrie tras**. Sekcja **Punkty w okolicy** pokazuje nazwę, adres, odległość w linii prostej, rodzaj obiektu i deklarowaną dostępność, także przy braku wyznaczonej trasy. Lista rozwija się po 20 pozycji. **Pokaż punkt** przybliża marker i otwiera nazwę oraz adres w dymku. Apple Maps / Google Maps są dostępne również dla punktu bez trasy OSRM.

Dla encji `geo_location` stan w kilometrach oznacza odległość od lokalizacji domu HA, zgodnie z kontraktem tej platformy. Dodatkowe atrybuty `nearest_zone`, `zone_ids` i `distance_to_zone_m` opisują wybrane strefy. W liście na karcie odległość jest liczona od aktualnie wybranej strefy.

Wbudowana mapa HA pokazuje markery encji. Geometrie pieszych tras i listę adresów udostępnia własna karta integracji.

## Trasa z aktualnej lokalizacji urządzenia

We własnej karcie **`custom:gdzie-sie-ukryc-card`** wybierz **Trasa z mojej lokalizacji** przy punkcie na liście, przy gotowej trasie albo w dymku markera. Zezwól przeglądarce lub aplikacji na odczyt położenia. Integracja wyznaczy jedną trasę pieszą od odczytanej pozycji do wskazanego punktu, także gdy nie udało się wcześniej obliczyć tras ze strefy.

Trasa z urządzenia jest różowa, a marker **J** oznacza odczytaną pozycję. Panel pokazuje nazwę i adres celu, długość trasy, czas dojścia, czas odczytu położenia i zgłoszoną dokładność. **Odśwież moją trasę** odczytuje położenie ponownie; **Ukryj moją trasę** usuwa ten widok. Google Maps i Apple Maps w tym panelu otrzymują odczytany punkt startowy oraz wybrany cel i obliczają własną trasę pieszą.

**W przeglądarce otwórz HA przez HTTPS i udziel zgody na lokalizację.** Adres `http://homeassistant.local:8123` lub zwykły HTTP z lokalnym IP zazwyczaj blokuje odczyt położenia. Karta pokaże przyczynę oraz linki do nawigacji zewnętrznej, która może użyć pozycji urządzenia we własnej aplikacji. Wymagania opisuje [dokumentacja Geolocation API](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition).

Położenie jest pobierane tylko po naciśnięciu przycisku. Każda karta i każde urządzenie mają własną trasę w pamięci widoku; integracja nie zapisuje pozycji urządzenia ani tej trasy w Store HA, sensorach czy encjach mapy. Współrzędne są przekazywane przez uwierzytelniony WebSocket do HA, a następnie do wybranego w opcjach silnika tras. Dostawca silnika może zapisywać zapytania w swoich logach; opis domyślnej usługi: [FOSSGIS](https://routing.openstreetmap.de/about.html). Wyznaczenie własnej trasy jest dostępne także dla zalogowanych użytkowników bez praw administratora.

Lista okolicy nadal wynika z wybranej strefy HA i promienia. Zmiana strefy zamyka trasę urządzenia. Odświeżenie danych źródła zachowuje ją z czasem poprzedniego odczytu położenia. Nie ma ciągłego śledzenia ani automatycznego przeliczania podczas przemieszczania się. Wbudowana mapa HA pokazuje encje punktów; przycisk pobierający pozycję urządzenia znajduje się we własnej karcie integracji.

Instrukcja i rozwiązywanie problemów: [docs/TRASA_Z_URZADZENIA.md](docs/TRASA_Z_URZADZENIA.md).

## Dom i inne lokalizacje

Położenie domu ustaw w ustawieniach lokalizacji Home Assistant. Integracja odczytuje `zone.home`, bez wpisywania adresu w kodzie.

Inne lokalizacje, np. pracę lub drugi dom, utwórz w **Ustawienia → Obszary, etykiety i strefy → Strefy**, a następnie wybierz w opcjach integracji. Obsługiwanych jest do 8 stref. Karta przełącza je listą nad mapą; każda ma własny zestaw tras.

Zmiana współrzędnych lub promienia powoduje ponowne wyszukanie w już pobranej pełnej bazie. Nie wymaga kolejnego pobrania CSV przed upływem okresu odświeżania. Trasa z poprzedniego położenia strefy nie jest używana jako trasa z nowego miejsca. Zmiana liczby osób w strefie nie odświeża tras.

## Pobieranie pełnej bazy

Źródło domyślne wykonuje jedno żądanie dla wszystkich stref:

```text
GET https://gdziesieukryc.pl/PS_XML/punkty_schronienia.csv
```

To plik opublikowany przez Komendę Główną PSP w katalogu otwartych danych. Nie używa wewnętrznego `/api/shelters/nearby`, cookies przeglądarki ani CAPTCHA. Żądanie eksportu nie zawiera współrzędnych domu.

CSV odczytywany jest w UTF-8, z zachowaniem publicznych identyfikatorów, nazw, adresów, rodzaju obiektu, dostępności i współrzędnych WGS84. Oryginalny dołączony CSV zachowuje wszystkie 11 kolumn, również opisy i jednostki administracyjne. Karta korzysta z pól potrzebnych do wyszukania i nawigacji.

HA sprawdza plik po pierwszym uruchomieniu, domyślnie co 24 godziny oraz po ręcznym **Odśwież**. Okres można zmienić w opcjach. Obsługiwane są `ETag` i `Last-Modified`, jeśli serwer je udostępnia. Suma SHA-256 pozwala rozpoznać niezmienioną treść bez ponownego parsowania. Parsowanie i wyszukiwanie działają poza pętlą zdarzeń HA.

Błąd HTTP, timeout lub uszkodzony eksport zachowują ostatni poprawny zbiór. Przy braku wcześniejszego zbioru używana jest pełna baza dołączona do integracji. Karta pokazuje pochodzenie danych, czas pozyskania, ostatnie udane sprawdzenie oraz komunikat błędu. Kolejna próba następuje po okresie odświeżania lub po ręcznym kliknięciu.

Plik ma obecnie około 15 MB. Integracja pobiera pełny zbiór do pamięci i zapisuje go lokalnie, ale do karty przekazuje tylko pobliskie punkty i wybrane trasy. Sensory zawierają podsumowania, bez pełnej listy punktów ani geometrii. Limit bezpieczeństwa: CSV 32 MiB, do 200 000 rekordów.

## Pełny JSON i narzędzia

`export/punkty-schronienia.json` zawiera **wszystkie 85 739 punktów** po normalizacji do formatu integracji. Oryginalna baza jest w `custom_components/gdzie_sie_ukryc/datasets/psp-punkty.csv`.

Tryb automatyczny nie wymaga ręcznego używania tych plików. Aby świadomie korzystać ze statycznego JSON, skopiuj go do `/config/gdzie_sie_ukryc/punkty-schronienia.json`, wybierz źródło **Plik lokalny** i ścieżkę `gdzie_sie_ukryc/punkty-schronienia.json`. Ten plik ma około 23 MB i mieści się w limicie pliku lokalnego 64 MiB. **Nie importuj pełnego pliku przyciskiem na karcie**: import WebSocket i własny feed JSON mają limit 8 MiB.

Samodzielne pobranie aktualnego pełnego eksportu na komputerze z Pythonem 3.10+:

```bash
python3 tools/download_points.py
```

Wynik zapisuje się w `export/punkty-schronienia.json`. Dla wydawcy, aktualizacja również bazy dołączonej do kolejnego wydania:

```bash
python3 tools/download_points.py --update-bundled
```

Konwersja już posiadanego CSV, JSON, GeoJSON lub HAR, bez połączenia z siecią:

```bash
python3 tools/import_points.py punkty.csv punkty.json
python3 tools/import_points.py zapis.har punkty.json
```

Konwerter HAR wybiera tylko rozpoznane punkty; nie uzyska brakujących punktów poza zapisanymi odpowiedziami. HAR może zawierać prywatne informacje i nie należy publikować go w repozytorium.

Pozostają opcjonalne źródła: import małego JSON w karcie, lokalny JSON/GeoJSON wewnątrz katalogu konfiguracji, własny końcowy URL feedu JSON oraz stary tryb zapytań strony. Stary tryb może zwracać 403 i jest ograniczony do 250 wyników na strefę. Nowy pełny CSV nie ma tego ograniczenia.

Przykład formatu (punkt fikcyjny, wyłącznie do testów):

```json
{
  "source": "https://gdziesieukryc.pl",
  "captured_at": "2026-09-13T12:00:00Z",
  "points": [
    {
      "id": "TEST-1",
      "name": "DANE TESTOWE — nie jest to schronienie",
      "address": "Adres testowy",
      "latitude": 50.298,
      "longitude": 18.672,
      "category": "DANE TESTOWE",
      "availability": "Nie dotyczy"
    }
  ]
}
```

## Wybór tras i mapa

1. Integracja odrzuca punkty poza promieniem od wybranej strefy.
2. Wybiera domyślnie 12 najbliższych w linii prostej; liczbę kandydatów można zwiększyć do 30.
3. Oblicza trasy piesze przez OSRM przygotowany dla ruchu pieszego.
4. Pokazuje domyślnie 3 najkrótsze trasy **wśród wybranych kandydatów**. Nie gwarantuje 3 najkrótszych tras w całej bazie.

Promień oznacza odległość geograficzną, więc droga piesza może być dłuższa. Każda trasa ma kolor, długość i ETA. **Pokaż trasę** przybliża pojedynczą trasę; **Pokaż wszystkie punkty i trasy** przywraca widok zbiorczy. Apple Maps i Google Maps otwierają nawigację pieszą i obliczają własną trasę.

Domyślny silnik to publiczna usługa demonstracyjna FOSSGIS:

```text
https://routing.openstreetmap.de/routed-foot/route/v1/foot
```

Zapytania tras są wykonywane kolejno z odstępem około sekundy. Limit dla tego samego hosta obejmuje zarówno trasy stref, jak i jednorazowe trasy urządzeń korzystających ze wspólnej sesji HA. Pierwsze uruchomienie może potrwać kilkanaście sekund lub dłużej, zwłaszcza przy kilku strefach. Możesz podać własny serwer OSRM z danymi przygotowanymi profilem pieszym; zmiana samego słowa w URL nie zmienia profilu danych serwera.

Brak poprawnej trasy nie jest zastępowany linią prostą podpisaną jako trasa piesza. Zapisana poprawna trasa może być wyświetlana z datą i linią przerywaną. OSRM dopasowuje końce do sieci w promieniu do 100 m; większe odstępy od pinów są oznaczone szarą linią przerywaną. Długość i ETA nie obejmują tych niepotwierdzonych połączeń. Pin obiektu nie musi wskazywać wejścia.

Pełny eksport nie przekazuje PSP współrzędnych stref. Silnik tras otrzymuje współrzędne początku i celu; przyciski nawigacji przekazują je Apple lub Google. Przeglądarka pobiera podkład z `tile.openstreetmap.org`. Możesz wyłączyć kafelki przez `show_tiles: false` albo ustawić własne `tile_url` i `tile_attribution` zgodnie z dostawcą.

Zapis punktów i tras działa po restarcie. Nowe trasy wymagają dostępnego silnika. Paczka nie zawiera mapy kafelkowej offline. W serwisie PSP są **punkty schronienia**, także obiekty inne niż formalne schrony; dane nie potwierdzają bieżącego otwarcia, właściwego wejścia ani dostępności dojścia w terenie.

## Encje

Dla każdej wybranej strefy powstają cztery sensory:

| Sensor | Wartość |
| --- | --- |
| Trasy | Liczba wyświetlanych tras |
| Punkty w promieniu | Wszystkie punkty z wybranego źródła w promieniu; w trybie pełnego CSV bez limitu 250 |
| Najbliższa trasa | Długość pierwszej trasy w metrach |
| Czas dojścia | ETA pierwszej trasy w minutach |

Atrybuty obejmują `source_status`, `source_error`, `points_updated_at`, `routes_updated_at`, `zone_id`, `dataset_points`, `dataset_source`, `dataset_origin`, `dataset_checked_at`, `map_points` i `map_points_limit`. `dataset_points` to liczba punktów w całej bazie, nie liczba najbliższych. `dataset_origin: live` oznacza bazę zweryfikowaną przez udane pobranie/sprawdzenie, `bundled` — dołączony CSV. `points_updated_at` to czas pozyskania treści, a nie data zmiany każdego obiektu przez PSP. `cached` z błędem oznacza dostępne dane zapisane przy nieudanym odświeżeniu.

Geometrie nie są atrybutami sensorów. Jest też przycisk **Odśwież punkty i trasy**, dostępny w automatyzacjach przez `button.press`. Wybierz rzeczywisty identyfikator encji w swojej instalacji. Odczyt karty używa uwierzytelnionego WebSocket HA; import i ręczne odświeżenie wymagają administratora.

## Problemy

| Objaw | Co sprawdzić |
| --- | --- |
| Wciąż `HTTP 403` ze starego źródła | Wersja 1.5.0, restart i źródło **Cała baza PSP — automatyczny eksport CSV** |
| `cached` i błąd eksportu | Sprawdź `dataset_points`; pełna zapisana/dołączona baza pozostaje dostępna. Po przywróceniu połączenia użyj Odśwież |
| Brak punktów przy bazie 85 tys. | Współrzędne `zone.home`, wybraną strefę i promień |
| Brak `datasets/psp-punkty.csv` | Skopiuj kompletny katalog integracji z paczki |
| Dane są, brak punktów w zakładce Mapa | Wersję 1.5.0, restart HA oraz encje `geo_location` w Narzędziach deweloperskich; własna karta pokazuje też listę adresów |
| Punkty znalezione, brak tras | Dostęp HA do silnika pieszych tras i komunikat błędu tras |
| Brak przycisku Trasa z mojej lokalizacji | Własna karta `custom:gdzie-sie-ukryc-card`, aktualizacja 1.5.0 i ponowne wczytanie panelu |
| Lokalizacja wymaga HTTPS | Otwórz HA przez HTTPS albo użyj linku nawigacji zewnętrznej w komunikacie |
| Brak zgody / timeout położenia | Zgoda dla strony lub aplikacji, systemowe usługi lokalizacji i ponowna próba |
| `Custom element doesn't exist` | Zasób modułu z `v=1.5.0` i ponowne wczytanie aplikacji |
| Brak Leaflet | Cały katalog `frontend/vendor/` |
| Pusty podkład | Dostęp przeglądarki do kafelków; podkład i trasy są niezależne |

## Źródła i licencje

- [Zbiór PSP w dane.gov.pl](https://dane.gov.pl/pl/dataset/28058,punkty-schronienia-w-polsce) oraz [metadane zasobu CSV](https://api.dane.gov.pl/1.4/resources/1393918,punkty-schronienia-dane-csv).
- [Oficjalny opis aplikacji PSP](https://github.com/KGPSP/gdziesieukryc.pl).
- [Strefy Home Assistant](https://www.home-assistant.io/integrations/zone/).
- [Mapa HA](https://www.home-assistant.io/dashboards/map/) i [encje geolokalizacji](https://developers.home-assistant.io/docs/core/entity/geo-location/).
- [Własne karty HA](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/).
- [FOSSGIS](https://routing.openstreetmap.de/) i [API OSRM](https://project-osrm.org/docs/v5.24.0/api/).
- [Zasady kafelków OpenStreetMap](https://operations.osmfoundation.org/policies/tiles/).

Integracja społecznościowa, niezależna od PSP. Kod własny i ikona: MIT. Leaflet 1.9.4: BSD-2-Clause, licencja w `frontend/vendor/LICENSE`. Dane PSP: **CC BY 4.0**, atrybucja i zakres zmian w [DATA_LICENSE.md](DATA_LICENSE.md). Licencja MIT kodu nie zmienia licencji danych.
