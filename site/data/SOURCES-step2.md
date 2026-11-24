# Data sources — build step 2 (national live-service layers)

Build step 2 of the NCT trail viewer (ITM-based plan,
`nct-viewer-itm-based-plan-2026-11-23.md` §2–§4). Every layer in this
step is national / trail-wide: no Minnesota clip, no chapter extent.
Each section below carries BOTH the references (service URL, pull
date, query) AND the interpretation method (the exact rules used to
turn raw data into the published classification), so a later reader
can reproduce every classification from the references plus the
stated rules, with nothing resting on undocumented judgment. This
is the standing rule (ITM `SOURCES.md`); it applies to this viewer
too.

Pull scripts live in `scripts/` (adapted from the Itasca Moraine
chapter viewer's `scripts/`, read-only source at
`~/workspace/itasca-trail-map/scripts/` — that repo was read, never
edited). Raw downloads and run logs live in `working/`.

Common corridor: the NCT centerline in this repo —
`site/data/centerline-natural.geojson` (3,202 features) +
`site/data/centerline-road.geojson` (939) +
`site/data/centerline-urban.geojson` (300) — 4,871.24 mi,
lon −101.45..−72.84, lat 38.69..48.10. The 2-mile corridor used by
the bridges, tribal-lands, and wetlands layers is a 3,218.69 m
buffer around that line.

## Trail alerts — NCTA (national)

- **What:** NCTA's own current-awareness notices — closures, storm
  damage, reroutes, new routes — quoted verbatim, credited to NCTA.
  **83 alert points**, dates 2020-12-31 to 2026-11-15 (the service
  keeps old alerts; nothing here is filtered by date).
- **URL:** https://services2.arcgis.com/UfGVyqUm4GHa2zrj/arcgis/rest/services/trail_alerts/FeatureServer
  — layer 1 "trail_alerts" (alert points). Same NCTA ArcGIS
  organisation as the official line.
- **Owner / publisher:** North Country Trail Association, on behalf
  of the National Park Service.
- **Pulled:** 2026-11-23 (CST; file metadata records pulled_utc_date
  2026-11-24) by `scripts/pull_trail_alerts_national.py`. Adapted
  from ITM `scripts/pull_trail_alerts.py` + `pull_minnesota_alerts.py`
  by dropping the chapter-extent / Minnesota-bbox clip: the query is
  one envelope over the national trail extent (lon −102.0..−72.3,
  lat 38.2..48.6, widened slightly past the centerline extent so no
  alert on the trail itself is clipped by the query). Method is
  otherwise ITM's: envelope selection, features fetched BY OBJECT ID
  in chunk-verified chunks of 500 (offset paging on these hosts has
  silently truncated before). Service counts cross-checked at pull
  time: layer 1 `returnCountOnly` = 83, fetched 83.
- **Date handling — READ BEFORE "FIXING":** the service stores each
  alert's Date as UTC midnight of the day AFTER the intended calendar
  date (a date-only field authored in a US timezone). The intended
  date is the America/Chicago calendar date of the stored instant:
  1753574400000 is stored as 2025-07-27T00:00Z and means 2025-07-26.
  The file therefore carries BOTH the raw epoch milliseconds
  (`date_ms`, verbatim) and the derived ISO calendar date (`date`,
  the America/Chicago date of `date_ms`). The map displays `date`;
  never re-derive it as the UTC date. America/Chicago is kept as the
  convention from the ITM pull so dates match the chapter viewer's;
  the service's own dates are day-granular, so the zone choice moves
  a date only when the stored instant sits at midnight UTC.
- **Positions:** solely from the returned GeoJSON GEOMETRY requested
  with outSR=4326 — the standing rule for this organisation's
  services (a sibling service's lat/long ATTRIBUTE columns are
  corrupt; this service carries none, and none would be read).
- **Text:** title / location / description are carried VERBATIM from
  the service — alerts are quoted, never rewritten or summarised.
  Fields: `title` (service `label`), `location` (service `Location`),
  `date`, `date_ms`, `description` (service `desc_`).
- **Use here:** `site/data/trail-alerts.geojson` (83 features,
  lon −101.38..−73.43, lat 39.01..48.09). Two alerts share a point
  and a date (East Fork State Park, 2026-08-20; Garrison Dam,
  2026-09-10) — they are distinct service records, kept as returned,
  not deduplicated.

## NCT reroutes — NCTA (national)

- **What:** Reroute lines from the same NCTA alerts service —
  **15 lines**, the second layer of the service. Same notices as the
  alert points, in line form.
