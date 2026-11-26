# Data sources — step 5: partner trails, OSM roads, OSM bike routes, NCTA map sheets

Date: 2026-11-23. Pull scripts: `scripts/pull-partner-trails.py`,
`scripts/pull-osm-corridor.py`, `scripts/pull-ncta-map-sheets.py`.
Raw pulls and downloads are kept outside the repo in
`~/workspace/nct-step5-work/` (partner-raw/, geofabrik/,
ncta-series/, corridor-2mi.geojson); re-running a script re-pulls
everything live and rebuilds the merged output.

Common rules for this step (standing rule: every layer documents its
references AND its interpretation method, so a later reader can
reproduce every output from the sources plus the stated rules):

- Lengths are geodesic miles on WGS84 (pyproj Geod), the same basis
  the completeness viewer's Mesabi overlap measurement used.
- Caveat on the centerline's own numbers: the centerline files carry
  a `miles` property per feature. Summed, those props give 4,871.24 mi
  (the viewer's headline total); the same geometry measured geodesically
  gives 4,768.56 mi. The gap is all in natural tread (props 3,334.99
  vs geodesic 3,230.08, −3.15%); road and urban agree within 0.6%.
  The props are presumably the source (NCTA) lengths, the geometry
  a simplification that cuts switchback corners. All step-5 mileages
  below are geodesic on the geometry as served, so cross-comparisons
  with the viewer's headline total carry that ~3% natural-tread caveat.
- Overpass was NOT used for anything in this step: it is unreachable
  from this VM (HTTP 406 on overpass-api.de, timeout on
  overpass.kumi.systems, 2026-11-23). OSM work went through the OSM
  API (relations/ways) and Geofabrik state extracts instead.

## 1. Partner / concurrent trails — `site/data/partner-trails.geojson`

687 features, 2,687.37 mi total. One feature per chained OSM line or
per source segment. Properties per feature: `trail` (group name),
`name` (segment name as the source carries it), `source`, `source_url`,
`length_mi` (geodesic), `concurrent_with_nct` (true when ≥50% of the
feature's length lies within 50 m of the NCT centerline),
`concurrent_miles` (geodesic length within that 50 m buffer),
`concurrent_pct`, `min_distance_m` (closest approach to the centerline),
`source_id`.

Overlap rule (interpretation): a partner trail's geometry is kept whole
wherever it overlaps the NCT centerline — the overlap is flagged in
the properties, never silently duplicated or deleted. The 50 m
tolerance is the one the ITM viewer used for its SHT/BRT overlap
checks and the Mesabi overlap measurement used. Distances are
measured in the UTM zone of each feature's centroid (pyproj +
shapely, per-feature zone). The length measure is the one kept: an
earlier vertex-fraction version overstated overlap on the long chained
OSM lines (it gave the Long Trail 0 concurrent miles while 23.66 mi
of it lie within 50 m), so the length measure replaced it.

Per trail (pulled 2026-11-23):

| Trail | Features | Miles | Within 50 m (mi) | Source |
|---|---|---|---|---|
| Superior Hiking Trail | 553 | 207.58 | 188.34 | MN DNR State Park Trails and Roads service (see below) |
| Border Route Trail | 24 | 46.07 | 43.99 | USFS National Forest System Trails (EDW_TrailNFSPublish_01) |
| BWCA portages | 39 | 20.50 | 3.65 | Same USFS service, 26 named portages/connectors |
| Trails near Border Route & SHT | 53 | 113.70 | 50.35 | Same USFS service, 28 named trails |
| Driftless Hiking Trail | 4 | 6.35 | 0.00 | OSM ways + traced loop (see below) |
| Buckeye Trail | 7 | 1,473.77 | 895.06 | OSM super-relation 1738661 |
| Finger Lakes Trail | 6 | 569.90 | 358.39 | OSM relations 12725656/57/58/61 |
| Long Trail | 1 | 249.50 | 23.66 | OSM relation 391736 |
| **Total** | **687** | **2,687.37** | **1,563.43** | |

### Superior Hiking Trail — 207.58 mi (553 features)

- Reference: Minnesota DNR State Park Trails and Roads service,
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_state_park_trails_roads/FeatureServer/0
  — query `trail_name == 'Superior Hiking Trail'`, two-pass fetch
  (id list first, then by objectIds in chunks of 500), adapted from
  ITM `scripts/pull-sht.py`.
- Interpretation: the DNR park file carries only the portions inside
  Minnesota state parks — 207.58 mi here (ITM measured 207.56 mi from
  the same service, Nov 16). The published trail is ~310 mi, so ~100
  mi are missing from this source, including the southern terminus
  approach through Jay Cooke State Park (the file's southernmost point
  sits ~7.5 km from the NCT line; the true southern terminus is
  ~936 m away). The line touches the NCT at its northern terminus
  (0 m at −89.93524, 47.98833). One source segment (objectid 383)
  runs ~1.2 km north past that terminus and is left in as the service
  carries it. No better public GIS source was used: the SHT
  Association publishes maps, not a GIS download.

**Superseded 2026-11-26 by the full line.** The DNR park file above
is no longer the viewer's SHT source: the full line from Lake
County's ArcGIS Online service (576 features, 330.0 mi — MAIN 291.1,
SPUR 32.2, CAMP 2.7, untyped 4.0) is now its own layer,
`site/data/sht-full.geojson`, wired by `scripts/pull-sht-full.py`
and documented in `site/data/SOURCES-sht-full.md`. This DNR entry
is kept here as the concurrency record only (188.34 mi within 50 m
of the NCT, measured 2026-11-23). The full line's southern end sits
101 m from the NCT centerline at Jay Cooke — closing the DNR file's
~7.5 km southern gap — and its northern end 2 m from the centerline
at the Pigeon River end. The full line's MAIN (291.1 mi) still sits
~19 mi short of the published ~310 mi trail; that shortfall is an
open gap, not explained by this pull.

