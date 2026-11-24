type: arcgis-export
url: https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_4_1/MapServer/export
layers: show:0
attribution: PAD-US 4.1 (USGS Gap Analysis Project)

# PAD-US overlay — live service, no local file (2026-11-22)

## Choice

**No local PAD-US file was built in this pass.** The viewer should consume
USGS PAD-US 4.1 as a **live ArcGIS service** (see "Wiring" below). No national
geodatabase was downloaded.

## Why not a local pull

The PAD-US 4.1 service was verified live on 2026-11-22 and it does serve
queries, but a corridor pull is too heavy for this pass:

- `PAD_US_gaz_combined` (layer 0, `PADUS4_1Combined`) returned **192
  features** for one small 0.4° × 0.3° envelope near Duluth, MN, and
  **1,016 features** for a same-size envelope near Columbus, OH (count-only
  queries, `returnCountOnly=true`, 2026-11-22). The trail corridor ribbon
  (~2 mi buffer around 4,871 mi of trail, ~19,500 sq mi) would therefore
  yield **thousands of features**, including very large complex polygons
  (national-forest proclamation boundaries with tens of thousands of
  vertices), paginated at `maxRecordCount: 2000` per page, each then needing
  a local clip to the ribbon and simplification. The result would be a
  multi-MB local file that a web viewer is better off consuming live.
- The whole-line corridor buffer itself could not be built in this VM in
  one shapely pass (the `unary_union` + 2 mi buffer of 4,373 lines was
  OOM-killed); a later local pull should build the buffer in chunks (e.g.
  per-state with `ogr2ogr`) rather than as one union.

## Services (verified live 2026-11-22)

All are public, no key required. Source: USGS Gap Analysis Project,
PAD-US 4.1 (March 2025), DOI `10.5066/P96WBCHS`.

- **Combined inventory — recommended for the viewer** (fee + designations +
  easements + marine + proclamation boundaries):
  `https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_gaz_combined/MapServer`
  Layer 0 `PADUS4_1Combined`. Fields include `FeatClass`, `Category`,
  `Own_Type`, `Own_Name`, `Mang_Type`, `Mang_Name`, `Unit_Nm`, `State_Nm`,
  `GIS_Acres`, `Pub_Access`, `GAP_Sts`. Service spatial reference WKID
  102039 (Albers); the `export` endpoint reprojects to the map CRS.
- **Fee only** (fee-simple footprint, no designations/easements):
  `https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_4_1/MapServer`
  Layer 0 `PADUS4_1Fee`. Spatial reference WKID 102100 (Web Mercator).
- **ArcGIS Online feature services, PAD-US 4.1** (same data, hosted feature
  layers — clickable, with popups; listed on the USGS PAD-US Web Services
  page, `https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-web-services`):
  - Manager Name (combined): `https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Manager_Name_PADUS/FeatureServer`, layer 0 `PADUS4_1ManagerName`
  - Public access / LLLT: `https://services.arcgis.com/UnTXoPXBYERF0OH6/ArcGIS/rest/services/PADUS_Public_LLLT/FeatureServer`
- **Not recommended as primary:** the cached tile service
  `PADUS3_0PublicAccess` (`https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/PADUS3_0PublicAccess/MapServer`)
  is PAD-US **3.0** (2022 vintage) and tiles-only (no attributes).

## Wiring (Leaflet + Esri Leaflet)

```js
// Raster overlay, good for the corridor overview (server renders it):
// NOTE (2026-11-23, verified in-browser): pass f: 'image'. The default
// f: 'json' round-trip returns a rendered-PNG href on the server's
// arcgisoutput host (igskrd911spmpa2.cr.usgs.gov), which does not answer
// from this environment, so the image errors and nothing draws. Direct
// image export loads the PNG straight from the MapServer and renders.
L.esri.dynamicMapLayer({
  url: 'https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US_gaz_combined/MapServer',
  layers: [0],
  opacity: 0.45,
  f: 'image'
}).addTo(map);
// Clickable vector with attributes, for identify/popups (heavier — enable
// at higher zooms or on demand):
L.esri.featureLayer({
  url: 'https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Manager_Name_PADUS/FeatureServer/0',
  fields: ['Own_Name', 'Mang_Name', 'Unit_Nm', 'GAP_Sts', 'Pub_Access', 'GIS_Acres']
});
```

## Caveats (from USGS / the source inventory)

- PAD-US does **not** tag which easements serve the NCT; any trail-easement
  reading needs an intersection with the trail corridor, and many trail
  easements (NCTA, local land trusts, handshake agreements being converted)
  may not be in it at all.
- The Easement class is NCED-derived (non-sensitive easements only);
  `Date_Est` is "not fully attributed". USGS strongly discourages comparing
  two PAD-US versions to look for changes in protection status.
- Combined-layer records overlap by design (fee + designation + easement on
  the same ground); the Fee layer is the non-overlapping footprint.
- Local park data gaps exist below the state level.

## If a local pull is done later

Query `PAD_US_gaz_combined/0` with `geometry` = the 2 mi corridor buffer
as Esri JSON (rebuild the buffer per-state; do not attempt one whole-line
shapely union on this VM), `geometryType=esriGeometryPolygon`,
`spatialRel=esriSpatialRelIntersects`, `outSR=4326`, paginated with
`resultOffset` (`maxRecordCount` 2000). Run a `returnCountOnly` query first
to size it. Clip each returned polygon to the buffer locally, simplify,
and keep only `FeatClass, Category, Own_Type, Own_Name, Mang_Type,
Mang_Name, Unit_Nm, State_Nm, GIS_Acres, Pub_Access, GAP_Sts`.