- **URL:** https://services2.arcgis.com/UfGVyqUm4GHa2zrj/arcgis/rest/services/trail_alerts/FeatureServer
  — layer 2 "trail_alerts_new_rte" (reroute lines).
- **Owner / publisher:** North Country Trail Association, on behalf
  of the National Park Service.
- **Pulled:** 2026-11-23 (CST; file metadata records pulled_utc_date
  2026-11-24) by `scripts/pull_trail_alerts_national.py`, same
  national envelope and object-id method as the alert points.
  Service counts cross-checked at pull time: layer 2
  `returnCountOnly` = 15, fetched 15.
- **Fields (verbatim from the service):** `name` (service
  `seg_name`), `trail_stat`, `length_mi` (`len_miles`), `property`
  (`prop_name`), `managing_authority` (`mng_auth`), `special_regs`.
  Nulls are the service's own nulls (e.g. one line carries
  `trail_stat` "NCT (on-road)" with no name) — never filled in.
- **No-reroute rule:** the file is always written, even when the
  service returns no lines — in that case as an empty
  FeatureCollection with the published schema and a metadata note
  saying so. No reroute is ever invented. (On this pull the service
  did return lines, so the file carries 15 features.)
- **Use here:** `site/data/nct-reroutes.geojson` (15 features,
  lon −101.39..−85.38, lat 42.43..48.09). This is the service's
  reroute layer, NOT the 2004 Arrowhead reroute corridor polygon
  (an excluded plan item, §3) and NOT a planned-route layer.

## Bridges — crossing opportunities (FHWA National Bridge Inventory 2025, national)

- **What:** Existing highway bridges that might carry the trail —
  crossing opportunities. **1,415 structures**, in two tiers:
  Tier 1 **372** (355 Highway-pedestrian + 17 Pedestrian-bicycle),
  Tier 2 **1,043** (Highway within 400 m). By state: Ohio 588,
  New York 250, Michigan 186, Minnesota 185, Pennsylvania 87,
  North Dakota 85, Wisconsin 24, Vermont 10, New Hampshire 0,
  Maine 0. Status: 1,281 open, 119 posted for load, 11 posted for
  other load-capacity restriction, 2 not applicable, 1 open with
  temporary shoring, 1 open temporary structure; 0 closed.
- **Source:** FHWA National Bridge Inventory (NBI) 2025,
  all-records delimited file (`2025AllRecordsDelimitedAllStates.txt`,
  from `2025allstatesallrecsdel.zip`, 58 MB):
  https://www.fhwa.dot.gov/bridge/nbi/2025allstatesallrecsdel.zip.
  Pulled by `scripts/pull_nbi_bridges_national.py` (2026-11-23;
  file metadata records pulled_utc_date 2026-11-24). Code values
  decoded per the FHWA Recording and Coding Guide FHWA-PD-96-001
  (Items 21/22 owner and maintenance, 41 open/posted/closed, 42
  type of service, 43 structure kind). Raw download cached at
  `working/bridges/2025allstatesallrecsdel.zip`; per-state extracts
  at `working/bridges/state_<FIPS>_all.txt`.
- **Source substitution — read this before re-pulling:** the
  intended source was the MnDOT bridge inventory `trans-bridges`
  (Minnesota Geospatial Commons; audited in the ITM repo,
  `docs/uofm-arrowhead-data-sources-audit-2026-11-18.md`, verdict:
  Use). It could NOT be pulled on 2026-11-18: the MnGeo enterprise
  host FeatureServer returns 499 Token Required; the GDRS download
  paths all return 404; MnDOT's own `mndotgis.dot.state.mn.us` is
  unreachable from this VM; no ArcGIS Online copy was found; the
  DNR Bridges Cartegraph service also 404s — apparently
  retired/moved. NBI is the federal inventory fed by the states
  from their own inspection systems, so the structures and bridge
  numbers are the same inventory — but it is NOT the MnDOT service.
  FOLLOW-UP: re-pull from `trans-bridges` when MnDOT access is
  sorted (live browser or token); the bridge number is the join key.
  The all-records file is used, not the per-state highway-only files,
  because pedestrian-only bridges (service on = 3) are non-highway
  records and are absent from the highway files.
- **States:** the ten states the NCT crosses — ND (38), MN (27),
  WI (55), MI (26), OH (39), PA (42), NY (36), VT (50), NH (33),
  ME (23). Only those states' records are extracted from the
  all-records file (149,615 records → 122,106 distinct structures).
  New Hampshire and Maine contribute zero kept structures: the
  centerline in this repo has no trail miles in either state
  (`site/data/states.geojson` carries 8 states; NH and ME are not
  among them) — the NCT's eastern terminus is in Vermont.
