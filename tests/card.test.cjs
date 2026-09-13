/* DOM tests using the actual card and bundled Leaflet; no browser control. */
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const { JSDOM } = require(process.env.GSU_JSDOM_PATH || "jsdom");
const root = resolve(__dirname, "..");
const original = JSON.parse(readFileSync(resolve(__dirname, "browser_data.json"), "utf8"));
const pause = (ms) => new Promise((done) => setTimeout(done, ms));

async function mount(admin = true) {
  const dom = new JSDOM("<!doctype html><body></body>", { url: "http://ha.test/", runScripts: "outside-only", pretendToBeVisual: true });
  const { window } = dom;
  window.ResizeObserver = class { observe() {} disconnect() {} };
  window.SVGSVGElement.prototype.createSVGRect = () => ({});
  for (const key of ["clientWidth", "offsetWidth"]) Object.defineProperty(window.HTMLElement.prototype, key, { get() { return parseInt(this.style.width, 10) || 900; } });
  for (const key of ["clientHeight", "offsetHeight"]) Object.defineProperty(window.HTMLElement.prototype, key, { get() { return parseInt(this.style.height, 10) || 420; } });
  window.eval(readFileSync(resolve(root, "custom_components/gdzie_sie_ukryc/frontend/vendor/leaflet.js"), "utf8"));
  window.__gsuLeaflet = window.L;
  const source = readFileSync(resolve(root, "custom_components/gdzie_sie_ukryc/frontend/gdzie-sie-ukryc-card.js"), "utf8")
    .replace("import.meta.url", JSON.stringify("http://ha.test/gdzie_sie_ukryc/frontend/gdzie-sie-ukryc-card.js"));
  window.eval(source);
  let data = structuredClone(original);
  const calls = [];
  const hass = { states: {}, user: { is_admin: admin }, async callWS(message) {
    calls.push(message);
    if (message.type.endsWith("/list")) return [{ entry_id: "test" }];
    if (message.type.endsWith("/data")) return structuredClone(data);
    if (message.type.endsWith("/refresh")) return { updated: true };
    if (message.type.endsWith("/import")) return { imported: message.payload.points.length, skipped: 0 };
    throw new Error("Unknown command");
  }};
  const card = window.document.createElement("gdzie-sie-ukryc-card");
  card.setConfig({ map_height: 420, show_tiles: false });
  window.document.body.append(card);
  card.hass = hass;
  await pause(250);
  return { dom, window, card, hass, calls, setData(value) { data = value; }, close() { card.remove(); dom.window.close(); } };
}

test("national CSV mode shows full coverage, attribution and bundled fallback", async () => {
  const fixture = await mount();
  try {
    const data = structuredClone(original);
    Object.assign(data, {
      source_mode: "open_data", source_status: "ok", point_count: 85739,
      dataset: { origin: "live", checked_at: data.points_updated_at },
    });
    Object.assign(data.locations["zone.home"], {
      source_status: "ok", source_error: null, found_count: 500,
      result_limit_reached: false,
    });
    fixture.setData(data);
    await fixture.card._load();
    assert.equal(fixture.card._importButton.hidden, true);
    assert.match(fixture.card._status.textContent, /85739 punktów w bazie/);
    assert.match(fixture.card._status.textContent, /500 znalezionych/);
    assert.match(fixture.card._notice.textContent, /co tydzień/);
    assert.doesNotMatch(fixture.card._notice.textContent, /limit 250/);
    const attribution = [...fixture.card.shadowRoot.querySelectorAll("a")].find(link => /CC BY 4.0/.test(link.textContent));
    assert.equal(attribution.href, "https://dane.gov.pl/pl/dataset/28058,punkty-schronienia-w-polsce");
    data.dataset.origin = "bundled";
    Object.assign(data.locations["zone.home"], { source_status: "cached", source_error: "Eksport CSV PSP: HTTP 403" });
    fixture.setData(data);
    await fixture.card._load();
    assert.match(fixture.card._notice.textContent, /baza dołączona/);
    assert.match(fixture.card._notice.textContent, /403/);
    assert.equal(fixture.card.shadowRoot.querySelectorAll(".route").length, 3);
  } finally { fixture.close(); }
});

test("card draws real route geometries, switches zones and resets selected route", async () => {
  const fixture = await mount();
  try {
    const { card, window } = fixture;
    assert.equal(card.shadowRoot.querySelectorAll(".route").length, 3);
    assert.equal(card.shadowRoot.querySelectorAll(".leaflet-overlay-pane svg path").length, 3);
    assert.match(card.shadowRoot.textContent, /min pieszo/);
    const select = card.shadowRoot.querySelector("select");
    assert.equal(select.options.length, 2);
    select.value = "zone.work";
    select.dispatchEvent(new window.Event("change"));
    assert.equal(card.shadowRoot.querySelectorAll(".route").length, 2);
    card.shadowRoot.querySelector(".actions button").click();
    assert.ok(card._selected);
    [...card.shadowRoot.querySelectorAll("button")].find(button => button.textContent === "Pokaż wszystkie trasy").click();
    assert.equal(card._selected, null);
    const google = new URL(card.shadowRoot.querySelector(".actions a").href);
    assert.equal(google.searchParams.get("travelmode"), "walking");
    assert.equal(google.searchParams.get("origin"), "50.296,18.67");
    const apple = new URL(card.shadowRoot.querySelectorAll(".actions a")[1].href);
    assert.equal(apple.searchParams.get("dirflg"), "w");
  } finally { fixture.close(); }
});

