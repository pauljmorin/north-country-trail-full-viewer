/* North Country Trail — full trail viewer, shell (step 1, Nov 2026).
 *
 * Forked from the Itasca Moraine chapter viewer's shell
 * (~/workspace/itasca-trail-map/site/, app.js v7): same layout (fixed
 * panel left, map fills the rest), same share-hash pattern
 * (#view=lat,lng,zoom & #base=code & #layers=… & #chapter=CODE), same
 * corner legend card, same layer-registry shape — one entry per layer,
 * lazy-loaded the first time its toggle is switched on. Plain script,
 * no build step, no API keys of our own (see the Mapbox note below),
 * vendored Leaflet, no CDN. Tiles stream; no basemap data is
 * downloaded.
 *
 * What this shell does (wave 1 wired, Nov 23, 2026):
 *   - the NCT centerline as the base line, in the same three classes
 *     the old viewer drew: natural tread (solid green), urban
 *     sidewalk (solid amber), road (dashed red)
 *   - chapters: a west-to-east list from data/chapter-extents.json;
 *     one compact <select> in the panel flies to a chapter (Nov 24,
 *     2026 panel rebuild — the chapter listbox is gone).
 *   - copy link, legend, print, whole trail as small icon buttons
 *     over the map's top-right corner.
 *   - panel dressed to the Itasca Moraine chapter viewer's look
 *     (Nov 24, 2026): NCTA logo masthead, Present button, small-caps
 *     collapsible layer groups that start collapsed, a slim Find
 *     input with no heading or hint, BASEMAP as one more collapsed
 *     group. Panel 319px, no scrollbar at desktop size.
 *   - every wave-1 layer wired into the registry: alerts, reroutes,
 *     NBI bridges, NWI wetlands, BIA tribal lands, PAD-US (live),
 *     chainage, chapter boundaries, road walk, camping, NCTA Places,
 *     mile markers, partner trails, OSM roads, OSM bike routes, NCTA
 *     map sheets, and gazetteer search. The two big files (NWI
 *     174 MB, OSM roads 109 MB) are OFF by default and lazy-load
 *     only when toggled on. Soils stays a stub: the NRCS service
 *     answered again Nov 23 but the national pull has not been run.
 *   - no data invented for any stub; the soils stub says so.
 *
 * Deliberately NOT here (plan §3): the 24 excluded items (inventory,
 * adopted sections, chapter-specific layers, Minnesota-only layers,
 * paper maps, AllTrails, volunteer protocol) and the 13 undecided
 * items (parcels, motorized, timber, state campgrounds, speeds,
 * crashes, shoulders, Street View points, photos, reroute corridors,
 * easements, forest health/invasives, tree height). No completeness
 * framing anywhere: no headline mileage, no case page.
 */
"use strict";

/* ------------------------------------------------------- tokens
   Design tokens: style.css carries the same values as CSS
   variables; keep the two in step. */
var COLORS = {
  natural: "#1a9850",   /* natural tread — solid green (as the old viewer) */
  urban: "#e08214",     /* urban sidewalk — solid amber (as the old viewer) */
  road: "#d7301f",      /* road — dashed red (as the old viewer) */
  highlight: "#b2182b", /* selected chapter, drawn over the base line */
  casing: "#ffffff",
};

/* Chapter names for popups, filled from chapter-extents.json at load.
   Variant codes in the source data fold into their parent chapter for
   highlighting (they are not separate chapters): "Central NY" into CNY,
   GTR into GTC, LON into Unassigned. */
var CHAPTER_NAMES = {};
var CHAPTER_MATCH = {
  "CNY": ["CNY", "Central NY"],
  "GTC": ["GTC", "GTR"],
  "Unassigned": ["None", null],
};

/* ------------------------------------------------------------- map */

/* Shareable view (ITM pattern, Nov 12, 2026): a #view=lat,lng,zoom link
   opens on that view. Parsed here, before the map exists, so the first
   paint is already the shared view. Invalid values fall back to the
   default below. */
var initialView = (function () {
  var m = /view=([-.\d]+),([-.\d]+),(\d+(?:\.\d+)?)/
    .exec(location.hash || "");
  if (!m) return null;
  var lat = parseFloat(m[1]), lng = parseFloat(m[2]),
      z = parseFloat(m[3]);
  if (!isFinite(lat) || !isFinite(lng) || !isFinite(z)) return null;
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
  if (z < 0 || z > 19) return null;
  return { center: [lat, lng], zoom: z };
})();

/* Default view: the whole trail, North Dakota to Vermont, until the
   centerline loads and fitBounds takes over (unless a shared view or
   a chapter was requested). */
var map = L.map("map", initialView ?
  { center: initialView.center, zoom: initialView.zoom, preferCanvas: true } :
  { center: [44.0, -88.0], zoom: 5, preferCanvas: true });
L.control.scale().addTo(map);

/* -------------------------------------------------------- basemaps
   National/general only. No Minnesota basemaps (MN hillshade, MN
   aerials by year, winter base) — those stay with the chapter viewer.
   Endpoints are the ITM viewer's verified ones (SOURCES.md there);
   the keyed bases carry the same public keys the ITM viewer already
   publishes in its page source, origin-restricted to
   pauljmorin.github.io. */

/* Mapbox Outdoors: the ITM viewer's public token (pk.*), copied
   from ~/workspace/itasca-trail-map/site/app.js line 194 — a public
   key by design, visible in the page source (ITM comment, Nov 16,
   2026: verified live over the chapter, HTTP 200). Same token as the
   chapter viewer; the map site is pauljmorin.github.io. */
var MAPBOX_TOKEN = "pk.eyJ1IjoicGF1bGptb3JpbiIsImEiOiJjbXdqYzg2djEwMXF5MnhxMTA2YTQ3Nm1kIn0.eH8KH7srHEdkoALWHYVvVQ";
var mapboxOutdoors = MAPBOX_TOKEN ? L.tileLayer(
  "https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/tiles/" +
    "{z}/{x}/{y}?access_token=" + MAPBOX_TOKEN, {
    tileSize: 512, zoomOffset: -1, maxZoom: 22, maxNativeZoom: 22,
    attribution: "© Mapbox, © OpenStreetMap contributors",
  }) : null;

var MAPTILER_KEY = "guMWwDin1DDGgTJSmAvP";
var maptilerOutdoor = L.tileLayer(
  "https://api.maptiler.com/maps/outdoor/{z}/{x}/{y}.png?key=" +
    MAPTILER_KEY, {
    tileSize: 512, zoomOffset: -1, maxZoom: 22, maxNativeZoom: 20,
    attribution: "© MapTiler, © OpenStreetMap contributors",
  });

var STADIA_KEY = "3835d885-64ac-4e35-a98c-c401e23ed7a7";
var stadiaOutdoors = L.tileLayer(
  "https://tiles.stadiamaps.com/tiles/outdoors/{z}/{x}/{y}.png" +
    "?api_key=" + STADIA_KEY, {
    maxZoom: 20, maxNativeZoom: 20,
    attribution: "© Stadia Maps, © OpenMapTiles, © OpenStreetMap " +
      "contributors",
  });

var topo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
  maxZoom: 18, maxNativeZoom: 17,
  attribution: "Map data: © OpenStreetMap contributors, SRTM | " +
    "map style: © OpenTopoMap (CC-BY-SA)",
}).addTo(map);

var osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap contributors",
});

var usgsTopo = L.tileLayer(
  "https://basemap.nationalmap.gov/arcgis/rest/services/" +
    "USGSTopo/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 17, maxNativeZoom: 16,
    attribution: "Topo: USGS, The National Map",
  });

var usgsImagery = L.tileLayer(
  "https://basemap.nationalmap.gov/arcgis/rest/services/" +
    "USGSImageryOnly/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 17, maxNativeZoom: 16,
    attribution: "Aerial imagery: USGS, The National Map (NAIP)",
  });

var esriImagery = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/" +
    "World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 18,
    attribution: "Aerial imagery: Esri, Maxar, Earthstar Geographics",
  });

var esriNatGeo = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/" +
    "NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 17, maxNativeZoom: 16,
    attribution: "National Geographic, Esri, DeLorme, HERE, " +
      "UNEP-WCMC, USGS",
  });

var cyclosm = L.tileLayer(
  "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png", {
    subdomains: "abc", maxZoom: 20,
    attribution: "© OpenStreetMap contributors, CyclOSM",
  });

/* White — no basemap (ITM pattern, Nov 17, 2026): an empty layer
   group, so choosing it removes the tiles and the map background
   goes white (body.base-white in style.css). */
var whiteBase = L.layerGroup([]);

/* Esri Wayback, one release per year (ITM's verified release ids;
   2015–2017 have no Wayback release in the ITM set, so they are not
   listed — a missing year is a gap in the list, not a broken tile).
   These are one <select> in the panel, not a button per year. */
var WAYBACK_IDS = {
  "2014": "5844", "2018": "23448", "2019": "4756", "2020": "29260",
  "2021": "26120", "2022": "45134", "2023": "56102", "2024": "16453",
  "2025": "13192",
};
function waybackLayer(year) {
  return L.tileLayer(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
      "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/" +
      WAYBACK_IDS[year] + "/{z}/{y}/{x}", {
      maxZoom: 18,
      attribution: "Aerial imagery (" + year + "): Esri World " +
        "Imagery Wayback",
    });
}
var waybackLayers = {};
Object.keys(WAYBACK_IDS).forEach(function (y) {
  waybackLayers[y] = waybackLayer(y);
});

/* The chooser list. Order is task order, not vendor order:
   Topographic / Streets & trails / Aerial / White. */
var BASES = [
  { name: "Topo (OpenTopoMap)", code: "topo", label: "OpenTopoMap",
    layer: topo },
  { name: "Streets (OSM)", code: "streets", label: "OpenStreetMap",
    layer: osm, subChoice: true },
  { name: "Trails (CyclOSM)", code: "trails", label: "Trails",
    sub: "CyclOSM", layer: cyclosm, subChoice: true },
  { name: "Outdoors (Mapbox)", code: "mapbox", label: "Mapbox Outdoors",
    sub: "Mapbox", layer: mapboxOutdoors, subChoice: true,
    needsKey: !MAPBOX_TOKEN },
  { name: "Outdoors (MapTiler)", code: "maptiler", label: "MapTiler Outdoor",
    sub: "MapTiler", layer: maptilerOutdoor, subChoice: true },
  { name: "Outdoors (Stadia)", code: "stadia", label: "Stadia Outdoors",
    sub: "Stadia", layer: stadiaOutdoors, subChoice: true },
  { name: "USGS Topo 1:24k", code: "usgs", label: "USGS Topo",
    sub: "1:24k quadrangles", layer: usgsTopo },
  { name: "Aerial (USGS)", code: "usgs-aerial", label: "Aerial (USGS)",
    sub: "NAIP", layer: usgsImagery },
  { name: "Aerial (Esri)", code: "esri-aerial", label: "Aerial (Esri)",
    sub: "World Imagery", layer: esriImagery },
  { name: "National Geographic (Esri)", code: "natgeo",
    label: "National Geographic", layer: esriNatGeo },
  { name: "White — no basemap", code: "white", label: "White",
    sub: "no base map", layer: whiteBase, white: true },
];
var currentBase = baseByName("Topo (OpenTopoMap)");