- **Dedupe:** the all-records file carries multiple records per
  structure (one per inventory route on/under it). Keyed by (state,
  STRUCTURE_NUMBER_008) — the state is part of the key because
  structure numbers repeat across states. One record per structure
  is kept — record type 1 (route on the structure) where one exists,
  else the first record — and the filter runs on that record.
  `nbi_records` carries the merged record count.
- **Coordinates:** NBI LAT_016 / LONG_017 are DDMMSS.ss
  (e.g. 45011920 = 45 deg 01' 19.20" N; 095472832 = 95 deg 47'
  28.32" W). Converted to decimal degrees here. The field is
  fixed-width with exactly two decimal digits on the seconds
  (an earlier ITM draft parsed the seconds as a plain float and
  shifted every point up to ~0.8 deg; this is the fix). 118
  structures were dropped for unparseable or out-of-range
  coordinates.
- **Method / judgments:** Corridor is the 2-mile buffer around the
  centerline in this repo (see "Common corridor" above). The
  national line spans UTM zones 14–19, so no single UTM zone is
  used: a kilometre equirectangular STRtree pre-filter (44° N,
  generous radii — 2.2 mi for Tier 1, 450 m for Tier 2) selects
  candidates, and the published `dist_trail_km` is then measured
  exactly in a local tangent plane centred on each bridge
  (equirectangular at the bridge's own latitude, accurate to
  <0.1% locally). Tier 1: service on in {3 Pedestrian-bicycle,
  5 Highway-pedestrian}, within 2 mi. [JUDGMENT] Tier 2: service
  on = 1 Highway, within 0.25 mi (400 m) of the trail — a vehicular
  bridge the trail route actually passes is one a hiker could use
  as a crossing without a detour; a 2-mi vehicular net would be
  every county-road bridge in the corridor and unreadable as a
  crossing-opportunities layer. Excluded in both tiers: K = bridge
  closed to all traffic, G = new structure not yet open. Blank
  open/closed codes are KEPT: the field does not apply to
  non-highway records, so a blank is not a closed bridge. Not
  carried: service on 2 Railroad (rail bridges are not crossings a
  hiker can use), 4 Highway-railroad, 6/7/8 interchange levels,
  9 Building/plaza, 0 Other. 848 structures dropped on status,
  2,842 on service, 116,883 on distance.
- **County names:** decoded from the U.S. Census TIGERweb
  State_County service
  (https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query,
  fields NAME + COUNTY + STATE, one query per state with a
  `returnCountOnly` cross-check), not from a hand-kept table — the
  ten-state county list is too large to maintain by hand. Counts
  fetched: ME 16, MI 83, MN 87, NH 10, NY 62, ND 53, OH 88, PA 67,
  VT 14, WI 72. (The "Saint Louis" FIPS quirk — FIPS sorts
  "St. Louis" as "Saint Louis", so St. Louis MN is 137, before
  Scott 139 — is handled by the lookup itself.)
- **Fields carried:** `bridge_number`, `facility_carried`,
  `features_crossed`, `location` (all as published; NBI text
  fields arrive single-quoted and the quotes are stripped),
  `state` / `state_code`, `county` / `county_code`,
  `district` (raw state DOT district code, not decoded),
  `owner` / `maintenance` (decoded agency type) + `owner_code` /
  `maintenance_code`, `year_built`, `year_reconstructed`,
  `structure_len_m`, `deck_width_m`, `sidewalk_left_m` /
  `sidewalk_right_m` (Item 50 curb/sidewalk widths — the
  pedestrian accommodation on the structure; 329 of the 372 Tier 1
  bridges carry a nonzero sidewalk), `service_on` /
  `service_under`, `open_closed`, `structure_kind`,
  `structure_type`, `tier`, `dist_trail_km`, `nbi_records`.
- **Minnesota cross-check (against ITM's pull, same source, same
  rules, different line):** all 80 of ITM's Minnesota bridges are
  present in this file (0 missing), including the two pure
  pedestrian bridges — 5342 (PEDESTRIAN over US 169, Itasca Co.,
  Tier 1, 0.01 km — identical to ITM) and 03514 (PEDESTRIAN over
  CSAH 10, Becker Co., Tier 1, 3.0 km — identical to ITM) — and
  the Ely bottleneck twins 97320/97321 (MN 169 over the Shagawa
  River, Tier 2, 0.03 / 0.0 km; ITM read 0.0–0.02 km against its
  own line vintage). This pull keeps 185 Minnesota bridges vs
  ITM's 80; the +105 are almost all in Duluth (St. Louis Co.:
  I-35, Chester Creek, Garfield Ave — e.g. 69885 PEDESTRIAN over
  I-35 at 0.0 km), because this repo's centerline draws the Duluth
  urban routing that ITM's 566-mi Minnesota line omitted (this
  repo's Minnesota line is 875 mi per `site/data/states.geojson`).
  The difference is a centerline difference, not a pull error.
