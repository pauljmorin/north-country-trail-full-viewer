/* North Country Trail completeness viewer — app.js (v1, Nov 2026).
 *
 * Stripped-down Leaflet viewer: the whole trail, ND to Vermont, in
 * three kinds of miles — natural tread / urban sidewalk / road — plus
 * state boundaries with per-state rollups and a PAD-US overlay.
 * No trip-planning features, no photo pins, no shoulder/speed/ATV/
 * timber/census/historical layers. See ../README.md for the data
 * contract (filenames the code expects in data/).
 *
 * Rollups embedded below are the v1 mileage table
 * (~/workspace/nct-completeness-viewer/mileage-table.csv, Nov 21, 2026;
 * geodesic miles on WGS84). They render the tables and the state
 * popups even before the GeoJSON files land; chapters.json and
 * states.geojson, when present, take precedence for the chapter table
 * and the map popups respectively.
 */
"use strict";

/* ------------------------------------------------------------ data */
/* Expected files in data/ (owned by the data agent — never written
   by this file). Missing files are reported in #load-status, not
   invented: the layer stays empty and the table falls back to the
   embedded rollup below. */
var DATA = {
  natural: "data/centerline-natural.geojson",
  urban: "data/centerline-urban.geojson",
  road: "data/centerline-road.geojson",
  states: "data/states.geojson",
  chapters: "data/chapters.json",
  padusNote: "data/padus-note.md"
};

/* Per-state rollup, west to east (mileage-table.csv v1). */
var STATES = [
  { code: "ND", name: "North Dakota", natural: 285.83, urban: 11.44, road: 169.63, total: 466.90, pct: 61.2 },
  { code: "MN", name: "Minnesota",    natural: 729.97, urban: 16.92, road: 128.34, total: 875.23, pct: 83.4 },
  { code: "WI", name: "Wisconsin",    natural: 147.67, urban: 1.51,  road: 64.51,  total: 213.69, pct: 69.1 },
  { code: "MI", name: "Michigan",     natural: 902.89, urban: 22.99, road: 255.05, total: 1180.93, pct: 76.5 },
  { code: "OH", name: "Ohio",         natural: 519.61, urban: 39.37, road: 513.73, total: 1072.71, pct: 48.4 },
  { code: "PA", name: "Pennsylvania", natural: 234.57, urban: 7.74,  road: 43.66,  total: 285.98, pct: 82.0 },
  { code: "NY", name: "New York",     natural: 466.68, urban: 20.29, road: 218.17, total: 705.14, pct: 66.2 },
  { code: "VT", name: "Vermont",      natural: 47.88,  urban: 4.41,  road: 18.37,  total: 70.65,  pct: 67.8 }
];
var TRAIL_TOTAL = { natural: 3335.09, urban: 124.68, road: 1411.47, total: 4871.24, pct: 68.5 };

/* Per-chapter rollup (mileage-table.csv v1). `unmapped: true` rows are
   rendered in the flagged unmapped table, not the chapter table.
   "Central NY" is a variant spelling of CNY, flagged in the table. */