function baseByName(name) {
  for (var i = 0; i < BASES.length; i++) {
    if (BASES[i].name === name) return BASES[i];
  }
  return null;
}
function baseByCode(code) {
  for (var i = 0; i < BASES.length; i++) {
    if (BASES[i].code === code) return BASES[i];
  }
  if (/^wayback-\d{4}$/.test(code)) return { code: code, wayback: true };
  return null;
}

function setBase(name) {
  var def = baseByName(name);
  if (!def || def === currentBase || def.needsKey) return;
  map.removeLayer(currentBase.layer);
  map.addLayer(def.layer);
  currentBase = def;
  document.body.classList.toggle("base-white", !!def.white);
  markActiveBase(name);
  var sel = document.getElementById("wayback-select");
  if (sel) sel.value = "";
  writeShareHash();
}
function setWayback(year) {
  if (!WAYBACK_IDS[year]) return;
  map.removeLayer(currentBase.layer);
  map.addLayer(waybackLayers[year]);
  currentBase = { name: "Aerial " + year + " (Wayback)",
    code: "wayback-" + year, layer: waybackLayers[year] };
  document.body.classList.toggle("base-white", false);
  markActiveBase(null);
  writeShareHash();
}
function markActiveBase(name) {
  document.querySelectorAll("#background-choices .bg-choice")
    .forEach(function (row) {
      var on = row.getAttribute("data-base") === name;
      row.classList.toggle("on", on);
      row.setAttribute("aria-pressed", on ? "true" : "false");
    });
}
(function buildBackground() {
  var wrap = document.getElementById("background-choices");
  BASES.forEach(function (def) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "bg-choice" + (def.subChoice ? " sub-choice" : "");
    btn.setAttribute("data-base", def.name);
    btn.setAttribute("aria-pressed",
      def === currentBase ? "true" : "false");
    if (def === currentBase) btn.classList.add("on");
    var label = def.label;
    if (def.sub) label += " — " + def.sub;
    if (def.needsKey) label += " (key needed)";
    btn.textContent = label;
    if (def.needsKey) {
      btn.disabled = true;
      btn.title = "Paste the public Mapbox token into MAPBOX_TOKEN " +
        "in app.js to enable this base.";
    } else {
      btn.addEventListener("click", function () { setBase(def.name); });
    }
    wrap.appendChild(btn);
  });
  var sel = document.getElementById("wayback-select");
  Object.keys(WAYBACK_IDS).sort().forEach(function (year) {
    var opt = document.createElement("option");
    opt.value = year;
    opt.textContent = "Aerial " + year + " (Esri Wayback)";
    sel.appendChild(opt);
  });
  sel.addEventListener("change", function () {
    if (sel.value) setWayback(sel.value);
  });
})();

/* ------------------------------------------------------------ helpers */

function esc(v) {
  if (v === null || v === undefined) return "";
  return String(v).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}
/* Status (Nov 24, 2026 panel rebuild): no status line lives in
   the panel. Success is silent; only a real load failure creates
   a status line, inserted just above the footer. */
function setStatus(text, isErr) {
  if (!isErr) return;
  var el = document.getElementById("load-status");
  if (!el) {
    el = document.createElement("p");
    el.id = "load-status";
    el.className = "status";
    el.setAttribute("role", "status");
    var foot = document.querySelector(".panel-foot");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(el, foot);
    else {
      var panel = document.getElementById("panel");
      if (panel) panel.appendChild(el);
    }
  }
  el.textContent = text;
  el.classList.toggle("error", true);
}
function fetchJson(url) {
  return fetch(url).then(function (res) {
    if (!res.ok) throw new Error(url + ": HTTP " + res.status);
    return res.json();
  });
}

/* ---- WAVE-1 LAYER BUILDERS (wired Nov 23, 2026) ----
   Styles + popups for every wave-1 layer. Popups follow the ITM
   content-first pattern: the fact first, then the source line.
   Nothing is invented: a null in the source is shown as "not
   stated" or omitted, never filled in. */

/* One shared canvas renderer for the heavy point/line layers
   (chainage, mile markers, NWI, OSM roads): SVG chokes on
   352,865 wetland polygons and 242,491 road lines. */
var canvasRenderer = L.canvas({ padding: 0.5 });

function fmtNum(v, digits) {
  if (v === null || v === undefined || v === "" || isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits === undefined ? 2 : digits);
}
function fmtMi(v) {
  if (v === null || v === undefined || isNaN(Number(v))) return "—";
  return Number(v).toFixed(2) + " mi";
}
function valOr(v, fallback) {
  if (v === null || v === undefined || v === "") return fallback || "not stated";
  return esc(v);
}
function srcLine(text) {
  return "<p class='pop-note'>" + text + "</p>";
}

/* ---- Trail alerts (NCTA, verbatim) ---- */
function alertPopup(f) {
  var p = f.properties || {};
  return "<h3>" + esc(p.title || "Trail alert") + "</h3>" +
    "<p><strong>" + esc(p.date || "") + "</strong>" +
    (p.location ? " &middot; " + esc(p.location) : "") + "</p>" +
    (p.description ? "<p>" + esc(p.description) + "</p>" : "") +
    srcLine("Quoted verbatim from the NCTA trail alerts service; " +
      "dates are the America/Chicago calendar date of the stored " +
      "instant (see Data sources).");
}
function alertMarker(f, ll) {
  return L.circleMarker(ll, { radius: 6, color: "#92400e", weight: 2,
    fillColor: "#f59e0b", fillOpacity: 0.9 });
}

/* ---- NCT reroutes (NCTA alerts service, layer 2) ---- */
function rerouteStyle() {
  return { color: "#7c3aed", weight: 3, opacity: 0.9 };
}
function reroutePopup(f) {
  var p = f.properties || {};
  return "<h3>" + esc(p.name || "Unnamed reroute") + "</h3>" +
    "<p>" + esc(p.trail_stat || "NCT reroute") +
    " &middot; " + fmtMi(p.length_mi) + "</p>" +
    "<p>Property: " + valOr(p.property) + "<br>Managing authority: " +
    valOr(p.managing_authority) + "</p>" +
    (p.special_regs ? "<p>Special regulations: " + esc(p.special_regs) + "</p>" : "") +
    srcLine("NCTA trail alerts service, layer 2 (reroute lines). " +
      "This is the service's reroute layer, not the 2004 Arrowhead " +
      "reroute corridor polygon.");
}

/* ---- NBI bridges ---- */
function bridgeMarker(f, ll) {
  var tier1 = (f.properties || {}).tier === 1;
  return L.circleMarker(ll, { radius: tier1 ? 5 : 4,
    color: tier1 ? "#1e40af" : "#475569", weight: 2,
    fillColor: tier1 ? "#2563eb" : "#94a3b8", fillOpacity: 0.9 });
}
function bridgePopup(f) {
  var p = f.properties || {};
  var sidewalk = [];
  if (p.sidewalk_left_m) sidewalk.push("left " + fmtNum(p.sidewalk_left_m, 1) + " m");
  if (p.sidewalk_right_m) sidewalk.push("right " + fmtNum(p.sidewalk_right_m, 1) + " m");
  return "<h3>Bridge " + esc(p.bridge_number || "") + "</h3>" +
    "<p><strong>" + esc(p.facility_carried || "Unnamed structure") + "</strong>" +
    (p.features_crossed ? " over " + esc(p.features_crossed) : "") + "</p>" +
    "<p>" + esc(p.location || "") +
    (p.county ? " &middot; " + esc(p.county) + " County, " + esc(p.state || "") : "") + "</p>" +
    "<p>Built " + (p.year_built || "not stated") +
    (p.year_reconstructed ? " &middot; rebuilt " + esc(p.year_reconstructed) : "") +
    " &middot; " + esc(p.structure_kind || "") + "</p>" +
    "<p>Carries: " + esc(p.service_on || "") +
    " &middot; under: " + esc(p.service_under || "") +
    " &middot; " + esc(p.open_closed || "") + "</p>" +
    "<p>Length " + fmtNum(p.structure_len_m, 1) + " m &middot; deck " +
    fmtNum(p.deck_width_m, 1) + " m" +
    (sidewalk.length ? " &middot; sidewalk " + sidewalk.join(", ") : "") + "</p>" +
    "<p>" + (p.tier === 1 ? "Tier 1 — pedestrian / highway-pedestrian bridge" :
      "Tier 2 — highway bridge within 400 m of the trail") +
    " &middot; " + fmtNum(p.dist_trail_km, 2) + " km from the trail</p>" +
    srcLine("FHWA National Bridge Inventory 2025. A crossing " +
      "opportunity, not a trail structure — check the bridge's own " +
      "status before relying on it.");
}

/* ---- NWI wetlands (classified GO / MAYBE / NO-GO) ---- */
/* WETLAND_RULES mirrors working/nwi/wetland-rules.json (and the
   pull script's RULE_TEXT table) — the full rule text lives once
   here, not once per feature. */