### Border Route Trail — 46.07 mi (24 features)

- Reference: USDA Forest Service National Forest System Trails
  (EDW_TrailNFSPublish_01),
  https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0
  — query `trail_name = 'BORDER ROUTE'` inside the Minnesota NCT
  envelope, adapted from ITM `scripts/pull-brt.py`.
- Interpretation: the TrailNFS line is the Superior NF's carried
  tread (trail no. 21007), 46.07 mi — shorter than the published
  ~65 mi. It shares tread with the NCT along the border: 43.99 of
  its 46.07 mi lie within 50 m of the centerline. Western end
  (−90.78325, 48.09088), eastern end at the Pigeon River
  (−89.95014, 47.99830), where the SHT's northern terminus also sits.

### BWCAW portages and connectors — 20.50 mi (39 features)

- Reference: same USFS TrailNFS service; query `trail_name IN (...)`
  with the 26 names from ITM `scripts/pull-bwca-portages.py`
  (AGAMOK-MUELLER, BORDER ROUTE CONNECTOR, BRT-CLEARWATER LK
  CAMPSITE TRL, BRT-PARTIDGE CAMPSITE — the service's spelling,
  a USFS typo kept as-is — BRT-SOCK LAKE CAMPSITE, TOPPER LAKE
  CAMPSITE SPUR, CLEARWATER-WEST PIKE, CLEARWATER/DANIELS LAKE,
  CRAB LAKE CUT-OFF, CRAB LAKE-MAIN BRT, FAY-WARCLUB,
  GLEE-BINGSHICK, GLEE-FAY, HATCHET CREEK-HATCHET POND, KOBE-THOMAS,
  MOUNTAIN-CLEARWATER, ROSE-DUNCAN, ROSE-ROVE, SOUTH LAKE,
  SOUTH LAKE-TOPPER LAKE, WARCLUB-SEAHORSE, WEST PIKE-PINE,
  WOOD LAKE, SOURDOUGH CREEK, FERNBERG AREA, KEKEKABIC-STRUP).
- Interpretation: short lake-to-lake portages and campsite spurs,
  0.03–3.67 mi each, along the Border Route / BWCAW tread. 26 named
  trails, 39 features (some names have several segments). Only
  3.65 mi lie within 50 m of the centerline — most portages leave
  the NCT tread for a lake, as portages do.

### Trails near the Border Route & SHT — 113.70 mi (53 features)