var CHAPTERS = [
  { code: "ADK",  name: "Adirondack Mountain Club",          natural: 75.95,  urban: 5.99,  road: 104.35, total: 186.29, pct: 40.8 },
  { code: "ADK-ON", name: "?? UNMAPPED CODE ??",            natural: 33.09,  urban: 0.00,  road: 5.36,   total: 38.45,  pct: 86.1, unmapped: true },
  { code: "ANF",  name: "Allegheny National Forest",         natural: 89.56,  urban: 0.00,  road: 2.90,   total: 92.46,  pct: 96.9 },
  { code: "ARW",  name: "Arrowhead",                        natural: 136.12, urban: 8.93,  road: 33.61,  total: 178.66, pct: 76.2 },
  { code: "BAW",  name: "Chief Baw Beese",                  natural: 18.36,  urban: 4.15,  road: 29.41,  total: 51.92,  pct: 35.4 },
  { code: "BRT",  name: "Border Route Trail",               natural: 64.88,  urban: 0.00,  road: 0.00,   total: 64.88,  pct: 100.0 },
  { code: "BSC",  name: "Brule-St. Croix",                  natural: 56.79,  urban: 1.09,  road: 47.78,  total: 105.66, pct: 53.8 },
  { code: "BTA",  name: "Buckeye Trail Association",        natural: 464.20, urban: 28.71, road: 439.75, total: 932.66, pct: 49.8 },
  { code: "BUT",  name: "Butler County",                    natural: 32.20,  urban: 0.00,  road: 16.23,  total: 48.42,  pct: 66.5 },
  { code: "CHE",  name: "Chequamegon",                      natural: 65.38,  urban: 0.43,  road: 1.93,   total: 67.74,  pct: 96.5 },
  { code: "CLA",  name: "Clarion County",                   natural: 84.04,  urban: 2.02,  road: 9.68,   total: 95.74,  pct: 87.8 },
  { code: "CND",  name: "Chief Noonday",                    natural: 53.19,  urban: 7.31,  road: 57.35,  total: 117.86, pct: 45.1 },
  { code: "CNY",  name: "Central New York",                 natural: 60.16,  urban: 9.06,  road: 17.91,  total: 87.14,  pct: 69.0 },
  { code: "Central NY", name: "Central New York (variant code)", natural: 1.02, urban: 0.00, road: 1.45, total: 2.46, pct: 41.3, variant: true },
  { code: "DPC",  name: "Dakota Prairie",                   natural: 58.42,  urban: 1.75,  road: 23.57,  total: 83.73,  pct: 69.8 },
  { code: "ELY",  name: "Ely Northwoods",                   natural: 15.53,  urban: 0.00,  road: 4.29,   total: 19.83,  pct: 78.4 },
  { code: "FLTC", name: "Finger Lakes Trail Conference",    natural: 296.28, urban: 5.24,  road: 89.11,  total: 390.63, pct: 75.8 },
  { code: "FLY",  name: "Central Flyway",                   natural: 116.04, urban: 0.00,  road: 23.60,  total: 139.64, pct: 83.1 },
  { code: "GMC",  name: "Green Mountain Club",              natural: 35.50,  urban: 0.00,  road: 1.94,   total: 37.44,  pct: 94.8 },
  { code: "GTC",  name: "Grand Traverse",                   natural: 77.65,  urban: 0.96,  road: 26.50,  total: 105.11, pct: 73.9 },
  { code: "GTR",  name: "?? UNMAPPED CODE ??",              natural: 0.87,   urban: 0.00,  road: 0.69,   total: 1.56,   pct: 55.8, unmapped: true },
  { code: "HRB",  name: "Harbor Springs",                   natural: 42.68,  urban: 0.54,  road: 6.09,   total: 49.31,  pct: 86.6 },
  { code: "HSS",  name: "Hiawatha Shore-to-Shore",          natural: 121.67, urban: 2.36,  road: 14.58,  total: 138.61, pct: 87.8 },
  { code: "HTG",  name: "Heritage",                         natural: 27.06,  urban: 0.00,  road: 14.89,  total: 41.95,  pct: 64.5 },
  { code: "ITM",  name: "Itasca Moraine",                   natural: 77.99,  urban: 0.00,  road: 0.32,   total: 78.31,  pct: 99.6 },
  { code: "J45",  name: "Jordan Valley 45\u00b0",            natural: 57.99,  urban: 0.41,  road: 21.27,  total: 79.67,  pct: 72.8 },
  { code: "KEK",  name: "Kekekabic Trail",                  natural: 39.03,  urban: 0.00,  road: 14.92,  total: 53.95,  pct: 72.3 },
  { code: "LLC",  name: "Laurentian Lakes",                 natural: 62.20,  urban: 0.13,  road: 9.09,   total: 71.42,  pct: 87.1 },
  { code: "LON",  name: "?? UNMAPPED CODE ??",              natural: 1.29,   urban: 0.00,  road: 0.19,   total: 1.48,   pct: 87.3, unmapped: true },
  { code: "MAC",  name: "Marquette Area",                   natural: 87.94,  urban: 0.00,  road: 22.34,  total: 110.28, pct: 79.7 },
  { code: "MALT", name: "Middlebury Area Land Trust",       natural: 11.17,  urban: 4.41,  road: 4.83,   total: 20.41,  pct: 54.7 },
  { code: "MWP",  name: "Minnesota Waters and Prairie",     natural: 21.50,  urban: 7.86,  road: 65.69,  total: 95.05,  pct: 22.6 },
  { code: "NMK",  name: "Ni-Miikanaake",                    natural: 70.71,  urban: 0.00,  road: 10.94,  total: 81.65,  pct: 86.6 },
  { code: "NORTA", name: "Northwestern Ohio Rail-to-Trails Assn", natural: 38.52, urban: 1.94, road: 3.69, total: 44.14, pct: 87.3 },
  { code: "None", name: "?? UNMAPPED CODE ??",              natural: 39.22,  urban: 3.77,  road: 87.93,  total: 130.92, pct: 30.0, unmapped: true },
  { code: "None", name: "?? UNMAPPED CODE ?? (null chapter)", natural: 13.46, urban: 2.15, road: 6.22, total: 21.84, pct: 61.6, unmapped: true },
  { code: "PWC",  name: "Peter Wolfe",                      natural: 113.74, urban: 0.00,  road: 6.02,   total: 119.76, pct: 95.0 },
  { code: "SHTA", name: "Superior Hiking Trail Association", natural: 300.26, urban: 0.00, road: 0.10,  total: 300.35, pct: 100.0 },
  { code: "SPW",  name: "Spirit of the Woods",              natural: 72.00,  urban: 0.00,  road: 7.30,   total: 79.30,  pct: 90.8 },
  { code: "SRV",  name: "Sheyenne River Valley",            natural: 63.43,  urban: 5.92,  road: 45.92,  total: 115.26, pct: 55.0 },
  { code: "SSC",  name: "Superior Shoreline",               natural: 95.20,  urban: 4.86,  road: 9.63,   total: 109.68, pct: 86.8 },
  { code: "STN",  name: "Star of the North",                natural: 9.97,   urban: 0.00,  road: 0.25,   total: 10.21,  pct: 97.6 },
  { code: "WAM",  name: "Wampum",                           natural: 43.11,  urban: 11.22, road: 70.72,  total: 125.04, pct: 34.5 },
  { code: "WMI",  name: "Western Michigan",                 natural: 89.77,  urban: 3.47,  road: 51.12,  total: 144.36, pct: 62.2 }
];

