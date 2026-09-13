# Gdzie się ukryć — integracja Home Assistant 1.2.0

Integracja pobiera lokalizację domu ze strefy `zone.home`, obsługuje dodatkowe strefy i pokazuje na karcie mapy trasy piesze do pobliskich punktów schronienia. Domyślnie pokazuje 3 trasy, szuka w promieniu 5 km i odświeża trasy co 24 godziny.

**Domyślnie pobiera punkty automatycznie z gdziesieukryc.pl**, korzystając z tego samego żądania co mapa strony. Mechanizm i nazwy pól potwierdzono na zapisie działania aplikacji PSP 1.3.74 z 13.09.2026. Nie potrzebujesz klucza API ani ręcznie dostarczanej listy punktów.

Interfejs strony jest wewnętrzny i nieudokumentowany. Może się zmienić lub odmówić połączenia z HA kodem 403. Dostęp z konkretnej instalacji sprawdź po uruchomieniu. Przy błędzie integracja zachowuje wcześniej pobrane punkty i trasy danego obszaru. Publiczne repozytorium zawiera kod i fikcyjne dane testowe; nie zawiera bazy rzeczywistych punktów.

[Instrukcja dla wydawcy: publikacja na GitHubie](docs/PUBLIKACJA_GITHUB.md). Po uzupełnieniu adresu repozytorium można je dodać do HACS jako repozytorium niestandardowe typu **Integration**.

