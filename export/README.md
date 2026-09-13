# Pełny JSON punktów

`punkty-schronienia.json`: 85 739 punktów z pełnego opublikowanego eksportu PSP pobranego 13.09.2026. Wydawca: Komenda Główna PSP, dane na licencji [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Źródło: [CSV PSP](https://gdziesieukryc.pl/PS_XML/punkty_schronienia.csv), [katalog dane.gov.pl](https://dane.gov.pl/pl/dataset/28058,punkty-schronienia-w-polsce).

JSON zawiera pola potrzebne do mapy i nawigacji po normalizacji i walidacji. Oryginalny CSV z wszystkimi kolumnami znajduje się w `custom_components/gdzie_sie_ukryc/datasets/psp-punkty.csv`. Atrybucja i zakres zmian: `../DATA_LICENSE.md` oraz pole `attribution` JSON.

Domyślny automatyczny tryb integracji pobiera CSV samodzielnie i nie potrzebuje tego JSON.

Aby użyć JSON jako statycznej bazy, skopiuj go do `/config/gdzie_sie_ukryc/punkty-schronienia.json` i w opcjach wybierz plik lokalny `gdzie_sie_ukryc/punkty-schronienia.json`. Ma około 23 MB; **użyj trybu pliku lokalnego, nie importu na karcie** (limit 8 MiB).

Ponowne pobranie na komputerze z Pythonem 3.10+:

```bash
python3 tools/download_points.py
```