/* ---------------------------------------------------------- helpers */
function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function fmt(n) {
  return Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtPct(n) {
  return Number(n).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
}
function rollupRows(r) {
  return "<tr><td>Natural tread</td><td class=\"num\">" + fmt(r.natural) + " mi</td></tr>" +
    "<tr><td>Urban sidewalk</td><td class=\"num\">" + fmt(r.urban) + " mi</td></tr>" +
    "<tr><td>Road &mdash; not yet built</td><td class=\"num\">" + fmt(r.road) + " mi</td></tr>" +
    "<tr><td><strong>Total</strong></td><td class=\"num\"><strong>" + fmt(r.total) + " mi</strong></td></tr>" +
    "<tr><td>% natural tread</td><td class=\"num\">" + fmtPct(r.pct) + "</td></tr>";
}
function stateByCode(code) {
  for (var i = 0; i < STATES.length; i++) if (STATES[i].code === code) return STATES[i];
  return null;
}
function stateByName(name) {
  var n = String(name || "").toLowerCase();
  for (var i = 0; i < STATES.length; i++) if (STATES[i].name.toLowerCase() === n) return STATES[i];
  return null;
}

/* Status line: which data files loaded, which are still missing. */
var loadNotes = [];
function setStatus() {
  var el = $("load-status");
  if (!el) return;
  var missing = loadNotes.filter(function (n) { return n.missing; });
  if (!missing.length) {
    el.textContent = "Map data loaded: centerline (natural / urban / road), state boundaries" +
      (padusState === "loaded" ? ", PAD-US public lands." : ". PAD-US overlay pending — see Data sources.");
  } else {
    el.textContent = "Still to load (data files not yet in site/data/): " +
      missing.map(function (n) { return n.file; }).join(", ") +
      ". Tables below use the v1 mileage table (Nov 21, 2026) meanwhile.";
  }
  el.classList.toggle("warn", missing.length > 0);
}
function noteLoaded(file) { loadNotes.push({ file: file }); setStatus(); }
function noteMissing(file) { loadNotes.push({ file: file, missing: true }); setStatus(); }

/* ------------------------------------------------------------- map */
/* Shareable view (borrowed from the Itasca Moraine viewer, Paul,
   Nov 12, 2026): a #v=lat,lng,zoom link opens on that view.
   Full hash format, documented at writeShareHash:
   #v=lat,lng,zoom & b=basemap-code & l=layer,layer (a token prefixed
   with "-" switches that layer OFF). */
function parseHash() {
  var hash = location.hash || "";
  var out = {};
  var vm = /v=([-\d.]+),([-\d.]+),(\d+(?:\.\d+)?)/.exec(hash);
  if (vm) {
    var lat = parseFloat(vm[1]), lng = parseFloat(vm[2]), z = parseFloat(vm[3]);
    if (isFinite(lat) && isFinite(lng) && isFinite(z) &&
        lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180 && z >= 0 && z <= 19)
      out.view = { center: [lat, lng], zoom: z };
  }
  var bm = /b=([a-z0-9-]+)/.exec(hash);
  if (bm) out.base = bm[1];
  var lm = /l=([a-z,\-]+)/.exec(hash);
  if (lm) {
    out.layersOn = []; out.layersOff = [];
    lm[1].split(",").forEach(function (tok) {
      if (!tok) return;
      if (tok.charAt(0) === "-") out.layersOff.push(tok.slice(1));
      else out.layersOn.push(tok);
    });
  }
  return out;
}
var initialHash = parseHash();

var map = L.map("map", initialHash.view ?
  { center: initialHash.view.center, zoom: initialHash.view.zoom } :
  { center: [44.2, -86.0], zoom: 5 });
map.attributionControl.setPrefix(false);

/* Basemaps: OSM standard (default) + Esri World Imagery + USGS Topo. */
var BASEMAPS = {
  osm: {
    code: "osm", name: "OpenStreetMap",
    layer: L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "\u00a9 OpenStreetMap contributors" })
  },
  esri: {
    code: "esri", name: "Esri World Imagery",
    layer: L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 19, attribution: "Esri, Maxar, Earthstar Geographics" })
  },
  usgs: {
    code: "usgs", name: "USGS Topo",
    layer: L.tileLayer("https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 19, attribution: "USGS, The National Map" })
  }
};
var currentBase = "osm";
if (initialHash.base && BASEMAPS[initialHash.base]) currentBase = initialHash.base;
BASEMAPS[currentBase].layer.addTo(map);

