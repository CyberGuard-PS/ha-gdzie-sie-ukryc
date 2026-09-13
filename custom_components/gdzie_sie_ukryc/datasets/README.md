# Pełna baza PSP

Wydawca: Komenda Główna Państwowej Straży Pożarnej.
Licencja danych: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Źródło: [oficjalny CSV](https://gdziesieukryc.pl/PS_XML/punkty_schronienia.csv), wskazany w [dane.gov.pl](https://dane.gov.pl/pl/dataset/28058,punkty-schronienia-w-polsce).

`psp-punkty.csv` zawiera niezmieniony eksport z 13.09.2026: 85 739 poprawnych punktów, wszystkie 11 kolumn. `snapshot.json` zawiera datę pobrania, sumę SHA-256, liczbę rekordów, źródło i licencję.

CSV służy jako pełna baza początkowa i zapasowa. Integracja automatycznie sprawdza aktualny eksport domyślnie co 24 godziny; PSP deklaruje publikację co tydzień. Pobrana nowsza baza zapisywana jest przez HA Store, bez modyfikowania tych plików instalacji.

Przekształcenie do danych mapy obejmuje wybór i normalizację pól oraz walidację współrzędnych. Oryginalny CSV pozostaje bez zmian. Opis katalogu deklaruje 85 853 rekordy; faktyczny dołączony plik ma 85 739 i żaden rekord nie został pominięty przez parser.

Aktualizacja bazy dołączonej przez wydawcę repozytorium:

```bash
python3 tools/download_points.py --update-bundled
```

Zachowaj atrybucję KG PSP, odnośniki i informację o zmianach przy dalszej dystrybucji. Licencja MIT integracji nie obejmuje danych PSP.