- **Use here:** `site/data/nbi-bridges.geojson` (1,415 features,
  lon −101.39..−73.07, lat 38.69..48.09). Tier 1 max distance
  3.21 km (≤ 3.21869 km corridor); Tier 2 max 0.40 km — both
  verified against the thresholds. Tier 1 popups say the bridge is
  a crossing a hiker can use; Tier 2 popups say to check on the
  ground whether the trail uses it.

## Tribal lands — BIA AIAN Land Area Representation (national)

- **What:** Every reservation whose boundary comes within 2 miles of
  the NCT — **11 reservations** (full unclipped geometry):
  Bad River (LAR0015, 0.08 trail mi inside), Grand Portage
  (LAR0022, 0.0 mi inside, 2.31 km from the trail), Huron
  Potawatomi (LAR0026, 0.0 mi, 0.60 km), L'Anse (LAR0029, 0.0 mi,
  3.18 km), Leech Lake (LAR0033, 12.01 mi inside), Little River
  (LAR0034, 0.45 mi), Little Traverse Bay (LAR0035, 0.0 mi,
  0.23 km), Sault Ste. Marie (LAR0046, 0.0 mi, 1.03 km), White
  Earth (LAR0051, 18.95 mi inside), Allegany (LAR0297, 6.76 mi
  inside), Oneida (New York) (LAR0319, 33.49 mi inside).
- **URL:** https://biamaps.geoplatform.gov/server/rest/services/DivLTR/BIA_AIAN_National_LAR/FeatureServer
  (layer 0, "BIA AIAN National LAR").
- **Owner / publisher:** Bureau of Indian Affairs, American Indian
  and Alaska Native Land Area Representation (AIAN-LAR). Public
  federal data; no licence restriction.
- **Pulled:** 2026-11-23 (CST; file metadata records pulled_utc_date
  2026-11-24) by `scripts/pull_tribal_lands_national.py`. Adapted
  from ITM `scripts/pull_leech_lake_reservation.py` (LAR0033) and
  `pull_white_earth_reservation.py` (LAR0051), which each fetch one
  reservation by LARID; this script fetches the whole layer (335
  features, `returnIdsOnly` + chunk-verified fetch by OBJECTID in
  chunks of 100) and keeps every feature within 2 mi of the
  centerline. Distance is tested in a kilometre equirectangular
  projection (111.320·cos(44°) km/deg lon, 111.195 km/deg lat)
  against per-piece 2-mi buffers indexed in an STRtree.
- **Selection rule:** a reservation is IN when its polygon
  intersects the 2-mile corridor around the centerline. Full
  unclipped reservation geometry is published, exactly as the ITM
  scripts publish full unclipped boundaries. The closest call is
  L'Anse at 3.18 km against a 3.21869 km threshold — the projection
  overstates lon distances at 46.7° N, so the true distance is
  slightly less; it is inside on either measure.
- **Per-reservation trail miles inside** are measured by
  intersecting the centerline with the reservation polygon and
  summing geodesic lengths (pyproj Geod, WGS84) of the inside
  pieces. Cross-checks against ITM's Minnesota measurements:
  White Earth 18.95 mi (ITM: 19 mi — agrees); Leech Lake 12.01 mi
  vs ITM's 2 mi — NOT a disagreement: ITM measured only its
  chapter's depicted chain (Chip-12's 2 mi); the full line has
  12.01 mi inside, in 3 contiguous segments around lon
  −94.28..−94.11, lat 47.00..47.05 (east of Walker, outside the
  chapter extent). Oneida (New York) 33.49 mi in 25 segments around
  lon −75.82..−75.55, lat 42.93..43.22 — the NCT/Finger Lakes Trail
  weaving through the Oneida boundary south of Syracuse; the BIA
  polygon there is the large historic boundary (lon −75.99..−75.43).
- **What is NOT used, per the ITM rule:** BIA's own GISACRES
  attribute contradicts its own geometry (Leech Lake: 1,794,106 vs
  823,249 ac geometry-measured; White Earth: 1,621,000.16 vs
  748,098 ac — both ~2.17x), so `area_acres` here is
  geometry-measured (geodesic, WGS84) and GISACRES is carried only
  as `gisacres_attribute` for the record. The Census
  off-reservation trust-land features are NOT included: this layer
  is reservations themselves, as in ITM. Neither source came from
  the tribe itself: both are federal publications.