var WETLAND_RULES = {
  "W3": { structure: "Avoid — reroute around; a bridge is a bridge project, not a trail-routing MAYBE",
    note: "Permanently flooded / open water ({code}).",
    judgment: "J2: categorical H→NO-GO is judgment" },
  "W4": { structure: "Avoid for a through-route; MAYBE only for a short, named, maintainable spur on bog bridge",
    note: "Black spruce / tamarack bog or bog shrub ({code}, regime {regime}). NPS Arrowhead precedent: 70 mi of this swamp was left unbuilt and rerouted.",
    judgment: "J3: spur exception, no numeric size threshold — table row applied as written" },
  "W5": { structure: "Short, narrow boardwalk only; NO-GO if the crossing exceeds ~300 ft",
    note: "Semipermanently flooded — surface water persists most of the growing season.",
    judgment: "J4: >~300 ft of F-regime tread = NO-GO, route-level check" },
  "W6": { structure: "Bog bridge / boardwalk, short crossing only — narrow point, perpendicular, spanning the full saturated width",
    note: "Seasonally flooded/saturated ({regime_name}).", judgment: null },
  "W6-analog": { structure: "Bog bridge / boardwalk, short crossing only",
    note: "Continuously saturated.",
    judgment: "Report rules do not name regime D; treated as seasonally saturated" },
  "W7": { structure: "Turnpike / puncheon — edge crossing, shortest distance, perpendicular",
    note: "Temporarily flooded/saturated ({regime_name}); field-check peat depth.",
    judgment: "J5: rod-sounding field upgrade — if a rod meets no resistance, upgrade to NO-GO" },
  "W8": {
    nogo: { structure: "No tread along the channel; a single bridge point is a separate project decision, not a routing MAYBE",
      note: "Perennial riverine (R2/R3). Stay 25 ft from the stream edge except at the crossing.", judgment: null },
    maybe: { structure: "Bridge / boardwalk at a narrow point only",
      note: "Intermittent riverine (R4/R5).", judgment: null } },
  "W9": { structure: "Field-check first — do NOT assume degraded = GO; LGU/TEP determination required",
    note: "Modifier '{mods}' (ditched/farmed/excavated) — WCA/404 status is not removed by the modifier.",
    judgment: "J6: MAYBE placement is judgment" },
  "W9-analog": { structure: "Field-check first",
    note: "Shore / intermittently exposed ({code}).",
    note_k: "Artificially flooded — water level is managed ({code}).",
    judgment: "Shore / intermittently exposed treated as W9 MAYBE; regime K (artificially flooded) treated the same way" },
  "UNCLASSIFIED": { structure: "Field-check first",
    note: "Cowardin code {code} ({wet_type}) matched no classification rule.",
    judgment: "No rule in W1-W10 names this code; field-check, do not assume GO" }
};
function wetlandStyle(f) {
  var p = f.properties || {};
  if (p.rating === "nogo") {
    return { color: "#991b1b", weight: 1, fillColor: "#dc2626",
      fillOpacity: 0.45, renderer: canvasRenderer };
  }
  return { color: "#92400e", weight: 1, dashArray: "4 3",
    fillColor: "#f59e0b", fillOpacity: 0.35, renderer: canvasRenderer };
}
function wetlandPopup(f) {
  var p = f.properties || {};
  var rule = WETLAND_RULES[p.rule] || WETLAND_RULES.UNCLASSIFIED;
  if (p.rule === "W8") rule = rule[p.rating === "nogo" ? "nogo" : "maybe"];
  function sub(t) {
    if (!t) return "";
    return t.replace("{code}", p.code || "").replace("{regime}", p.regime || "")
      .replace("{regime_name}", p.regime_name || "")
      .replace("{mods}", p.modifier || "").replace("{wet_type}", p.wetland_type || "");
  }
  var rating = p.rating === "nogo" ? "NO-GO" : "MAYBE";
  var note = (p.rule === "W9-analog" && p.regime === "K") ? rule.note_k : rule.note;
  return "<h3>Wetland — " + rating + "</h3>" +
    "<p><strong>" + esc(p.wetland_type || p.code || "") + "</strong>" +
    (p.code ? " &middot; Cowardin " + esc(p.code) : "") +
    (p.regime_name ? " &middot; " + esc(p.regime_name) : "") + "</p>" +
    "<p>Rule " + esc(p.rule || "UNCLASSIFIED") + " &middot; " +
    esc(p.system || "") + " / " + esc(p["class"] || "") +
    (p.subclass ? " / " + esc(p.subclass) : "") +
    " &middot; " + fmtNum(p.acres, 1) + " ac" +
    (p.n_polygons > 1 ? " (" + p.n_polygons + " source polygons merged)" : "") +
    (p.state ? " &middot; " + esc(p.state) : "") + "</p>" +
    "<p>" + esc(sub(rule.structure)) + "</p>" +
    "<p>" + esc(sub(note)) + "</p>" +
    (rule.judgment ? "<p class='pop-note'>Judgment: " + esc(rule.judgment) + "</p>" : "") +
    srcLine("USFWS National Wetlands Inventory, classified for trail " +
      "routing (see Data sources). Screening only — not a delineation. " +
      "The W2 overlay (public waters / rare communities) is NOT applied " +
      "in this build.");
}

/* ---- Tribal lands (BIA) ---- */
function tribalStyle() {
  return { color: "#6b4f1d", weight: 2, fillColor: "#a16207", fillOpacity: 0.15 };
}
function tribalPopup(f) {
  var p = f.properties || {};
  return "<h3>" + esc(p.name || "Tribal land") + "</h3>" +
    "<p>Bureau of Indian Affairs AIAN Land Area Representation" +
    (p.larid ? " &middot; " + esc(p.larid) : "") +
    (p.region ? " &middot; " + esc(p.region) + " region" : "") + "</p>" +
    "<p>" + fmtNum(p.area_acres, 0) + " ac (geometry-measured)" +
    " &middot; " + fmtMi(p.trail_miles_inside) + " of trail inside" +
    " &middot; " + fmtNum(p.dist_trail_km, 2) + " km from the trail</p>" +
    srcLine("Federal reservation boundary as published — not a legal " +
      "survey. Neither this source nor the map came from the tribe itself.");
}

/* ---- Parcels (county records, Option A — statewide services) ---- */
/* ITM model: crossed parcels solid outline, adjoining parcels dashed.
   ONE color everywhere (Paul, Nov 25, 2026): deep cyan outline
   #0891b2, bright cyan wash #22d3ee — the old crossed-orange
   (#b35806 / #fdbb84) and adjoining-khaki (#a89a5b / #e7e1c3)
   vanished on summer satellite (orange on brown/green) and on
   color-infrared (orange on red vegetation), and the khaki was
   nearly invisible on light paper. Cyan is rare in natural
   imagery, so it reads on light paper, dark LiDAR hillshade,
   summer satellite and CIR red alike (complementary to red).
   Crossed vs adjoining is now dash-only — solid = the trail
   crosses the parcel, dashed "3 3" = adjoining ring — same
   color, same fill. Same color in the ITM viewer and the Leech
   Lake viewer. Faint below corridor zoom, full style at corridor
   zoom and above. The NCT viewer has no zoom bands (ITM's
   currentBand), so the threshold is a plain zoom: full style at
   zoom 11+, faint below. The style function reads the zoom at render
   time; the zoomend listener near the share-hash code re-styles the
   loaded layer when the zoom crosses 11. */
var PARCELS_FULL_ZOOM = 11;
function parcelStyle(f) {
  var crossed = (f.properties || {}).corridor === "crossed";
  if (map.getZoom() < PARCELS_FULL_ZOOM) {
    return { color: "#0891b2", weight: 1,
      opacity: 0.4, dashArray: crossed ? null : "3 3",
      fillColor: "#22d3ee",
      fillOpacity: 0.05 };
  }
  return { color: "#0891b2", weight: 2,
    dashArray: crossed ? null : "3 3",
    fillColor: "#22d3ee",
    fillOpacity: 0.10 };
}
/* Minnesota assessor class-code labels — copied verbatim from
   the Itasca Moraine chapter viewer (St. Louis County's
   published ClassCodeLegend). Itasca County's compiled records
   carry the bare numeric code in useclass1, not the descriptive
   string the other counties carry. */
var PARCEL_LAND_CLASS_LABELS = {
  "Co Admin-TaxForf": "County-administered tax-forfeited land",
  "983 Co Admin-TaxForf": "County-administered tax-forfeited land",
  "5E STATE ACQUIRED - PILT": "State-acquired land, payment in lieu of taxes (PILT)",
  "5E COUNTY ADMINISTERED - PILT": "County-administered land, payment in lieu of taxes (PILT)",
  "Tax Forfeited County Administered/PILT": "County-administered tax-forfeited land (PILT)",
  "5E STATE ADMINISTERED - PILT": "State-administered land, payment in lieu of taxes (PILT)",
  "Non-Comm Seasonal Residential Recreational": "Non-commercial seasonal residential / recreational",
  "30% DNR-RentPmt": "DNR rent-payment land, 30%",
  "Srr": "Seasonal residential / recreational",
  "125 Srr": "Seasonal residential / recreational",
  "ForestParkRefuge": "Forest, park or refuge land",
  "941 ForestParkRefuge": "Forest, park or refuge land",
  "Res 1 Unit": "Residential, 1 unit",
  "100 Res 1 Unit": "Residential, 1 unit",
  "4C12 SEASONAL RESIDENTIAL RECREATION": "Seasonal residential / recreational (class 4c12)",
  "1A/1B/4BB RESIDENTIAL SINGLE UNIT": "Residential single unit (classes 1a / 1b / 4bb)",
  "State Admin Lands Outside ConCon Area/PILT": "State-administered land outside a consolidated conservation area (PILT)",
  "State Acq Lands Outside ConCon Area/PILT": "State-acquired land outside a consolidated conservation area (PILT)",
  "982 State Admin-DNR": "State-administered land (DNR)",
  "942 Indian Resrv": "Indian reservation land",
  "211 Rural Vacant Land": "Rural vacant land",
  "2B/1B RURAL VACANT LAND": "Rural vacant land (classes 2b / 1b)",
  "981 State Acquired": "State-acquired land",
  "Ag Non-Productive Contiguous": "Agricultural, non-productive, contiguous",
  "State Trust Lands in ConCon Area/PILT": "State trust land in a consolidated conservation area (PILT)",
  "5E COUNTY-PUBLIC SERVICE-OTHER": "County public-service land, other",
  "Non-Homestead Qualifying Single Res Unit": "Non-homestead qualifying single residential unit",
  "InLieuTx Co D 8": "In lieu of taxes, county ditch 8",
  "5E FORESTS,PARKS,WILDLIFE REFUGES": "Forests, parks and wildlife refuges",
  /* Numeric assessor class codes (Nov 18, 2026 — Arrowhead parcels):
     Itasca County's compiled records carry the bare numeric code
     in useclass1, not the descriptive string the other counties
     carry. Definitions are the Minnesota assessor class-code
     system, from St. Louis County's published ClassCodeLegend
     (the same statewide codes; Itasca's 33 codes are all listed
     there). The label function appends "(county code: N)". */
  "105": "Agricultural, non-contiguous",
  "111": "Rural vacant land",
  "112": "Managed forest land",
  "151": "Non-commercial seasonal residential / recreational",
  "200": "Residential, 2–3 units",
  "201": "Residential, 1 unit",
  "203": "Residential, 1–3 units (previously seasonal residential recreational)",
  "204": "Non-homestead qualifying single residential unit",
  "205": "Apartment (4 or more units)",
  "211": "Unimproved residential land",
  "215": "Manufactured home park",
  "233": "Commercial (preferred)",
  "234": "Industrial (preferred)",
  "240": "Utility / pipeline land (non-preferred, county-assessed)",
  "243": "Commercial (non-preferred)",
  "244": "Industrial (non-preferred)",
  "324": "Qualifying low-income rental housing, 4+ units",
  "501": "Railroad",
  "505": "Street or roadway",
  "560": "Housing redevelopment authority property",
  "650": "State-acquired land outside a consolidated conservation area (PILT)",
  "660": "State-administered land outside a consolidated conservation area (PILT)",
  "670": "Tax-forfeited land, county-administered (PILT)",
  "671": "Tax-forfeited platted city lots (non-PILT)",
  "710": "Public K–12 school",
  "715": "Public hospital",
  "720": "Public college",
  "730": "Charitable institution",
  "736": "Agricultural historical society",
  "770": "County public service enterprise",
  "771": "County public property, all other",
  "775": "Municipal public service enterprise",
  "776": "Municipal property, all other",
};
function parcelLandClassLabel(raw) {
  if (raw == null) return null;
  if (raw === "None") return "No classification listed";
  var label = PARCEL_LAND_CLASS_LABELS[raw];
  if (!label) return raw;
  return label + " (county code: " + raw + ")";
}