/* Overlays. Each starts as an empty group; GeoJSON is fetched into
   it, so the layer control exists before the data arrives. */
var naturalLayer = L.geoJSON(null, {
  style: { color: "#2e7d32", weight: 3, opacity: 0.9 }
});
var urbanLayer = L.geoJSON(null, {
  style: { color: "#e67e22", weight: 3.5, opacity: 0.95 }
});
/* Road = the unfinished miles: dashed red, must read as the gap. */
var roadLayer = L.geoJSON(null, {
  style: { color: "#c0392b", weight: 3, opacity: 0.9, dashArray: "7 5" }
});
var statesLayer = L.geoJSON(null, {
  style: { color: "#555555", weight: 1.2, opacity: 0.8, fillOpacity: 0, dashArray: "4 3" },
  onEachFeature: function (feature, layer) {
    var p = feature.properties || {};
    var st = stateByCode(p.code || p.STATE || p.state) || stateByName(p.name || p.NAME);
    var r = null;
    if (st) r = st;
    else if (isFinite(+p.natural) || isFinite(+p.natural_tread_mi)) {
      r = { natural: +(p.natural != null ? p.natural : p.natural_tread_mi),
            urban: +(p.urban != null ? p.urban : p.urban_sidewalk_mi),
            road: +(p.road != null ? p.road : p.road_mi),
            total: +(p.total != null ? p.total : p.total_mi),
            pct: +(p.pct != null ? p.pct : p.pct_natural_tread) };
    }
    var title = esc(p.name || p.NAME || (st && st.name) || "State");
    var body = r ? "<table class=\"pop-table\">" + rollupRows(r) + "</table>"
      : "<p>No rollup for this state yet.</p>";
    layer.bindPopup("<strong>" + title + "</strong>" + body +
      "<p class=\"pop-note\">Miles are geodesic on WGS84, NCTA centerline pull Nov 21, 2026.</p>");
  }
});
var padusLayer = L.geoJSON(null, {
  style: { color: "#1b5e20", weight: 1, opacity: 0.6, fillColor: "#66bb6a", fillOpacity: 0.25 },
  onEachFeature: function (feature, layer) {
    var p = feature.properties || {};
    var name = p.Unit_Nm || p.NAME || p.name || "Public land";
    var mgr = p.Mang_Name || p.MANAGER || p.manager || p.Agency || "";
    layer.bindPopup("<strong>" + esc(name) + "</strong>" +
      (mgr ? "<br>Manager: " + esc(mgr) : "") +
      "<p class=\"pop-note\">PAD-US public lands. See Data sources for the source.</p>");
  }
});
var padusState = "pending"; /* pending | loaded | tile */
var padusTileLayer = null;