- Reference: same USFS TrailNFS service; query `trail_name IN (...)`
  with the 28 names from ITM `scripts/pull-near-brt-sht.py`
  (KEKEKABIC, SNOWBANK, OLD PINES LOOP, BENEZIE-BECOOSIN LOOP,
  MAGNETIC ROCK, CARIBOU ROCK, BRIDAL VEIL FALLS, BRYCE BREON,
  CENTENNIAL, GUNFLINT LOOKOUT, KEKEKABIC TO MAGNETIC ROCK, UPPER
  GUNFLINT WEST END / SOUTH RIM / OVERLOOK / CUT ACROSS / ASPEN
  RABBIT / POWER LINE / LONELY LAKE / SHORT CUT / WARRENS ROAD,
  GUNFLINT LAKE G CONNECT, SOUTH FOWL ATV, SOUTH FOWL SNOWMOBILE,
  THOMAS LAKE WINTER, THIRTEEN CORNERS, MADDEN WINTER, HIDDEN
  VALLEY TREZONA, TREZONA).
- Interpretation: named Superior NF / BWCAW trails that meet the NCT
  in the Arrowhead corner — 13 touch the BRT tread directly, the rest
  meet it within ~700 m to ~60 km west (the Kekekabic is the BRT's
  western connector; its drawn line stops ~3 km short of the BRT
  line). 50.35 mi within 50 m of the centerline. The Upper Gunflint
  near-misses (Amperage, North Star, Big Pine, Rabbit Run, Highlands,
  Connector, Aspen Alley, Ham Lake, Little Pine, River — 100–300 m
  from the NCT, inventory-verified as not meeting it) are NOT in this
  layer, per the ITM inventory.

### Driftless Hiking Trail — 6.35 mi (4 features)

- Reference: OpenStreetMap API, ways 1248941083 (Phoebe Point Trail),
  1248943005 (Welsh Hills Trail, inner chord), 1248953013 (Knobs Road
  Trail) — `https://www.openstreetmap.org/api/0.6/way/<id>/full` —
  plus the traced Welsh Hills outer loop (2.085 mi) from the ITM
  working file
  `~/workspace/itasca-trail-map/data/driftless/driftless-traced-welsh-phoebe.geojson`
  (read as an input only; the ITM repo was not edited), adapted from
  ITM `scripts/pull-driftless.py`. ODbL.
- Interpretation: the built Driftless segments near Taliesin, WI.
  Weaver Road is NOT in OSM and has no trifold PDF — a known gap,
  not included, nothing invented. Total 6.35 mi (ITM measured 6.340).
  0.00 mi within 50 m of the NCT — the Driftless trail does not run
  with the NCT; it is included as a partner trail per the plan
  because ITM carried it, not because it is concurrent.

### Buckeye Trail — 1,473.77 mi (7 features)

- Reference: OpenStreetMap super-relation 1738661,
  https://www.openstreetmap.org/relation/1738661 (Buckeye Trail
  Association; network nwn, ref BT). Fetched via the OSM API:
  the super-relation's 26 member section relations (each named
  "Buckeye Trail (<place>)") fetched with `/relation/<id>/full`,
  4,495 member ways, 82,863 nodes, then chained end-to-end by
  shared endpoint node id into 7 LineStrings. ODbL.
  Relation ids and the 4,495-way count cross-checked against
  longhikes.org/trails/buckeye/ (super-relation 1738661, 28 section
  relations, 4,495 ways, 2,371.8 km — the live relation carries 26
  section members, same 4,495 ways).
- Interpretation: the full Ohio loop, 1,473.77 mi measured (published
  ~1,444 mi; longhikes measures 2,371.8 km = 1,473.8 mi from the same
  relation — agreement to 0.01 mi). 895.06 mi lie within 50 m of the
  NCT centerline: the NCT follows the Buckeye across most of Ohio.
  The 7 chained lines are the loop broken at junctions where more
  than one unused way shares an endpoint (the chainer stops a chain
  there rather than guessing the turn).

### Finger Lakes Trail — 569.90 mi (6 features)

