# Historia zmian

## 1.5.0 — 2026-09-13

- Przycisk **Trasa z mojej lokalizacji** przy punktach listy, gotowych trasach i w dymkach markerów. Po kliknięciu karta odczytuje bieżące położenie urządzenia z wysoką dokładnością, bez akceptowania pozycji z cache.
- Jednorazowa trasa piesza do publicznego identyfikatora punktu przez uwierzytelniony WebSocket HA i skonfigurowany silnik tras. Dostępna także dla zwykłych zalogowanych użytkowników.
- Osobny różowy przebieg, marker aktualnej pozycji, długość i czas dojścia, czas odczytu i dokładność. Przyciski ponownego odczytu położenia, przybliżenia i ukrycia trasy; nawigacja Google Maps / Apple Maps z odczytanej pozycji.
- Czytelne komunikaty o HTTPS, odmowie dostępu, niedostępnym położeniu, timeout i awarii silnika. Nawigacja zewnętrzna może ustalić początek na swoim urządzeniu.
- Pozycja i trasa urządzenia pozostają w pamięci jego karty; nie zmieniają zapisu stref, Store, sensorów i encji punktów. Starsze odpowiedzi po zmianie celu, zamknięciu lub odłączeniu karty są ignorowane.
- Wspólny limit żądań silnika tras dla stref, urządzeń i wpisów korzystających z tej samej sesji HA i hosta. Zachowany odstęp co najmniej sekundy.
- Pełna opublikowana baza 85 739 punktów PSP, encje mapy, nazwy, adresy oraz dotychczasowe źródła są nadal dołączone.

## 1.4.0 — 2026-09-13

- Pobliskie punkty jako encje `geo_location`, widoczne we wbudowanej mapie HA wraz z nazwą i adresem.
- Własna karta rysuje punkty również wtedy, gdy silnik tras nie odpowiada.
- Lista punktów w okolicy: nazwy, adresy, odległość w linii prostej, dostępność i nawigacja Apple / Google.
- Domyślnie 100 punktów na mapie i liście na strefę; nowa opcja z zakresem 30–500, niezależna od liczby kandydatów do tras.
- Punkty wspólne dla kilku stref mają jedną encję; zmiana obszaru usuwa nieaktualne punkty mapy i ich rejestracje.
- Nazwy i adresy w dymkach oraz przycisk Pokaż punkt; lista rozwijana po 20 pozycji.
- Zachowanie oryginalnych bajtów CSV w Git, aby normalizacja końców linii nie zmieniała sumy kontrolnej dołączonej bazy.

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