function parcelPopup(f) {
  var p = f.properties || {};
  return "<h3>Parcel " + esc(p.parcel_id || "—") + "</h3>" +
    "<p>" + esc(p.county || "") + " County" +
    (p.state ? ", " + esc(p.state) : "") +
    (p.land_class ? " &middot; " + esc(parcelLandClassLabel(p.land_class)) : "") + "</p>" +
    "<p>" + fmtNum(p.acres, 2) + " ac &middot; " +
    (p.corridor === "crossed" ? "crossed by the trail" :
      "adjoining a crossed parcel") + "</p>" +
    (p.owner ? "<p>Owner: " + esc(p.owner) + "</p>" : "") +
    (p.owner_address ? "<p>Mailing address: " + esc(p.owner_address) +
      "</p>" : "") +
    srcLine(esc(p.source || "County parcel records") +
      (p.vintage ? " — " + esc(p.vintage) : "") +
      ". Owner name and mailing address as published in the county " +
      "records (public record). Taxpayer fields were never pulled. " +
      "Not suitable for accurate boundary determination.");
}

/* ---- PAD-US public land (live ArcGIS service) ---- */
function padusBuild() {
  if (typeof L.esri === "undefined") {
    throw new Error("Esri Leaflet failed to load (site/esri-leaflet.js) — PAD-US needs it");
  }
  var raster = L.esri.dynamicMapLayer({
    url: "https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_gaz_combined/MapServer",
    layers: [0], opacity: 0.45,
    /* f:"image" (not the default f:"json"): the JSON round-trip returns
       a rendered-PNG href on the server's arcgisoutput host, which does
       not answer from this environment, so the image errors and nothing
       draws. Direct image export loads the PNG straight from the
       MapServer and renders (verified in-browser Nov 23, 2026). */
    f: "image",
    attribution: "PAD-US 4.1 (USGS Gap Analysis Project)"
  });
  /* Clickable vector (Manager Name) for popups; drawn nearly
     invisible so it does not double-draw over the raster. */
  var vector = L.esri.featureLayer({
    url: "https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Manager_Name_PADUS/FeatureServer/0",
    fields: ["Own_Name", "Mang_Name", "Unit_Nm", "GAP_Sts", "Pub_Access", "GIS_Acres"],
    style: { color: "#1d4ed8", weight: 0, fillOpacity: 0.02 }
  });
  /* Popup content for a Manager Name feature (bound in the 'add' handler
     below — see note). */
  var padusPopup = function (layer) {
    var p = (layer.feature && layer.feature.properties) || {};
    return "<h3>" + esc(p.Unit_Nm || p.Mang_Name || "Public land") + "</h3>" +
      "<p>Owner: " + valOr(p.Own_Name) + "<br>Manager: " + valOr(p.Mang_Name) + "</p>" +
      "<p>GAP status " + valOr(p.GAP_Sts) + " &middot; public access: " +
      valOr(p.Pub_Access) + " &middot; " + fmtNum(p.GIS_Acres, 0) + " ac</p>" +
      srcLine("USGS PAD-US 4.1, live service. Combined inventory — fee " +
        "+ designations + easements overlap by design; the fee layer is " +
        "the non-overlapping footprint. PAD-US does not tag which " +
        "easements serve the NCT.");
  };
  /* Bind the popup when the vector joins the map and unbind it when it
     leaves. Esri Leaflet's bindPopup only registers the map-click handler
     if the layer already has a map (this._map), and this featureLayer's
     onAdd does not re-register it — so binding here at build time (before
     the layer is added) silently never wires the click, and no popup ever
     opens. Binding on 'add' / unbinding on 'remove' also keeps clicks
     from identifying against the service after the layer is toggled off. */
  vector.on("add", function () { vector.bindPopup(padusPopup); });
  vector.on("remove", function () { vector.unbindPopup(); });
  return L.layerGroup([raster, vector]);
}

/* ---- Chainage (derived) ---- */
function chainageMarker(f, ll) {
  var every10 = !!(f.properties || {}).every10;
  return L.circleMarker(ll, { radius: every10 ? 4 : 2.5,
    color: "#14532d", weight: 1,
    fillColor: every10 ? "#14532d" : "#1a9850", fillOpacity: 0.9,
    renderer: canvasRenderer });
}
function chainagePopup(f) {
  var p = f.properties || {};
  return "<h3>Mile " + esc(p.miles_from_west) + "</h3>" +
    "<p>" + fmtNum(p.miles_from_west, 0) +
    " miles from the western terminus (Lake Sakakawea State Park).</p>" +
    srcLine("Step-3 chain: the ordered centerline walk, 4,826.21 mi " +
      "total. The gazetteer's independent chain walk totals 4,827.41 mi " +
      "— see Data sources for why the two differ by 1.20 mi.");
}

/* ---- Chapter boundaries (derived) ---- */
function boundaryMarker(f, ll) {
  var term = (f.properties || {}).kind === "terminus";
  return L.circleMarker(ll, { radius: term ? 7 : 4.5,
    color: "#b2182b", weight: 2,
    fillColor: term ? "#b2182b" : "#ffffff", fillOpacity: 0.95 });
}
function boundaryPopup(f) {
  var p = f.properties || {};
  if (p.kind === "terminus") {
    return "<h3>" + esc(p.name || "Terminus") + "</h3>" +
      "<p>Chainage " + fmtMi(p.chainage_mi) + "</p>" +
      (p.note ? "<p>" + esc(p.note) + "</p>" : "") +
      srcLine("Step-3 chain terminus. The eastern terminus is the " +
        "Appalachian Trail junction in Vermont, not Crown Point — " +
        "Crown Point is a chapter junction in this layer.");
  }
  var variant = ["None", "LON", "GTR", "Central NY"].indexOf(p.chapter_from_code) >= 0 ||
    ["None", "LON", "GTR", "Central NY"].indexOf(p.chapter_to_code) >= 0;
  return "<h3>" + esc(p.chapter_from_name || p.chapter_from_code) + " → " +
    esc(p.chapter_to_name || p.chapter_to_code) + "</h3>" +
    "<p>" + esc(p.chapter_from_code) + " → " + esc(p.chapter_to_code) +
    " &middot; chainage " + fmtMi(p.chainage_mi) + "</p>" +
    "<p>" + esc(p.state_from || "") +
    (p.state_to && p.state_to !== p.state_from ? " → " + esc(p.state_to) : "") + "</p>" +
    (variant ? srcLine("Junction with unassigned or variant-coded " +
      "ground — the gazetteer's 38 named boundaries collapse these " +
      "interleavings; this layer shows all 86 data junctions. See " +
      "Data sources.") :
      srcLine("Chapter extent endpoint, from the chapter change in " +
        "the centerline data."));
}

/* ---- Road walk (derived) ---- */
function roadWalkStyle() {
  return { color: "#7f1d1d", weight: 4, opacity: 0.75 };
}
function roadWalkPopup(f) {
  var p = f.properties || {};
  return "<h3>" + esc(p.segment || "Road walk") + "</h3>" +
    "<p>" + fmtMi(p.length_mi) + " &middot; chain miles " +
    fmtNum(p.chain_start_mi, 2) + "–" + fmtNum(p.chain_end_mi, 2) + "</p>" +
    "<p>Chapters: " + esc((p.chapters || []).join(", ")) +
    " &middot; states: " + esc((p.states || []).join(", ")) + "</p>" +
    srcLine("Derived from the centerline's road class, west to east. " +
      "No road name, speed limit, shoulder width or crash data — the " +
      "source carries none; those are undecided measurement programs.");
}

/* ---- Camping + NCTA Places (NCTA points service) ---- */
function pointPopup(f, kindLabel) {
  var p = f.properties || {};
  var name = p.name || (p.type || kindLabel) + " (unnamed in the NCTA service)";
  var html = "<h3>" + esc(name) + "</h3>" +
    "<p><strong>" + esc(p.type || kindLabel) + "</strong>" +
    (p.subtype ? " &middot; " + esc(p.subtype) : "") +
    (p.extra_types && p.extra_types.length ? " &middot; " + esc(p.extra_types.join(", ")) : "") + "</p>";
  if (p.owner) html += "<p>Owner: " + esc(p.owner) + "</p>";
  if (p.chapter || p.state) {
    html += "<p>" + (p.chapter ? "Chapter " + esc(p.chapter) : "") +
      (p.chapter && p.state ? " &middot; " : "") + esc(p.state || "") + "</p>";
  }
  if (p.description) html += "<p>" + esc(p.description) + "</p>";
  html += srcLine("NCTA Point Data (public), waypoint " +
    esc(p.waypoint_id || "") +
    (p.updated ? " &middot; updated " + esc(p.updated) : "") +
    ". Descriptions are carried verbatim from the NCTA service.");
  return html;
}
function campingMarker(f, ll) {
  return L.circleMarker(ll, { radius: 5, color: "#14532d", weight: 2,
    fillColor: "#2a7f62", fillOpacity: 0.9, renderer: canvasRenderer });
}
var PLACE_COLORS = { "Parking": "#64748b", "Water": "#0284c7",
  "Developed Water Source": "#0284c7", "POI": "#b45309",
  "Shelter": "#78350f", "Ford": "#0f766e" };
function placeMarker(f, ll) {
  var c = PLACE_COLORS[(f.properties || {}).type] || "#475569";
  return L.circleMarker(ll, { radius: 5, color: "#1e293b", weight: 1.5,
    fillColor: c, fillOpacity: 0.9, renderer: canvasRenderer });
}

/* ---- Mile markers (NCTA state half-mile services) ---- */
function mileMarker(f, ll) {
  return L.circleMarker(ll, { radius: 2.5, color: "#1e293b", weight: 1,
    fillColor: "#334155", fillOpacity: 0.9, renderer: canvasRenderer });
}
function milePopup(f) {
  var p = f.properties || {};
  return "<h3>" + esc(p.ident || "Mile marker") + "</h3>" +
    "<p>State mile " + fmtNum(p.mile, 1) + " &middot; " + esc(p.state || "") +
    " &middot; " + esc(p.region || "") + "</p>" +
    "<p>" + esc(p.index_ || "") +
    (p.wypnt_id ? " &middot; " + esc(p.wypnt_id) : "") +
    " &middot; " + esc(p.source_service || "") + "</p>" +
    srcLine("State reckoning — miles from that state's start, not " +
      "trail-wide chainage. Coverage gaps: Minnesota east of mile 558.5 " +
      "(Border Route / Superior Hiking Trail stretches), the ~932 mi " +
      "Buckeye Trail portion of Ohio, and the ~390 mi Finger Lakes " +
      "portion of New York have no half-mile index. See Data sources.");
}

/* ---- Partner / concurrent trails ---- */
var PARTNER_COLORS = { "Superior Hiking Trail": "#0e7490",
  "Border Route Trail": "#7c3aed", "BWCA portages": "#0f766e",
  "Trails near Border Route & SHT": "#65a30d",
  "Driftless Hiking Trail": "#b45309", "Buckeye Trail": "#b91c1c",
  "Finger Lakes Trail": "#1d4ed8", "Long Trail": "#166534" };