- Reference: OpenStreetMap region relations 12725656 (Allegany),
  12725657 (Western Finger Lakes), 12725658 (Eastern Finger Lakes),
  12725661 (Catskill), each fetched with
  `/relation/<id>/full` — 814 member ways, 28,761 nodes, chained
  into 6 LineStrings. ODbL. Cross-checked against
  longhikes.org/trails/finger-lakes/ (four region relations,
  921.1 km).
- Interpretation: the whole main Finger Lakes Trail, 569.90 mi
  (published ~580 mi; longhikes measures 921.1 km = 572.3 mi from
  the same relations — this pull is 0.4% short, the chaining gaps
  at junctions). 358.39 mi lie within 50 m of the NCT: the NCT
  follows the FLT across New York. The two spur relations under
  the Eastern region — Lick Brook (11285669) and Buttermilk Falls
  (11285670) — are EXCLUDED as alternates, not the main track
  (longhikes puts them in alternates.geojson). The NCTA-hosted
  `agol_flt` layer (only the segments the NCT shares, 628.9 km)
  was not used: the OSM relations are the whole trail.

### Long Trail — 249.50 mi (1 feature)

- Reference: OpenStreetMap relation 391736,
  https://www.openstreetmap.org/relation/391736 (Green Mountain
  Club; network rwn, ref LT), fetched with
  `/relation/391736/full` — 155 member ways, 19,894 nodes, chained
  into a single LineString. ODbL. Cross-checked against
  longhikes.org/trails/long-trail/ (relation 391736, 153 ways,
  400.9 km in 1 part).
