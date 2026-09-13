# Publikacja repozytorium na GitHubie

ZIP zawiera pełne źródła repozytorium, integrację, kartę mapy, ikonę, licencje, przykłady, testy i konfigurację GitHub Actions. Rozpakuj go do jednego katalogu na komputerze. Do GitHuba przesyłasz **zawartość tego katalogu**, tak aby `hacs.json`, `README.md` i `custom_components` znajdowały się w głównym katalogu repozytorium.

## 1. Uzupełnij tożsamość repozytorium

Nie da się z góry ustalić Twojego loginu GitHub. Z katalogu rozpakowanej paczki uruchom na Macu/Linuxie:

```bash
python3 tools/prepare_repository.py TWOJ_LOGIN
python3 tools/check_repository.py
```

Zastąp `TWOJ_LOGIN` swoim rzeczywistym loginem. Domyślna nazwa repozytorium to `ha-gdzie-sie-ukryc`. Skrypt nie łączy się z siecią. Uzupełnia `documentation`, `issue_tracker`, `codeowners` w manifeście, adresy w README, link pomocy w formularzu zgłoszeń i `.github/CODEOWNERS`.

Gdy używasz innej nazwy lub organizacji:

```bash
python3 tools/prepare_repository.py NAZWA_ORGANIZACJI --repository NAZWA_REPO --codeowner TWOJ_LOGIN
```

Na Windowsie użyj `py -3` zamiast `python3`. Wystarczy Python 3.10+; nie instaluj HA, aby tylko przygotować repozytorium.

Alternatywnie uzupełnij ręcznie `REPLACE_ME` w `manifest.json`, `README.md`, `.github/CODEOWNERS` i `.github/ISSUE_TEMPLATE/config.yml`. Adresy muszą wskazywać Twoje repozytorium, a opiekun kodu musi być rzeczywistym kontem GitHub. Nie publikuj szablonowych danych jako gotowego wydania.

## 2. Utwórz repozytorium

Na GitHubie utwórz repozytorium `ha-gdzie-sie-ukryc` w swoim koncie lub organizacji. Dla HACS ustaw **Public**, włącz **Issues** i wpisz opis:

> Home Assistant: mapa tras pieszych do pobliskich punktów schronienia z gdziesieukryc.pl.

Dodaj tematy w polu Topics: `home-assistant`, `hacs`, `custom-integration`, `poland`, `shelter`, `lovelace`.

Przy publikowaniu przez Git nie twórz osobno README ani licencji na ekranie tworzenia repozytorium: te pliki są już w paczce.

## 3. Wyślij pliki

Z rozpakowanego katalogu, po przygotowaniu metadanych:

```bash
git init -b main
git add .
git commit -m "Initial release 1.2.0"
git remote add origin https://github.com/TWOJ_LOGIN/ha-gdzie-sie-ukryc.git
git push -u origin main
```

Zmień URL na własny. Do uwierzytelnienia użyj normalnego logowania GitHub, GitHub Desktop albo swojego klienta Git. Nie wpisuj tokenu do URL ani plików projektu. Na Macu możesz również wybrać **File → Add Local Repository** w GitHub Desktop i opublikować repozytorium jako publiczne.

Możesz przesłać pliki przez stronę GitHuba, ale dopilnuj obecności `.github` z workflowami i pozostałych plików repozytorium. Do głównego katalogu wrzuć rozpakowane źródła, nie sam plik ZIP. ZIP instalacyjny jest dodatkiem do wydania.

## 4. Sprawdź Actions

Po pierwszym pushu otwórz kartę **Actions**:

- **Testy kodu**: Python, Ruff, struktura repozytorium i testy karty na Node.js.
- **Walidacja HACS**: oficjalny walidator repozytoriów typu integration. Wymaga rzeczywistego publicznego repozytorium, opisu i tematów.

Nie są potrzebne dodatkowe sekrety API. Jeśli test struktury wskazuje `REPLACE_ME`, wróć do kroku 1 i wyślij poprawione pliki. Lokalne sprawdzenie struktury nie zastępuje oficjalnego walidatora HACS na GitHubie.

## 5. Utwórz wydanie

Gdy testy przejdą, wybierz **Releases → Draft a new release**, utwórz tag **`v1.2.0`** na gałęzi `main` i opublikuj wydanie. Treść zmian znajdziesz w `CHANGELOG.md`.

Workflow **Paczka wydania** zbuduje ZIP `gdzie_sie_ukryc.zip` z całym katalogiem integracji i dołączy go do tego wydania. To paczka do instalacji ręcznej. HACS pobiera katalog integracji ze źródeł wydania, dlatego nie wymaga ręcznego dołączania ZIP-a ani ustawienia `zip_release`.

Jeśli Actions są wyłączone lub automatyczne dołączenie paczki nie zadziała, utwórz ZIP lokalnie:

```bash
python3 tools/build_release.py --tag v1.2.0
```

Dołącz `dist/gdzie_sie_ukryc.zip` do wydania. Nie commituj `dist`. Przy kolejnych wydaniach wersja manifestu i tag muszą być zgodne.

## 6. Dodaj repozytorium do HACS

W HA: **HACS → ⋮ → Repozytoria niestandardowe**, wklej URL swojego repozytorium i wybierz **Integration / Integracja**. Pobierz projekt, uruchom HA ponownie i dodaj integrację zgodnie z README. Nie trzeba zgłaszać repozytorium do głównego katalogu HACS, aby używać go jako repozytorium niestandardowego.

## Zawartość publicznego wydania

Wszystkie pliki ZIP-a są przeznaczone do umieszczenia w repozytorium. Dane testowe są fikcyjne. Nie dodawaj do niego pełnego HAR, zapisów lokalizacji domu, kopii HA, tokenów ani wyodrębnionej prywatnie listy rzeczywistych punktów. Plik `.gitignore` pomija typowe pliki tego rodzaju.

Dokumentacja zaznacza, że projekt jest niezależną integracją społecznościową i korzysta z wewnętrznego interfejsu strony. Testy nie potwierdzają dostępu z każdego hosta HA ani bieżącej dostępności punktów schronienia.

## Dokumentacja źródłowa

- [Wymagania publikacji integracji HACS](https://www.hacs.xyz/docs/publish/integration/).
- [Ogólne wymagania i wersje HACS](https://www.hacs.xyz/docs/publish/start/).
- [Repozytoria niestandardowe HACS](https://www.hacs.xyz/docs/faq/custom_repositories/).
- [Oficjalny walidator GitHub Actions HACS](https://www.hacs.xyz/docs/publish/action/).
- [Manifest integracji Home Assistant](https://developers.home-assistant.io/docs/creating_integration_manifest/).