/* Copy link — SACRED (Itasca Moraine viewer): icon-only button,
   upper-right, composes centre/zoom/basemap/layers into the hash.
   Do not remove or redesign. */
var copyLinkControl = L.Control.extend({
  options: { position: "topright" },
  onAdd: function () {
    var btn = L.DomUtil.create("button", "copy-link-btn leaflet-bar");
    btn.type = "button";
    btn.id = "copy-link-btn";
    btn.title = "Copy link to this view";
    btn.setAttribute("aria-label", "Copy link to this view");
    btn.textContent = "\u29c9"; /* icon only — no text label */
    L.DomEvent.disableClickPropagation(btn);
    L.DomEvent.on(btn, "click", function () {
      writeShareHash();
      var url = location.href;
      function done(ok) {
        btn.textContent = ok ? "\u2713" : "\u29c9";
        btn.title = ok ? "Copied" : "Copy failed — copy the address bar";
        window.setTimeout(function () {
          btn.textContent = "\u29c9";
          btn.title = "Copy link to this view";
        }, 2000);
      }
      function fallbackCopy(text) {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        var ok = false;
        try { ok = document.execCommand("copy"); } catch (e) {}
        document.body.removeChild(ta);
        done(ok);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () { done(true); },
          function () { fallbackCopy(url); });
      } else fallbackCopy(url);
    });
    return btn;
  }
});
map.addControl(new copyLinkControl());

/* Legend (bottom-right): the three line styles must be visually
   distinct at a glance; road reads as the gap. */
var legendControl = L.Control.extend({
  options: { position: "bottomright" },
  onAdd: function () {
    var div = L.DomUtil.create("div", "map-legend leaflet-bar");
    div.innerHTML =
      "<h2>Legend</h2>" +
      "<div class=\"lg-row\"><span class=\"lg-line lg-natural\"></span>Natural tread — built (3,335.09 mi)</div>" +
      "<div class=\"lg-row\"><span class=\"lg-line lg-urban\"></span>Urban sidewalk — walkable, not trail (124.68 mi)</div>" +
      "<div class=\"lg-row\"><span class=\"lg-line lg-road\"></span>Road — not yet built (1,411.47 mi)</div>" +
      "<div class=\"lg-row\"><span class=\"lg-line lg-state\"></span>State boundary (click for rollup)</div>" +
      "<div class=\"lg-row\"><span class=\"lg-fill lg-padus\"></span>Public land (PAD-US, off by default)</div>";
    return div;
  }
});
map.addControl(new legendControl());