- Interpretation: the whole Long Trail, 249.50 mi (published 272 mi;
  longhikes measures 400.9 km = 249.1 mi from the same relation —
  OSM does not reach the published mileage; the Green Mountain
  Club's own track is restricted and was not used). The NCT meets
  the Long Trail only at its eastern end: 23.66 mi within 50 m of
  the centerline (9.5%), `concurrent_with_nct` false — the shared
  eastern-end miles are recorded in `concurrent_miles`, not hidden
  by the whole-feature flag. First coordinate (−73.155535,
  42.743819) is the southern terminus; last (−72.488248, 45.008651)
  the northern terminus at the Canadian border.

## 2. OSM roads — `site/data/osm-roads.geojson` (deployed as two chunks)

242,491 features, 48,375.13 geodesic mi total (file 113 MB). **Split
for deployment (Nov 24, 2026):** GitHub rejects files over 100 MB, so
the single file is kept locally (gitignored) and deployed as two
chunks by `scripts/split_oversized_layers.py`, split by centroid
longitude at the median (−84.253) — `osm-roads-west.geojson` (121,332
features, 52.3 MB), `osm-roads-east.geojson` (121,159, 51.9 MB).
Chunk counts sum to 242,491, verified by the script. `site/app.js`
fetches both and merges them (`mergeParts`) so the layer renders
identically. Pulled
2026-11-24 (Geofabrik extracts downloaded 2026-11-23/24; the pull ran
in two parts — the first agent completed ND/MN/WI/MI/OH and was
killed mid-extract on Pennsylvania, leaving a 0-byte
`corridor-pennsylvania.osm.pbf`; the resume run deleted it and
finished PA/NY/VT, reusing the downloaded extracts and the five
finished per-state outputs, then merged all eight states with the
same script's merge step — `~/workspace/nct-step5-work/resume-osm.py`).
The resume also had to reinstall the toolchain first (osmium-tool,
gdal-bin, python3-shapely/pyproj via apt): the runtime drain that
killed the first run had also wiped osmium/ogr2ogr/shapely from the
VM — they were not present when the resume started.

- Reference: OpenStreetMap via Geofabrik state extracts,
  https://download.geofabrik.de/north-america/us/<state>-latest.osm.pbf
  (north-dakota, minnesota, wisconsin, michigan, ohio, pennsylvania,
  new-york, vermont), downloaded 2026-11-23/24, ODbL. Extracted
  with GDAL's OSM driver (`lines` layer) by
  `scripts/pull-osm-corridor.py`.
- Interpretation — corridor: the NCT centerline
  (`site/data/centerline-*.geojson`) buffered by 2 mi (3,218.69 m),
  buffered per UTM zone (zones 14–18 cover the trail) so the 2 mi
  is true metres, unioned, then simplified to ~50 m
  (0.00045 deg) for the clip step — the raw union has ~109k
  vertices, which makes GDAL's per-feature clip test very slow;
  simplification moves the corridor edge by at most ~50 m against
  a 2 mi buffer. The corridor polygon is saved at
  `~/workspace/nct-step5-work/corridor-2mi.geojson` for audit.
- Interpretation — what counts as a road: `highway` in the road
  family only — motorway, motorway_link, trunk, trunk_link,
  primary, primary_link, secondary, secondary_link, tertiary,
  tertiary_link, unclassified, residential, living_street, service,
  track, road, pedestrian, busway. EXCLUDED on purpose: footway,
  path, cycleway, steps, bridleway, corridor, construction,
  proposed, raceway, bus_guideway, escape and the rest — those are
  trails, paths and street furniture, not road centerlines. This
  replaces ITM's Minnesota-only MnGeo roads with a national
  equivalent. Properties per feature: `osm_id`, `name`, `highway`,
  `ref`, `surface`, `length_mi` (geodesic).
- Interpretation — state boundaries: ways crossing a state line are
  split at the Geofabrik state boundary, so one physical road can
  appear as two features (one per state). Nothing is de-duplicated
  across states.
- Counts by state (features = per-state ogr2ogr pull counts, before
  the corridor clip; miles = final clipped features assigned by
  midpoint to `site/data/states.geojson` — the two counts differ by
  a handful where a feature's midpoint falls across the line, and
  165 features / 25.40 mi fall in the gaps between the state
  polygons and are listed as border/unknown):

| State | Features (pull) | Miles (clipped, by midpoint) |
|---|---|---|
| North Dakota | 8,294 | 3,815.15 |
| Minnesota | 29,574 | 6,491.75 |
| Wisconsin | 2,544 | 1,287.86 |
| Michigan | 56,640 | 12,020.74 |
| Ohio | 109,603 | 15,774.29 |
| Pennsylvania | 10,970 | 3,066.91 |
| New York | 21,497 | 5,373.64 |
| Vermont | 3,369 | 519.40 |
| border/unknown | — | 25.40 |
| **Total** | **242,491** | **48,375.13** |

- By highway value: service 153,840 (63% of features — `service`
  is in the kept family per the plan, so driveways, parking aisles
  and access roads are included; that is the spec, not a leak),
  residential 44,601, track 16,803, tertiary 7,906, unclassified
  6,375, secondary 4,285, primary 3,219, trunk 1,976, motorway
  1,557, motorway_link 1,184, trunk_link 270, primary_link 142,
  tertiary_link 119, secondary_link 108, living_street 69,
  pedestrian 33, road 4, busway 0. 68,175 features carry a name.
  34 features round to 0.000 mi after clipping (slivers at the
  corridor edge); none has a null geometry.

## 3. OSM bike routes — `site/data/osm-bike-routes.geojson`

132 features, 1,992.27 geodesic mi total. Pulled 2026-11-24, same
run and same extracts as §2 (five states from the first agent's run,
PA/NY/VT from the resume run). 127 unique relation ids — five
routes appear twice, once per state, because they cross a state
line. 111 of 132 features carry a name; none rounds to 0.000 mi.

- Counts by state (features = per-state pull counts; miles = final
  clipped features by midpoint, same method as §2):

| State | Features | Miles |
|---|---|---|
| North Dakota | 0 | 0.00 |
| Minnesota | 25 | 556.99 |
| Wisconsin | 5 | 17.40 |
| Michigan | 28 | 288.70 |
| Ohio | 43 | 784.60 |
| Pennsylvania | 13 | 150.84 |
| New York | 15 | 159.05 |
| Vermont | 3 | 28.76 |
| border/unknown | — | 5.94 |
| **Total** | **132** | **1,992.27** |

  (Wisconsin shows 5 pulled features but 4 by midpoint — one
  route's midpoint falls in the border gap. North Dakota has no
  OSM bicycle route relation in the corridor at all.)

- The Mesabi Trail IS in here: OSM relation 5326107, one feature,
  148.40 mi in the corridor, name "Mesabi Trail", ref "Mesabi",
  network "rcn", first coordinate (−92.5292961, 47.5166803) near
  Virginia, MN. Its 107.94 mi overlap with the NCT at a 50 m
  buffer (mesabi-overlap-2026-11-23.md) is a separate measurement,
  not this layer's number.

- Reference: same Geofabrik state extracts as §2 (same download),
  GDAL OSM driver `multilinestrings` layer (route relations),
  filter `other_tags` containing `"route"=>"bicycle"`, clipped to
  the same 2 mi corridor, by `scripts/pull-osm-corridor.py`. ODbL.
- Interpretation: every OSM bicycle route relation whose geometry
  falls in the corridor, as the relation is mapped — one feature
  per relation per state (a route crossing a state line appears
  once per state). Properties: `osm_id` (relation id), `name`,
  `ref`, `network`, `route` (= "bicycle"), `length_mi` (geodesic).
  The Mesabi Trail comes in here as OSM relation 5326107, one
  route among others; its overlap with the NCT was measured
  separately in `mesabi-overlap-2026-11-23.md` (107.94 mi at a
  50 m buffer) and that document is a cross-check only, not this
  layer's source.

## 4. NCTA map sheets — `site/data/ncta-map-sheets.geojson`

523 features (one Polygon per sheet). No sheet images are built
here — footprints only; the viewer shell handles images later.

- Reference: the NCTA's published per-state map-series GeoPDFs,
  free downloads from https://northcountrytrail.org/maps/ (links as
  listed on https://northcountrytrail.org/trail-map/, "Printable"
  per state), downloaded 2026-11-23/24:
  nd_map_series.pdf (45,446,952 bytes), mn_map_series.pdf
  (158,785,473 bytes — md5 3c0509b12bc45a6b907f623d46614ce2,
  identical to the copy ITM pulled Nov 11, 2026),
  wi_map_series.pdf (53,308,001), mi_map_series_up.pdf
  (123,866,846), mi_map_series_lp.pdf (97,043,080),
  oh_map_series_northwest.pdf (6,259,248),
  oh_map_series_eastern.pdf (8,799,176), pa_map_series.pdf
  (42,201,483), ny_map_series.pdf (22,412,192), vt_map_series.pdf
  (8,816,978).
- Interpretation — footprints: each PDF page carries one sheet as a
  GeoPDF viewport (`/VP`); the `/Measure /GPTS` array gives the map
  frame's four lat/lon corners in LPTS order BL, TL, TR, BR, read
  with pikepdf. The footprint polygon is the ring BL, BR, TR, TL.
  Pages with no `/VP` (cover/index pages, if any) would be skipped
  and recorded — there were none: every page of every series is a
  sheet. Adapted from ITM
  `working/ncta-sheets/build_sheets_full.py` (Minnesota only).
- Interpretation — sheet labels: the printed label is read off the
  page text (`pdftotext -layout`): it sits in the title block just
  below the "* Section Maps" line — e.g. MN-001, MI UP-091,
  MI LP-089, OH-014, ND-081, WI-034, PA-044, NY-043, VT-010.
  Verified against the page number (label number == page number in
  every series; first and last page of each series spot-checked,
  zero label issues across all 523 pages). NOTE: the two Ohio PDFs
  BOTH number OH-001… — sheet ids repeat across the Northwest
  (13 sheets) and Eastern (14 sheets) series, so `series` is part
  of a sheet's identity (`oh-northwest` / `oh-eastern`).
- Interpretation — `trail_miles_in_sheet`: geodesic miles of the NCT
  centerline (`site/data/centerline-*.geojson`) inside the sheet
  quad. This replaces ITM's `miles` string (a Minnesota-mile-range
  label that needs chainage, which does not exist trail-wide yet).
  Where a quad straddles a state line it catches centerline miles
  from the neighbouring state, so per-state sums double-count border
  miles; the trail-wide total does not.
