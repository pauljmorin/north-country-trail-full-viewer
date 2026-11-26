# Data sources — Superior Hiking Trail, full line

Date: 2026-11-26. Pull script: `scripts/pull-sht-full.py`. Raw pull kept
outside the repo in `~/workspace/nct-sht-work/raw/` (sht-full-raw.geojson,
576 features as served); re-running the script re-pulls everything live
and rebuilds the merged output.

## Reference

- Lake County, Minnesota, ArcGIS Online service:
  `https://services1.arcgis.com/NlvHF2FHoAfPIDvG/arcgis/rest/services/Superior_Hiking/FeatureServer/3`
  (FeatureServer, 1 layer, 576 features, public, keyless — fetched live
  2026-11-26, `outSR=4326`, `f=geojson`, paged by OBJECTID).
- Trail authority: Superior Hiking Trail Association (SHTA). Collector
  as the service carries it, per feature: Sundew Technical Services
  (498 features), MN DNR State Parks (74), Larry Sampson (1), blank
  (3 — the untyped segments below).
- Found by the Lake County GIS audit,
  `docs/lake-county-gis-audit-2026-11-26.md` (candidate 1). Audit's live
  verification (SUM(MILES) = 330.0) reproduced exactly by this pull.

## Interpretation — what the file is

`site/data/sht-full.geojson` — one feature per source segment, geometry
as served (WGS84), with normalized properties: `trail` ("Superior
Hiking Trail"), `sht_type` (MAIN / SPUR / CAMP / null), `miles` (the
service's own MILES value), `length_mi` (geodesic miles on WGS84,
pyproj Geod), `collector`, `source_id` (OBJECTID), `source`,
`source_url`.

- **Mileage is the service's own MILES, not NCTA mileage.** The popup
  shows both the service miles and the geodesic length. No chainage
  is derived from this line, and no mile of it is presented as NCTA
  mileage — the SHT is a partner trail with its own mileage system
  (SHTA's), and the NCT runs on the SHT from Duluth to Grand Portage
  (audit; the NCT centerline meets this line at both ends — see
  Verification).
- **Styling (viewer):** MAIN solid (#0e7490, weight 3); SPUR thinner
  dashed (weight 2, "6 4"); CAMP thinner dotted (weight 2, "2 4");
  untyped dashed grey (weight 2, "6 4"). The style rule is the
  audit's: MAIN as the trail line, SPUR/CAMP as secondary.
- **Untyped segments — kept as served, not classified (judgment
  labeled):** 3 segments (OBJECTIDs 574–576, 3.99 service miles)
  carry a blank SHT_TYPE and a blank COLLECTOR in the service. They
  form one continuous stretch (lat ~47.15–47.17, lon ~−91.45…−91.49)
  that chains off MAIN segment 180 at (−91.44559, 47.1728) and
  dead-ends at (−91.47682, 47.14863). They are drawn dashed grey and
  the popup says "Untyped in source" — the map does not assert a type
  the source does not state. A re-pull may type them; the script
  normalizes whitespace-only types to null so the gap stays visible.
- **Nothing is de-duplicated, merged, or re-chained.** The file keeps
  the service's 576 segments as 576 features, including any
  overlapping or duplicate tread the service carries.

## Counts (recomputed from the file on disk, not from pull logs)

| SHT_TYPE | Features | Service MILES | Geodesic mi |
|---|---|---|---|
| MAIN | 390 | 291.1 | 290.99 |
| SPUR | 105 | 32.2 | 32.21 |
| CAMP | 78 | 2.7 | 2.70 |
| (untyped) | 3 | 4.0 | 3.99 |
| **Total** | **576** | **330.0** | **329.90** |

Geodesic total is 0.03% under the service total — the geometry is
essentially unsimplified (unlike the NCTA centerline, whose drawn
length runs ~2% short of its `miles` props on natural tread).

## Gaps (honest, not filled)

- **MAIN is 291.1 mi against a published trail of ~310 mi.** The
  ~19 mi shortfall is not explained by this pull — it is not a
  geometry-simplification effect (geodesic agrees with service
  MILES to 0.1 mi on MAIN). It may be unmapped segments, service
  undercount, or a different published basis; nothing is invented
  to close it.
- **The DNR park file's southern gap is closed by this source:**
  the DNR file's southernmost point sat ~7.5 km from the NCT line;
  this line's southern end (−92.37267, 46.65495, Jay Cooke State
  Park) sits 101 m from the NCT centerline. The northern end
  (−89.93582, 47.99914) sits 2 m from the centerline at the Pigeon
  River end.
- **This replaces the DNR park file as the fuller SHT source in
  this viewer.** The partner-trails layer keeps its 553-feature
  DNR SHT (207.58 mi) as the concurrency record only; its
  per-trail note and the data-sources page carry the supersession.
  The ITM viewer's 208-mi DNR SHT is untouched by this change
  (NCT viewer only, per the adoption).

## Verification

- Every feature parses (`json.load`); no null geometries.
- Feature count (576) and SUM(MILES) by type (MAIN 291.1, SPUR
  32.2, CAMP 2.7, untyped 4.0, total 330.0) recomputed from the
  file on disk and match the audit's live SUM(MILES) exactly.
- Endpoint check (shapely + pyproj Geod, 2026-11-26): SHT
  southernmost point 101 m from the nearest NCT centerline point
  (−92.37136, 46.65487); northernmost point 2 m from the nearest
  centerline point (−89.93582, 47.99916). The three untyped
  segments chain end-to-end (exact 5-decimal endpoint match) and
  touch MAIN segment 180 at one end only.