/* Layer control (minimal): basemaps + overlays. PAD-US label says
   plainly whether it is live or still a placeholder. */
var OVERLAY_DEFS = [
  { id: "natural", label: "Centerline — natural tread", layer: naturalLayer, on: true },
  { id: "urban",   label: "Centerline — urban sidewalk", layer: urbanLayer, on: true },
  { id: "road",    label: "Centerline — road (unfinished)", layer: roadLayer, on: true },
  { id: "states",  label: "State boundaries", layer: statesLayer, on: true },
  { id: "padus",   label: "PAD-US public lands (pending — no data yet)", layer: padusLayer, on: false }
];
var layerControl = null;
function buildLayerControl() {
  var base = {}, over = {};
  Object.keys(BASEMAPS).forEach(function (k) { base[BASEMAPS[k].name] = BASEMAPS[k].layer; });
  OVERLAY_DEFS.forEach(function (d) { over[d.label] = d.layer; });
  if (layerControl) map.removeControl(layerControl);
  layerControl = L.control.layers(base, over, { collapsed: false });
  layerControl.addTo(map);
  OVERLAY_DEFS.forEach(function (d) {
    if (d.on) d.layer.addTo(map);
  });
}
/* Apply an explicit #l= hash before the control is built. */
if (initialHash.layersOn || initialHash.layersOff) {
  OVERLAY_DEFS.forEach(function (d) {
    if (initialHash.layersOff && initialHash.layersOff.indexOf(d.id) >= 0) d.on = false;
    else if (initialHash.layersOn && initialHash.layersOn.indexOf(d.id) >= 0) d.on = true;
  });
}

/* Write the share hash: #v=lat,lng,zoom&b=code&l=on,off… — a "-"
   prefix marks a layer that is OFF, so the link is exact. */
function writeShareHash() {
  var c = map.getCenter();
  var parts = ["#v=" + c.lat.toFixed(5) + "," + c.lng.toFixed(5) + "," + map.getZoom(),
    "b=" + currentBase];
  var toks = OVERLAY_DEFS.map(function (d) {
    return (map.hasLayer(d.layer) ? "" : "-") + d.id;
  });
  parts.push("l=" + toks.join(","));
  var hash = parts.join("&");
  try { history.replaceState(null, "", hash); }
  catch (e) { location.hash = hash; }
}
map.on("moveend", writeShareHash);
map.on("overlayadd overlayremove", writeShareHash);
map.on("baselayerchange", function (e) {
  Object.keys(BASEMAPS).forEach(function (k) {
    if (BASEMAPS[k].layer === e.layer) currentBase = k;
  });
  writeShareHash();
});

/* -------------------------------------------------- PAD-US wiring */
/* The data agent documents PAD-US in data/padus-note.md as
   key: value lines, e.g.
     type: geojson
     file: padus.geojson
   or
     type: tiles
     url: https://…/{z}/{x}/{y}.png
     attribution: …
   or (ArcGIS dynamic MapServer — no cached tiles; each Leaflet tile
   is rendered through the export endpoint, no extra library)
     type: arcgis-export
     url: https://…/MapServer/export
     layers: show:0
     attribution: …
   No note yet → the layer stays a clearly-marked placeholder and
   the fact is reported in #load-status and the README. */
