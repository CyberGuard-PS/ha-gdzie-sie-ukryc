/* Gdzie się ukryć 1.2.0 — local Lovelace card, no CDN dependency. */
const ASSET_BASE = new URL(".", import.meta.url);
const COLORS = ["#176bd6", "#cf4c16", "#7f45b9", "#058273", "#bb2970", "#69561a"];

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
      .list {padding:8px 16px}.route {border-bottom:1px solid var(--divider-color,#e1e6eb);padding:14px 4px;display:grid;grid-template-columns:28px 1fr;gap:10px}.route:last-child{border:0}
      .number {color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px}.route h3{font-size:15px;line-height:1.4;margin:0 0 3px}
      .route p {margin:3px 0;font-size:13px;line-height:1.5;color:var(--secondary-text-color,#59697b)}.route .metrics{font-size:15px;font-weight:600;color:var(--primary-text-color,#1c2938)}
      .actions {display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}.actions a{font-size:13px;color:var(--primary-color,#176bd6);text-decoration:none;padding:5px 7px;border:1px solid var(--divider-color,#d8e0e7);border-radius:6px}.actions button{font-size:13px;padding:5px 7px}
      .notice {margin:8px 20px 0;padding:10px 12px;background:var(--secondary-background-color,#f5f7fa);border-radius:8px;font-size:13px;line-height:1.5;white-space:pre-line}.notice:empty{display:none}
      .footer{padding:12px 20px 16px;font-size:12px;line-height:1.5;color:var(--secondary-text-color,#59697b)}.footer a{color:var(--primary-color,#176bd6)}.empty{padding:16px 4px;font-size:14px;line-height:1.6}
      .pin {border:2px solid #fff;border-radius:50%;color:white;font-weight:700;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 6px #0006;font:700 14px system-ui;width:28px;height:28px;box-sizing:border-box}
      .leaflet-popup-content{font:14px/1.5 system-ui}.leaflet-popup-content p{margin:6px 0}
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
    this._zones.addEventListener("change", () => { this._selected = null; this._renderLocation(true); });
    this._refresh = node("button", "Odśwież");
    this._refresh.addEventListener("click", () => this._forceRefresh());
    this._fit = node("button", "Pokaż wszystkie trasy");
    this._fit.addEventListener("click", () => { this._selected = null; this._renderMap(true); });
    controls.append(this._zones, this._fit, this._refresh);
    top.append(this._title, controls);
    this._status = node("div", "Ładowanie integracji…", "status");
    this._status.setAttribute("role", "status");
    this._mapContainer = node("div", undefined, "map");
    this._mapContainer.setAttribute("aria-label", "Mapa tras do punktów schronienia");
    this._notice = node("div", undefined, "notice");
    this._notice.setAttribute("role", "status");
    this._list = node("div", undefined, "list");
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
    this._card.append(top, this._status, this._mapContainer, this._notice, this._list, footer);
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
    const sourceStatus = location?.source_status ?? this._data.source_status;
    const pointsDate = location && "points_updated_at" in location ? location.points_updated_at : this._data.points_updated_at;
    const sourceError = location && "source_error" in location ? location.source_error : this._data.source_error;
    const automatic = this._data.source_mode === "psp";
    const modes = { empty: "Brak punktów w danych źródłowych", imported: "Punkty z importu", ok: automatic ? "Punkty pobrane z gdziesieukryc.pl" : "Źródło odświeżone", cached: "Punkty z ostatniego zapisu", error: "Źródło niedostępne", partial: "Część lokalizacji wymaga odświeżenia" };
    this._status.textContent = `${modes[sourceStatus] ?? "Punkty schronienia"} · dane: ${dateLabel(pointsDate)}`;
    if (!location) {
      this._list.append(node("p", this._data.origin_errors?.join(". ") || "Brak lokalizacji. W opcjach integracji wybierz strefę Dom.", "empty"));
      this._renderMap(fit); return;
    }
    const routes = location.routes ?? [];
    this._status.textContent += `\n${location.found_count} znalezionych punktów w promieniu · ${routes.length} tras · trasy: ${dateLabel(location.routes_updated_at)}`;
    const notes = [];
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
        : location.found_count > 0 ? "Punkty znalezione; brak obliczonej trasy pieszej. Sprawdź usługę tras i odśwież."
        : this._data.source_mode === "import" && this._data.point_count === 0 ? "Zaimportuj plik JSON z punktami z serwisu. Instrukcja jest w paczce integracji."
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
      show.addEventListener("click", () => { this._selected = route.shelter.id; this._renderMap(true); });
      actions.append(show, ...this._navigationLinks(location.origin, route.shelter));
      content.append(actions); row.append(badge, content); this._list.append(row);
    });
    if (location.unrouted?.length) this._list.append(node("p", `${location.unrouted.length} kandydatów bez nowej trasy: widoczne jako szare punkty.`, "empty"));
    this._renderMap(fit);
  }

  _navigationLinks(origin, shelter) {
    const start = `${origin.latitude},${origin.longitude}`;
    const end = `${shelter.latitude},${shelter.longitude}`;
    const google = new URL("https://www.google.com/maps/dir/");
    google.search = new URLSearchParams({ api: "1", origin: start, destination: end, travelmode: "walking" });
    const apple = new URL("https://maps.apple.com/");
    apple.search = new URLSearchParams({ saddr: start, daddr: end, dirflg: "w" });
    return [["Google Maps", google], ["Apple Maps", apple]].map(([label, url]) => {
      const link = node("a", label); link.href = url.href; link.target = "_blank"; link.rel = "noopener noreferrer"; return link;
    });
  }

  _marker(lat, lon, text, color, popup) {
    const pin = node("div", text, "pin"); pin.style.background = color;
    return this._L.marker([lat, lon], { icon: this._L.divIcon({ html: pin, className: "", iconSize: [28, 28], iconAnchor: [14, 14] }) })
      .bindPopup(popup).addTo(this._layer);
  }

  _renderMap(fit = false) {
    if (!this._map || !this._layer) return;
    this._layer.clearLayers();
    const location = this._location();
    if (!location) return;
    const origin = location.origin;
    this._marker(origin.latitude, origin.longitude, "D", "#273c50", node("strong", origin.name));
    let selectedLine = null;
    (location.routes ?? []).forEach((route, index) => {
      const color = COLORS[index % COLORS.length];
      const selected = this._selected === route.shelter.id;
      const line = this._L.geoJSON(route.geometry, { style: { color, weight: selected ? 6 : 4, opacity: this._selected && !selected ? .35 : .9, dashArray: route.status === "cached" ? "8 6" : undefined } }).addTo(this._layer);
      line.on("click", () => { this._selected = route.shelter.id; this._renderMap(true); });
      if (selected) selectedLine = line;
      const popup = node("div"); popup.append(node("strong", `${index + 1}. ${route.shelter.name}`), node("p", route.shelter.address), node("p", `${meters(route.distance_m)} · ${Math.ceil(route.duration_s / 60)} min pieszo`));
      this._marker(route.shelter.latitude, route.shelter.longitude, index + 1, color, popup);
      const coords = route.geometry.coordinates;
      if (route.end_gap_m > 10) this._L.polyline([[coords.at(-1)[1], coords.at(-1)[0]], [route.shelter.latitude, route.shelter.longitude]], { color: "#657789", weight: 2, dashArray: "3 6" }).bindTooltip("Odcinek do punktu: przejście i wejście niepotwierdzone").addTo(this._layer);
      if (route.start_gap_m > 10) this._L.polyline([[origin.latitude, origin.longitude], [coords[0][1], coords[0][0]]], { color: "#657789", weight: 2, dashArray: "3 6" }).bindTooltip("Odcinek początkowy: przejście niepotwierdzone").addTo(this._layer);
    });
    (location.unrouted ?? []).forEach(point => this._marker(point.shelter.latitude, point.shelter.longitude, "?", "#657789", node("div", `${point.shelter.name} · brak nowej trasy`)));
    if (fit) {
      this._map.invalidateSize();
      const bounds = selectedLine?.getBounds() ?? this._layer.getBounds();
      if (bounds.isValid()) this._map.fitBounds(bounds.pad(.12), { maxZoom: 16, animate: false });
    }
  }

  async _forceRefresh() {
    if (!this._entryId) return;
    this._refresh.disabled = true;
    this._notice.textContent = "Pobieranie punktów i obliczanie tras…";
    this._selected = null;
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
if (!window.customCards.some(card => card.type === "gdzie-sie-ukryc-card")) window.customCards.push({ type: "gdzie-sie-ukryc-card", name: "Gdzie się ukryć", description: "Trasy piesze do punktów schronienia z wybranych stref HA", preview: false });