function partnerStyle(f) {
  var c = PARTNER_COLORS[(f.properties || {}).trail] || "#475569";
  return { color: c, weight: 3, opacity: 0.85 };
}
function partnerPopup(f) {
  var p = f.properties || {};
  return "<h3>" + esc(p.name || p.trail || "Partner trail") + "</h3>" +
    "<p><strong>" + esc(p.trail || "") + "</strong> &middot; " +
    fmtMi(p.length_mi) + "</p>" +
    "<p>" + fmtMi(p.concurrent_miles) + " within 50 m of the NCT" +
    (p.concurrent_pct !== undefined && p.concurrent_pct !== null ?
      " (" + fmtNum(p.concurrent_pct, 0) + "%)" : "") +
    (p.concurrent_with_nct ? " &middot; concurrent" : "") +
    " &middot; closest approach " + fmtNum(p.min_distance_m, 0) + " m</p>" +
    (p.source_url ? "<p>Source: <a href='" + esc(p.source_url) +
      "' target='_blank' rel='noopener'>" + esc(p.source || "source") + "</a></p>" :
      (p.source ? "<p>Source: " + esc(p.source) + "</p>" : "")) +
    srcLine("Partner-trail geometry is kept whole where it overlaps " +
      "the NCT — the overlap is flagged here, never deleted. The 50 m " +
      "tolerance is the ITM viewer's overlap rule.");
}

/* ---- OSM roads ---- */
function osmRoadStyle() {
  return { color: "#6b7280", weight: 1, opacity: 0.55,
    renderer: canvasRenderer };
}
function osmRoadPopup(f) {
  var p = f.properties || {};
  return "<h3>" + esc(p.name || "Unnamed road") + "</h3>" +
    "<p>" + esc(p.highway || "") +
    (p.ref ? " &middot; " + esc(p.ref) : "") +
    (p.surface ? " &middot; surface " + esc(p.surface) : "") +
    " &middot; " + fmtMi(p.length_mi) + "</p>" +
    srcLine("OpenStreetMap road centerlines in the 2 mi trail " +
      "corridor (Geofabrik state extracts). ODbL.");
}

/* ---- OSM bike routes ---- */
function osmBikeStyle() {
  return { color: "#059669", weight: 3, opacity: 0.85 };
}
function osmBikePopup(f) {
  var p = f.properties || {};
  return "<h3>" + esc(p.name || "Bike route") + "</h3>" +
    "<p>" + (p.ref ? esc(p.ref) + " &middot; " : "") +
    esc(p.network || "") + " &middot; " + fmtMi(p.length_mi) + "</p>" +
    "<p>OSM relation " + esc(p.osm_id || "") + "</p>" +
    srcLine("OpenStreetMap bicycle route relations in the 2 mi " +
      "corridor. The Mesabi Trail (relation 5326107) is in here as " +
      "one route among others. ODbL.");
}

/* ---- NCTA map sheets ---- */
function sheetStyle() {
  return { color: "#1d4ed8", weight: 1, fillColor: "#3b82f6", fillOpacity: 0.08 };
}
function sheetPopup(f) {
  var p = f.properties || {};
  return "<h3>Sheet " + esc(p.sheet || "") + "</h3>" +
    "<p>" + esc(p.state || "") + " &middot; series " + esc(p.series || "") +
    " &middot; page " + esc(p.page || "") + "</p>" +
    "<p>" + fmtMi(p.trail_miles_in_sheet) + " of trail in this sheet</p>" +
    (p.source_pdf ? "<p><a href='" + esc(p.source_pdf) +
      "' target='_blank' rel='noopener'>NCTA map-series PDF</a></p>" : "") +
    srcLine("Footprint only — no sheet images are built here. " +
      "Coverage gaps: Ohio 13%, New York 40%, Minnesota 67% of " +
      "centerline miles fall inside a published sheet; the gaps are " +
      "gaps in the published series, not in this pull. See Data sources.");
}

/* Generic GeoJSON builder: one L.geoJSON with a style / point
   function and a popup function. */
/* Merge one FeatureCollection, or an array of them (a layer split
   across several files — wetlands and OSM roads, both over GitHub's
   100 MB file cap), into a single FeatureCollection so the layer
   draws exactly as it would from one file. */
function mergeParts(gj) {
  if (!gj) return gj;
  if (!Array.isArray(gj)) return gj;
  var features = [];
  gj.forEach(function (part) {
    if (part && part.features) features = features.concat(part.features);
  });
  return { type: "FeatureCollection", features: features };
}

function geojsonLayer(gj, opts) {
  return L.geoJSON(gj, {
    style: opts.style || undefined,
    pointToLayer: opts.pointToLayer || undefined,
    renderer: opts.renderer || undefined,
    onEachFeature: function (f, l) {
      if (opts.popup) bindPop(l, opts.popup(f));
    }
  });
}

/* ---- Gazetteer search (search index, not a map layer) ---- */
var gazData = null, gazMarker = null, gazLoading = null;
function initGazetteer() {
  var input = document.getElementById("gaz-search");
  var results = document.getElementById("gaz-results");
  if (!input || !results) return;
  input.disabled = false;
  input.addEventListener("input", function () {
    var q = input.value.trim().toLowerCase();
    if (q.length < 2) { results.innerHTML = ""; return; }
    if (!gazData) {
      if (!gazLoading) {
        results.innerHTML = "<div class='gaz-result'>Loading place index&hellip;</div>";
        gazLoading = fetchJson("data/gazetteer.json").then(function (gj) {
          gazData = gj;
          gazSearch(q);
        }).catch(function (err) {
          results.innerHTML = "<div class='gaz-result'>Place index failed to load — " +
            esc(err.message) + "</div>";
          gazLoading = null;
        });
      }
      return;
    }
    gazSearch(q);
  });
  input.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { results.innerHTML = ""; input.blur(); }
  });
  document.addEventListener("click", function (e) {
    if (!document.getElementById("gazetteer").contains(e.target)) {
      results.innerHTML = "";
    }
  });
}
function gazSearch(q) {
  var results = document.getElementById("gaz-results");
  var tokens = q.split(/\s+/).filter(Boolean);
  var hits = gazData.entries.filter(function (e) {
    var t = e.search_text || "";
    for (var i = 0; i < tokens.length; i++) {
      if (t.indexOf(tokens[i]) < 0) return false;
    }
    return true;
  }).slice(0, 8);
  var total = gazData.entries.filter(function (e) {
    var t = e.search_text || "";
    for (var i = 0; i < tokens.length; i++) {
      if (t.indexOf(tokens[i]) < 0) return false;
    }
    return true;
  }).length;
  if (!hits.length) {
    results.innerHTML = "<div class='gaz-result'>No places match &ldquo;" +
      esc(q) + "&rdquo;.</div>";
    return;
  }
  var html = "";
  hits.forEach(function (e, i) {
    html += "<button type='button' class='gaz-result' data-i='" + i + "'>" +
      "<span class='gaz-name'>" + esc(e.name) + "</span>" +
      "<span class='gaz-meta'>" + esc(e.kind) + " &middot; " +
      esc(e.state || "") +
      (e.chainage_mi !== null && e.chainage_mi !== undefined ?
        " &middot; mi " + Number(e.chainage_mi).toFixed(1) : " &middot; off the mapped line") +
      "</span></button>";
  });
  if (total > hits.length) {
    html += "<div class='gaz-more'>" + total + " matches — showing the first " +
      hits.length + ".</div>";
  }
  results.innerHTML = html;
  results.querySelectorAll(".gaz-result").forEach(function (btn) {
    btn.addEventListener("click", function () {
      showGazResult(hits[Number(btn.getAttribute("data-i"))]);
      results.innerHTML = "";
    });
  });
}
function showGazResult(e) {
  var ll = [e.coordinates[1], e.coordinates[0]];
  if (gazMarker) map.removeLayer(gazMarker);
  gazMarker = L.marker(ll).addTo(map);
  var html = "<h3>" + esc(e.name) + "</h3>" +
    "<p><strong>" + esc(e.kind) + "</strong>" +
    (e.chapter ? " &middot; chapter " + esc(e.chapter) : "") +
    (e.state ? " &middot; " + esc(e.state) : "") + "</p>";
  if (e.kind === "Chapter boundary") {
    html += "<p>" + esc(e.west_chapter || "") + " → " + esc(e.east_chapter || "") + "</p>" +
      (e.junction_name ? "<p>At " + esc(e.junction_name) + "</p>" : "<p>Junction place name not stated in the extents table.</p>");
  }
  if (e.chainage_mi !== null && e.chainage_mi !== undefined) {
    html += "<p>Chainage " + fmtMi(e.chainage_mi) + " from the western terminus" +
      " &middot; " + fmtMi(e.from_east_mi) + " from the east end</p>";
  } else {
    html += "<p>Off the mapped line — nearest centerline segment is " +
      fmtNum(e.snap_m, 0) + " m away, so no chainage is given rather " +
      "than a fabricated one.</p>";
  }
  if (e.kind === "Mile marker") {
    html += "<p>State mile " + fmtNum(e.state_mile, 1) + " &middot; " + esc(e.state_ident || "") + "</p>";
  }
  if (e.subtype) html += "<p>" + esc(e.subtype) + "</p>";
  html += srcLine("NCT gazetteer — 8,930 entries from NCTA points, " +
    "state mile markers, and chapter boundaries. See Data sources.");
  gazMarker.bindPopup(html, { maxWidth: 320 }).openPopup();
  map.flyTo(ll, Math.max(map.getZoom(), 12));
  var el = document.getElementById("inspector");
  if (el) el.innerHTML = html +
    "<p><button type='button' class='clear-chapter' id='gaz-clear-btn'>Clear marker</button></p>";
  var btn = document.getElementById("gaz-clear-btn");
  if (btn) btn.addEventListener("click", function () {
    if (gazMarker) { map.removeLayer(gazMarker); gazMarker = null; }
    showChapterRecord(selectedChapter ?
      chapterExtents.filter(function (r) { return r.code === selectedChapter; })[0] : null, 0);
    if (!selectedChapter) showChapterRecord(null, 0);
  });
}

/* ------------------------------------------------------ layer registry
   Each entry: {id, title, group, onByDefault, file(s), style, popup,
   build}. A STUB entry carries `stub: true` and no data — only soils
   is still a stub (service recovered, pull not yet run); its toggle
   is disabled and marked "coming soon". Nothing is invented for a
   stub. Search entries (gazetteer) carry `search: true` and no map
   layer — they wire the Find box instead of a toggle. */
