# Aktualizacja i publikacja na GitHubie

Paczka jest przygotowana dla **[CyberGuard-PS/ha-gdzie-sie-ukryc](https://github.com/CyberGuard-PS/ha-gdzie-sie-ukryc)**. Zawiera pełne źródła, integrację, kartę, licencje, pełną bazę CSV, pełny JSON, testy i GitHub Actions. Na GitHubie `hacs.json`, `README.md` i `custom_components` mają znajdować się w głównym katalogu repozytorium.

## Aktualizacja istniejącego repozytorium do 1.5.0

1. Otwórz swój sklonowany lokalny katalog repozytorium, np. `~/Downloads/ha-gdzie-sie-ukryc-git`. Rozpakowany ZIP nie zawiera `.git`; jeśli pracujesz tylko w takim katalogu, najpierw wykonaj kroki **Nowy checkout** poniżej. Najpierw pobierz zmiany z GitHuba:

```bash
git pull --no-rebase origin main
```

2. Rozpakuj ZIP i skopiuj **jego zawartość** do tego katalogu, zastępując pliki wcześniejszej wersji. Zachowaj istniejący katalog `.git`. Skopiuj również `.github`, inne pliki konfiguracji, `datasets` w integracji i `export` w katalogu głównym.
3. W katalogu repozytorium uruchom:

```bash
python3 tools/check_repository.py
git add .
git commit -m "Update 1.5.0: routes from current device location"
git push origin main
```

Nie trzeba ponownie wykonywać `git init` ani dodawać `origin`. Jeśli masz niezacommitowane wcześniejsze zmiany, zachowaj je przez commit lub stash przed pobraniem zmian. W razie konfliktów scal pliki i zakończ merge przed pushem.

Możesz wykonać te same kroki przez GitHub Desktop: **Fetch/Pull origin**, skopiowanie plików paczki, commit i **Push origin**.

## Nowy checkout

Jeśli nie masz lokalnego repozytorium, najpierw sklonuj istniejące:

```bash
git clone https://github.com/CyberGuard-PS/ha-gdzie-sie-ukryc.git
cd ha-gdzie-sie-ukryc
```

Następnie rozpakuj zawartość ZIP bezpośrednio do tego sklonowanego katalogu i wykonaj check, commit oraz push jak powyżej. Jeśli ZIP jest w Pobrane, możesz użyć:

```bash
unzip -o ~/Downloads/ha-gdzie-sie-ukryc-github-1.5.0.zip -d .
```

Wszystkie polecenia Git wykonuj w sklonowanym katalogu zawierającym `.git`. Dzięki temu uwzględnisz historię już istniejącą na GitHubie.

## Tożsamość i uwierzytelnienie Git

Jeśli Git zgłasza brak autora, skonfiguruj go dla tego repozytorium (zastąp wartości swoimi):

```bash
git config user.name "Piotr"
git config user.email "TWOJ_ADRES_EMAIL_LUB_GITHUB_NOREPLY"
```

GitHub nie przyjmuje hasła konta do operacji Git przez HTTPS. Możesz użyć GitHub Desktop lub, jeśli masz GitHub CLI:

```bash
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git
```

Nie wpisuj tokenu do adresu zdalnego repozytorium ani plików projektu.

## Wydanie i HACS

Po pushu sprawdź **Actions**: testy kodu i oficjalny walidator HACS. Repozytorium dla HACS powinno być publiczne, mieć opis, włączone Issues oraz tematy, np. `home-assistant`, `hacs`, `custom-integration`, `poland`, `shelter`, `lovelace`.

Gdy testy przejdą, wybierz **Releases → Draft a new release**, utwórz i opublikuj tag **`v1.5.0`** na `main`. Historia zmian jest w `CHANGELOG.md`. Workflow wydania dołączy `gdzie_sie_ukryc.zip` z całym katalogiem integracji, w tym pełną bazą CSV i licencjami.

Lokalne zbudowanie paczki instalacyjnej:

```bash
python3 tools/build_release.py --tag v1.5.0
```

Wynik: `dist/gdzie_sie_ukryc.zip`. Nie commituj `dist`. HACS pobiera katalog integracji ze źródeł wydania; nie trzeba ustawiać `zip_release`.

W HA dodaj `https://github.com/CyberGuard-PS/ha-gdzie-sie-ukryc` w **HACS → ⋮ → Repozytoria niestandardowe**, typ **Integration**. Pobierz aktualizację, uruchom HA ponownie i wybierz pełny eksport CSV zgodnie z README. Nie trzeba zgłaszać repozytorium do głównego katalogu HACS.

## Inny właściciel lub nazwa projektu

Metadane są już ustawione dla CyberGuard-PS. Dla innego repozytorium możesz uruchomić bez połączenia z siecią:

```bash
python3 tools/prepare_repository.py TWOJ_LOGIN --repository NAZWA_REPO --codeowner LOGIN_OPIEKUNA
python3 tools/check_repository.py
```

Skrypt aktualizuje manifest, adresy README, pomoc w formularzu zgłoszeń i CODEOWNERS. Jeśli CyberGuard-PS jest organizacją, ustaw `--codeowner` na rzeczywisty login opiekuna. Na Windowsie użyj `py -3` zamiast `python3`.

## Publikowane dane

Dołączony ogólnopolski eksport PSP jest oficjalnie opublikowany na **CC BY 4.0**. Możesz umieścić go w repozytorium wraz z atrybucją `DATA_LICENSE.md`, `datasets/README.md` i metadanymi. Pełny JSON jest pochodną tego eksportu. Fikcyjne dane testowe są oznaczone w przykładach.

Nie dodawaj swojego HAR, kopii konfiguracji HA, lokalizacji domu ani tokenów. Wydanie nie zawiera tych danych. Automatyczny pełny eksport nie wysyła współrzędnych stref do PSP.

## Oficjalna dokumentacja

- [Wymagania integracji HACS](https://www.hacs.xyz/docs/publish/integration/).
- [Repozytoria niestandardowe HACS](https://www.hacs.xyz/docs/faq/custom_repositories/).
- [Walidator HACS](https://www.hacs.xyz/docs/publish/action/).
- [Manifest integracji HA](https://developers.home-assistant.io/docs/creating_integration_manifest/).
- [Dane PSP i licencja](https://api.dane.gov.pl/1.4/datasets/28058,punkty-schronienia-w-polsce).