- **Use here:** `site/data/tribal-lands.geojson` (11 features,
  lon −96.07..−75.43, lat 42.00..48.02). The popup and the Sources
  card carry the line: *the federal reservation boundary as
  published — not a legal survey.* Tribal management/forestry data
  is NOT in scope here — that stays relationship-only, per the
  ITM project's standing line.

## Public land (PAD-US) — live ArcGIS service, no local file

- **What:** USGS Protected Areas Database of the United States
  (PAD-US) 4.1 — public-land ownership and management, replacing
  ITM's Minnesota-only government-owned-lands layer nationally.
- **Services (verified live 2026-11-22, re-checked 2026-11-23;
  public, no key required). Source: USGS Gap Analysis Project,
  PAD-US 4.1 (March 2025), DOI `10.5066/P96WBCHS`:**
  - **Combined inventory — recommended for the viewer** (fee +
    designations + easements + marine + proclamation boundaries):
    `https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_gaz_combined/MapServer`,
    layer 0 `PADUS4_1Combined`. Fields include `FeatClass`,
    `Category`, `Own_Type`, `Own_Name`, `Mang_Type`, `Mang_Name`,
    `Unit_Nm`, `State_Nm`, `GIS_Acres`, `Pub_Access`, `GAP_Sts`.
    Spatial reference WKID 102039 (Albers); the `export` endpoint
    reprojects to the map CRS.
  - **Fee only** (fee-simple footprint, no designations/easements):
    `https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_4_1/MapServer`,
    layer 0 `PADUS4_1Fee`. Spatial reference WKID 102100 (Web
    Mercator).
  - **ArcGIS Online feature services, PAD-US 4.1** (same data,
    hosted feature layers — clickable, with popups):
    Manager Name (combined):
    `https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Manager_Name_PADUS/FeatureServer`,
    layer 0 `PADUS4_1ManagerName`; Public access / LLLT:
    `https://services.arcgis.com/UnTXoPXBYERF0OH6/ArcGIS/rest/services/PADUS_Public_LLLT/FeatureServer`.
  - **Not recommended as primary:** the cached tile service
    `PADUS3_0PublicAccess` is PAD-US **3.0** (2022 vintage) and
    tiles-only (no attributes).
- **Why no local file (the pull that was NOT done):** the PAD-US
  4.1 service was verified live and it does serve queries, but a
  corridor pull is too heavy for this pass: `PAD_US_gaz_combined`
  (layer 0) returned **192 features** for one small 0.4° × 0.3°
  envelope near Duluth, MN, and **1,016 features** for a same-size
  envelope near Columbus, OH (count-only queries,
  `returnCountOnly=true`, 2026-11-22). The trail corridor ribbon
  (~2 mi buffer around 4,871 mi of trail, ~19,500 sq mi) would
  therefore yield **thousands of features**, including very large
  complex polygons (national-forest proclamation boundaries with
  tens of thousands of vertices), paginated at `maxRecordCount:
  2000` per page, each then needing a local clip to the ribbon and
  simplification. The whole-line corridor buffer itself could not
  be built in this VM in one shapely pass (the `unary_union` +
  2 mi buffer of 4,373 lines was OOM-killed); a later local pull
  should build the buffer in chunks (e.g. per-state with `ogr2ogr`)
  rather than as one union. Full detail in `site/data/padus-note.md`.
- **Wiring (Leaflet + Esri Leaflet) — recorded in
  `site/data/padus-layer.json`, which is the file the shell reads:**
  raster overview
  `L.esri.dynamicMapLayer({ url:
  'https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_gaz_combined/MapServer',
  layers: [0], opacity: 0.45 })`; clickable vector
  `L.esri.featureLayer({ url:
  'https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Manager_Name_PADUS/FeatureServer/0',
  fields: ['Own_Name', 'Mang_Name', 'Unit_Nm', 'GAP_Sts',
  'Pub_Access', 'GIS_Acres'] })`. Default: the combined raster;
  fee-only as the alternative where overlap matters; the Manager_Name
  feature layer for click/identify popups (heavier — enable at higher
  zooms or on demand). OFF by default (coverage layer, not a trail
  layer).
- **Caveats (from USGS / the source inventory):** PAD-US does **not**
  tag which easements serve the NCT; any trail-easement reading needs
  an intersection with the trail corridor, and many trail easements
  (NCTA, local land trusts, handshake agreements being converted)
  may not be in it at all. The Easement class is NCED-derived
  (non-sensitive easements only); `Date_Est` is "not fully
  attributed". USGS strongly discourages comparing two PAD-US
  versions to look for changes in protection status. Combined-layer
  records overlap by design (fee + designation + easement on the same
  ground); the Fee layer is the non-overlapping footprint. Local park
  data gaps exist below the state level.
