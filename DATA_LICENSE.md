# Dane punktów schronienia — CC BY 4.0

Wydawca: **Komenda Główna Państwowej Straży Pożarnej (KG PSP)**.

- Zbiór: [Punkty schronienia w Polsce](https://dane.gov.pl/pl/dataset/28058,punkty-schronienia-w-polsce), ID 28058.
- Metadane: [oficjalny katalog API dane.gov.pl](https://api.dane.gov.pl/1.4/datasets/28058,punkty-schronienia-w-polsce).
- Zasób: **Punkty schronienia — dane CSV**, ID 1393918.
- Oryginalny eksport: [punkty_schronienia.csv](https://gdziesieukryc.pl/PS_XML/punkty_schronienia.csv).
- Licencja wskazana w oficjalnym katalogu: [Creative Commons Uznanie autorstwa 4.0 Międzynarodowe — CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Deklarowana częstotliwość publikacji: co tydzień.

## Dołączony zbiór

Pobrano 13.09.2026. Dokładny czas pozyskania jest w `custom_components/gdzie_sie_ukryc/datasets/snapshot.json`.

**85 739 wierszy, 85 739 poprawnych unikalnych punktów, 0 pominiętych rekordów i 0 powtórzonych identyfikatorów.** Rozmiar CSV: 15 077 217 bajtów. SHA-256:

```text
5ac8a41ffae67a1b5acf0ab679182d80c78019e6300c3afbd62ecadbaf8e728b
```

Katalogowy opis wskazuje 85 853 rekordy i datę danych 07.09.2026. Faktycznie pobrany plik zawiera 85 739 rekordów. Nie przypisujemy tej różnicy błędom parsera ani nie uzupełniamy brakujących rekordów fikcyjnymi danymi. Dołączona baza obejmuje cały pobrany, opublikowany CSV; nie jest deklaracją liczby obiektów w wewnętrznej bazie aplikacji w danej chwili.

## Pliki i zmiany

`custom_components/gdzie_sie_ukryc/datasets/psp-punkty.csv` to oryginalna treść eksportu, **bez zmian**, z wszystkimi 11 kolumnami.

`export/punkty-schronienia.json` jest pochodną do celów mapy Home Assistant: znormalizowano nazwy pól, wybrano publiczny identyfikator, nazwę, adres, współrzędne WGS84, rodzaj obiektu i dostępność, oraz sprawdzono poprawność współrzędnych i unikalność identyfikatorów. Opisy ogólne i podział administracyjny pozostają w oryginalnym CSV. Pochodzenie i licencję zapisano również w polu `attribution` JSON.

Przy dalszej dystrybucji zachowaj informację o KG PSP, źródle, licencji i wykonanych zmianach. Dane podlegają CC BY 4.0; odrębna licencja MIT dotyczy kodu integracji i nie zastępuje licencji danych.
