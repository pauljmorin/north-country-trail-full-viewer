# Data sources — step 4: NCTA points + gazetteer

**Built 2026-11-24 UTC (2026-11-23 evening CST).** Step 4 of the NCT
viewer plan
(`nct-viewer-itm-based-plan-2026-11-23.md`): the NCTA points layers
run nationally, with the ITM Minnesota clip removed. Scripts live in
`scripts/`; outputs in `site/data/`. Nothing here was invented: every
number below is a count or a measurement from the pull, and every
gap is reported as a gap.

---

## 1. Camping — `site/data/camping.geojson` (502 features)

### References

- **Service:** North Country Trail (Public), NCTA on behalf of NPS —
  `https://services2.arcgis.com/UfGVyqUm4GHa2zrj/arcgis/rest/services/nct_public/FeatureServer`,
  **layer 1, "Point Data - Public"** (the waypoint layer behind the
  public map / FarOut).
- **Pulled:** 2026-11-24 UTC by
  `scripts/pull_ncta_points_national.py` (adapted from the ITM
  viewer's `scripts/pull_points.py`, clip removed).
- **Query:** `where 1=1`, no bounding-box clip — the full national
  service. Features fetched by object id (returnIdsOnly, then POST
  chunks of 500 ids, chunk-verified with split-and-retry — offset
  paging is never trusted on these hosts). **2,546 features fetched,
  0 dropped** (none lacked geometry).

### Interpretation method

- The Camping layer is an exact split on the service's own type:
  `wptType == "Camping"` — nothing else, no reclassification. The
  other 2,044 waypoints go to NCTA Places (§2).
- Properties are cleaned the ITM way, and `wptType` is carried
  **verbatim**: `name` (waypointName), `type` (wptType), `subtype`
  (iconSet2), `extra_types` (iconSet3/4/5 where set), `owner`,
  `description` (descriptionText), `chapter`, `state`,
  `waypoint_id` (waypointID), `source`, `updated` (ISO date).
  Blank strings and the literal string `"None"` become null.
  Positions come from the returned GeoJSON geometry (`outSR=4326`).
- **Counts:** 502 Camping. By state: MI 947 / MN 455 / ND 328 /
  PA 305 / WI 204 / NY 205 / OH 73 / VT 29 across the whole points
  pull (all 8 trail states covered).
- **Data-quality notes (carried as-is, not repaired):**
  - 96 waypoints have no name in the service (86 Parking, 6 Water,
    3 Camping, 1 POI). Their `name` is null and their `waypoint_id`
    (e.g. `nct_MI_parking_10110`) is the identifier.
  - The service's `chapter` field is empty for 1,358 of the 2,546
    points, so the gazetteer (§4) attributes chapter from geometry
    instead of trusting that field.
  - Descriptions are carried **verbatim** from the NCTA public
    service, including contact details the NCTA itself publishes
    (6 descriptions contain an email address or phone number, e.g.
    the Mackinac Bridge Authority transport number and two trail
    angels' Gmail addresses). The gazetteer's search text does NOT
    include descriptions, so those details do not propagate into
    the search index.

### Spot checks (from the service response itself)

- "Lake Sakakawea State Park" (Camping, ND) at the western
  terminus; "Au Sable Point Campsites" (Camping, MI, Federal, fee);
  "Crown Point Campground" (Camping, NY) at the eastern end;
  "Itasca County Fairgrounds Campground" (Camping, MN).

---

## 2. NCTA Places — `site/data/ncta-places.geojson` (2,044 features)

### References

- Same service, layer, pull, and query as §1
  (`scripts/pull_ncta_points_national.py`). Everything in layer 1
  that is not Camping.

### Interpretation method

- Same cleaning as §1. `wptType` carried verbatim — the type
  distribution is: **POI 729, Parking 697, Water 545, Shelter 53,
  Ford 18, Developed Water Source 2**. "Ford" and "Developed Water
  Source" are service types, kept as such; they were not merged
  into Water or POI.
- **Spot checks:** "45th Parallel (Register)" (POI, MI) at latitude
  45.000009; "Mackinac Bridge" (POI, MI); "Lake Sakakawea State
  Park Visitor Center" (POI and Parking, ND); "Bin Walk-In"
  (Shelter, MI).

---

## 3. Mile markers — `site/data/mile-markers.geojson` (6,344 features)

### References

- **There is no single national mile-marker service.** The NCTA
  publishes one half-mile service per state or sub-state stretch
  on the same ArcGIS organisation
  (`https://services2.arcgis.com/UfGVyqUm4GHa2zrj/arcgis/rest/services/<name>/FeatureServer`,
  layer 0 in every case). 16 services were found and fetched in
  full on 2026-11-24 UTC by
  `scripts/pull_mile_markers_national.py` (adapted from the ITM
  viewer's `scripts/pull_mile_markers.py`, which covers only
  `mn_halfmile_points`).

  | Service | Region | Fetched | Mile span |
  |---|---|---|---|
  | `nd_halfmile_points` | North Dakota | 911 | ND 0–454.5 |
  | `mn_halfmile_points` | Minnesota | 1,119 | MN 0–558.5 |
  | `wi_halfmile_points` | Wisconsin | 422 | WI 0–210.5 |
  | `halfmile_wi` | Wisconsin (2nd generation) | 433 | WI 0–215.5 |
  | `mi_halfmile_points` | Michigan, whole state | 2,355 | MI 0–1,176.5 |
  | `halfmile_mi_up` | Michigan Upper Peninsula | 1,107 | MI-UP 0–552.5 |
  | `halfmile_mi_lp` | Michigan Lower Peninsula | 1,240 | MI-LP 0–619.0 |
  | `oh_e_halfmile_points` | Eastern Ohio | 164 | OH-E 0–81.0 |
  | `oh_nw_halfmile_points` | Northwest Ohio | 108 | NW OH 0–53.0 |
  | `pa_halfmile_points` | Pennsylvania | 570 | PA 0–284.0 |
  | `anf_halfmile_points` | Allegheny National Forest | 199 | ANF 0–98.5 |
  | `a100_halfmile_points` | "A-100" Allegheny index | 196 | Mile 0–97.3 |
  | `cny_halfmile_points` | Central New York | 549 | NY 0–273.5 |
  | `halfmile_ny` | New York (2nd generation) | 552 | NY 0–275.0 |
  | `vt_halfmile_points` | Vermont | 143 | VT 0–70.5 |
  | `halfmile_vt` | Vermont (2nd generation) | 142 | VT 0–70.0 |

- **Query per service:** `where 1=1`, no clip; object-id fetch in
  POST chunks of 500, chunk-verified. **10,210 features fetched
  in total, 0 without geometry.**

### Interpretation method

- **Corrupt attribute columns (ITM warning, verified again
  here):** the services' `lat` / `long` attribute columns are
  wrong (Minnesota's longitude attribute duplicates the latitude
  value; Michigan's are null). They are never read. `outFields`
  is limited to `ident, index_, wypnt_id`; positions come solely
  from the GeoJSON geometry (`outSR=4326`).
- Each output feature keeps `ident`, `index_` (Index = whole mile,
  Interval = half mile), `wypnt_id`, `mile` (parsed float;
  `"Start"` = 0.0), `state`, `region`, `source_service`.
- **Each service is a STATE reckoning** (miles from that state's
  start). State reckonings are never merged or converted into a
  trail-wide mileage; the gazetteer (§4) carries the trail-wide
  chainage separately. The state indexes dovetail end to end:
  each starts where the previous ends (ND → MN → WI → MI →
  OH-NW → OH-E → PA → NY → VT), which corroborates the set.
- **Deduplication — the paired services are two generations of
  one index, not two routes.** A point-for-point overlap test at
  100 m does NOT see them (only 0.5–29% within 100 m), because
  the two generations run a systematic ~200–350 m apart
  (cross-track offset, same endpoints, same mile ranges;
  same-mile points are kilometres apart only because the
  mile-zero points differ). The script therefore calls two
  services duplicate generations when ALL THREE hold: (1) the
  median nearest-neighbour distance between their point sets is
  under 400 m (less than half the 800 m half-mile spacing);
  (2) their mile ranges agree within 5%; (3) their endpoints
  agree within 5 km (allowing reversed endpoints — the A-100
  index runs north to south while the ANF index runs south to
  north). The survivor is the generation that fits the currently
  mapped centerline best (fraction of points within 100 m of a
  centerline vertex, median distance as tie-break). The numbers
  behind every drop are in the output file's metadata
  (`overlap_report`) and in the script's stdout.

  | Dropped service | Reason | Key numbers |
  |---|---|---|
  | `wi_halfmile_points` | Duplicate generation of `halfmile_wi` | median NN 264 m; ranges 210.5 vs 215.5; survivor fits centerline better (74.1% vs 73.2% within 100 m) |
  | `halfmile_ny` | Duplicate generation of `cny_halfmile_points` | median NN 338 m; ranges 273.5 vs 275.0; survivor 62.1% vs 60.5% |
  | `halfmile_vt` | Duplicate generation of `vt_halfmile_points` | median NN 201 m; ranges 70.5 vs 70.0; survivor 76.9% vs 73.2% |
  | `a100_halfmile_points` | Duplicate generation of `anf_halfmile_points` (reversed direction: Mile-0 at the north end, ANF-0 at the south end) | median NN 228 m; ranges 98.5 vs 97.3; survivor 80.9% vs 80.6% |
  | `anf_halfmile_points` | Chapter-local reckoning redundant with the Pennsylvania state service: 100% of its points lie within 500 m of a `pa_halfmile_points` point | — |
  | `mi_halfmile_points` | Duplicate generation of the UP+LP pair pooled | median NN 198 m; ranges 1,176.5 vs 1,171.5; UP+LP fit the centerline better (71.6% vs 69.3% within 100 m) |

  **Kept: 10 of 16 services, 6,344 markers.** By state: MI 2,347
  (UP 1,107 + LP 1,240), MN 1,119, ND 911, NY 549, OH 272, PA 570,
  VT 143, WI 433.

### Coverage — what is covered, what is missing (nothing invented)

State marker span vs the mapped state total (from
`site/data/chapters.json` / the mileage table):

| State | Marker span | Mapped total | Coverage |
|---|---|---|---|
| ND | 0–454.5 (911 pts) | 466.91 mi | ~Full; shortfall is unchained tail miles + route-vintage difference, not a missing stretch |
| MN | 0–558.5 (1,119 pts) | 875.15 mi | **Partial.** Index ends at the BRT junction (Gunflint Trail, mile 558.5). The Border Route Trail (64.88 mi) and Superior Hiking Trail (300.29 mi) affiliate stretches have **no** MN index — ~317 mi unindexed |
| WI | 0–215.5 (433 pts) | 213.63 mi | Full (index 1.9 mi longer than mapped — reckoning vs mapped difference) |
| MI | UP 0–552.5 + LP 0–619.0 (2,347 pts) | 1,180.92 mi | ~Full (combined span 1,171.5 mi) |
| OH | E 0–81.0 + NW 0–53.0 (272 pts) | 1,072.78 mi | **Partial.** Only NORTA (~44 mi) and Wampum OH (~81 mi) are indexed. The ~932 mi Buckeye Trail portion has **no** half-mile index |
| PA | 0–284.0 (570 pts) | 286.00 mi | Full |
| NY | 0–273.5 (549 pts) | 705.02 mi | **Partial.** Index covers CNY → ADK-ON → ADK (eastern NY, Cuyler to Crown Point). The ~390 mi Finger Lakes Trail portion has **no** index — ~430 mi unindexed |
| VT | 0–70.5 (143 pts) | 70.66 mi | Full |

- **Route-vintage caveats (kept, flagged, not "fixed"):** the
  Northwest Ohio index sits a median 675 m off the mapped
  centerline (it follows an older/longer routing: 53 mi vs
  44.14 mapped NORTA miles; p90 2,637 m). The North Dakota
  index is similarly offset on parts of its length (median
  133 m, p90 1,289 m). Both are the only index for their
  ground, so they are kept with this note.

---

## 4. Gazetteer — `site/data/gazetteer.json` (8,930 entries, 3.91 MB)

### References

- **Inputs:** `site/data/camping.geojson` (§1),
  `site/data/ncta-places.geojson` (§2),
  `site/data/mile-markers.geojson` (§3); chapter endpoint
  **names** from `ncta-chapter-extents-2026-11-23.md` (repo root);
  centerline `site/data/centerline-{natural,road,urban}.geojson`
  (4,871.07 mi).
- **Built:** 2026-11-24 UTC by
  `scripts/build_gazetteer_national.py` (adapted from the ITM
  viewer's `scripts/build_gazetteer.py`; the section chain is
  replaced by a walk of the centerline itself — see below).
- **Shape:** a search index, not a browsable list: a JSON object
  with `metadata` plus an `entries` array. Each entry carries
  `name`, `kind`, `coordinates`, `chapter`, `state`,
  `chainage_mi` (or null), `from_east_mi`, `snap_m`, `off_chain`,
  `named`, `search_text`, plus kind-specific fields (markers:
  `state_mile`, `state_ident`, `source_service`; points:
  `subtype`, `waypoint_id`; boundaries: `west_chapter`,
  `east_chapter`, `junction_name`, `prev_endpoint`,
  `next_endpoint`). Entries are sorted by chainage (nulls last),
  then kind, then name.

### Interpretation method

- **Chainage (miles from the western terminus).** There are no
  adopted sections trail-wide, so the chain is built by walking
  the centerline: segments joined end-to-end by nearest endpoint
  (150 m tolerance), starting at the western terminus (Lake
  Sakakawea State Park, −101.45349, 47.51963), taking the nearest
  unused continuation at each step. The walk orders **4,348 of
  4,441 segments** into one chain west to east (chapter sequence
  FLY … MALT, GMC last, ending at the Appalachian Trail junction,
  −72.83922, 43.67478 — the eastern terminus). **93 segments
  (69.71 mi, mostly short stubs and parallel alternates) do not
  join the walk** and are left unchained; they are listed in the
  output metadata only as a count, not drawn.
- A point's chainage is the stored `miles` of the main-chain
  segments before its nearest main-chain segment, plus its
  fraction along that segment (by geometry length), **plus the
  straight-line distance of any unmapped gap the walk jumped**
  to reach that segment. The walk jumped **38 times inside the
  main chain (26.05 straight-line miles total)**; every jump is
  listed in the metadata with its gap and the chapters either
  side. The largest in-chain jump is 7.27 km (4.52 mi) in the
  Buckeye Trail, Ohio. The 40.75 km jump at the end (AT junction
  back to a stray MALT segment near Middlebury Gap) is the
  terminal break, not a chain gap, and is recorded separately.
  **Total chainage 4,827.41 mi** = 4,801.36 mapped miles in the
  main chain + 26.05 gap miles (vs 4,871.07 mapped miles total;
  the difference is the 69.71 unchained miles minus the 26.05
  gap miles).
- **Off-chain rule (ITM's 250 m snap limit):** a point whose
  nearest main-chain segment is more than 250 m away gets
  `chainage_mi = null` and `off_chain = true` rather than a
  fabricated position along the trail. Its true coordinates and
  snap distance are still recorded. **8,377 of 8,930 entries
  have a chainage; 553 do not** (231 Camping, 284 other places,
  38 mile markers). Only **26** of the 553 sit within 250 m of
  an unchained segment (a chain defect, listed by name in the
  metadata); the rest are genuinely off the mapped line —
  near-trail campgrounds and the like. This matches the ITM
  viewer's own finding: its BP1–BP11 campsites sit 1.9–3.0 km
  off the depicted chain there, and the same points are
  off-chain here.
- **Chapter/state attribution** comes from the nearest centerline
  segment of any kind (within 5 km); for NCTA points the
  service's own `chapter`/`state` fields are the fallback when
  geometry attribution fails. The service chapter field alone
  would not do (1,358 of 2,546 points have it blank).
- **Chapter boundaries (38) + termini (2).** A boundary sits at
  the chain point where the eastern chapter's first main-chain
  segment starts; its chainage is that point's chainage. The
  junction place name is the endpoint string the two chapters
  share in the extents table (exact, substring, or ≥2 shared
  content tokens / a shared number token). **35 of 38 junctions
  are named**; the 3 nulls are honest: FLY/SRV (the ND gap —
  Lonetree WMA vs Lake Ashtabula name different places), CNY/ADK
  (the central-New-York gap — Oneida–Herkimer line vs
  Forestport), and HSS/HRB (Mackinac Bridge south end vs
  Mackinaw City trailhead). The extents table's west/east
  columns are not always in walk direction (GMC and MALT are
  listed reversed), so no direction is assumed from the table —
  the walk order decides west vs east, the terminus names are
  the end chapter's endpoint that does NOT name the neighbouring
  junction, and the boundary entries carry the two wordings that
  named the junction (`prev_endpoint` / `next_endpoint`).
  Boundary chainages are monotonic west to east (first 258.34,
  last 4,789.97). Note the FLY/SRV boundary chainage (258.34)
  sits ~119 mi past FLY's 139 mi: the mapped route between
  Lonetree WMA and Lake Ashtabula is 114 mi of chapter-unassigned
  (`None`-coded) centerline, which the walk follows.
- **Name rule (ITM):** a waypoint with no name in the NCTA
  service takes its kind as its name ("Parking", "Camping",
  …), with `named=false` (96 entries). Mile markers are named
  by their ident ("MN-187.5"). Descriptions are NOT carried
  into the gazetteer or its search text (see §1).
- **Validation of the chain (in the build output + metadata):**
  per-chapter walk miles vs `site/data/chapters.json` totals
  agree within 5 mi for every chapter except five, and those
  five diffs are exactly the chapter's unchained tail miles:
  FLY −5.79, SRV −7.68, ARW −11.62, NMK −5.39, BTA −14.76.
  State-marker spot checks: MN-Start chainage 451.57 vs
  ND-454.5 chainage 451.69 (the two indexes meet at the state
  line); MN-558.5 chainage 1,009.31, i.e. 557.74 chainage miles
  for 558.5 state miles; Mackinac Bridge POI chainage
  2,080.38, snap 5.12 m.

### Counts by kind

Camping 502 · Parking 697 · Water 545 · POI 729 · Shelter 53 ·
Ford 18 · Developed Water Source 2 · Mile marker 6,344 · Chapter
boundary 38 · Terminus 2. By state: MI 3,308 · MN 1,590 · ND 1,244 ·
PA 877 · NY 759 · WI 630 · OH 346 · VT 176.

---

## Reproducibility

```sh
python3 scripts/pull_ncta_points_national.py   # -> camping.geojson, ncta-places.geojson
python3 scripts/pull_mile_markers_national.py  # -> mile-markers.geojson
python3 scripts/build_gazetteer_national.py    # -> gazetteer.json
```

All three are standard library + `requests`, no credentials, no
API keys. Re-running the pulls re-fetches the live services; the
dedupe decisions are computed from the fetched data each time
(the rules are in the scripts, the numbers in the outputs'
metadata), so a re-run that drops a different service is a
finding about the services, not a bug — check the printed
DUP-CHECK lines.

## Concurrent-work note

Step 3 (derived layers) built `site/data/chapter-boundaries.geojson`
in parallel with this step. This gazetteer's 38 boundary entries
were derived independently per the step-4 brief (extents table +
centerline walk). The shell agent should cross-check the two
boundary sets (coordinates + chainages) before wiring the layer.