- **If a local pull is done later:** query `PAD_US_gaz_combined/0`
  with `geometry` = the 2 mi corridor buffer as Esri JSON (rebuild
  the buffer per-state; do not attempt one whole-line shapely union
  on this VM), `geometryType=esriGeometryPolygon`,
  `spatialRel=esriSpatialRelIntersects`, `outSR=4326`, paginated with
  `resultOffset` (`maxRecordCount` 2000). Run a `returnCountOnly`
  query first to size it. Clip each returned polygon to the buffer
  locally, simplify, and keep only `FeatClass, Category, Own_Type,
  Own_Name, Mang_Type, Mang_Name, Unit_Nm, State_Nm, GIS_Acres,
  Pub_Access, GAP_Sts`.
- **Use here:** `site/data/padus-layer.json` (service URLs, layers
  to show, wiring notes). There is deliberately NO
  `site/data/padus*.geojson` in this step.

## Wetlands (NWI) — classified for trail routing

- **What:** the USFWS National Wetlands Inventory along the full
  North Country Trail, classified GO / MAYBE / NO-GO for trail
  routing. **352,865 polygons, 1,453,362.8 ac**, in the 2-mile
  corridor around the full centerline (4,871 mi); a wetland counts
  when its polygon intersects the buffer. By rating: **MAYBE
  309,439 / NO-GO 43,426**. There are NO GO features in the file:
  GO is absence of a polygon (rule W1 below). By rule: W6 99,842,
  W6-analog 58,586, W7 56,734, W8 51,797, W9 21,722, W3 19,750, W5
  17,534, W4 15,453, W9-analog 11,440, UNCLASSIFIED 7. By state:
  MN 107,313; WI 61,320; ND 48,711; MI 45,127; OH 41,919; NY 37,168;
  VT 5,715; PA 5,328; state null 264 (centroids outside the
  `states.geojson` polygons — border waters). File:
  `site/data/nwi-wetlands.geojson`, **181,713,702 bytes** — large
  for a viewer file; the layer is OFF by default and LAZY, and the
  shell should not load it eagerly. **Split for deployment (Nov 24,
  2026):** GitHub rejects files over 100 MB, so the single file is
  kept locally (gitignored) and deployed as four chunks by
  `scripts/split_oversized_layers.py` — `nwi-wetlands-mn.geojson`
  (107,313 features, 51.6 MB), `nwi-wetlands-nd-mi.geojson` (93,838,
  43.8 MB), `nwi-wetlands-oh-ny.geojson` (79,087, 36.2 MB),
  `nwi-wetlands-wi-vt-pa.geojson` (72,627, 33.2 MB; includes the 264
  state-null border waters). Chunk counts sum to 352,865, verified
  by the script. `site/app.js` fetches all four and merges them
  (`mergeParts`) so the layer renders identically.
- **Source:** USFWS National Wetlands Inventory, national service
  as republished on ArcGIS Online:
  `https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/USA_Wetlands/FeatureServer/0`
  (layer 0 "USA_Wetlands", maxRecordCount 1000). Per-polygon vintage
  is NOT exposed by the service — recorded as a limit. (Minnesota's
  content in the national file is the DNR June 2019 update delivered
  to FWS; other states' vintages vary and are not stated by the
  service.) Pulled 2026-11-23
  (CST; file metadata records pulled_utc_date 2026-11-24) by
  `scripts/pull_nwi_corridor_national.py` (fetch log
  `working/nwi/pull-run-2026-11-23.log`; raw fetch
  `working/nwi/raw-nwi.geojson`, 377,906 unique features, 205 MB;
  processing log `working/nwi/process-run-2026-11-23.log`).
- **Service substitutions (verified live):** the brief's URL
  `https://www.fws.gov/wetlands/arcgis/rest/services/Wetlands/MapServer`
  returns **404** — the service moved to ArcGIS Online (the URL
  above). The DNR's own updated-NWI service returns **499 Token
  Required** — not publicly queryable. The research report's R4b
  citation (Wetlands_RLIS FeatureServer) is WRONG — it is Portland
  Metro RLIS (Oregon State Plane North, wkid 2913); it returns 0
  features on the trail. Do not use it.
  `inSR=4326` is REQUIRED on the USA_Wetlands service — envelope
  queries without it fail with 400.
