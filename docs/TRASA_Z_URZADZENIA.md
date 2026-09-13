# Trasa z położenia telefonu, tabletu lub komputera

Funkcja wersji 1.5.0 działa we własnej karcie `custom:gdzie-sie-ukryc-card`. Dotychczasowy YAML karty pozostaje poprawny; nie trzeba wybierać encji `device_tracker` telefonu.

## Użycie

1. Zainstaluj kompletną aktualizację 1.5.0, uruchom ponownie HA i ponownie wczytaj panel. Ręcznie utrzymywany zasób JavaScript powinien mieć `v=1.5.0`.
2. Otwórz panel przez HTTPS na urządzeniu, którego położenie ma być początkiem trasy. W urządzeniu włącz usługi lokalizacji.
3. Na liście punktów lub w dymku markera wybierz **Trasa z mojej lokalizacji**. W Safari i innych przeglądarkach zaakceptuj pytanie o udostępnienie położenia. Aplikacja HA i system również muszą pozwalać na odczyt lokalizacji, jeżeli udostępniają tę funkcję widokowi karty.
4. Poczekaj na odczyt położenia i obliczenie trasy. Różowa linia prowadzi z markera **J** do wybranego celu. Panel pod mapą zawiera nazwę, adres, długość, czas dojścia, czas odczytu i zgłoszoną dokładność.
5. **Odśwież moją trasę** wykonuje nowy odczyt położenia i nowe obliczenie. **Pokaż moją trasę** przybliża ten przebieg; **Ukryj moją trasę** zamyka go. Nawigacja Google Maps / Apple Maps w panelu używa odczytanej pozycji jako początku własnej trasy pieszej.

Wysoka dokładność jest żądana, ale dostępny pomiar zależy od sprzętu, systemu i sygnału. Komputer może korzystać z położenia ustalanego przez sieć Wi-Fi. Karta pokazuje dokładność zgłoszoną przez urządzenie; ponad 100 m dodaje ostrzeżenie. Przerywane krótkie odcinki łączą odczytaną pozycję i cel z siecią dróg, a ich przejście oraz wejście nie są potwierdzone przez silnik.

## Gdy odczyt nie działa

| Komunikat | Działanie |
| --- | --- |
| Lokalizacja wymaga HTTPS | Otwórz HA przez HTTPS. Zwykły adres lokalny HTTP nie spełnia wymagania Geolocation API; localhost jest szczególnym przypadkiem zaufanego kontekstu. |
| Brak zgody na lokalizację | Zezwól stronie HA lub aplikacji na dostęp do położenia i sprawdź systemowe usługi lokalizacji. Następnie ponów żądanie. |
| Przeglądarka lub aplikacja nie udostępnia lokalizacji | Otwórz panel przez HTTPS w przeglądarce obsługującej Geolocation API. Widok aplikacji może mieć własne ograniczenia. |
| Nie można ustalić położenia / timeout | Włącz lokalizację urządzenia i spróbuj ponownie przy dostępnej pozycji. Limit oczekiwania na pomiar wynosi 20 s; czas decyzji o zgodzie może być dodatkowy. |
| HTTP 403 / 429 / 503 lub brak poprawnej trasy pieszej | Sprawdź dostęp HA do skonfigurowanego silnika tras. Silnik wymaga pozycji przy dostępnej sieci pieszych dróg oraz poprawnego celu. |
| Punkt nie istnieje w aktualnej bazie | Wczytaj aktualne dane karty i wybierz punkt ponownie. |
| Brak przycisku we wbudowanej zakładce Mapa HA | Otwórz własną kartę integracji na panelu. Wbudowana mapa pokazuje encje punktów. |

Po błędzie karta udostępnia linki Google Maps i Apple Maps z samym celem oraz trybem pieszym. Wówczas własna nawigacja może ustalić początek na urządzeniu; przy braku jej lokalizacji może poprosić o ręczne określenie startu. Karta HA nie pokazuje w tym przypadku obliczonego przebiegu z bieżącej pozycji.

## Zakres i dane lokalizacji

Lista okolicy i trasy stref są wyznaczane względem stref HA. Przycisk urządzenia oblicza jedną trasę do wskazanego punktu z używanego właśnie urządzenia. Dwa urządzenia mogą równocześnie wybrać różne cele i początki, także jako zwykli zalogowani użytkownicy.

Karta żąda pozycji dopiero po kliknięciu, z `enableHighAccuracy: true`, `maximumAge: 0` i `timeout: 20000`. Nie prowadzi ciągłego śledzenia. Pomiar może stracić aktualność po przemieszczeniu się; panel zachowuje czas odczytu, a kolejny pomiar wykonuje przycisk odświeżenia własnej trasy.

Jednorazowe współrzędne są wysyłane przez uwierzytelniony WebSocket do HA i przekazywane skonfigurowanemu silnikowi tras. Cel serwer odczytuje z aktualnej bazy po publicznym identyfikatorze punktu. Integracja nie zapisuje pozycji ani tej trasy w Store HA, sensorach, encjach geolokalizacji, plikach eksportu, localStorage lub GitHubie. Trasa jest przechowywana w pamięci danej karty; zmiana strefy, ukrycie lub odłączenie widoku ją usuwają. Dostawca silnika tras może zapisywać współrzędne w logach swoich żądań. Po otwarciu linku nawigacji współrzędne startu i celu otrzymuje także wybrany dostawca map.

Aktualizacja źródła nie nadpisuje indywidualnej trasy położeniem domu ani pozycją innego urządzenia. Starsze odpowiedzi po wybraniu kolejnego celu lub zamknięciu widoku są ignorowane. Trasy stref i urządzeń dzielą kolejkę do tego samego hosta silnika, aby zachować limit jednej próby na sekundę publicznej usługi.

## Dokumentacja źródłowa

- [Geolocation API — zgoda, HTTPS i opcje odczytu](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition).
- [Home Assistant — uwierzytelniony WebSocket](https://developers.home-assistant.io/docs/api/websocket/).
- [FOSSGIS — zasady użycia i informacje o logowaniu zapytań](https://routing.openstreetmap.de/about.html).
- [Google Maps URLs — początek, cel i tryb pieszy](https://developers.google.com/maps/documentation/urls/get-started).
- [Apple Map Links — adresy początku i celu, tryb pieszy](https://developer.apple.com/library/archive/featuredarticles/iPhoneURLScheme_Reference/MapLinks/MapLinks.html).