- Counts found vs published: the "published list" is the per-state
  series itself — 10 PDFs, 523 sheets total (ND 81, MN 104, WI 34,
  MI-UP 91, MI-LP 89, OH-NW 13, OH-E 14, PA 44, NY 43, VT 10).
  For comparison, NCTA's 2018 announcement posts gave older counts
  (MN 92 maps then, now 104; MI Upper Peninsula 90 then, now 91;
  ND maps to ND-051 then, now 81) — the series have been revised
  since, and the counts above are from the live PDFs.
- Coverage (measured, not assumed): 3,148.9 geodesic centerline
  miles fall inside a sheet quad (66% of the 4,768.56 geodesic
  centerline miles). By state (exact state polygons from
  `site/data/states.geojson`): PA 100% (278.7/278.7), VT 100%
  (69.6/69.6), ND 100% (463.4/463.6), WI 100% (208.5/208.5), MI
  100% (1,139.0/1,139.0), MN 67% (571.0/851.0), NY 40%
  (271.6/686.6), OH 13% (137.4/1,060.3). The gaps are gaps in the
  published series, not in this pull: Ohio's published GeoPDFs
  cover only the Northwest and Eastern ends (27 sheets) — central
  Ohio (~920 mi) has no series PDF on the trail-map page; New
  York's 43 sheets cover the western part, ~415 mi in the east
  (Adirondacks) have none; Minnesota's uncovered ~280 mi are all
  east of lon −93° (Arrowhead / Border Route region) — the MN
  series numbers state miles 0–558.5 while the centerline carries
  ~851 geodesic miles in Minnesota. No sheet footprints were
  invented for the uncovered miles.