var LAYERS = [
  {
    id: "base-line", title: "North Country Trail — base line",
    label: "NCT base line",
    group: "The trail",
    onByDefault: true,
    files: ["data/centerline-natural.geojson",
      "data/centerline-road.geojson",
      "data/centerline-urban.geojson"],
    swatch: { kind: "line", color: COLORS.natural },
    build: function (parts) { return buildBaseLine(parts); },
    popup: baseLinePopup,
  },
  {
    id: "chapters", title: "Chapters — click a chapter in the panel " +
      "to highlight its miles and zoom to them",
    label: "Chapters",
    group: "The trail",
    onByDefault: true,
    file: "data/chapter-extents.json",
    swatch: { kind: "line", color: COLORS.highlight },
    build: function (gj) { return buildChapters(gj); },
  },
  {
    /* Waymarked Trails hiking routes (ITM pattern): a transparent
       tile overlay, drawn over any base. Keyless, free. Tiles are
       blank where no waymarked route crosses — correct behaviour,
       not a missing tile. */
    id: "waymarked", title: "Hiking routes (Waymarked Trails)",
    label: "Hiking routes (Waymarked Trails)",
    group: "The trail",
    onByDefault: false,
    file: null,
    swatch: { kind: "line", color: "#7e6a9e" },
    build: function () {
      return L.tileLayer(
        "https://tile.waymarkedtrails.org/hiking/{z}/{x}/{y}.png", {
          maxZoom: 18, opacity: 0.75,
          attribution: "Hiking routes: © Waymarked Trails (Sarah " +
            "Hoffmann), © OpenStreetMap contributors",
        });
    },
  },
  /* ---- WAVE 1 (wired Nov 23, 2026) ---- */
  {
    id: "alerts", label: "Trail alerts", group: "Alerts & reroutes",
    onByDefault: false,
    title: "NCTA trail alerts (closures, storm damage) — quoted verbatim, 83 points. Dates are the America/Chicago calendar date of the stored instant.",
    file: "data/trail-alerts.geojson",
    swatch: { kind: "dot", color: "#f59e0b" },
    build: function (gj) {
      return geojsonLayer(gj, { pointToLayer: alertMarker, popup: alertPopup });
    },
  },
  {
    id: "reroutes", label: "NCT reroutes", group: "Alerts & reroutes",
    onByDefault: false,
    title: "Reroute lines from the NCTA alerts service, layer 2 — 15 lines.",
    file: "data/nct-reroutes.geojson",
    swatch: { kind: "line", color: "#7c3aed" },
    build: function (gj) {
      return geojsonLayer(gj, { style: rerouteStyle, popup: reroutePopup });
    },
  },
  {
    id: "nbi-bridges", label: "Bridges — crossing opportunities",
    group: "Crossings & land", onByDefault: false,
    title: "FHWA National Bridge Inventory 2025 — 1,415 structures. Tier 1: pedestrian / highway-pedestrian within 2 mi; Tier 2: highway bridges within 400 m.",
    file: "data/nbi-bridges.geojson",
    swatch: { kind: "dot", color: "#2563eb" },
    build: function (gj) {
      return geojsonLayer(gj, { pointToLayer: bridgeMarker, popup: bridgePopup });
    },
  },
  {
    id: "wetlands-nwi", label: "Wetlands (NWI) — trail routing",
    group: "Crossings & land", onByDefault: false,
    title: "USFWS National Wetlands Inventory, classified GO / MAYBE / NO-GO — 352,865 polygons, split into 4 files (GitHub rejects files over 100 MB; the single 174 MB file is kept locally, gitignored). Loads only when switched on; may take a while. OFF by default.",
    files: ["data/nwi-wetlands-mn.geojson",
      "data/nwi-wetlands-nd-mi.geojson",
      "data/nwi-wetlands-oh-ny.geojson",
      "data/nwi-wetlands-wi-vt-pa.geojson"],
    swatch: { kind: "fill", color: "#dc2626" },
    build: function (parts) {
      return geojsonLayer(mergeParts(parts), { style: wetlandStyle, popup: wetlandPopup });
    },
  },
  {
    id: "tribal-bia", label: "Tribal lands (BIA)",
    group: "Crossings & land", onByDefault: false,
    title: "BIA AIAN Land Area Representation — 11 reservations within 2 mi of the trail. Federal boundary as published, not a legal survey.",
    file: "data/tribal-lands.geojson",
    swatch: { kind: "fill", color: "#a16207" },
    build: function (gj) {
      return geojsonLayer(gj, { style: tribalStyle, popup: tribalPopup });
    },
  },
  {
    id: "padus", label: "Public land (PAD-US)",
    group: "Crossings & land", onByDefault: false,
    title: "USGS PAD-US 4.1, live ArcGIS service (no local file) — combined-inventory raster plus a clickable Manager Name vector for popups. OFF by default.",
    file: null,
    swatch: { kind: "fill", color: "#4d7c0f" },
    build: function () { return padusBuild(); },
  },
  {
    id: "parcels", label: "Parcels", group: "Crossings & land",
    onByDefault: false,
    title: "County parcels the trail crosses, plus the adjoining ring — 141,687 parcels, 3,031.45 trail miles (63.7%). Six statewide services (ND, MN, WI, VT, NY, OH); Michigan, NY's 5 opt-out counties and Pennsylvania mostly blank. OFF by default; loads only when switched on — 98 MB file, may take a while.",
    file: "data/parcels.geojson",
    swatch: { kind: "fill", color: "#22d3ee", border: "#0891b2" },
    build: function (gj) {
      return geojsonLayer(gj, { style: parcelStyle, popup: parcelPopup,
        renderer: canvasRenderer });
    },
  },
  {
    id: "soils", label: "Soils (SSURGO) — trail routing",
    group: "Crossings & land", onByDefault: false, stub: true,
    title: "NRCS SSURGO — not yet built",
    note: "The NRCS Soil Data Access service answered again on 2026-11-23 (both hosts, HTTP 200) after the Nov 18 outage (HTTP 502), so the national pull is unblocked — but it has not been run yet. No soils data is shown; nothing is invented here.",
  },
  {
    id: "chainage", label: "Chainage (miles from west end)",
    group: "Derived", onByDefault: false,
    title: "One point per integer mile, 1–4,826, from the step-3 chain walk (4,826.21 mi total). Every 10th mile is drawn larger.",
    file: "data/chainage.geojson",
    swatch: { kind: "dot", color: "#1a9850" },
    build: function (gj) {
      return geojsonLayer(gj, { pointToLayer: chainageMarker, popup: chainagePopup });
    },
  },
  {
    id: "chapter-boundaries", label: "Chapter boundaries",
    group: "Derived", onByDefault: false,
    title: "Chapter extent endpoints from the chapter change in the centerline data — 86 junctions + 2 termini. The gazetteer's 38 named boundaries collapse the unassigned/variant interleavings; see Data sources.",
    file: "data/chapter-boundaries.geojson",
    swatch: { kind: "dot", color: "#b2182b" },
    build: function (gj) {
      return geojsonLayer(gj, { pointToLayer: boundaryMarker, popup: boundaryPopup });
    },
  },
  {
    id: "road-walk", label: "Road walk", group: "Derived",
    onByDefault: false,
    title: "Road-walk segments derived from the centerline's road class — 573 segments, 1,393.98 mi. No speed limits, shoulder widths or crash data (undecided measurement programs).",
    file: "data/road-walk.geojson",
    swatch: { kind: "line", color: "#7f1d1d" },
    build: function (gj) {
      return geojsonLayer(gj, { style: roadWalkStyle, popup: roadWalkPopup });
    },
  },
  {
    id: "camping", label: "Camping", group: "Places & points",
    onByDefault: false,
    title: "NCTA camping waypoints, nationally — 502. One layer (the chapter viewer splits it three ways by chapter).",
    file: "data/camping.geojson",
    swatch: { kind: "dot", color: "#2a7f62" },
    build: function (gj) {
      return geojsonLayer(gj, { pointToLayer: campingMarker,
        popup: function (f) { return pointPopup(f, "Camping"); } });
    },
  },
  {
    id: "ncta-places", label: "NCTA Places", group: "Places & points",
    onByDefault: false,
    title: "NCTA points (parking, water, POI, shelter, ford) — 2,044. Types are the service's own, carried verbatim.",
    file: "data/ncta-places.geojson",
    swatch: { kind: "dot", color: "#0284c7" },
    build: function (gj) {
      return geojsonLayer(gj, { pointToLayer: placeMarker,
        popup: function (f) { return pointPopup(f, "Place"); } });
    },
  },
  {
    id: "mile-markers", label: "NCTA mile markers",
    group: "Places & points", onByDefault: false,
    title: "NCTA state half-mile markers — 6,344. Coverage gaps in Minnesota (east of mile 558.5), Ohio (Buckeye portion) and New York (Finger Lakes portion) — honest gaps, not filled. See Data sources.",
    file: "data/mile-markers.geojson",
    swatch: { kind: "dot", color: "#334155" },
    build: function (gj) {
      return geojsonLayer(gj, { pointToLayer: mileMarker, popup: milePopup });
    },
  },
  {
    id: "partner-trails", label: "Concurrent / partner trails",
    group: "Other trails & roads", onByDefault: false,
    title: "Trails that run with the NCT — Buckeye, Finger Lakes, Long Trail, Superior Hiking Trail, Border Route Trail, Driftless, BWCA portages — 687 features, 2,687.37 mi.",
    file: "data/partner-trails.geojson",
    swatch: { kind: "line", color: "#b91c1c" },
    build: function (gj) {
      return geojsonLayer(gj, { style: partnerStyle, popup: partnerPopup });
    },
  },
  {
    id: "osm-roads", label: "Roads (OSM)", group: "Other trails & roads",
    onByDefault: false,
    title: "OSM road centerlines in the 2 mi corridor — 242,491 features, split into 2 files (GitHub rejects files over 100 MB; the single 109 MB file is kept locally, gitignored). Loads only when switched on; may take a while. OFF by default.",
    files: ["data/osm-roads-west.geojson", "data/osm-roads-east.geojson"],
    swatch: { kind: "line", color: "#6b7280" },
    build: function (parts) {
      return geojsonLayer(mergeParts(parts), { style: osmRoadStyle, popup: osmRoadPopup });
    },
  },
  {
    id: "osm-bike", label: "Bike routes (OSM)",
    group: "Other trails & roads", onByDefault: false,
    title: "OpenStreetMap bicycle routes — 132 features, 1,992.27 mi. The Mesabi Trail (relation 5326107) is in here as one route among others.",
    file: "data/osm-bike-routes.geojson",
    swatch: { kind: "line", color: "#059669" },
    build: function (gj) {
      return geojsonLayer(gj, { style: osmBikeStyle, popup: osmBikePopup });
    },
  },
  {
    id: "ncta-sheets", label: "NCTA map sheets", group: "Reference",
    onByDefault: false,
    title: "NCTA map-sheet footprints, full set — 523 sheets. Footprints only, no sheet images. Coverage gaps: Ohio 13%, New York 40%, Minnesota 67% — honest gaps, not filled. See Data sources.",
    file: "data/ncta-map-sheets.geojson",
    swatch: { kind: "fill", color: "#3b82f6" },
    build: function (gj) {
      return geojsonLayer(gj, { style: sheetStyle, popup: sheetPopup });
    },
  },
  {
    id: "gazetteer", label: "Place search (gazetteer)",
    group: "Reference", onByDefault: false, search: true,
    title: "Search 8,930 places along the trail — NCTA points, state mile markers, chapter boundaries. Type at least 2 characters in Find above.",
    note: "Search, not a list.",
  },

];

function layerById(id) {
  for (var i = 0; i < LAYERS.length; i++) {
    if (LAYERS[i].id === id) return LAYERS[i];
  }
  return null;
}