- **Pull method:** the corridor (centerline envelope lon
  −101.45..−72.84, lat 38.69..48.10) is cut into 0.25° cells (4,485
  cells in the envelope, **328 intersecting the corridor**); each
  cell is queried by geometry POST (the cell's intersection with the
  corridor buffer, simplified 0.002°, widened 0.5 km — a superset;
  the exact clip happens in Python), rings in ArcGIS JSON format
  (exterior clockwise, holes counter-clockwise), `resultOffset`
  pagination 1,000/page ordered by OBJECTID, with a
  `returnCountOnly` cross-check per cell. Dedupe by OBJECTID across
  cells: **377,906 unique features**. Clip to the exact corridor in
  Python: 335,738 polygons kept; 42,111 fell outside the corridor
  (the query geometry was a widened superset), 57 invalid geometries
  skipped, 0 topology failures (see build notes below); 12,868
  source codes failed `parse_code()` and were classified from the
  service's parsed fields instead (the classify fallback — they are
  counted, not dropped). Dissolve: touching polygons with the same
  (rating, Cowardin code) merged into connected components,
  exploded — 352,865 output features (more than the 335,738 clipped
  inputs, because a union can split into several components, as in
  ITM's Minnesota pull: 89,366 → 91,479). Simplification:
  server-side maxAllowableOffset 0.0002 (~22 m) +
  geometryPrecision 5; coordinates rounded to 4 decimals.
  **Memory note (differs from ITM):** ITM built the corridor as one
  unary_union + buffer of its 348-line Minnesota line. The national
  line has 4,756 pieces; a whole-line union + buffer was OOM-killed
  on this VM once before, so this script NEVER builds one corridor
  polygon — it buffers each line piece individually, indexes the
  buffers in an STRtree, and unions only the few pieces near each
  cell / polygon. The corridor test is identical (intersects the
  2-mi buffer); only the construction is chunked.
- **Build notes (two failures fixed during this pull, recorded so a
  re-run does not re-chase them):** (1) the first processing run died
  at feature ~300,000 with a GEOS TopologyException ("unable to
  assign free hole to a shell", southern Ohio, ~−81.4, 40.1) in the
  clip intersection — the union of nearby line buffers can carry a
  bad hole. Fixed in `clip_to_corridor`: repair the union with
  `make_valid` before intersecting, retry with both sides repaired,
  then fall back to per-piece intersection; a feature that fails all
  three is skipped and counted (`topology_fail`, 0 on the final run).
  (2) the second run died in the dissolve output with
  `AttributeError: 'GeometryCollection' object has no attribute
  'exterior'` — `make_valid` / overlay fallbacks can return
  collections carrying lines/points. Fixed by flattening each
  dissolved result to its Polygon parts only. (3) a runtime restart
  killed a third processing run mid-clip (~300,000/377,906); the raw
  fetch was intact and the run was re-started with `--from-raw` —
  no re-fetch was needed.
- **Classification — the interpretation method (Nov 18, 2026
  classification sweep; full text in ITM `SOURCES.md`, "Wetlands
  (NWI)" — this script implements it, it does not re-derive it). NO
  published Cowardin→GO/MAYBE/NO-GO matrix exists — this
  classification is a flagged synthesis, and every judgment stays
  labeled as judgment. Apply in order; first rule that fires wins:**
  - W1 — No polygon → GO (screening only). Judgment J1: GO as
    absence is the chapter's definition.
  - W2 — Overlay: overlaps DNR public waters, a calcareous fen,
    or a Minnesota Biological Survey rare natural community →
    NO-GO pending agency advice, regardless of code. **NOT APPLIED
    in this build** — NWI alone cannot identify these and the viewer
    has no public-waters / Natural Heritage layer yet (open gap).
  - W3 — Open / permanent water: regime H, Lacustrine UB, or
    PUB/PAB with H → NO-GO. Judgment J2: the categorical H→NO-GO
    is judgment.
  - W4 — Large bog / muskeg complex: PFO2/PFO4/PSS2/3/4 with regime
    B/C → NO-GO for a through-route; MAYBE only for a short, named,
    maintainable spur. Judgment J3: the spur exception and the word
    "large" (no numeric threshold is set). **Build note: no size
    gate is applied** — every bog-class B/C complex is NO-GO for a
    through-route, because no published threshold exists; the size
    question is left to the field/route check.
  - W5 — Semipermanently flooded (regime F) → MAYBE, short narrow
    boardwalk only; >~300 ft of F-regime tread = NO-GO. Judgment
    J4: the 300-ft threshold; the length check is route-level, not
    applied in the layer.
  - W6 — Seasonally flooded/saturated (regime C/E) → MAYBE, bog
    bridge / boardwalk, short crossing only.
  - W7 — Temporarily flooded / saturated (regime A/B) → MAYBE,
    turnpike / puncheon. Judgment J5: rod-sounding field upgrade —
    if a rod meets no resistance, upgrade to NO-GO.
  - W8 — Riverine FIRST (before W3–W7): R2/R3 perennial → NO-GO
    along the channel (a single bridge point is a separate project
    decision); R4/R5 intermittent → MAYBE, bridge/boardwalk at a
    narrow point. Stay ≥25 ft from the stream edge except at the
    crossing.
  - W9 — Modifiers d (partly drained/ditched), f (farmed), x
    (excavated), or Class US / shore → MAYBE, field-check first; do
    NOT downgrade to GO. Judgment J6: the MAYBE placement.
  - W10 — Cumulative length through any MAYBE class on a proposed
    route >~½ mile → NO-GO for the route as drawn. Judgment J7:
    the ½-mile figure; route-level, not applied in the layer.
  - **Combined rules C1–C4** (applied where the two layers are read
    together): C1 stricter governs — a NO-GO from either dataset is
    a NO-GO overall. C2 soil cannot rescue a wetland — a
    Not-limited soil inside any NWI polygon is never GO. C3 NWI
    polygon + hydric major component = highest-confidence wetland;
    hydric soil with no NWI polygon = MAYBE/field-check, never GO;
    NWI polygon on a non-hydric unit still governs. C4 absence from
    BOTH datasets is the only GO (plus a side-hill 3–10% alignment,
    rule S4) — screening only.
  - **Build-time judgments (extensions of the report's register,
    labeled here):** J13 — regime D (Continuously Saturated) is not
    named in the report's rules; treated as W6-analog MAYBE (bog
    bridge/boardwalk), the same treatment as C/E. J14 — regime K
    (Artificially Flooded) is not named in the report's rules;
    treated as W9-analog MAYBE (field-check; water level is
    managed). Both are the chapter's judgment, not a published rule.
    The parser also handles split classes (e.g. PFO1/4D) by reading
    the regime from the END of the full code — taking the first
    '/'-part alone loses the regime — and regime-less codes (e.g.
    PUS) by parsing against the known class set, so the class
    letters are not misread as a regime.
- **What each feature carries:** `code` (Cowardin), `wetland_type`,
  `system`, `class`, `subclass`, `regime`, `regime_name`,
  `modifier`, `rating` (maybe | nogo), `rule` (short id: W3–W9,
  W6-analog, W9-analog, UNCLASSIFIED), `acres`, `n_polygons`
  (source polygons merged into this feature), `state` (from this
  repo's `site/data/states.geojson`, by centroid; null where the
  centroid falls outside those polygons, e.g. border waters).
  The full rule text (structure + note + judgment tag) is NOT
  repeated per feature — it lives once in
  `working/nwi/wetland-rules.json` (and in the pull script's
  RULE_TEXT table, which the shell's app.js WETLAND_RULES should
  mirror). **State replaces ITM's county/region**, which were
  Minnesota-specific.
- **Dataset limits:** Minimum mapping unit 0.5 ac; identification
  ~90%, classification ~75%; 95% of features within ±5.9 m.
  Intended use 1:12,000 or smaller. NWI is a screening layer, not a
  delineation: field delineation + permits before any MAYBE becomes
  a route.
- **Regulatory gates:** federal Clean Water Act §404, Nationwide
  Permit 42 (2026 reissue, ≤½ acre, pre-construction notification
  required). Minnesota Wetland Conservation Act: avoid → minimize
  → replace; de minimis exemption 400 sq ft / 10,000 sq ft,
  type- and location-dependent — confirm with the local government
  unit. (Other states have their own wetland programs; the
  Minnesota gates are stated here because the classification sweep
  was written for Minnesota — do not read them as national law.)
- **Open gaps:** (1) W2 overlay not applied (above). (2) W4 has no
  numeric "large" threshold (above). (3) W5 300-ft and W10 ½-mile
  are route-level checks — they need an actual drawn route, not a
  layer. (4) Per-polygon vintage is not exposed by the service.
- **Use here:** `site/data/nwi-wetlands.geojson` (single file, local
  only — deployed as the four chunks above), layer
  "wetlands-nwi" ("Wetlands (NWI) — trail routing", OFF by default,
  LAZY). Style (as ITM): MAYBE amber fill (#f59e0b, 0.35) with a
  dashed edge, NO-GO solid red fill (#dc2626, 0.45); dissolved
  features ordered MAYBE then NO-GO so NO-GO draws on top where
  they overlap. Popup shows classification, rule + judgment tag,
  Cowardin code + water regime in words, wetland type,
  system/class, acres, state, the rule's structure + note, the
  screening-only caveat, and the W2 gap.