## Verification (this step)

- Every GeoJSON parses (`json.load`); feature counts and mileages
  above are recomputed from the files on disk, not from pull logs.
- Partner trails: per-trail mileages cross-checked against the
  sources' own published figures (SHT 207.58 vs ITM 207.56 from the
  same service; BRT 46.07 vs ITM 46.07; Driftless 6.35 vs ITM 6.340;
  Buckeye 1,473.77 vs longhikes 1,473.8 from the same relation;
  FLT 569.90 vs longhikes 572.3, −0.4% chaining gaps; Long Trail
  249.50 vs longhikes 249.1). Overlap re-measured independently
  by buffer intersection (verify script
  `~/workspace/nct-step5-work/verify-step5.py`): total within-50 m
  1,563.43 mi; Long Trail 23.66 mi, Buckeye 895.06 mi, FLT
  358.39 mi, SHT 188.34 mi, BRT 43.99 mi.
- Map sheets: Minnesota footprints compared corner-for-corner
  against ITM's `pages-geo.json` (same source file) — maximum corner
  deviation 0 degrees (exact). Sample coordinates spot-checked
  (VT-001 quad at lon −73.43..−73.35, lat 44.01..44.08 — western
  Vermont at the New York border, where the NCT enters the state).
- Roads / bike routes: both files parse (`json.load`); feature
  counts and mileages recomputed from the files on disk, not from
  pull logs (`~/workspace/nct-step5-work/verify-osm.py`,
  log `verify-osm.log`). Roads: 242,491 features, metadata
  features/total_miles agree with the recomputed sums (48,375.13
  mi); a 500-feature sample re-measured geodesically agrees with
  the stored `length_mi` props to 0.9999. Bikes: 132 features,
  1,992.27 mi; full geodesic re-measure agrees exactly.
  Every road `highway` value is in the kept family (no excluded
  value present). Corridor placement: all 132 bike features have
  midpoints within 1.99 mi of the centerline; a 2,000-road random
  sample and all 132 bike features are covered by the corridor
  polygon to within 2 m (the strict `covers` test flags
  boundary-touching features whose clipped difference measures
  0.0000 mi — float round-trip on the boundary, not overhang).
  A cruder per-UTM-zone midpoint check flagged 28 of 12,125
  sampled roads up to 10.47 mi out, but all five spot-checked
  flags sit inside the corridor polygon — that check groups
  centerline segments by centroid zone, so segments straddling a
  zone boundary are missing from the neighbouring zone's union;
  the direct polygon check is the one that counts. Mesabi
  relation 5326107 confirmed present (148.40 mi). Sample
  coordinates: first three roads are residential streets around
  (−98.02, 46.91) in North Dakota, on the corridor.