test("cached routes show their date and dashed geometry; empty imports show instructions", async () => {
  const fixture = await mount();
  try {
    const data = structuredClone(original);
    data.source_status = "cached";
    Object.values(data.locations).forEach(location => {
      location.routing_error = "HTTP 503";
      location.routes.forEach(route => route.status = "cached");
    });
    fixture.setData(data);
    await fixture.card._load();
    assert.match(fixture.card.shadowRoot.textContent, /Zapisana trasa/);
    assert.ok(fixture.card.shadowRoot.querySelector('svg path[stroke-dasharray="8 6"]'));
    data.point_count = 0;
    data.source_status = "empty";
    Object.values(data.locations).forEach(location => { location.routes = []; location.found_count = 0; location.routing_error = null; });
    fixture.setData(data);
    await fixture.card._load();
    assert.equal(fixture.card.shadowRoot.querySelectorAll(".route").length, 0);
    assert.match(fixture.card.shadowRoot.querySelector(".empty").textContent, /Zaimportuj plik JSON/);
  } finally { fixture.close(); }
});

test("untrusted point names remain text and non-admin import controls are hidden", async () => {
  const fixture = await mount(false);
  try {
    const data = structuredClone(original);
    data.locations["zone.home"].routes[0].shelter.name = '<img id="injected" src=x onerror="alert(1)">';
    fixture.setData(data);
    await fixture.card._load();
    assert.equal(fixture.card.shadowRoot.querySelector("#injected"), null);
    assert.match(fixture.card.shadowRoot.querySelector("h3").textContent, /<img id=/);
    assert.equal(fixture.card._refresh.hidden, true);
    assert.equal(fixture.card._importButton.hidden, true);
    assert.equal(fixture.card.shadowRoot.querySelector(".actions a").hidden, false);
  } finally { fixture.close(); }
});

test("card remounts its map without leaking Leaflet state", async () => {
  const fixture = await mount();
  try {
    fixture.card.remove();
    assert.equal(fixture.card._map, null);
    fixture.window.document.body.append(fixture.card);
    await pause(250);
    assert.equal(fixture.card.shadowRoot.querySelectorAll(".leaflet-overlay-pane svg path").length, 3);
    assert.ok(fixture.card._map);
  } finally { fixture.close(); }
});

test("automatic mode reports each zone's own data status, date and result limit", async () => {
  const fixture = await mount();
  try {
    const data = structuredClone(original);
    data.source_mode = "psp";
    data.source_status = "partial";
    data.source_error = "zone.work: HTTP 403";
    Object.assign(data.locations["zone.home"], {
      source_status: "ok", source_error: null, points_updated_at: data.points_updated_at,
      returned_count: 250, result_limit_reached: true,
    });
    Object.assign(data.locations["zone.work"], {
      source_status: "error", source_error: "HTTP 403", points_updated_at: null,
      routes: [], unrouted: [], found_count: 0,
    });
    fixture.setData(data);
    await fixture.card._load();
    assert.equal(fixture.card._importButton.hidden, true);
    assert.match(fixture.card._status.textContent, /Punkty pobrane z gdziesieukryc.pl/);
    assert.match(fixture.card._notice.textContent, /limit 250/);
    assert.doesNotMatch(fixture.card._notice.textContent, /403/);
    fixture.card._zones.value = "zone.work";
    fixture.card._zones.dispatchEvent(new fixture.window.Event("change"));
    assert.match(fixture.card._status.textContent, /Źródło niedostępne · dane: brak danych/);
    assert.match(fixture.card._notice.textContent, /HTTP 403/);
    assert.doesNotMatch(fixture.card.shadowRoot.querySelector(".empty").textContent, /Zaimportuj/);
    assert.equal(fixture.card.shadowRoot.querySelectorAll(".route").length, 0);
  } finally { fixture.close(); }
});

test("an empty automatic reply explains the search radius and refresh requests a new update", async () => {
  const fixture = await mount();
  try {
    const data = structuredClone(original);
    data.source_mode = "psp";
    data.source_status = "empty";
    data.point_count = 0;
    Object.values(data.locations).forEach(location => { location.routes = []; location.found_count = 0; });
    fixture.setData(data);
    await fixture.card._load();
    assert.match(fixture.card.shadowRoot.querySelector(".empty").textContent, /Serwis nie zwrócił punktów/);
    await fixture.card._forceRefresh();
    assert.equal(fixture.calls.filter(message => message.type === "gdzie_sie_ukryc/refresh").length, 1);
  } finally { fixture.close(); }
});