/* Base-line styles: the same three-class treatment as the old viewer —
   natural tread solid green, urban sidewalk solid amber, road dashed
   red. A white casing under the natural line keeps it legible on
   imagery bases (ITM casing pattern). */
function baseLineStyle(feature) {
  var cls = feature.properties && feature.properties["class"];
  if (cls === "road") {
    return { color: COLORS.road, weight: 2.5, opacity: 0.9,
      dashArray: "6 4", lineCap: "round" };
  }
  if (cls === "urban") {
    return { color: COLORS.urban, weight: 2.5, opacity: 0.9,
      lineCap: "round" };
  }
  return { color: COLORS.natural, weight: 3, opacity: 0.95,
    lineCap: "round" };
}
function baseLineCasingStyle(feature) {
  var cls = feature.properties && feature.properties["class"];
  if (cls === "natural") {
    return { color: COLORS.casing, weight: 5, opacity: 0.7,
      lineCap: "round", interactive: false };
  }
  return { color: COLORS.casing, weight: 0, opacity: 0,
    interactive: false };
}
function classLabel(cls) {
  if (cls === "road") return "Road";
  if (cls === "urban") return "Urban sidewalk";
  return "Natural tread";
}
function baseLinePopup(f) {
  var p = f.properties || {};
  var chapter = CHAPTER_NAMES[p.chapter] || p.chapter || "Unassigned";
  var miles = (p.miles !== undefined && p.miles !== null) ?
    Number(p.miles).toFixed(2) + " mi" : "";
  var rows = "<h3>North Country Trail</h3>" +
    "<p><strong>" + esc(classLabel(p["class"])) + "</strong>" +
    (miles ? " &middot; " + esc(miles) : "") + "</p>" +
    "<p>Chapter: " + esc(chapter) +
    (p.state ? " &middot; " + esc(p.state) : "") + "</p>";
  if (p.seg_name) rows += "<p>" + esc(p.seg_name) + "</p>";
  rows += "<p class='pop-note'>Centerline: NCTA official route, " +
    "pull of November 21, 2026.</p>";
  return rows;
}
function bindPop(layer, html) {
  layer.bindPopup(html, { maxWidth: 320 });
}

var wholeTrailBounds = null;
var baseFeatures = []; /* all centerline features, for chapter highlight */

function buildBaseLine(parts) {
  /* parts: [natural, road, urban] GeoJSON in file order. A
     FeatureGroup (not a LayerGroup) so getBounds works for the
     whole-trail zoom. */
  var group = L.featureGroup();
  parts.forEach(function (gj) {
    if (!gj || !gj.features) return;
    baseFeatures = baseFeatures.concat(gj.features);
    var casing = L.geoJSON(gj, { style: baseLineCasingStyle });
    var core = L.geoJSON(gj, {
      style: baseLineStyle,
      onEachFeature: function (f, l) { bindPop(l, baseLinePopup(f)); },
    });
    group.addLayer(casing);
    group.addLayer(core);
  });
  wholeTrailBounds = group.getBounds();
  if (!initialView && !requestedChapter) {
    map.fitBounds(wholeTrailBounds.pad(0.02));
  }
  return group;
}

/* ---------------------------------------------------------- chapters */

var chapterExtents = [];
var selectedChapter = null;
var highlightLayer = null;

function buildChapters(extents) {
  chapterExtents = extents;
  extents.forEach(function (row) {
    CHAPTER_NAMES[row.code] = row.name;
  });
  CHAPTER_NAMES["None"] = "Unassigned";
  buildChapterList();
  buildLegend();
  /* A chapter requested in the share hash applies once the data is in. */
  if (requestedChapter) {
    var code = requestedChapter;
    requestedChapter = null;
    selectChapter(code, true);
  }
  return L.layerGroup([]); /* the chapter layer is the panel + highlight */
}

function chapterCodesFor(code) {
  return CHAPTER_MATCH[code] || [code];
}
function featuresForChapter(code) {
  var wanted = chapterCodesFor(code);
  return baseFeatures.filter(function (f) {
    var c = f.properties && f.properties.chapter;
    if (c === undefined) c = null;
    return wanted.indexOf(c) >= 0;
  });
}

/* Chapter dropdown, alone (Nov 24, 2026 panel rebuild): the
   chapter listbox is gone — the <select> is the only chapter
   picker, populated west to east from the extents table. */
function buildChapterList() {
  var sel = document.getElementById("chapter-select");
  if (!sel) return;
  sel.innerHTML = "";
  var blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "Choose a chapter…";
  sel.appendChild(blank);
  chapterExtents.forEach(function (row) {
    var opt = document.createElement("option");
    opt.value = row.code;
    opt.textContent = row.name + " (" + row.code + ")";
    sel.appendChild(opt);
  });
}

/* Chapter dropdown: choosing one flies to it exactly as clicking
   its row does; choosing the blank entry clears the selection. */
(function wireChapterSelect() {
  var sel = document.getElementById("chapter-select");
  if (!sel) return;
  sel.addEventListener("change", function () {
    if (sel.value) selectChapter(sel.value, false);
    else clearChapter();
  });
})();

function selectChapter(code, fromHash) {
  var row = null;
  chapterExtents.forEach(function (r) { if (r.code === code) row = r; });
  if (!row) return;
  clearHighlight();
  selectedChapter = code;
  var feats = featuresForChapter(code);
  if (feats.length) {
    highlightLayer = L.geoJSON(
      { type: "FeatureCollection", features: feats }, {
        style: { color: COLORS.highlight, weight: 6, opacity: 0.85,
          lineCap: "round" },
        interactive: false,
      });
    highlightLayer.addTo(map);
    if (!fromHash || !initialView) {
      map.fitBounds(highlightLayer.getBounds().pad(0.08));
    }
  }
  markChapterRow(code);
  showChapterRecord(row, feats.length);
  writeShareHash();
}
function clearChapter() {
  clearHighlight();
  selectedChapter = null;
  markChapterRow(null);
  showChapterRecord(null, 0);
  if (wholeTrailBounds) map.fitBounds(wholeTrailBounds.pad(0.02));
  writeShareHash();
}
function clearHighlight() {
  if (highlightLayer) {
    map.removeLayer(highlightLayer);
    highlightLayer = null;
  }
}
/* Keep the dropdown in step with selections and clears. */
function markChapterRow(code) {
  var sel = document.getElementById("chapter-select");
  if (sel) sel.value = code || "";
}
function showChapterRecord(row, featureCount) {
  var el = document.getElementById("inspector");
  if (!row) {
    /* No chapter selected: the inspector stays empty (and hidden
       by :empty) — no permanent placeholder box in the panel. */
    el.innerHTML = "";
    return;
  }
  var extra = "";
  if (row.code === "CNY") {
    extra = "<p class='pop-note'>Includes 2.46 mi tagged " +
      "&ldquo;Central NY&rdquo;, a variant spelling of this chapter.</p>";
  } else if (row.code === "GTC") {
    extra = "<p class='pop-note'>Includes 1.56 mi tagged " +
      "&ldquo;GTR&rdquo;, a probable variant of this chapter.</p>";
  } else if (row.code === "Unassigned") {
    extra = "<p class='pop-note'>Includes 1.48 mi tagged " +
      "&ldquo;LON&rdquo; (New Rockford Canal), code meaning unconfirmed. " +
      "Miles as tagged in the NCTA source; some stretches carry no " +
      "chapter at all.</p>";
  }
  el.innerHTML =
    "<h3>" + esc(row.name) + "</h3>" +
    "<p><strong>" + esc(row.code) + "</strong> &middot; " +
      esc(row.states) + " &middot; " +
      Number(row.miles).toFixed(2) + " mi</p>" +
    "<p>From " + esc(row.west) + " to " + esc(row.east) + ".</p>" +
    (row.url ? "<p><a href='" + esc(row.url) + "' target='_blank' " +
      "rel='noopener'>Chapter page</a></p>" : "") +
    "<p class='pop-note'>" + featureCount + " centerline features " +
      "highlighted. Mileage is the sum of the NCTA source's miles " +
      "field per chapter (pull of November 21, 2026); see About for " +
      "the caveats.</p>" +
    extra +
    "<p><button type='button' class='clear-chapter' " +
      "id='clear-chapter-btn'>Show whole trail</button></p>";
  var btn = document.getElementById("clear-chapter-btn");
  if (btn) btn.addEventListener("click", clearChapter);
}

/* ------------------------------------------------------- layer toggles
   Working layers load lazily the first time their toggle is switched
   on (ITM pattern); stubs render disabled, marked "coming soon". */
function ensureLayer(def, addToMap) {
  if (def.stub || def.layer) {
    if (def.layer && addToMap) map.addLayer(def.layer);
    return Promise.resolve(def.layer || null);
  }
  var files = def.files || (def.file ? [def.file] : []);
  if (!files.length) {
    /* Tile / constructed layer: build synchronously. */
    try {
      def.layer = def.build(null);
    } catch (err) {
      bootErrors.push(def.label + ": " + err.message);
      setStatus("Could not load " + def.label + " — " + err.message, true);
      return Promise.resolve(null);
    }
    if (addToMap && def.layer) map.addLayer(def.layer);
    return Promise.resolve(def.layer);
  }
  return Promise.all(files.map(fetchJson)).then(function (parts) {
    def.layer = def.build(parts.length === 1 ? parts[0] : parts);
    if (addToMap && def.layer) map.addLayer(def.layer);
    return def.layer;
  }).catch(function (err) {
    bootErrors.push(def.label + ": " + err.message);
    setStatus("Could not load " + def.label + " — " + err.message, true);
    return null;
  });
}
function buildLayerToggles() {
  var wrap = document.getElementById("layer-toggles");
  var groups = [];
  LAYERS.forEach(function (def) {
    if (groups.indexOf(def.group) < 0) groups.push(def.group);
  });
  groups.forEach(function (group) {
    /* ITM pattern: the group heading is a small-caps disclosure
       row; clicking it (or Enter/Space on it) opens or closes the
       group. Groups start COLLAPSED (Nov 24, 2026 panel rebuild)
       — the panel shows only the grey group rows, as ITM does. */
    var h = document.createElement("div");
    h.className = "tog-group";
    h.setAttribute("role", "button");
    h.setAttribute("aria-expanded", "false");
    h.tabIndex = 0;
    h.textContent = "▸ " + group;
    var body = document.createElement("div");
    body.className = "tog-group-body collapsed";
    h.addEventListener("click", function () { toggleLayerGroup(h, body); });
    h.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleLayerGroup(h, body);
      }
    });
    wrap.appendChild(h);
    wrap.appendChild(body);
    LAYERS.forEach(function (def) {
      if (def.group !== group) return;
      if (def.search) return; /* gazetteer: wired to Find, not a toggle */
      var row = document.createElement("label");
      row.className = "tog-row" + (def.stub ? " tog-stub" : "");
      var box = document.createElement("input");
      box.type = "checkbox";
      box.checked = !!def.onByDefault;
      box.disabled = !!def.stub;
      def.box = box;
      var text = document.createElement("span");
      text.className = "tog-label";
      text.textContent = def.label;
      row.appendChild(box);
      row.appendChild(text);
      if (def.stub) {
        var tag = document.createElement("span");
        tag.className = "tog-coming";
        tag.textContent = "coming soon";
        row.appendChild(tag);
        row.title = def.title + " — " + (def.note || "");
      } else if (def.title) {
        row.title = def.title;
      }
      box.addEventListener("change", function () {
        if (box.checked) {
          ensureLayer(def, true).then(function () { writeShareHash(); });
        } else if (def.layer) {
          map.removeLayer(def.layer);
          /* The chapter select lives in the panel, not on the map —
             switching Chapters off also clears any selection. */
          if (def.id === "chapters") clearChapter();
          writeShareHash();
        }
      });
      body.appendChild(row);
    });
  });
}
function toggleLayerGroup(h, body) {
  var collapsed = body.classList.toggle("collapsed");
  h.textContent = (collapsed ? "▸ " : "▾ ") +
    h.textContent.replace(/^[▸▾] /, "");
  h.setAttribute("aria-expanded", collapsed ? "false" : "true");
}