function wirePadus() {
  return fetch(DATA.padusNote).then(function (r) {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.text();
  }).then(function (text) {
    var kv = {};
    text.split(/\r?\n/).forEach(function (line) {
      var m = /^([A-Za-z_]+):\s*(.+?)\s*$/.exec(line);
      if (m) kv[m[1].toLowerCase()] = m[2];
    });
    if (kv.type === "geojson" && kv.file) {
      return fetch(kv.file.indexOf("data/") === 0 ? kv.file : "data/" + kv.file)
        .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
        .then(function (gj) {
          padusLayer.addData(gj);
          padusState = "loaded";
          setPadusLabel("PAD-US public lands");
          noteLoaded(kv.file);
        });
    }
    if (kv.type === "tiles" && kv.url) {
      padusTileLayer = L.tileLayer(kv.url, {
        maxZoom: 19, attribution: kv.attribution || "PAD-US (USGS)"
      });
      var def = OVERLAY_DEFS.filter(function (d) { return d.id === "padus"; })[0];
      def.layer = padusTileLayer;
      padusState = "tile";
      setPadusLabel("PAD-US public lands");
      noteLoaded("PAD-US tile service (see padus-note.md)");
      buildLayerControl();
      return null;
    }
    if (kv.type === "arcgis-export" && kv.url) {
      /* ArcGIS dynamic MapServer (not a cached tile service): render
         each Leaflet tile through the export endpoint. No extra JS
         library — a plain L.GridLayer building export URLs from the
         tile bounds in EPSG:3857. Verified live 2026-11-22: 256x256
         export over the UP of Michigan returned HTTP 200 PNG in 0.8 s. */
      var ArcgisExportLayer = L.GridLayer.extend({
        createTile: function (coords) {
          var tile = document.createElement("img");
          tile.width = 256; tile.height = 256; tile.alt = "";
          var bounds = this._tileCoordsToBounds(coords);
          var crs = map.options.crs;
          var sw = crs.project(bounds.getSouthWest());
          var ne = crs.project(bounds.getNorthEast());
          var bbox = [sw.x, sw.y, ne.x, ne.y].map(function (v) {
            return Math.round(v);
          }).join(",");
          tile.src = kv.url + "?bbox=" + bbox +
            "&bboxSR=3857&imageSR=3857&size=256,256&format=png32" +
            "&transparent=true&layers=" +
            encodeURIComponent(kv.layers || "show:0") + "&f=image";
          return tile;
        }
      });
      padusTileLayer = new ArcgisExportLayer({
        opacity: 0.45,
        attribution: kv.attribution || "PAD-US (USGS)"
      });
      var def2 = OVERLAY_DEFS.filter(function (d) { return d.id === "padus"; })[0];
      def2.layer = padusTileLayer;
      padusState = "tile";
      setPadusLabel("PAD-US public lands");
      noteLoaded("PAD-US live service (see padus-note.md)");
      buildLayerControl();
      return null;
    }
    throw new Error("padus-note.md has no usable type/file/url");
  }).catch(function () {
    padusState = "pending";
    setPadusLabel("PAD-US public lands (pending — no data yet)");
    noteMissing(DATA.padusNote + " (PAD-US overlay placeholder)");
  });
}
function setPadusLabel(label) {
  OVERLAY_DEFS.forEach(function (d) { if (d.id === "padus") d.label = label; });
  buildLayerControl();
}

/* ------------------------------------------------- GeoJSON loading */
function loadGeoJSON(url, layer, label) {
  return fetch(url).then(function (r) {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }).then(function (gj) {
    layer.addData(gj);
    noteLoaded(url);
  }).catch(function () {
    noteMissing(url + " (" + label + ")");
  });
}

