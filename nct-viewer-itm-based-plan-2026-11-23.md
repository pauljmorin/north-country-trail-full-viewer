# NCT trail viewer, ITM-based — scope and build plan

**Date:** 2026-11-23. **Status: plan only — nothing built.** This file exists so
Paul can approve the layer list before any building starts.

**Direction (Paul, Nov 23, 18:46):** the full viewer looks and behaves like
the ITM viewer — NOT like a "how complete" viewer. The completeness viewer
is superseded as the product: its data (centerline GeoJSON, chapter sums,
chapter extents, Mesabi overlap) feeds the new viewer, but the completeness
framing (headline mileage, "how complete is it?" title, case page) is
dropped. The chapters enrichment of the old `site/` was stopped for this
reason; the chapter-extents data carries into the new build as a chapter
layer/panel. This repo (`north-country-trail-full-viewer`) IS the new
viewer's repo — no second repo.

**Paul's brief (Nov 23, 18:41):** "can we now start getting the trail viewer
together that is based on the ITM chapter viewer? no inventory, no sections but
the other layers and features that are in that viewer?"

**Template read:** the Itasca Moraine chapter viewer, local repo
`~/workspace/itasca-trail-map/` (live at
https://pauljmorin.github.io/itasca-moraine-trail-map/site/), `site/app.js`
(10,257 lines), `site/index.html`, `SOURCES.md` (3,015 lines, every layer
documented with references + interpretation method), `DESIGN.md`, `scripts/`
(60+ pull/build scripts). The NCT completeness viewer (now this repo,
`~/workspace/north-country-trail-full-viewer/`, renamed Nov 23) was read, not
touched — the chapters builder that was enriching its old `site/` was stopped
Nov 23 when Paul set the ITM-viewer direction; its derived chapter data
carries into the new build.

**Headline numbers:** the ITM viewer carries **105 overlay layers** in its
registry (plus ~30 basemap services and the UI features in §4). Of those 105,
36 are individual Minnesota DNR paper-map layers and 10 are Forest
Service / Fish & Wildlife paper-map layers — nearly half the registry is
georeferenced paper maps, not data layers.

---

## 1. What "inventory" and "sections" mean in the ITM viewer

Paul's exclusion is two words, but each maps to more than one thing in the
viewer. The plan assumes the narrow reading below; §6 asks Paul to confirm.

### "Inventory" — three candidates

| # | Candidate | What it is in the viewer |
|---|---|---|
| A | **Inventoried trail** layer (`inventoried-trail`) | One layer, 1 feature, 10.91 mi — the GPS tracks actually walked while inventorying the trail (Nov 11 + Nov 18, 2026), teal, OFF by default. "Only the ground actually walked is drawn." A gap in it is a gap in the inventory, not a gap in the trail. |
| B | **"ITM inventory" panel group** (4 layers) | Camping (`chapterplaces`), AllTrails-listed trails, NCTA Places, ITM Assets. The group's own name in the panel. |
| C | **The asset-pin inventory system** | `data/assets.geojson` (84+ pins: signs, blazes, markers, etc.), the photo pipeline (`scripts/photo_pipeline.py`, `assign_serials.py`), the classification tool (`site/classify.html`), and the photo lightbox. Pins carry chainage/section, serials, type + condition from the photo. |

**Assumed reading: A is certainly out; C goes with it** (pins are the
inventory's product). B is ambiguous — Camping and NCTA Places are
NCTA-sourced, not inventory-sourced, and they sit in the group only by panel
placement. §3 puts Camping + NCTA Places in INCLUDED and ITM Assets +
AllTrails in EXCLUDED/UNDECIDED, and §6 asks Paul to confirm.

### "Sections" — two candidates

| # | Candidate | What it is in the viewer |
|---|---|---|
| A | **Adopted sections** layer (`stretches`) | 30 named sections (West-1…West-14, Chip-1…Chip-13, GAP-W) with adopter initials, chainage start/end, maintenance notes, NCTA sheet numbers. The chapter's adoption program made visible. |
| B | **The section-naming system** | Section names label map sections (by standard cartography rules, never on the trail line), gazetteer points carry a `section` property, and two derived layers hang off the stretches: Adoption segment ends (`boundaries`) and Adoption gap (`gaps`). "Chapter boundaries" (`termini`) is different — it marks chapter extent endpoints, not adopted sections. |

**Assumed reading: A is certainly out, and B's derived layers (segment ends,
adoption gap) go with it.** The gazetteer `section` property and the
section-name labels are a display convention, not a layer; they disappear
with the stretches because there is nothing to name. Chapter boundaries
(`termini`) stay — they are chapter extents, and the chapter-extents work
just built them trail-wide.

---

## 2. ITM inventory — every layer and feature

Scope column: **G** = general (national or trail-wide by nature),
**MN** = Minnesota-specific source, **CH** = chapter-specific (Itasca
Moraine chapter's own data/program). "How built" is the script or service;
static GeoJSON in `site/data/` means a pull/build script produced it.

### The trail (12 layers)

| Layer | What it does | Data source / how built | Scope |
|---|---|---|---|
| NCT — all Minnesota | The NCT across all of Minnesota | NCTA `nct_public` FeatureServer layer 2, clipped to MN (`scripts/pull_minnesota_line.py`) | G (the NCT-wide viewer already has the full line) |
| Inventoried trail | GPS tracks walked while inventorying, 10.91 mi | Chapter GPX files (Nov 11 + Nov 18, 2026), chopped for the car tail | CH — **excluded (inventory, §1A)** |
| Arrowhead reroute polygon | 2004 NPS preferred-alternative corridor, 1 feature | 2004 corridor polygon, filed 2026-11-18 | CH/segment — **excluded as a layer** (see §3 undecided: reroute corridors generally) |
| NCTA Trail | The official trail line, chapter clip | NCTA `nct_public`, chapter clip (`scripts/pull_official_line.py`) | G — included as the base line |
| Star of the North Chapter trail | STN chapter's line, MN-84 to Hwy 6, 26.67 mi | Chapter line (`scripts/build_stn_line.py`) | CH — **excluded** (its miles are in the main line) |
| Adopted sections | 30 named sections + adopter initials + maintenance notes | Chapter spreadsheet, joined by `scripts/join_adopters.py` | CH — **excluded (sections, §1A)** |
| Chapter loops | 3 chapter-managed loops off the NCT (Waboose etc.) | Chapter data (`data/loops/`) | CH — **excluded** (other chapters could add loops later) |
| Adoption segment ends | Ends of adopted sections | Derived from stretches | CH — **excluded with sections** |
| Chainage (miles from west end) | Mileage along the trail from the west end | Derived from the trail line (`data/chainage.geojson`) | G — included, computed trail-wide |
| Chapter boundaries | Chapter extent endpoints | Chapter extent data | G — included (chapter-extents file just built) |
| Adoption gap | Unadopted stretches (GAP-W, 2.92 mi) | Derived from stretches | CH — **excluded with sections** |
| NCTA mile markers | NCTA Minnesota half-mile points | NCTA service (`scripts/pull_mile_markers.py`) | G — included, pending a trail-wide pull check |

### Other trails (12 layers + 3 partner-trail layers)

| Layer | What it does | Data source / how built | Scope |
|---|---|---|---|
| ATV trails | OHV/ATV-UTV trails near the trail | MN DNR `trans_ohv_trails_mn` service | MN — undecided (see §3) |
| Dirt bike trails | Dirt-bike trails near the trail | MN DNR service | MN — undecided |
| Snowmobile trails | Snowmobile trails near the trail | MN DNR `trans_snowmobile_trails_mn` service | MN — undecided |
| Bike trails | Bike trails incl. Mesabi Trail | MN DNR state trails + OSM harvest (`scripts/pull_bike_trails.py`, `harvest_mesabi_osm.py`) | Mixed — included via OSM (see §3) |
| Proposed ATV trails | Proposed ATV routes near the trail (hunt) | Chapter hunt, 2026-11-18/20 (club reports, minutes, news sweep) | CH hunt — **excluded as a layer** (concept transferable per state — undecided) |
| Proposed ATV crossings | Where proposed ATV routes would cross the NCT | Derived from the proposals hunt | CH — **excluded with the proposals** |
| Superior Hiking Trail | The SHT where it meets/overlaps the NCT | SHT pull (`scripts/pull-sht.py`, `agol_sht_public` layer 1) | Regional partner — included as "concurrent/partner trails" (§3) |
| Border Route Trail | The BRT where it meets the NCT | BRT pull (`scripts/pull-brt.py`) | Regional partner — included as partner trails |
| Driftless Hiking Trail | Driftless trail (Iowa Co., WI) | Driftless pull (`scripts/pull-driftless.py`) | Regional partner — included as partner trails |
| Trails near the Border Route & SHT | Nearby trails in that corner | Intersecting-trails inventory (`scripts/pull-near-brt-sht.py`) | Regional — included as partner trails |
| BWCAW portages & connectors | Portages/connectors near the NCT | BWCA pull (`scripts/pull-bwca-portages.py`) | Regional — included as partner trails |
| AllTrails-listed trails | Trails listed on AllTrails near the NCT | AllTrails (group "ITM inventory") | G service — **excluded** (licensing/terms unclear; see §6) |
| Hiking routes (Waymarked Trails) | Waymarked hiking-route overlay | Waymarked Trails tiles (global) | G — included |

### Land ownership (8 layers)

| Layer | What it does | Data source / how built | Scope |
|---|---|---|---|
| Parcels | County parcels, click for owner/info (OFF by default, faint below zoom 11) | Six statewide parcel services — ND NDGISHUB, MN MnGeo, WI V12, VT VCGI, NY NYS ITS, OH ODNR (`scripts/pull_parcels_state.py` + `scripts/merge_parcels.py`); taxpayer fields excluded | **BUILT Nov 24, 2026 (Option A)** — 141,687 parcels, 3,031.45 trail miles (63.7%); MI/NY-opt-out/PA/Hubbard backfill open |
| Parcels — Driftless area | Parcels, Iowa Co., WI | County pull (`scripts/pull-driftless-parcels.py`) | CH/regional — **undecided with parcels** |
| Parcels — Arrowhead | Parcels, Arrowhead corridor | County pulls (`scripts/pull_parcels_arrowhead*.py`) | CH/regional — **undecided with parcels** |
| Parcels — Star of the North | Parcels, STN corridor | County pull (`scripts/pull_parcels_stn.py`) | CH/regional — **undecided with parcels** |
| Government-owned lands | Who the entity is to talk to / work with (Federal/State/Land trust/Private) | MN `plan_gov_own_open` service (`scripts/pull_gov_owned_lands.py`) | MN — **included via PAD-US instead (§3)** |
| Leech Lake Reservation | Reservation boundary polygon | BIA national service (`scripts/pull_leech_lake_reservation.py`) | G — included (all tribal lands via BIA) |
| White Earth Reservation | Reservation boundary polygon | BIA national service (`scripts/pull_white_earth_reservation.py`) | G — included (all tribal lands via BIA) |
| Conservation easements | Easement polygons | MN source (panel: "The land", subgroup Management) | MN — undecided (national NCED exists; small if it works) |

### The land (3 layers + Management 6 + Timber sales 2 + Wetlands + soils 1)

| Layer | What it does | Data source / how built | Scope |
|---|---|---|---|
| Cass forest stands (inventory) | Forest inventory stands, not a sale | Cass Co. FIM service | MN/CH — **excluded (inventory, §1C)** |
| Examined for future sale — watch list | DNR stand exams (1,077) + annual exams (89) | MN DNR stand-exam services | MN — undecided |
| Past timber sales | Past sales (county + DNR) | MN DNR + county sales data | MN — undecided |
| Wetlands (NWI) — trail routing | NWI polygons classified go/maybe/no-go for routing | USFWS NWI national service (`scripts/pull_nwi_corridor.py`) | G — included |
| Soils (SSURGO) — trail routing | SSURGO map units classified for routing | NRCS Soil Data Access (`scripts/pull_ssurgo_corridor.py`) — **currently BLOCKED (HTTP 502)** | G — included when the service recovers |
| Forest health + blowdown (2025) | DNR forest-health survey, 2025 | MN DNR `env_forest_health_survey_2025` service | MN — **excluded** (USFS ADS is a possible national equivalent — see §6) |
| Invasive species sightings | DNR terrestrial invasive observations | MN DNR `env_invasive_terrestrial_obs` service | MN — **excluded** (EDDMapS is a possible national equivalent — see §6) |
| Chippewa Forest Plan areas (2004) | 2004 forest-plan management areas | Chippewa NF 2004 plan | Forest-specific — **excluded** (every national forest has its own plan) |
| Tree height | Canopy-height (lidar CHM) | MN lidar (`scripts/build_lidar_trio.py`) | MN — **excluded** (USGS 3DEP lidar is national but heavy — see §6) |
| Height lines — every 5 m | Contours derived from CHM | MN lidar-derived | MN — **excluded with tree height** |

### Road walk (5 layers)

| Layer | What it does | Data source / how built | Scope |
|---|---|---|---|
| Road walk | Road-walk segments, click for popup (speeds etc.) | Chapter-built geometry from Trail Research Brief T07 + Arrowhead pieces (`scripts/build_roadwalk.py`) | CH-built — **included as derived-from-centerline (§3)** |
| Speed limits | Speed-limit badges on road walks, with Street View links | Street View / manual, wired by `scripts/wire_streetview_26.py` | Method G, data manual — undecided on scope |
| Accident-prone areas | Crash markers on road walks | MnDOT High-Injury Network + crash data (western road walk only) | MN — undecided (each state DOT has its own) |
| Shoulder widths — road stretches | Colored line stretches (thin/adequate/generous + grass class) | Measured from Street View, 1 point/mile (`scripts/build_shoulder_layer.py`) | Method G, data manual — undecided on scope |
| Shoulder widths — measured points | Dots at each measured mile with statistics + Street View frame link | Same measurement program | Method G, data manual — undecided with the stretches |

### Around the trail (8 layers)

| Layer | What it does | Data source / how built | Scope |
|---|---|---|---|
| Non-road access | Access points not on roads | Chapter-built (`data/access/`, `access-points.geojson`) | CH — **excluded** (access is chapter work) |
| Roads | Road centerlines | MN road centerlines, MnGeo (`data/roads.geojson`) | MN — **included via OSM/TIGER (§3)** |
| Trail alerts | NCTA closures, storm damage, reroutes (verbatim) | NCTA `trail_alerts` service (`scripts/pull_trail_alerts.py`, `pull_minnesota_alerts.py`) | G — included directly |
| NCT reroutes | Reroute lines from the alerts service | Same NCTA service, layer 2 | G — included directly |
| Camping | NCTA camping waypoints | NCTA points service (`scripts/build_chapter_places.py`, `seed_chapter_places.py`) | G — included |
| Camping — Arrowhead | NCTA camping waypoints, Arrowhead | Same NCTA points service | G — included (as the one camping layer) |
| Camping — Star of the North | NCTA camping waypoints, STN | Same NCTA points service | G — included (as the one camping layer) |
| DNR state forest campgrounds | MN DNR state-forest campground inventory | MN DNR `struc_state_forest_campgrounds` service | MN — undecided (state-by-state + USFS RIDB) |
| Bridges — crossing opportunities | Pedestrian/mixed-use bridges within 2 mi + highway bridges within 400 m | FHWA National Bridge Inventory 2025 (`scripts/pull_nbi_bridges.py`) | G — included directly |
| NCTA Places | NCTA points (parking, water, etc.) | NCTA points service (`scripts/pull_points.py`) | G — included |
| ITM Assets | Chapter asset pins (signs, blazes, markers) + photos | Chapter photo pipeline + `data/assets.geojson` | CH — **excluded (inventory, §1C)** |
| Street View | Street View links at trailheads, crossings, road-walk points | Google Street View, browser-verified points (`scripts/build_streetview_extension.py`) | Coverage G, points CH-placed — included as a feature, point generation undecided (§3) |
| Matt's NCTA map sheets | NCTA map-sheet footprints (MN sheets) | NCTA sheets (`data/ncta-sheets.geojson`) | G — included, needs the full sheet set |

### Paper-map layers (46 layers — georeferenced GeoPDFs, not data)

| Group | What it is | Scope |
|---|---|---|
| Minnesota DNR maps (35 layers) | One layer per DNR paper map (state forests, parks, trails — Waboose, Tettegouche, Split Rock, Jay Cooke, Gitchi-Gami, C.J. Ramstad, etc.) | MN — **excluded** (a trail-wide equivalent would be hundreds of state/park maps) |
| Forest Service maps (6 layers) | USFS paper maps for MN forests (Chippewa South, Ely, Virginia, Upper Trail, Grand Marais) | Forest-specific — **excluded** |
| Fish & Wildlife maps (4 layers) | Tamarac NWR maps (index + 3 sheets) | Refuge-specific — **excluded** |

### Basemaps (~30 services)

National/general — transfer: OpenStreetMap, OpenTopoMap, USGS Topo,
USGS Imagery, Esri Imagery, Esri NatGeo, CyclOSM, Mapbox Outdoors, MapTiler
Outdoor, Stadia Outdoors, Waymarked Trails, Esri Wayback (2014–2025),
white (blank) base. Minnesota-only — do not transfer: MN hillshade (WMS),
MN aerials by year (1991–2025, WMS), snow pistes / winter base. (The ITM
viewer streams tiles; it downloads no basemap data. The same applies
trail-wide.)

### UI features (not layers)

| Feature | What it does | Transfers? |
|---|---|---|
| Gazetteer search | Search 257 places: sections, crossings, parking, camping, water (built by `scripts/build_gazetteer.py` from NCTA points + chapter places) | Yes — rebuilt on NCTA points trail-wide (medium) |
| Inspector panel | Click a feature → merged record popup (content first, then design pass) | Yes — code reuse |
| Copy link | Shareable link with map state (hash) | Yes — code reuse (completeness viewer already has it) |
| Print dialog + GeoPDF export | Print one map (window or drawn box), paper sizes, DPI, simple-map mode; downloads a GeoPDF (`export.html`, `print-dialog.js`, `geopdf-writer.js`, `pdf-lib`) | Yes — code reuse |
| Present mode | Big-screen present strip/card/key | Yes — code reuse |
| Photo lightbox | Popup photos open full-size, step through, captions | Code yes; photos no (see §6) |
| Legend (corner card + print legend) | Legend panel + print legend | Yes — code reuse |
| Basemap switcher | Base choices in the panel | Yes — code reuse |
| Data sources page | Every layer: references + interpretation method (`SOURCES.md` → `data-sources.html`) | Yes — this is a standing rule, applies to the new viewer too |
| About / Volunteer protocol / Export & print pages | Chapter pages | About adapts; Volunteer protocol is chapter-specific (exclude — no trail-wide protocol exists); Export & print adapts |
| Asset classification tool (`classify.html`) | Classify pins from photos | No — tied to the asset inventory (excluded) |
| Adoption panel header | "73.2 of 76.2 mi adopted" + gap link | No — adoption is out (sections) |

---

## 3. Proposed NCT viewer layer list

Counts: **21 included data items + the UI feature set**, **24 excluded
items** (the 46 paper-map layers count as 3 groups), **13 undecided**.
Excluded items are out unless Paul reinstates one; undecided items are not
built until Paul answers the question beside them.

### INCLUDED (21) — ITM features minus inventory and sections

| # | Item | Notes |
|---|---|---|
| 1 | NCT base line (full centerline) | Already in the completeness viewer (3 classes: natural / road / urban). The new viewer draws the same line as its base. |
| 2 | Chainage | Miles from the western terminus, computed from the centerline. |
| 3 | Chapter boundaries | Chapter extent endpoints — from the chapter-extents file just built. |
| 4 | NCTA mile markers | Pending a trail-wide pull check (ITM's are Minnesota half-mile points from the NCTA service). |
| 5 | Bike trails (via OSM) | OpenStreetMap bicycle routes nationally; the Mesabi question is the completeness viewer's separate bike-path work, not this viewer's. |
| 6 | Concurrent / partner trails | SHT, BRT, Driftless, BWCA portages in ITM become a category: Buckeye Trail, Finger Lakes Trail, Long Trail, Superior Hiking Trail, and the rest, where they run with the NCT. |
| 7 | Waymarked hiking routes | Global overlay, transfers as-is. |
| 8 | Public land (PAD-US) | Replaces ITM's Minnesota-only government-owned-lands layer. PAD-US is national and already documented in the completeness viewer (`site/data/padus-note.md`, live export service). |
| 9 | Tribal lands (BIA) | All tribal lands along the trail via the BIA national service (ITM has Leech Lake + White Earth from the same service). |
| 10 | Wetlands (NWI) | USFWS national service, same script as ITM (`pull_nwi_corridor.py`), run trail-wide. |
| 11 | Soils (SSURGO) | NRCS national service — include when it recovers; currently BLOCKED (HTTP 502) in ITM too. |
| 12 | Road walk (derived) | ITM's is chapter-built geometry; trail-wide it is derived from the centerline's road class (1,411 mi) — no manual geometry. Popups carry the same content pattern. |
| 13 | Roads | OSM / TIGER road centerlines nationally, replacing ITM's Minnesota-only MnGeo roads. |
| 14 | Trail alerts | NCTA `trail_alerts` service, national, no bounding-box clip. |
| 15 | NCT reroutes | Same service, layer 2. |
| 16 | Camping (one layer) | NCTA camping waypoints nationally (ITM splits them into three layers by chapter; the NCT-wide viewer has one). |
| 17 | Bridges (NBI) | FHWA National Bridge Inventory 2025, national — same script as ITM. |
| 18 | NCTA Places | NCTA points service nationally (parking, water, etc.). |
| 19 | Street View | Feature transfers (Google coverage is national). Which points get links is undecided (§6). |
| 20 | NCTA map sheets | Full sheet set trail-wide (ITM carries the Minnesota sheets). |
| 21 | Gazetteer search | Rebuilt on NCTA points trail-wide (ITM's has 257 places; trail-wide will be thousands — search, not a list). |
| — | UI features | Inspector popups, copy link, print dialog + GeoPDF export, present mode, legend, basemap switcher (national basemaps only), data-sources page. All code reuse from ITM. |

### EXCLUDED (24) — inventory, sections, chapter-specific, MN-only

Inventory/sections (Paul's brief): Inventoried trail; Adopted sections;
Adoption segment ends; Adoption gap; Cass forest stands (inventory); ITM
Assets (+ photo pipeline + classification tool); Adoption panel header.
Chapter-specific: Star of the North chapter line; Chapter loops; Arrowhead
reroute polygon (as a layer — see undecided #10); Proposed ATV trails +
crossings; Non-road access. MN-only with no national equivalent carried:
Forest health + blowdown; Invasive species; Chippewa Forest Plan areas;
Tree height; Height lines/contours. Paper maps: all 35 Minnesota DNR maps,
all 6 Forest Service maps, all 4 Fish & Wildlife maps. Other: AllTrails
(licensing/terms unclear — see §6); Volunteer protocol page (no trail-wide
protocol exists); Minnesota basemaps (MN hillshade, MN aerials by year,
winter base).

### UNDECIDED (13) — need Paul's call before building

| # | Item | Question for Paul |
|---|---|---|
| 1 | Parcels trail-wide | **DECIDED Nov 23, 2026 (Paul: "Do the parcels") — Option A built Nov 24:** six statewide services, 141,687 parcels, 3,031.45 trail miles (63.7%). Backfill (MI 9 county services + PA 6 sources + Hubbard) still open. |
| 2 | Motorized trails (ATV / dirt bike / snowmobile) | MN DNR services don't extend. Build from USFS MVUM (national) + state OHV data, or leave motorized out? **Medium–large.** |
| 3 | Timber (examined-for-sale + past sales) | MN DNR + county model doesn't extend. Hunt state equivalents, or leave timber out? **Large.** |
| 4 | State campgrounds | ITM's DNR model is MN-only. Hunt per-state campground data + USFS RIDB, or is NCTA camping enough? **Medium.** |
| 5 | Speed limits — scope | Badges are manual (Street View). All 1,411 road miles, or a pilot corridor first? **Large if all.** |
| 6 | Crash data — scope | Each state DOT publishes its own. Hunt all eight states, or leave crashes out? **Medium–large.** |
| 7 | Shoulder measurement — scope | 1 point per mile, measured from Street View by hand. Trail-wide that is ~1,400 points. Pilot a corridor, automate, or leave it as an MN-only layer? **Large.** |
| 8 | Street View point generation | Auto-generate links at crossings + road miles, or place points by hand as ITM does? **Medium.** |
| 9 | Photos | Is there any trail-wide photo program, or do photos stay out entirely? (ITM's photos come from the chapter inbox + Drive.) **Large if yes.** |
| 10 | Reroute corridors generally | Arrowhead's 2004 corridor is one case. Are there other planned reroute corridors worth drawing, case by case? **Small–medium.** |
| 11 | Easements via NCED | The National Conservation Easement Database is national. Worth a check, or leave easements out? **Small (check first).** |
| 12 | Forest health / invasives, national equivalents | USFS Aerial Detection Survey / EDDMapS exist nationally. Worth wiring, or leave both out? **Small–medium.** |
| 13 | Tree height / contours via USGS 3DEP | National lidar exists but is heavy at trail scale. Worth it, or leave terrain layers out? **Large/heavy.** |

---

## 4. What the completeness viewer already has (reuse) vs new pulls

**Reuse as-is:** the centerline in three classes (natural / road / urban,
4,871.24 mi); `chapters.json` + the chapter-extents file (endpoints, miles,
source URLs); `states.geojson`; the mileage table; the PAD-US note and live
service; the data-sources documentation pattern (references + interpretation
method per layer — a standing rule); the copy-link share hash; vendored
Leaflet, no CDN; the GitHub Pages deploy pattern (`site/` as web root).

**Reuse with adaptation:** the ITM viewer's `app.js` panel/inspector/
print/present code (the completeness viewer's `app.js` is a different, much
smaller viewer — the new viewer forks ITM's code, not the completeness
viewer's).

**New data pulls needed (source in brackets):**
- NCTA trail alerts, national, no bbox clip [NCTA `trail_alerts` service —
  ITM scripts exist, drop the MN clip] — easy.
- NBI bridges 2025 [FHWA — ITM script `pull_nbi_bridges.py` exists] — easy.
- NWI wetlands, trail-wide corridor [USFWS — ITM script exists] — easy.
- BIA tribal lands, trail-wide [BIA national service — ITM script pattern
  exists] — easy.
- PAD-US [live export service — already documented] — easy.
- SSURGO soils [NRCS — retry when the service recovers; ITM script exists]
  — blocked, retry.
- NCTA points nationally: camping, Places, mile markers
  [`pull_points.py`, `pull_mile_markers.py`, `build_chapter_places.py` —
  run nationally; check mile-marker coverage trail-wide] — medium.
- NCTA map sheets, full set [NCTA sheets — ITM has the MN subset] — medium.
- Partner/concurrent trails [Buckeye, Finger Lakes, Long Trail, SHT, etc. —
  hunt per trail; some overlap the NCT line itself] — medium.
- OSM roads + bike routes, trail-wide corridor [Overpass / Geofabrik] —
  medium.
- Chainage + chapter boundaries + road-walk segments [derived from the
  centerline + chapter extents — no external pull] — small.
- Undecided-gated pulls (only on Paul's call): parcels hunt (per-state),
  motorized (USFS MVUM + state OHV), timber (state equivalents),
  campgrounds (per-state + RIDB), crash data (8 state DOTs), easements
  (NCED check), forest health / invasives (USFS ADS / EDDMapS).

**Does not exist yet trail-wide:** the shoulder/speed measurement data (a
measurement program, not a pull); any trail-wide photo set; any trail-wide
adopter/section data (excluded by the brief); a trail-wide gazetteer index
(built from NCTA points in the build).

---

## 5. Build order and size

Sizes are plain words, not hours. Each step depends on the one before it
only where stated.

1. **Shell + base line + chapters + basemaps + copy link + legend.**
   Fork ITM's `app.js`/`index.html`/`style.css`, swap in the NCT centerline
   and chapters, keep the national basemaps. **Small.**
2. **National live-service layers.** Alerts, NBI bridges, NWI wetlands, BIA
   tribal lands, PAD-US. Each is a pull script + a GeoJSON + a panel toggle.
   **Small each.**
3. **Derived layers.** Chainage, chapter boundaries, road-walk segments from
   the centerline road class. **Small–medium.**
4. **NCTA points.** Gazetteer/search, camping, Places, mile markers.
   **Medium** (the gazetteer is the biggest piece here — thousands of
   places, needs the same search-index treatment as ITM's 257).
5. **Partner trails + OSM roads/bike + map sheets.** **Medium.**
6. **Soils.** When the NRCS service recovers. **Small.**
7. **Undecided-gated pieces.** Only on Paul's answers in §6. Parcels,
   timber, shoulders/speeds measurement are the large ones; the rest are
   medium or smaller.

**What is NOT built in this plan:** the completeness viewer's tables/case
page (that viewer stays a separate product — "how complete is the trail",
not for hikers); the bike-path fourth class (separate pending work in the
completeness viewer); the Mesabi overlap (already measured, 107.94 mi).

---

## 6. Open questions for Paul

1. **"No inventory" — how wide?** Just the Inventoried trail layer, or
   also the "ITM inventory" panel group and the whole asset-pin system
   (pins, photo pipeline, classification tool)? The plan assumes the wide
   reading (all of §1 A + C out; Camping + NCTA Places kept because they
   are NCTA-sourced, not inventory-sourced).
2. **"No sections" — how wide?** Just the Adopted sections layer, or also
   the section naming in search and the segment-ends/gap layers? The plan
   assumes all of §1 A + B out except Chapter boundaries (chapter extents,
   not adopted sections).
3. **Who is the viewer for?** ITM is chapter-branded for its volunteers and
   the public; the completeness viewer is explicitly "not for hikers" (for
   chapter leaders and decision-makers). Is the NCT-wide viewer for hikers,
   chapter leaders, decision-makers, or all three? This decides how much
   trip-planning content (camping, water, parking) it needs.
4. **Adoption trail-wide?** Is there an NCT-wide adopter program to show,
   or is adoption chapter-internal everywhere? If the latter, the whole
   adoption concept stays out, as planned.
5. **Photos?** Any trail-wide photo program, or do photos stay out
   entirely? (This also decides whether the lightbox code is carried over.)
6. **Parcels trail-wide?** DECIDED Nov 23, 2026 — Option A built Nov 24 (six statewide services, 141,687 parcels, 63.7%). Backfill still open.
7. **Timber, state campgrounds, shoulders/speeds, crashes?** Approve as
   later phases, or cut? (Shoulders/speeds in particular are a measurement
   program, not a data pull — ~1,400 points by hand at trail scale.)
8. **AllTrails?** ITM lists AllTrails-listed trails. Carry it over, or
   leave it out on licensing/terms grounds?
9. **Repo?** Same repo as the completeness viewer, or its own repo? They
   are different products (completeness case vs trail map). Note: the
   completeness viewer repo is still local-only — Paul has not created the
   GitHub repo for it yet either.
10. **Branding?** ITM is branded as the chapter only, never national NCTA
    or NPS. An NCT-wide viewer cannot be chapter-branded — does Paul want
    NCTA branding, and is that cleared with NCTA?
11. **Forest health / invasives / tree height, national equivalents?**
    USFS ADS, EDDMapS, and USGS 3DEP exist nationally. Worth wiring, or
    leave all three out?
12. **Paper maps?** The plan excludes all 46. Any paper-map set worth
    carrying over (e.g. USFS forest maps along the trail), or none?

---

*End of plan. No building starts until Paul approves the layer list (§3) and
answers the questions in §6 — or as many of them as he wants to answer now,
with the rest deferred to the phases that need them.*