/* Basemap group (Nov 24, 2026 panel rebuild): the BASEMAP row in
   the panel is a static .tog-group like the layer groups above,
   with the base buttons + Wayback selector inside its body. It
   starts collapsed, exactly like the layer groups. */
(function wireBasemapGroup() {
  var h = document.getElementById("basemap-group");
  var body = document.getElementById("basemap-body");
  if (!h || !body) return;
  h.addEventListener("click", function () { toggleLayerGroup(h, body); });
  h.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleLayerGroup(h, body);
    }
  });
})();

/* ------------------------------------------------------------ legend
   Legend rows are generated from the same style constants as the map
   (ITM rule: hand-copied legend strings drifted in v3), so the legend
   can never drift from the map. */
function legendHtml() {
  function line(color, dash) {
    return "<span class='leg-line' style='border-top-color:" + color +
      (dash ? ";border-top-style:dashed" : "") + "'></span>";
  }
  return "<div class='leg-row'>" + line(COLORS.natural) +
    " Natural tread — built off-road trail</div>" +
    "<div class='leg-row'>" + line(COLORS.urban) +
    " Urban sidewalk</div>" +
    "<div class='leg-row'>" + line(COLORS.road, true) +
    " Road</div>" +
    "<div class='leg-row'>" + line(COLORS.highlight) +
    " Selected chapter (highlight)</div>" +
    "<div class='leg-row'><span class='leg-line' style='" +
    "border-top-color:#7e6a9e'></span> Waymarked hiking routes " +
    "(when on)</div>" +
    "<p class='leg-note'>Base line: NCTA official centerline, pull of " +
    "November 21, 2026. Urban sidewalk and road miles are drawn as " +
    "they are classified in the source; the split is documented in " +
    "About.</p>";
}
function buildLegend() {
  var el = document.getElementById("legend");
  if (!el) return;
  var html = legendHtml();
  /* One row per wired overlay, from the registry's own swatches, so
     the legend can never drift from the map. */
  var skip = { "base-line": 1, "chapters": 1, "waymarked": 1 };
  var rows = "";
  LAYERS.forEach(function (def) {
    if (!def.swatch || def.stub || def.search || skip[def.id]) return;
    var sw = def.swatch;
    var mark = sw.kind === "dot" ?
      "<span class='leg-dot' style='background:" + sw.color + "'></span>" :
      sw.kind === "fill" ?
      "<span class='leg-fill' style='background:" + sw.color + "'></span>" :
      "<span class='leg-line' style='border-top-color:" + sw.color + "'></span>";
    rows += "<div class='leg-row'>" + mark + " " + esc(def.label) +
      " (when on)</div>";
  });
  if (rows) {
    html += "<p class='leg-note'>Overlays, switched on in the panel:</p>" + rows;
  }
  el.innerHTML = html;
}
(function wireLegend() {
  var btn = document.getElementById("btn-legend");
  var card = document.getElementById("legend-card");
  btn.addEventListener("click", function () {
    var hidden = card.hasAttribute("hidden");
    if (hidden) card.removeAttribute("hidden");
    else card.setAttribute("hidden", "");
    btn.setAttribute("aria-pressed", hidden ? "true" : "false");
  });
})();

/* Present (Nov 24, 2026 — ITM-look reshape): the ⛶ button in the
   masthead hides the panel so the map fills the screen; ‹ Show
   panel (or Esc) brings it back. No present strip or record card —
   the national viewer has no section record to present. */
(function wirePresent() {
  var btn = document.getElementById("present-btn");
  var show = document.getElementById("show-panel-btn");
  if (!btn || !show) return;
  function enter() {
    document.body.classList.add("presenting");
    show.hidden = false;
    map.invalidateSize();
  }
  function exit() {
    document.body.classList.remove("presenting");
    show.hidden = true;
    map.invalidateSize();
  }
  btn.addEventListener("click", enter);
  show.addEventListener("click", exit);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" &&
        document.body.classList.contains("presenting")) exit();
  });
})();

/* ---------------------------------------------------------- copy link
   Share hash (ITM pattern): #view=lat,lng,zoom & #base=code &
   #layers=… & #chapter=CODE. The hash is rewritten on every
   move so the address bar always holds the current view.
   COMPACT layers= (Paul, Nov 24, 2026): only layers whose state
   differs from their default are listed — "id" for a layer that
   is on but off by default, "-id" for one that is off but on by
   default. Unlisted layers keep their defaults, so the reader
   accepts both this compact form and the old long form (every
   layer listed), and old shared links keep working. The part is
   omitted entirely when nothing differs from the defaults. */
var shareHashReady = true;
function writeShareHash() {
  if (!shareHashReady || !history.replaceState) return;
  var c = map.getCenter();
  var parts = [
    "view=" + c.lat.toFixed(5) + "," + c.lng.toFixed(5) + "," +
      map.getZoom(),
    "base=" + (currentBase && currentBase.code ? currentBase.code : "topo"),
  ];
  var layerParts = [];
  LAYERS.forEach(function (def) {
    if (def.stub || !def.box) return;
    if (def.box.checked !== !!def.onByDefault) {
      layerParts.push(def.box.checked ? def.id : "-" + def.id);
    }
  });
  if (layerParts.length) parts.push("layers=" + layerParts.join(","));
  if (selectedChapter) parts.push("chapter=" + selectedChapter);
  history.replaceState(null, "", "#" + parts.join("&"));
}
map.on("moveend", writeShareHash);

/* Parcels restyle on zoom: parcelStyle reads the zoom at render time,
   so crossing zoom 11 needs an explicit re-style of the loaded layer. */
map.on("zoomend", function () {
  var def = layerById("parcels");
  if (def && def.layer) def.layer.setStyle(parcelStyle);
});

var requestedChapter = null;
(function applyHash() {
  var hash = location.hash || "";
  var bm = /base=([a-z0-9\-]+)/.exec(hash);
  if (bm) {
    var baseDef = baseByCode(bm[1]);
    if (baseDef && baseDef.wayback) {
      var y = bm[1].replace("wayback-", "");
      if (WAYBACK_IDS[y]) {
        map.removeLayer(currentBase.layer);
        map.addLayer(waybackLayers[y]);
        currentBase = { name: "Aerial " + y + " (Wayback)",
          code: bm[1], layer: waybackLayers[y] };
        var sel = document.getElementById("wayback-select");
        if (sel) sel.value = y;
      }
    } else if (baseDef && !baseDef.needsKey) {
      setBase(baseDef.name);
    }
  }
  var cm = /chapter=([A-Za-z\-]+)/.exec(hash);
  if (cm) requestedChapter = cm[1];
})();

(function wirePanelButtons() {
  /* Map-corner icon buttons (Nov 24, 2026 panel rebuild): the
     buttons are icon-only, so copy feedback swaps the icon for a
     check instead of replacing the label text. */
  var copyLinkBtn = document.getElementById("copy-link-btn");
  var copyIcon = copyLinkBtn.innerHTML;
  copyLinkBtn.addEventListener("click", function () {
    writeShareHash();
    var url = location.href;
    function done(ok) {
      if (ok) {
        copyLinkBtn.textContent = "✓";
        copyLinkBtn.classList.add("copied");
        copyLinkBtn.title = "Copied!";
      } else {
        copyLinkBtn.title = "Copy failed — copy the address bar";
      }
      window.setTimeout(function () {
        copyLinkBtn.innerHTML = copyIcon;
        copyLinkBtn.classList.remove("copied");
        copyLinkBtn.title = "Copy link to this view";
      }, 2000);
    }
    function fallbackCopy(text) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) {}
      document.body.removeChild(ta);
      done(ok);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        done(true);
      }, function () { fallbackCopy(url); });
    } else {
      fallbackCopy(url);
    }
  });
  var printBtn = document.getElementById("print-btn");
  if (printBtn) printBtn.addEventListener("click", function () {
    window.print();
  });
  var wholeBtn = document.getElementById("whole-trail-btn");
  wholeBtn.addEventListener("click", function () {
    if (selectedChapter) clearChapter();
    else if (wholeTrailBounds) map.fitBounds(wholeTrailBounds.pad(0.02));
  });
})();

/* -------------------------------------------------------------- boot
   Load order: base line first (it defines the whole-trail bounds and
   the feature pool the chapter highlight draws from), then chapters.
   The #layers= hash applies after the toggles exist. */
buildLayerToggles();
initGazetteer();
buildLegend();
showChapterRecord(null, 0);

var baseDef = layerById("base-line");
var chaptersDef = layerById("chapters");
var bootErrors = [];
ensureLayer(baseDef, true).then(function () {
  return ensureLayer(chaptersDef, false);
}).then(function () {
  /* #layers= hash: tokens switch layers on/off; a token prefixed
     with "-" switches that layer off. Unknown tokens are ignored.
     Layers the hash does not name keep their defaults, so the
     compact form (only layers that differ from default) and the
     old long form (every layer listed) both apply — old shared
     links keep working. */
  var m = /layers=([a-z,\-]+)/.exec(location.hash || "");
  if (m) {
    var wanted = [], unwanted = [];
    m[1].split(",").forEach(function (tok) {
      if (tok.charAt(0) === "-") unwanted.push(tok.slice(1));
      else if (tok) wanted.push(tok);
    });
    var jobs = [];
    LAYERS.forEach(function (def) {
      if (def.stub || !def.box) return;
      if (unwanted.indexOf(def.id) >= 0) {
        def.box.checked = false;
        if (def.layer) map.removeLayer(def.layer);
      } else if (wanted.indexOf(def.id) >= 0 && !def.box.checked) {
        def.box.checked = true;
        jobs.push(ensureLayer(def, true));
      }
    });
    return Promise.all(jobs);
  }
}).then(function () {
  /* Boot complete: success is silent (no status line in the
     panel — see setStatus); failures already reported via
     setStatus above. */
  writeShareHash();
}).catch(function (err) {
  setStatus("Could not load the base line — " + err.message, true);
});