[Zgłoszenia błędów](https://github.com/CyberGuard-PS/ha-gdzie-sie-ukryc/issues) · [Historia zmian](CHANGELOG.md)

W serwisie PSP są **punkty schronienia** — również inne obiekty niż formalne schrony. Integracja zachowuje tę terminologię. Nie potwierdza, że obiekt jest otwarty, jaka jest jego kategoria ochrony ani gdzie znajduje się właściwe wejście.

## Instalacja przez HACS

Wymagany Home Assistant **2026.9.0 lub nowszy**; testy wykonano na Core 2026.9.2.

1. W HACS wybierz **⋮ → Repozytoria niestandardowe**, podaj `https://github.com/CyberGuard-PS/ha-gdzie-sie-ukryc` i wybierz typ **Integration / Integracja**.
2. Pobierz **Gdzie się ukryć** i uruchom ponownie HA.
3. W **Ustawienia → Urządzenia i usługi → Dodaj integrację** wyszukaj **Gdzie się ukryć**.
4. Zostaw źródło **Automatycznie z gdziesieukryc.pl**, wybierz **Dom** i ewentualnie dodatkowe strefy.
5. Po obliczeniu tras dodaj kartę do swojego panelu.

```yaml
type: custom:gdzie-sie-ukryc-card
title: Gdzie się ukryć
zone: zone.home
map_height: 420
```

Karta i biblioteka Leaflet są częścią integracji. **Nie kopiujesz osobnego katalogu `www` ani nie instalujesz karty jako drugiego repozytorium HACS.** W standardowym trybie zarządzania zasobami przez UI integracja automatycznie dodaje moduł JavaScript do Lovelace. Ponownie wczytaj panel lub aplikację po dodaniu integracji.

Jeśli zasoby utrzymujesz w YAML, dodaj w `configuration.yaml`:

```yaml
lovelace:
  resource_mode: yaml
  resources:
    - url: /gdzie_sie_ukryc/frontend/gdzie-sie-ukryc-card.js?v=1.2.0
      type: module
```

Przykład jest w `examples/lovelace-resources.yaml`. Połącz go z istniejącą sekcją `lovelace`, zamiast tworzyć drugi klucz. Nie dodawaj tego samego modułu dwukrotnie. Gdy automatyczne dodanie zasobu nie powiedzie się, możesz użyć tego URL w **Ustawienia → Panele → ⋮ → Zasoby**, z typem **Moduł JavaScript**.

Pierwsze uruchomienie przy 12 kandydatach na strefę trwa kilkanaście sekund lub dłużej. Więcej stref zwiększa ten czas. Przycisk **Odśwież** pobiera punkty i przelicza trasy. Karta sama odnajduje wpis integracji.

## Instalacja ręczna

Pobierz źródła repozytorium albo paczkę `gdzie_sie_ukryc.zip` z GitHub Release. Skopiuj **cały** katalog `custom_components/gdzie_sie_ukryc` do `/config/custom_components/gdzie_sie_ukryc`, uruchom HA ponownie i wykonaj kroki dodania integracji oraz karty powyżej.

`/config` oznacza katalog zawierający Twój `configuration.yaml`. W HA Container jest to katalog zamontowany do `/config`. Pozostałych plików repozytorium nie trzeba kopiować do HA. Instalacja ręczna nie wymaga Node.js, npm ani narzędzi deweloperskich.

## Dom i dodatkowe lokalizacje

Położenie domu ustaw w Home Assistant w ustawieniach lokalizacji domu. Integracja czyta je ze strefy `zone.home` i nie wymaga wpisywania adresu w kodzie.

Dodatkowe lokalizacje utwórz jako strefy: **Ustawienia → Obszary, etykiety i strefy → Strefy**. Możesz wskazać na mapie np. pracę, drugi dom albo mieszkanie bliskich. Następnie w opcjach integracji wybierz te strefy w polu lokalizacji początkowych. Obsługiwanych jest maksymalnie 8 stref. W karcie przełączasz je listą nad mapą; dla każdej zapisany jest osobny zestaw tras.

Zmiana współrzędnych wybranej strefy powoduje odświeżenie. Zapisana trasa zaczynająca się w poprzedniej lokalizacji nie jest używana dla nowej lokalizacji. Zmiana opcji integracji przeładowuje encje.

## Automatyczne pobieranie i zakres danych

Dla każdej strefy HA wysyła żądanie:

```text
GET https://gdziesieukryc.pl/api/shelters/nearby
    ?lat=<szerokość>&lng=<długość>&radius=<metry>&limit=250
```

To ścieżka i nazwy parametrów zaobserwowane w HAR, a nie publiczna dokumentacja operatora. Promień ustawiony w HA w kilometrach jest przeliczany na metry. W odpowiedzi znajdują się `data`, `count` i `source`. Przypisanie pól:

| Pole serwisu | Znaczenie w integracji |
| --- | --- |
| `id_publiczny` | Stabilny identyfikator punktu |
| `nazwa` | Nazwa |
| `lokalizacja_lat`, `lokalizacja_lon` | Współrzędne WGS84 |
| `lokalizacja_adres` | Adres |
| `rodzaj_obiektu` | Rodzaj obiektu podany przez źródło |
| `dostepnosc` | Dostępność deklarowana w źródle |

Pole `dystans_metry` z odpowiedzi zależy od środka zapytania strony. HA oblicza odległość od wybranej strefy samodzielnie. Odpowiedź zaobserwowana w zapisie działania strony była uporządkowana rosnąco po tej odległości. Integracja dodatkowo sortuje punkty i odrzuca te poza własnym promieniem.

Każde zapytanie prosi o maksymalnie 250 punktów. Po osiągnięciu tego limitu karta i atrybut sensora `result_limit_reached` wskazują, że licznik nie przedstawia pełnej liczby punktów w okolicy. Integracja nie pobiera całej Polski ani nie zakłada niepotwierdzonego stronicowania. Wybór najkrótszych tras jest ograniczony do zwróconych punktów i skonfigurowanej liczby kandydatów.

Punkty pobierane są domyślnie co 24 godziny, po zmianie współrzędnych lub promienia oraz po ręcznym odświeżeniu. Restart wykorzystuje zapisane odpowiedzi do upływu okresu odświeżania. Zmiana liczby osób w strefie nie uruchamia pobierania. Żądania dla kilku stref są wykonywane kolejno z odstępem około sekundy. Po błędzie źródła dalsze zapytania PSP w danym cyklu są wstrzymywane. Kolejna próba nastąpi po skonfigurowanym okresie albo po kliknięciu **Odśwież**.

Odpowiedzi są przechowywane osobno dla obszaru każdej strefy. Błąd nie usuwa poprzedniego poprawnego zapisu dla tego samego obszaru. Zmiana współrzędnych lub promienia unieważnia jego użycie. Poprawna odpowiedź z pustą listą usuwa wcześniejsze punkty tego obszaru. W przypadku awarii bez wcześniejszych danych sensor liczby punktów ma stan nieznany.

## Aktualizacja z wersji 1.0.0 / 1.1.0

1. Zastąp katalog integracji kompletnym katalogiem z nowej wersji albo zainstaluj repozytorium przez HACS i uruchom HA ponownie.
2. Jeżeli używałeś importu, w **opcjach istniejącej integracji** wybierz **Automatycznie z gdziesieukryc.pl**. Dotychczasowy wybór źródła jest zachowany.
3. W trybie zasobów UI integracja zmieni stary adres `/local/gdzie-sie-ukryc/...` na nowy i usunie duplikaty tego modułu. Przy YAML zmień adres ręcznie na `/gdzie_sie_ukryc/frontend/gdzie-sie-ukryc-card.js?v=1.2.0`.
4. Ponownie wczytaj panel lub aplikację HA. Stary katalog `/config/www/gdzie-sie-ukryc` nie jest już potrzebny.

Nie trzeba usuwać wpisu integracji ani tworzyć go od nowa. Nowe trasy obliczane są nadal dla stref z Twojej konfiguracji HA.

## Źródła dodatkowe i konwerter

Jeśli chcesz użyć własnych danych, nadal dostępne są import JSON, lokalny plik i feed. Są opcjonalne i nie zastępują domyślnego trybu automatycznego.

Konwerter można uruchomić lokalnie:

```bash
python3 tools/import_points.py zapis.har punkty.json
```

Rozpoznaje pola PSP, odpowiedzi listy i szczegóły pojedynczego punktu, standardowy JSON i GeoJSON. Używa wyłącznie biblioteki standardowej Python 3.10+ i nie łączy się z siecią. Nie przekazuj pełnego HAR do HA ani publicznego repozytorium. Wynik zawiera tylko wybrane pola punktów i datę pozyskania.

### Format punktów

Poniższy przykład zawiera **fikcyjne dane do testu formatu**. Nie jest listą obiektów ochronnych. Współrzędne, nazwę i adres zastąp wartościami z rzeczywistego źródła.

```json
{
  "source": "https://gdziesieukryc.pl",
  "captured_at": "2026-09-13T07:00:00Z",
  "points": [
    {
      "id": "ID_Z_SERWISU",
      "name": "RZECZYWISTA_NAZWA_Z_SERWISU",
      "address": "RZECZYWISTY_ADRES_Z_SERWISU",
      "latitude": 50.298,
      "longitude": 18.672,
      "category": "Punkt schronienia",
      "availability": "Brak informacji"
    }
  ]
}
```

`captured_at` to czas pozyskania danych; jeśli go nie podasz, HA zapisze czas importu. `availability` i `category` przepisuj zgodnie ze źródłem. Brak informacji o dostępności nie oznacza dostępności całodobowej. Jeżeli wpis nie ma identyfikatora, importer tworzy stabilny identyfikator ze współrzędnych i opisu. Błędne punkty pomija z podaniem ich liczby.

Plik `examples/punkty-testowe.json` jest wyłącznie do sprawdzenia instalacji. Wszystkie jego wpisy oznaczono jako testowe. Usuń je przez import rzeczywistego zestawu, zanim zaczniesz korzystać z mapy.

## Pozostałe źródła danych

**Plik lokalny:** umieść JSON w `/config/gdzie_sie_ukryc/punkty.json`, w opcjach wybierz lokalny plik i ścieżkę `gdzie_sie_ukryc/punkty.json`. Możesz aktualizować plik swoim procesem i używać przycisku odświeżania. Integracja czyta plik podczas cyklu odświeżania, nie obserwuje zapisu pliku w czasie rzeczywistym. Ścieżka musi wskazywać JSON/GeoJSON wewnątrz katalogu konfiguracji HA.

**Feed JSON:** gdy uzyskasz od operatora potwierdzony URL danych albo przygotujesz własny feed z pozyskanych punktów, wybierz źródło URL i podaj jego pełny adres. Integracja wykonuje GET i oczekuje jednej pełnej odpowiedzi JSON w opisanym formacie. Ten wariant nie implementuje uwierzytelniania ani stronicowania. Do połączenia z PSP służy osobny tryb automatyczny, który sam ustawia parametry strefy. Nie dodawaj tokenów do URL. Przekierowania i odpowiedzi HTML są odrzucane; trzeba podać końcowy adres feedu. HTTPS jest obsługiwany z normalną weryfikacją certyfikatu; LAN HTTP może być użyty dla własnej usługi.

W trybie importu integracja automatycznie odświeża **trasy**. Punkty aktualizujesz przez ponowny import. W trybie pliku lub feedu podczas cyklu odświeżania aktualizowane są również punkty.

## Jak wybierane i rysowane są trasy

1. Integracja pobiera pobliskie punkty z PSP dla strefy albo czyta wybrane źródło dodatkowe, a następnie sprawdza własny promień.
2. Wybiera domyślnie 12 punktów najbliższych w linii prostej.
3. Dla kandydatów oblicza rzeczywiste trasy piesze przez OSRM z danymi przygotowanymi dla ruchu pieszego.
4. Pokazuje domyślnie 3 trasy o najmniejszej długości **wśród tych kandydatów**, razem z czasem dojścia z silnika tras. Nie jest to gwarancja 3 najkrótszych tras w całej bazie. Możesz zwiększyć liczbę kandydatów do 30.

Promień to odległość geograficzna punktu od strefy. Trasa przez drogi i przejścia może być dłuższa. Lista jest ograniczona do danych pobranych lub zaimportowanych dla tego obszaru; brak punktów na mapie nie potwierdza braku takich obiektów w rzeczywistości.

Każda trasa ma własny kolor. Kliknij **Pokaż trasę**, aby przybliżyć wybraną trasę; **Pokaż wszystkie trasy** przywraca widok zbiorczy. Karta pokazuje długość, przybliżony czas i opis punktu. Przyciski **Apple Maps** i **Google Maps** przekazują początek i cel do nawigacji pieszej. Nawigacja w tych aplikacjach oblicza własną trasę; nie musi ona pokrywać się z OSRM.

OSRM dopasowuje współrzędne do sieci dróg i przejść w promieniu maksymalnie 100 m. Odcinki od domu do sieci i od końca sieci do punktu nie są potwierdzonymi przejściami; karta oznacza większe odstępy cienką szarą linią przerywaną. **Długość i ETA dotyczą trasy z silnika, bez tych niepotwierdzonych odcinków.** Pin może oznaczać obiekt, a nie jego wejście.

Gdy silnik nie zwróci poprawnej trasy, integracja nie zastępuje jej prostą linią podpisaną jako trasa piesza. Kandydat bez nowej trasy jest szary. Poprzednia poprawna trasa może pozostać jako **Zapisana trasa**, z datą i linią przerywaną. Błąd połączenia wstrzymuje dalsze zapytania podczas bieżącego cyklu; następny cykl lub ręczne odświeżenie spróbuje ponownie.

## Silnik tras, podkład i działanie bez połączenia

Domyślny URL silnika:

```text
https://routing.openstreetmap.de/routed-foot/route/v1/foot
```

Jest to publiczna usługa demonstracyjna FOSSGIS. Próbne zapytania piesze odpowiedziały poprawnie. Zapytania są wykonywane kolejno z odstępem co najmniej około sekundy. Publiczna usługa nie daje gwarancji dostępności. Możesz użyć własnego OSRM, ale dane muszą być przygotowane profilem pieszym; samo słowo `foot` w URL serwera przygotowanego dla samochodów nie zmienia sposobu wyznaczania tras.

W trybie automatycznym serwis PSP otrzymuje współrzędne każdej wybranej strefy i promień. Silnik tras otrzymuje współrzędne każdej lokalizacji początkowej i celu. Do wyznaczenia tras nie wysyła się nazw stref ani adresów punktów. Własny silnik usuwa potrzebę przekazywania współrzędnych do publicznej usługi tras; tryb automatyczny nadal wysyła współrzędne stref do PSP. Kliknięcie przycisku nawigacji przekazuje współrzędne odpowiednio Apple lub Google.

Podkład mapy pobiera przeglądarka z `tile.openstreetmap.org`. Nie ma masowego pobierania map ani własnej pamięci offline kafelków. Przy awarii podkładu zapisane linie i punkty nadal mogą być widoczne na pustym tle. Żeby korzystać z własnych kafelków albo nie wysyłać zapytań o podkład, ustaw:

```yaml
type: custom:gdzie-sie-ukryc-card
zone: zone.home
map_height: 420
show_tiles: false
```

Możesz też podać `tile_url` i `tile_attribution` dla własnego serwera. Atrybucję ustaw zgodnie z dostawcą podkładu.

Punkty i ostatnie trasy są zapisywane przez mechanizm HA Store. Przetrwają restart. Brak internetu nie pozwala obliczyć nowej trasy z publicznego silnika; pozwala wyświetlić wcześniej zapisaną, o ile nadal dotyczy tej samej lokalizacji i punktu. Ta paczka nie zapewnia pełnej mapy offline ani informacji o bieżących zagrożeniach na drodze. Dostęp do HA podczas awarii internetu wymaga działającej lokalnej sieci i hosta HA.

## Encje i automatyzacje

Dla każdej strefy powstają cztery sensory:

| Sensor | Wartość |
| --- | --- |
| Trasy | Liczba wyświetlanych tras |
| Punkty w promieniu | Liczba znalezionych punktów przed ograniczeniem kandydatów, maksymalnie 250 z PSP; stan nieznany przy błędzie bez zapisu |
| Najbliższa trasa | Długość pierwszej trasy w metrach albo brak wartości |
| Czas dojścia | ETA pierwszej trasy w minutach albo brak wartości |

Sensory mają atrybuty `source_status`, `points_updated_at`, `routes_updated_at`, `route_status`, `nearest_address`, `result_limit_reached` i `zone_id`. Status źródła i data dotyczą odpowiedniej strefy. Nie zawierają geometrii, dzięki czemu Recorder nie zapisuje dużych zestawów współrzędnych przy każdej aktualizacji.

Jest też przycisk **Gdzie się ukryć · Odśwież punkty i trasy**, który można wywołać z automatyzacji działaniem `button.press`. Wybierz jego rzeczywisty identyfikator w swojej instalacji; HA nadaje identyfikatory encji i może dopisać numer przy kolizji.

Karta używa uwierzytelnionego WebSocket HA do odczytu tras. Import i ręczne odświeżenie z karty wymagają administratora. Zwykły użytkownik HA może oglądać dane i uruchamiać nawigację.

## Rozwiązywanie problemów

| Objaw | Co sprawdzić |
| --- | --- |
| Integracja nie pojawia się w wyszukiwarce | Ścieżkę `/config/custom_components/gdzie_sie_ukryc/manifest.json` i restart HA |
| `Custom element doesn't exist` | Zasób modułu, katalog `www` i ponowne wczytanie aplikacji / przeglądarki |
| Brak lokalnej biblioteki Leaflet | Czy zainstalowano cały katalog `custom_components/gdzie_sie_ukryc/frontend/vendor/` |
| Brak punktów | Źródło automatyczne w opcjach, położenie strefy, promień i komunikat karty |
| Import: brak rozpoznanych współrzędnych | Schemat odpowiedzi; przypisz pola do przykładu JSON |
| Punkty są, trasy nie powstają | Dostęp HA do silnika pieszych tras, URL z końcowym profilem i poprawne współrzędne |
| PSP zwraca 403 / HTML / 429 | Serwis odrzuca połączenie lub limituje ruch; odczekaj i odśwież. Zachowywane są poprzednie dane. Zapasowy JSON można uruchomić w trybie importu. Integracja nie obsługuje CAPTCHA ani cookies przeglądarki |
| Podkład mapy jest pusty | Dostęp przeglądarki do kafelków; punkty i trasy są pobierane niezależnie |
| Nie ma dodatkowej lokalizacji | Czy strefa została dodana i wybrana w opcjach integracji |

## Weryfikacja i źródła

Zakres wykonanych testów jest opisany w `docs/WERYFIKACJA.md`. Testy nie zastępują sprawdzenia dostępu do PSP w konkretnej instalacji HA ani dostępności obiektów w terenie. Podgląd `tests/browser_fixture.html` zawiera jawnie oznaczone punkty testowe, z geometrią rzeczywistych próbnych tras pieszych.

- [Oficjalny opis aplikacji PSP i punktów schronienia](https://github.com/KGPSP/gdziesieukryc.pl).
- [Oficjalna historia zmian aplikacji PSP](https://github.com/KGPSP/gdziesieukryc.pl/blob/main/CHANGELOG.md).
- [Strefy Home Assistant](https://www.home-assistant.io/integrations/zone/).
- [Własne karty Home Assistant](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/).
- [DataUpdateCoordinator w Home Assistant](https://developers.home-assistant.io/docs/integration_fetching_data/).
- [Silnik demonstracyjny FOSSGIS](https://routing.openstreetmap.de/).
- [Kontrakt API OSRM](https://project-osrm.org/docs/v5.24.0/api/).
- [Warunki korzystania z kafelków OpenStreetMap](https://operations.osmfoundation.org/policies/tiles/).
- [Informacja o blokadach stron w przeglądarce ChatGPT](https://help.openai.com/articles/20001280-using-cloud-browser-in-chatgpt#when-a-website-blocks-the-task).

To integracja społecznościowa, niezależna od PSP. Kod własny i autorska ikona na licencji MIT, Leaflet 1.9.4 na licencji BSD-2-Clause — licencja biblioteki jest w `custom_components/gdzie_sie_ukryc/frontend/vendor/LICENSE`. Licencja kodu nie nadaje praw do danych źródłowych; ich pochodzenie pozostaje wskazane przy punktach.