/* ------------------------------------------------------------ tables */
function renderStateTable() {
  var tb = document.querySelector("#state-table tbody");
  if (!tb) return;
  tb.innerHTML = STATES.map(function (s) {
    return "<tr><th scope=\"row\">" + esc(s.name) + " (" + esc(s.code) + ")</th>" +
      "<td class=\"num\">" + fmt(s.natural) + "</td>" +
      "<td class=\"num\">" + fmt(s.urban) + "</td>" +
      "<td class=\"num\">" + fmt(s.road) + "</td>" +
      "<td class=\"num\">" + fmt(s.total) + "</td>" +
      "<td class=\"num\">" + fmtPct(s.pct) + "</td></tr>";
  }).join("");
}
function chapterRows(rows) {
  return rows.map(function (c) {
    var name = esc(c.name || c.code);
    if (c.variant) name += " <span class=\"flag\">variant of CNY</span>";
    return "<tr><th scope=\"row\">" + name + "</th>" +
      "<td><code>" + esc(c.code) + "</code></td>" +
      "<td class=\"num\">" + fmt(c.natural) + "</td>" +
      "<td class=\"num\">" + fmt(c.urban) + "</td>" +
      "<td class=\"num\">" + fmt(c.road) + "</td>" +
      "<td class=\"num\">" + fmt(c.total) + "</td>" +
      "<td class=\"num\">" + fmtPct(c.pct) + "</td></tr>";
  }).join("");
}
function renderChapterTables(rows, sourceLabel) {
  var mapped = rows.filter(function (c) { return !c.unmapped; })
    .sort(function (a, b) { return b.road - a.road; });
  var unmapped = rows.filter(function (c) { return !!c.unmapped; })
    .sort(function (a, b) { return b.total - a.total; });
  var ct = document.querySelector("#chapter-table tbody");
  if (ct) ct.innerHTML = chapterRows(mapped);
  var ut = document.querySelector("#unmapped-table tbody");
  if (ut) {
    ut.innerHTML = unmapped.map(function (c) {
      return "<tr><th scope=\"row\"><code>" + esc(c.code) + "</code>" +
        (c.name && c.name.indexOf("null") >= 0 ? " <span class=\"flag\">null chapter field</span>" : "") +
        "</th><td class=\"num\">" + fmt(c.natural) + "</td>" +
        "<td class=\"num\">" + fmt(c.urban) + "</td>" +
        "<td class=\"num\">" + fmt(c.road) + "</td>" +
        "<td class=\"num\">" + fmt(c.total) + "</td>" +
        "<td class=\"num\">" + fmtPct(c.pct) + "</td></tr>";
    }).join("");
  }
  var note = $("chapter-source-note");
  if (note) note.textContent = "Sorted by road miles, largest gap first. " +
    "Chapter attribution is NCTA\u2019s native chapter field; there is no " +
    "chapter-boundary geometry yet. Source: " + sourceLabel + ".";
}
function loadChapters() {
  return fetch(DATA.chapters).then(function (r) {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }).then(function (json) {
    var rows = Array.isArray(json) ? json : json.chapters;
    if (!Array.isArray(rows) || !rows.length) throw new Error("no rows");
    /* Normalise field names; chapters.json wins when present. */
    rows = rows.map(function (c) {
      return {
        code: c.code, name: c.name || c.code,
        natural: +(c.natural != null ? c.natural : c.natural_tread_mi),
        urban: +(c.urban != null ? c.urban : c.urban_sidewalk_mi),
        road: +(c.road != null ? c.road : c.road_mi),
        total: +(c.total != null ? c.total : c.total_mi),
        pct: +(c.pct != null ? c.pct : c.pct_natural_tread),
        unmapped: !!c.unmapped ||
          ["ADK-ON", "GTR", "LON", "None"].indexOf(c.code) >= 0,
        variant: !!c.variant || c.code === "Central NY"
      };
    });
    renderChapterTables(rows, "data/chapters.json");
    noteLoaded(DATA.chapters);
  }).catch(function () {
    renderChapterTables(CHAPTERS, "embedded v1 mileage table (Nov 21, 2026) — data/chapters.json not yet present");
    noteMissing(DATA.chapters + " (chapter table uses embedded rollup)");
  });
}

/* -------------------------------------------------------------- boot */
renderStateTable();
buildLayerControl();
writeShareHash();
loadChapters();
loadGeoJSON(DATA.natural, naturalLayer, "natural tread centerline");
loadGeoJSON(DATA.urban, urbanLayer, "urban sidewalk centerline");
loadGeoJSON(DATA.road, roadLayer, "road centerline");
loadGeoJSON(DATA.states, statesLayer, "state boundaries");
wirePadus();
