/* Gdzie się ukryć 1.5.0 — local Lovelace card, no CDN dependency. */
const ASSET_BASE = new URL(".", import.meta.url);
const COLORS = ["#176bd6", "#cf4c16", "#7f45b9", "#058273", "#bb2970", "#69561a"];
const DEVICE_COLOR = "#d9166b";

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}

function dateLabel(value) {
  if (!value || !Number.isFinite(Date.parse(value))) return "brak danych";
  return new Date(value).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
}

function meters(value) {
  return value >= 1000 ? `${(value / 1000).toLocaleString("pl-PL", { maximumFractionDigits: 2 })} km` : `${Math.round(value)} m`;
}

function loadLeaflet() {
  if (window.__gsuLeaflet) return Promise.resolve(window.__gsuLeaflet);
  if (!window.__gsuLeafletPromise) {
    window.__gsuLeafletPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = new URL("vendor/leaflet.js", ASSET_BASE).href;
      script.onload = () => { window.__gsuLeaflet = window.L; resolve(window.__gsuLeaflet); };
      script.onerror = () => { window.__gsuLeafletPromise = null; reject(new Error("Brak lokalnego pliku vendor/leaflet.js. Zainstaluj ponownie integrację razem z katalogiem frontend.")); };
      document.head.append(script);
    });
  }
  return window.__gsuLeafletPromise;
}

class GdzieSieUkrycCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._selected = null;
    this._signature = null;
    this._data = null;
    this._map = null;
    this._loading = false;
    this._focusedPoint = null;
    this._nearbyVisible = 20;
    this._deviceRequest = 0;
    this._deviceRoute = null;
    this._deviceTarget = null;
    this._deviceStatus = "";
    this._deviceFocus = false;
  }

  setConfig(config) {
    const height = Number(config.map_height ?? 420);
    if (!Number.isFinite(height) || height < 240 || height > 1000) throw new Error("map_height: od 240 do 1000 px");
    this._config = { title: "Gdzie się ukryć", ...config, map_height: height };
    if (!this._built) this._build();
    this._title.textContent = this._config.title;
    this._mapContainer.style.height = `${height}px`;
    this._signature = null;
    this._scheduleLoad();
  }

  set hass(hass) {
    this._hass = hass;
    const signature = Object.values(hass.states ?? {}).filter(state => state.attributes?.integration === "gdzie_sie_ukryc")
      .map(state => `${state.entity_id}:${state.last_updated}`).sort().join("|");
    if (signature !== this._signature) {
      this._signature = signature;
      this._scheduleLoad();
    }
    this._updateAdmin();
  }

  connectedCallback() {
    if (this._config) this._initMap();
    this._scheduleLoad();
  }

  disconnectedCallback() {
    this._clearDeviceRoute(false);
    clearTimeout(this._loadTimer);
    this._observer?.disconnect();
    this._map?.remove();
    this._map = null;
  }

  _build() {
    this._built = true;
    const style = node("style");
    style.textContent = `
      :host {display:block} ha-card {display:block;overflow:hidden;background:var(--ha-card-background,var(--card-background-color,#fff));color:var(--primary-text-color,#1c2938);border-radius:var(--ha-card-border-radius,12px)}
      .top {padding:20px 20px 12px;display:flex;gap:12px;align-items:center;flex-wrap:wrap} h2{font-size:21px;line-height:1.25;margin:0;flex:1}
      .controls {display:flex;gap:8px;align-items:center;flex-wrap:wrap} select,button {font:inherit;font-size:14px;border:1px solid var(--divider-color,#d8e0e7);border-radius:8px;background:var(--secondary-background-color,#f6f8fb);color:inherit;padding:8px 10px;cursor:pointer}
      button:disabled{opacity:.5;cursor:wait} button:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid #3d91ee;outline-offset:2px}
      .status {padding:0 20px 12px;font-size:13px;color:var(--secondary-text-color,#59697b);line-height:1.5;white-space:pre-line}
      .map {width:100%;height:420px;background:#e8eef0;color:#172535;font:14px system-ui;z-index:0} .map .leaflet-control-attribution{font-size:10px;max-width:calc(100% - 40px)}
      .list {padding:8px 16px}.route,.point {border-bottom:1px solid var(--divider-color,#e1e6eb);padding:14px 4px;display:grid;grid-template-columns:28px 1fr;gap:10px}.route:last-child,.point:last-child{border:0}
      .number {color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px}.route h3,.point h3{font-size:15px;line-height:1.4;margin:0 0 3px}
      .route p,.point p {margin:3px 0;font-size:13px;line-height:1.5;color:var(--secondary-text-color,#59697b)}.route .metrics{font-size:15px;font-weight:600;color:var(--primary-text-color,#1c2938)}
      .nearby-list{max-height:600px;overflow-y:auto}.nearby-title{font-size:17px;margin:12px 4px 6px}.nearby-summary{font-size:13px;line-height:1.5;color:var(--secondary-text-color,#59697b);margin:6px 4px}.more-points{margin:12px 4px}
      .actions {display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}.actions a{font-size:13px;color:var(--primary-color,#176bd6);text-decoration:none;padding:5px 7px;border:1px solid var(--divider-color,#d8e0e7);border-radius:6px}.actions button{font-size:13px;padding:5px 7px}
      .notice {margin:8px 20px 0;padding:10px 12px;background:var(--secondary-background-color,#f5f7fa);border-radius:8px;font-size:13px;line-height:1.5;white-space:pre-line}.notice:empty{display:none}
      .footer{padding:12px 20px 16px;font-size:12px;line-height:1.5;color:var(--secondary-text-color,#59697b)}.footer a{color:var(--primary-color,#176bd6)}.empty{padding:16px 4px;font-size:14px;line-height:1.6}
      .pin {border:2px solid #fff;border-radius:50%;color:white;font-weight:700;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 6px #0006;font:700 14px system-ui;width:28px;height:28px;box-sizing:border-box}
      .leaflet-popup-content{font:14px/1.5 system-ui}.leaflet-popup-content p{margin:6px 0}
      .device-route{margin:12px 16px;padding:14px;border:2px solid ${DEVICE_COLOR};border-radius:10px}.device-route h3{font-size:17px;margin:0 0 8px}.device-route p{font-size:13px;line-height:1.5;margin:6px 0}.device-route .metrics{font-size:15px;font-weight:600}.device-route-button{border-color:${DEVICE_COLOR}}
      @media(max-width:450px){.top{padding:16px 14px 10px}.status{padding:0 14px 10px}.controls{width:100%}select{flex:1;max-width:100%}.footer{padding:12px 14px}.list{padding:8px 10px}.notice{margin-left:14px;margin-right:14px}}
    `;
    const css = node("link");
    css.rel = "stylesheet";
    css.href = new URL("vendor/leaflet.css", ASSET_BASE).href;
    css.onload = () => this._map?.invalidateSize();
    this._card = node("ha-card");
    const top = node("div", undefined, "top");
    this._title = node("h2");
    const controls = node("div", undefined, "controls");
    this._zones = node("select");
    this._zones.setAttribute("aria-label", "Lokalizacja początkowa");
    this._zones.addEventListener("change", () => { this._clearDeviceRoute(false); this._selected = null; this._focusedPoint = null; this._nearbyVisible = 20; this._renderLocation(true); });
    this._refresh = node("button", "Odśwież");
    this._refresh.addEventListener("click", () => this._forceRefresh());
    this._fit = node("button", "Pokaż wszystkie punkty i trasy");
    this._fit.addEventListener("click", () => { this._deviceFocus = false; this._selected = null; this._focusedPoint = null; this._renderMap(true); });
    controls.append(this._zones, this._fit, this._refresh);
    top.append(this._title, controls);
    this._status = node("div", "Ładowanie integracji…", "status");
    this._status.setAttribute("role", "status");
    this._mapContainer = node("div", undefined, "map");
    this._mapContainer.setAttribute("aria-label", "Mapa pobliskich punktów schronienia i tras");
    this._notice = node("div", undefined, "notice");
    this._notice.setAttribute("role", "status");
    this._devicePanel = node("div", undefined, "device-route");
    this._devicePanel.setAttribute("role", "status");
    this._devicePanel.setAttribute("aria-live", "polite");
    this._devicePanel.hidden = true;
    this._list = node("div", undefined, "list");
    this._pointsList = node("div", undefined, "list nearby-list");
    const footer = node("div", undefined, "footer");
    const source = node("a", "Dane punktów: gdziesieukryc.pl");
    source.href = "https://gdziesieukryc.pl/"; source.target = "_blank"; source.rel = "noopener noreferrer";
    footer.append(source, node("span", ". Wpis oznacza punkt schronienia. Dostępność i wejście sprawdź w źródle lub u zarządcy. Trasa opiera się na mapie dróg i przejść."));
    this._importButton = node("button", "Importuj punkty JSON");
    this._importButton.style.marginTop = "10px";
    this._importButton.addEventListener("click", () => this._fileInput.click());
    this._fileInput = node("input"); this._fileInput.type = "file"; this._fileInput.accept = ".json,.geojson,application/json"; this._fileInput.hidden = true;
    this._fileInput.addEventListener("change", () => this._importFile());
    footer.append(node("br"), this._importButton, this._fileInput);
    const fixMap = node("a", "Popraw mapę OpenStreetMap");
    fixMap.href = "https://www.openstreetmap.org/fixthemap"; fixMap.target = "_blank"; fixMap.rel = "noopener noreferrer";
    footer.append(node("br"), fixMap);
    this._card.append(top, this._status, this._mapContainer, this._devicePanel, this._notice, this._list, this._pointsList, footer);
    this.shadowRoot.append(css, style, this._card);
    this._updateAdmin();
    if (this.isConnected) this._initMap();
  }

  _updateAdmin() {
    if (!this._refresh) return;
    const admin = this._hass?.user?.is_admin === true;
    this._refresh.hidden = !admin;
    this._importButton.hidden = !admin || this._data?.source_mode !== "import";
  }

  async _initMap() {
    if (this._map || this._initializing || !this._mapContainer || !this.isConnected) return;
    this._initializing = true;
    try {
      this._L = await loadLeaflet();
      if (!this.isConnected) return;
      this._map = this._L.map(this._mapContainer, { zoomControl: true, scrollWheelZoom: false }).setView([52, 19], 6);
      if (this._config.show_tiles !== false) {
        this._tiles = this._L.tileLayer(this._config.tile_url ?? "https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19, attribution: this._config.tile_attribution ?? '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
        }).addTo(this._map);
        this._tiles.on("tileerror", () => { if (!this._tileError) { this._tileError = true; this._notice.textContent = "Nie udało się pobrać podkładu mapy. Zapamiętane punkty i linie tras pozostają widoczne."; } });
      }
      this._layer = this._L.featureGroup().addTo(this._map);
      this._deviceLayer = this._L.featureGroup().addTo(this._map);
      this._observer = new ResizeObserver(() => this._map?.invalidateSize());
      this._observer.observe(this._mapContainer);
      this._renderMap(true);
    } catch (error) { this._notice.textContent = error.message; }
    finally { this._initializing = false; }
  }

  _scheduleLoad() {
    clearTimeout(this._loadTimer);
    if (!this._config || !this._hass || !this.isConnected) return;
    this._loadTimer = setTimeout(() => this._load(), 150);
  }

  async _load() {
    if (this._loading) { this._reloadPending = true; return; }
    this._loading = true;
    try {
      if (!this._entryId || (this._config.entry_id && this._entryId !== this._config.entry_id)) {
        this._clearDeviceRoute(false);
        const entries = await this._hass.callWS({ type: "gdzie_sie_ukryc/list" });
        this._entryId = this._config.entry_id ?? entries[0]?.entry_id;
      }
      if (!this._entryId) { this._status.textContent = "Dodaj integrację „Gdzie się ukryć” w Ustawienia → Urządzenia i usługi."; return; }
      const oldZone = this._zones.value;
      this._data = await this._hass.callWS({ type: "gdzie_sie_ukryc/data", entry_id: this._entryId });
      this._zones.replaceChildren(...Object.values(this._data.locations ?? {}).map(location => {
        const option = node("option", location.origin.name); option.value = location.origin.id; return option;
      }));
      const preferred = oldZone || this._config.zone;
      if (preferred && this._data.locations?.[preferred]) this._zones.value = preferred;
      this._notice.textContent = "";
      this._renderLocation(oldZone !== this._zones.value);
      this._updateAdmin();
    } catch (error) {
      this._status.textContent = `Nie udało się odczytać integracji: ${error.message ?? error}`;
      if (error.code === "not_loaded") this._entryId = null;
    } finally {
      this._loading = false;
      if (this._reloadPending) { this._reloadPending = false; this._scheduleLoad(); }
    }
  }

  _location() { return this._data?.locations?.[this._zones?.value]; }

  _renderLocation(fit = false) {
    if (!this._data) return;
    const location = this._location();
    this._list.replaceChildren();
    this._pointsList.replaceChildren();
    const sourceStatus = location?.source_status ?? this._data.source_status;
    const pointsDate = location && "points_updated_at" in location ? location.points_updated_at : this._data.points_updated_at;
    const sourceError = location && "source_error" in location ? location.source_error : this._data.source_error;
    const fullDataset = this._data.source_mode === "open_data";
    const automatic = fullDataset || this._data.source_mode === "psp";
    const modes = { empty: "Brak punktów w danych źródłowych", imported: "Punkty z importu", ok: fullDataset ? "Cała opublikowana baza PSP" : automatic ? "Punkty pobrane z gdziesieukryc.pl" : "Źródło odświeżone", cached: "Punkty z ostatniego zapisu", error: "Źródło niedostępne", partial: "Część lokalizacji wymaga odświeżenia" };
    this._status.textContent = `${modes[sourceStatus] ?? "Punkty schronienia"} · dane: ${dateLabel(pointsDate)}`;
    if (fullDataset) this._status.textContent += ` · ${this._data.point_count} punktów w bazie`;
    if (fullDataset) {
      const attribution = node("p", undefined, "empty");
      const catalog = node("a", "Dane: Komenda Główna PSP (CC BY 4.0)");
      catalog.href = "https://dane.gov.pl/pl/dataset/28058,punkty-schronienia-w-polsce";
      catalog.target = "_blank"; catalog.rel = "noopener noreferrer";
      attribution.append(catalog); this._list.append(attribution);
    }
    if (!location) {
      this._list.append(node("p", this._data.origin_errors?.join(". ") || "Brak lokalizacji. W opcjach integracji wybierz strefę Dom.", "empty"));
      this._renderMap(fit); return;
    }
    const routes = location.routes ?? [];
    this._status.textContent += `\n${location.found_count} znalezionych punktów w promieniu · ${this._nearbyPoints(location).length} punktów na mapie · ${routes.length} tras · trasy: ${dateLabel(location.routes_updated_at)}`;
    const notes = [];
    if (fullDataset) notes.push(`Pełny eksport PSP, publikowany co tydzień. Ostatnie sprawdzenie: ${dateLabel(this._data.dataset?.checked_at)}.`);
    if (fullDataset && this._data.dataset?.origin === "bundled") notes.push("Używana jest baza dołączona do integracji. Odświeżenie pobierze aktualny eksport po przywróceniu dostępu.");
    if (sourceStatus === "cached") notes.push("Odświeżenie punktów nie powiodło się. Wyświetlane są ostatnie zapisane dane.");
    if (sourceError && ["cached", "error"].includes(sourceStatus)) notes.push(sourceError);
    if (location.result_limit_reached) notes.push(`Serwis zwrócił limit ${location.returned_count ?? 250} wyników. Licznik nie oznacza pełnej liczby punktów w okolicy.`);
    if (location.skipped_points) notes.push(`Pominięto ${location.skipped_points} punktów z nieprawidłowymi danymi.`);
    if (location.routing_error) notes.push("Nie udało się obliczyć części tras. Zapamiętane trasy mają oznaczenie „Zapisana trasa”.");
    const datasetAge = Date.now() - Date.parse(pointsDate);
    if (Number.isFinite(datasetAge) && datasetAge > 7 * 86400000) notes.push("Dane punktów mają ponad 7 dni. Sprawdź ich aktualność.");
    if (this._data.origin_errors?.length) notes.push(this._data.origin_errors.join(". "));
    this._notice.textContent = notes.join("\n");
    if (!routes.length) {
      const emptyMessage = sourceStatus === "error" ? "Nie udało się pobrać punktów dla tej lokalizacji. Sprawdź komunikat powyżej i użyj przycisku Odśwież po przywróceniu połączenia."
        : location.found_count > 0 ? "Punkty są widoczne na mapie i liście poniżej. Brak obliczonej trasy pieszej — sprawdź usługę tras lub otwórz nawigację do wybranego punktu."
        : this._data.source_mode === "import" && this._data.point_count === 0 ? "Zaimportuj plik JSON z punktami z serwisu. Instrukcja jest w paczce integracji."
        : fullDataset ? "W opublikowanej bazie PSP nie znaleziono punktów w wybranym promieniu. Sprawdź lokalizację Dom i promień w opcjach integracji."
        : automatic ? "Serwis nie zwrócił punktów w wybranym promieniu. Możesz zwiększyć promień w opcjach integracji."
        : "Brak znanych punktów w promieniu tej lokalizacji. Zwiększ promień lub sprawdź zakres danych źródłowych.";
      this._list.append(node("p", emptyMessage, "empty"));
    }
    routes.forEach((route, index) => {
      const row = node("div", undefined, "route");
      const color = COLORS[index % COLORS.length];
      const badge = node("div", index + 1, "number"); badge.style.background = color;
      const content = node("div");
      content.append(node("h3", route.shelter.name), node("p", route.shelter.address || "Adres niepodany"),
        node("p", `${meters(route.distance_m)} · ok. ${Math.max(1, Math.ceil(route.duration_s / 60))} min pieszo`, "metrics"),
        node("p", `${route.shelter.category} · dostępność: ${route.shelter.availability}`));
      if (route.status === "cached") content.append(node("p", `Zapisana trasa · obliczona ${dateLabel(route.calculated_at)}`));
      if (route.end_gap_m > 10 || route.start_gap_m > 10) content.append(node("p", `Mapa kończy trasę przy sieci dróg. Odcinek do punktu (${meters(route.end_gap_m)}) i właściwe wejście wymagają sprawdzenia.`));
      const actions = node("div", undefined, "actions");
      const show = node("button", "Pokaż trasę");
      show.addEventListener("click", () => { this._deviceFocus = false; this._focusedPoint = null; this._selected = route.shelter.id; this._renderMap(true); });
      actions.append(show, this._deviceButton(route.shelter), ...this._navigationLinks(location.origin, route.shelter));
      content.append(actions); row.append(badge, content); this._list.append(row);
    });
    if (location.unrouted?.length) this._list.append(node("p", `${location.unrouted.length} kandydatów bez nowej trasy: widoczne jako szare punkty.`, "empty"));
    this._renderNearby(location);
    this._renderMap(fit);
  }

  _nearbyPoints(location) {
    if (Array.isArray(location?.nearby)) return location.nearby;
    // Older backends still expose routed/failed candidates, but not a nearby list.
    const points = new Map();
    for (const point of [...(location?.routes ?? []), ...(location?.unrouted ?? [])]) points.set(point.shelter.id, point);
    return [...points.values()].sort((a, b) => (a.straight_distance_m ?? 0) - (b.straight_distance_m ?? 0));
  }

  _renderNearby(location) {
    this._pointsList.replaceChildren();
    const points = this._nearbyPoints(location);
    this._pointsList.hidden = !points.length;
    if (!points.length) return;
    this._pointsList.append(node("h3", "Punkty w okolicy", "nearby-title"));
    const summary = `Na mapie ${points.length} najbliższych z ${location.found_count} punktów w promieniu. Lista według odległości w linii prostej.`;
    this._pointsList.append(node("p", summary + (location.nearby_truncated ? " Liczbę punktów na mapie i liście zwiększysz w opcjach integracji." : ""), "nearby-summary"));
    points.slice(0, this._nearbyVisible).forEach((point, index) => {
      const shelter = point.shelter;
      const row = node("div", undefined, "point");
      const badge = node("div", index + 1, "number"); badge.style.background = "#058273";
      const content = node("div");
      content.append(node("h3", shelter.name), node("p", shelter.address || "Adres niepodany", "point-address"));
      if (Number.isFinite(point.straight_distance_m)) content.append(node("p", `${meters(point.straight_distance_m)} w linii prostej`, "point-distance"));
      content.append(node("p", `${shelter.category ?? "Punkt schronienia"} · dostępność: ${shelter.availability ?? "Brak informacji"}`));
      const actions = node("div", undefined, "actions");
      const show = node("button", "Pokaż punkt");
      show.addEventListener("click", () => { this._deviceFocus = false; this._selected = null; this._focusedPoint = shelter.id; this._renderMap(true); });
      actions.append(show, this._deviceButton(shelter), ...this._navigationLinks(location.origin, shelter));
      content.append(actions); row.append(badge, content); this._pointsList.append(row);
    });
    if (points.length > this._nearbyVisible) {
      const more = node("button", `Pokaż kolejne ${Math.min(20, points.length - this._nearbyVisible)} punktów`, "more-points");
      more.addEventListener("click", () => { this._nearbyVisible += 20; this._renderNearby(location); });
      this._pointsList.append(more);
    }
  }

  _navigationLinks(origin, shelter) {
    const end = `${shelter.latitude},${shelter.longitude}`;
    const google = new URL("https://www.google.com/maps/dir/");
    const googleParams = new URLSearchParams({ api: "1", destination: end, travelmode: "walking" });
    const apple = new URL("https://maps.apple.com/");
    const appleParams = new URLSearchParams({ daddr: end, dirflg: "w" });
    if (origin) {
      const start = `${origin.latitude},${origin.longitude}`;
      googleParams.set("origin", start); appleParams.set("saddr", start);
    }
    google.search = googleParams; apple.search = appleParams;
    return [["Google Maps", google], ["Apple Maps", apple]].map(([label, url]) => {
      const link = node("a", label); link.href = url.href; link.target = "_blank"; link.rel = "noopener noreferrer"; return link;
    });
  }

  _deviceButton(shelter) {
    const button = node("button", "Trasa z mojej lokalizacji", "device-route-button");
    button.type = "button";
    button.addEventListener("click", () => this._routeFromDevice(shelter));
    return button;
  }

  _getDevicePosition() {
    if (window.isSecureContext === false) return Promise.reject(new Error("Lokalizacja wymaga HTTPS. Otwórz Home Assistant przez adres HTTPS; zwykły adres HTTP w sieci lokalnej nie udostępnia położenia przeglądarce."));
    if (typeof navigator.geolocation?.getCurrentPosition !== "function") return Promise.reject(new Error("Przeglądarka lub aplikacja nie udostępnia lokalizacji. Otwórz panel w Safari, Chrome lub Firefox przez HTTPS."));
    return new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(position => {
      const { latitude, longitude, accuracy } = position?.coords ?? {};
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
        reject(new Error("Urządzenie nie zwróciło poprawnego położenia.")); return;
      }
      const captured = Number.isFinite(position?.timestamp) && Number.isFinite(new Date(position.timestamp).getTime()) ? position.timestamp : Date.now();
      resolve({ latitude, longitude, accuracy_m: Number.isFinite(accuracy) && accuracy >= 0 ? accuracy : null, located_at: new Date(captured).toISOString() });
    }, error => {
      const messages = {
        1: "Brak zgody na lokalizację. Zezwól tej stronie lub aplikacji na dostęp do położenia w ustawieniach urządzenia i spróbuj ponownie.",
        2: "Nie można ustalić położenia. Włącz usługi lokalizacji urządzenia i spróbuj ponownie.",
        3: "Minął czas oczekiwania na położenie. Spróbuj ponownie, gdy urządzenie może ustalić lokalizację.",
      };
      reject(new Error(messages[error?.code] ?? "Nie udało się odczytać lokalizacji urządzenia."));
    }, { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 }));
  }

  async _routeFromDevice(shelter) {
    if (!this._entryId || !this._hass || !this.isConnected) return;
    const request = ++this._deviceRequest;
    const entryId = this._entryId;
    const hass = this._hass;
    const current = () => request === this._deviceRequest && entryId === this._entryId && this.isConnected;
    this._deviceRoute = null; this._deviceTarget = shelter; this._deviceFocus = false;
    this._deviceStatus = "Ustalanie aktualnej lokalizacji tego urządzenia…";
    this._renderDeviceRoute(); this._renderMap();
    try {
      const position = await this._getDevicePosition();
      if (!current()) return;
      this._deviceStatus = "Wyznaczanie trasy pieszej z odczytanego położenia…";
      this._renderDeviceRoute();
      const result = await hass.callWS({ type: "gdzie_sie_ukryc/route_from_device", entry_id: entryId, point_id: shelter.id, latitude: position.latitude, longitude: position.longitude });
      if (!current()) return;
      this._deviceRoute = { ...result, accuracy_m: position.accuracy_m, located_at: position.located_at };
      this._deviceTarget = result.route.shelter; this._deviceStatus = ""; this._deviceFocus = true;
      this._selected = null; this._focusedPoint = null;
      this._renderDeviceRoute(); this._renderMap(true);
    } catch (error) {
      if (!current()) return;
      this._deviceStatus = `Nie udało się wyznaczyć trasy z mojej lokalizacji. ${error.message ?? error}`;
      this._renderDeviceRoute();
    }
  }

  _clearDeviceRoute(render = true) {
    ++this._deviceRequest;
    this._deviceRoute = null; this._deviceTarget = null; this._deviceStatus = ""; this._deviceFocus = false;
    this._deviceLayer?.clearLayers();
    this._renderDeviceRoute();
    if (render) this._renderMap(true);
  }

  _renderDeviceRoute() {
    if (!this._devicePanel) return;
    this._devicePanel.replaceChildren();
    this._devicePanel.hidden = !this._deviceTarget;
    if (!this._deviceTarget) return;
    const device = this._deviceRoute;
    const shelter = this._deviceTarget;
    this._devicePanel.append(node("h3", "Trasa z mojej lokalizacji"), node("strong", shelter.name), node("p", shelter.address || "Adres niepodany"));
    if (this._deviceStatus) this._devicePanel.append(node("p", this._deviceStatus));
    if (device) {
      const route = device.route;
      this._devicePanel.append(node("p", `${meters(route.distance_m)} · ok. ${Math.max(1, Math.ceil(route.duration_s / 60))} min pieszo`, "metrics"), node("p", `Położenie odczytano: ${dateLabel(device.located_at)} · trasę obliczono: ${dateLabel(route.calculated_at)}`));
      if (device.accuracy_m !== null) this._devicePanel.append(node("p", `Dokładność lokalizacji urządzenia: ok. ${meters(device.accuracy_m)}.`));
      if (device.accuracy_m > 100) this._devicePanel.append(node("p", "Położenie jest mało dokładne. Odśwież moją trasę po uzyskaniu dokładniejszej lokalizacji."));
      if (route.start_gap_m > 10 || route.end_gap_m > 10) this._devicePanel.append(node("p", `Przerywane odcinki do sieci dróg: początek ${meters(route.start_gap_m)}, dojście do punktu ${meters(route.end_gap_m)}. Przejście i wejście wymagają sprawdzenia.`));
      if (["cached", "error"].includes(device.source_status)) this._devicePanel.append(node("p", `Punkt pochodzi z ostatniej zapisanej bazy: ${dateLabel(device.points_updated_at)}.`));
    }
    const actions = node("div", undefined, "actions");
    if (device) {
      const show = node("button", "Pokaż moją trasę");
      show.addEventListener("click", () => { this._deviceFocus = true; this._selected = null; this._focusedPoint = null; this._renderMap(true); });
      const refresh = node("button", "Odśwież moją trasę");
      refresh.addEventListener("click", () => this._routeFromDevice(shelter));
      actions.append(show, refresh, ...this._navigationLinks(device.origin, shelter));
    } else if (this._deviceStatus.startsWith("Nie udało")) {
      actions.append(this._deviceButton(shelter), ...this._navigationLinks(null, shelter));
      this._devicePanel.append(node("p", "Możesz też otworzyć Google Maps lub Apple Maps — nawigacja ustali punkt startowy na urządzeniu, jeśli ma dostęp do lokalizacji."));
    }
    const close = node("button", device ? "Ukryj moją trasę" : "Zamknij");
    close.addEventListener("click", () => this._clearDeviceRoute());
    actions.append(close); this._devicePanel.append(actions);
  }

  _marker(lat, lon, text, color, popup, layer = this._layer) {
    const pin = node("div", text, "pin"); pin.style.background = color;
    return this._L.marker([lat, lon], { icon: this._L.divIcon({ html: pin, className: "", iconSize: [28, 28], iconAnchor: [14, 14] }) })
      .bindPopup(popup).addTo(layer);
  }

  _renderMap(fit = false) {
    if (!this._map || !this._layer) return;
    this._layer.clearLayers();
    this._deviceLayer?.clearLayers();
    this._mapMarkers = new Map();
    const location = this._location();
    if (!location) { this._renderDeviceMap(); return; }
    const origin = location.origin;
    this._marker(origin.latitude, origin.longitude, "D", "#273c50", node("strong", origin.name));
    let selectedLine = null;
    (location.routes ?? []).forEach((route, index) => {
      const color = COLORS[index % COLORS.length];
      const selected = this._selected === route.shelter.id;
      const line = this._L.geoJSON(route.geometry, { style: { color, weight: selected ? 6 : 4, opacity: this._deviceFocus || (this._selected && !selected) ? .35 : .9, dashArray: route.status === "cached" ? "8 6" : undefined } }).addTo(this._layer);
      line.on("click", () => { this._deviceFocus = false; this._focusedPoint = null; this._selected = route.shelter.id; this._renderMap(true); });
      if (selected) selectedLine = line;
      const coords = route.geometry.coordinates;
      if (route.end_gap_m > 10) this._L.polyline([[coords.at(-1)[1], coords.at(-1)[0]], [route.shelter.latitude, route.shelter.longitude]], { color: "#657789", weight: 2, dashArray: "3 6" }).bindTooltip("Odcinek do punktu: przejście i wejście niepotwierdzone").addTo(this._layer);
      if (route.start_gap_m > 10) this._L.polyline([[origin.latitude, origin.longitude], [coords[0][1], coords[0][0]]], { color: "#657789", weight: 2, dashArray: "3 6" }).bindTooltip("Odcinek początkowy: przejście niepotwierdzone").addTo(this._layer);
    });
    const points = new Map(this._nearbyPoints(location).map(point => [point.shelter.id, point]));
    for (const point of [...(location.routes ?? []), ...(location.unrouted ?? [])]) if (!points.has(point.shelter.id)) points.set(point.shelter.id, point);
    const failed = new Set((location.unrouted ?? []).map(point => point.shelter.id));
    const routes = new Map((location.routes ?? []).map((route, index) => [route.shelter.id, { route, index }]));
    for (const point of points.values()) {
      const shelter = point.shelter;
      const routed = routes.get(shelter.id);
      const color = routed ? COLORS[routed.index % COLORS.length] : failed.has(shelter.id) ? "#657789" : "#058273";
      const popup = node("div");
      popup.append(node("strong", shelter.name), node("p", shelter.address || "Adres niepodany"));
      if (Number.isFinite(point.straight_distance_m)) popup.append(node("p", `${meters(point.straight_distance_m)} w linii prostej`));
      if (routed) popup.append(node("p", `${meters(routed.route.distance_m)} · ${Math.ceil(routed.route.duration_s / 60)} min pieszo`));
      popup.append(node("p", `${shelter.category ?? "Punkt schronienia"} · dostępność: ${shelter.availability ?? "Brak informacji"}`));
      popup.append(this._deviceButton(shelter));
      const marker = this._marker(shelter.latitude, shelter.longitude, routed ? routed.index + 1 : failed.has(shelter.id) ? "?" : "•", color, popup);
      marker.bindTooltip(node("span", [shelter.name, shelter.address].filter(Boolean).join(" — ")));
      this._mapMarkers.set(shelter.id, marker);
    }
    const deviceBounds = this._renderDeviceMap();
    if (this._focusedPoint && !this._mapMarkers.has(this._focusedPoint)) this._focusedPoint = null;
    if (fit) {
      this._map.invalidateSize();
      const focused = this._mapMarkers.get(this._focusedPoint);
      if (focused) {
        this._map.setView(focused.getLatLng(), 17, { animate: false }); focused.openPopup();
      } else {
        const bounds = this._deviceFocus && deviceBounds?.isValid() ? deviceBounds : selectedLine?.getBounds() ?? this._layer.getBounds().extend(this._deviceLayer.getBounds());
        if (bounds.isValid()) this._map.fitBounds(bounds.pad(.12), { maxZoom: 16, animate: false });
      }
    }
  }

  _renderDeviceMap() {
    const device = this._deviceRoute;
    if (!device || !this._deviceLayer) return null;
    const { origin, route } = device;
    const shelter = route.shelter;
    const popup = node("div");
    popup.append(node("strong", "Moja lokalizacja"), node("p", `Odczyt: ${dateLabel(device.located_at)}`));
    if (device.accuracy_m !== null) popup.append(node("p", `Dokładność: ok. ${meters(device.accuracy_m)}`));
    this._marker(origin.latitude, origin.longitude, "J", DEVICE_COLOR, popup, this._deviceLayer);
    if (device.accuracy_m > 0 && device.accuracy_m <= 1000) this._L.circle([origin.latitude, origin.longitude], { radius: device.accuracy_m, color: DEVICE_COLOR, weight: 1, fillOpacity: .08, interactive: false, className: "device-accuracy" }).addTo(this._deviceLayer);
    const line = this._L.geoJSON(route.geometry, { style: { color: DEVICE_COLOR, weight: 6, opacity: .95, className: "device-path" } }).bindTooltip("Trasa z lokalizacji tego urządzenia").addTo(this._deviceLayer);
    line.on("click", () => { this._deviceFocus = true; this._selected = null; this._focusedPoint = null; this._renderMap(true); });
    const coords = route.geometry.coordinates;
    if (route.start_gap_m > 10) this._L.polyline([[origin.latitude, origin.longitude], [coords[0][1], coords[0][0]]], { color: DEVICE_COLOR, weight: 2, dashArray: "3 6", className: "device-gap" }).bindTooltip("Dojście do sieci dróg: przejście niepotwierdzone").addTo(this._deviceLayer);
    if (route.end_gap_m > 10) this._L.polyline([[coords.at(-1)[1], coords.at(-1)[0]], [shelter.latitude, shelter.longitude]], { color: DEVICE_COLOR, weight: 2, dashArray: "3 6", className: "device-gap" }).bindTooltip("Dojście do punktu: przejście i wejście niepotwierdzone").addTo(this._deviceLayer);
    if (!this._mapMarkers.has(shelter.id)) {
      const targetPopup = node("div");
      targetPopup.append(node("strong", shelter.name), node("p", shelter.address || "Adres niepodany"), this._deviceButton(shelter));
      const marker = this._marker(shelter.latitude, shelter.longitude, "C", DEVICE_COLOR, targetPopup, this._deviceLayer);
      marker.bindTooltip(node("span", [shelter.name, shelter.address].filter(Boolean).join(" — ")));
      this._mapMarkers.set(shelter.id, marker);
    }
    return this._deviceLayer.getBounds().extend([shelter.latitude, shelter.longitude]);
  }

  async _forceRefresh() {
    if (!this._entryId) return;
    this._refresh.disabled = true;
    this._notice.textContent = "Pobieranie punktów i obliczanie tras…";
    this._selected = null;
    this._focusedPoint = null;
    try {
      await this._hass.callWS({ type: "gdzie_sie_ukryc/refresh", entry_id: this._entryId });
      await this._load();
    } catch (error) { this._notice.textContent = error.message ?? String(error); }
    finally { this._refresh.disabled = false; }
  }

  async _importFile() {
    const file = this._fileInput.files?.[0];
    this._fileInput.value = "";
    if (!file || !this._entryId) return;
    this._importButton.disabled = true;
    try {
      if (file.size > 8 * 1024 * 1024) throw new Error("Plik przekracza 8 MiB. Użyj importera do pliku lokalnego.");
      let payload = JSON.parse(await file.text());
      if (payload.log?.entries) throw new Error("Plik HAR przetwórz lokalnie narzędziem tools/import_points.py z paczki.");
      if (Array.isArray(payload)) payload = { points: payload };
      this._notice.textContent = "Import punktów i obliczanie tras…";
      const result = await this._hass.callWS({ type: "gdzie_sie_ukryc/import", entry_id: this._entryId, payload });
      await this._load();
      this._notice.textContent = `Zaimportowano ${result.imported} punktów. Pominięto: ${result.skipped}.`;
    } catch (error) { this._notice.textContent = error.message ?? String(error); }
    finally { this._importButton.disabled = false; }
  }

  getCardSize() { return Math.ceil((this._config?.map_height ?? 420) / 50) + 6; }
  getGridOptions() { return { columns: 12, min_columns: 6, rows: "auto" }; }
  static getStubConfig() { return { type: "custom:gdzie-sie-ukryc-card", title: "Gdzie się ukryć", zone: "zone.home", map_height: 420 }; }
}

if (!customElements.get("gdzie-sie-ukryc-card")) customElements.define("gdzie-sie-ukryc-card", GdzieSieUkrycCard);
window.customCards = window.customCards ?? [];
if (!window.customCards.some(card => card.type === "gdzie-sie-ukryc-card")) window.customCards.push({ type: "gdzie-sie-ukryc-card", name: "Gdzie się ukryć", description: "Punkty schronienia i trasy piesze ze stref HA lub położenia urządzenia", preview: false });
