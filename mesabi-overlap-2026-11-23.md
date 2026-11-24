# Mesabi Trail overlap in the NCT completeness viewer

Date: 2026-11-23. Viewer commit 169f145 (not yet on GitHub).
Companion geometry: `mesabi-trail-osm-2026-11-23.geojson` (same directory).

## Headline

**107.94 miles of the NCT centerline's "natural tread" run on or immediately
beside the Mesabi Trail** (50 m buffer; see Method). All of it is in
Minnesota, in two chapters:

| Chapter | Overlap (mi) | NCT features touched | Chapter natural total (mi) | Left after subtracting |
|---|---|---|---|---|
| ARW (Arrowhead) | 94.72 | 42 (14 fully inside the buffer) | 136.12 | 41.40 |
| ELY (Ely) | 13.22 | 3 | 15.54 | 2.32 |
| **Total** | **107.94** | **45** | — | — |

Effect if the Mesabi miles come out of natural tread:

- Trail-wide natural tread: 3,335.09 → **3,227.15 mi** (68.5% → 66.3% of the
  4,871.24 mi existing route).
- Minnesota natural tread: 729.93 → **621.99 mi**.
- A Mesabi-only bike-path category would hold 107.94 mi; other bike paths
  are still to be judged case by case and are NOT in this number.

## Comparison with the Minnesota off-road paved pool

Off-road paved NCT miles in Minnesota (NCTA source: `trail_stat='NCT'`
and `trail_surf` in Asphalt/Paved/Concrete) total **132.11 mi**. The
Mesabi overlap is **81.7%** of that pool, leaving ~24.2 mi of paved NCT in
Minnesota that is not on the Mesabi. Cross-check against the live NCTA
source for the Mesabi corridor bbox (lon −93.523 to −91.830, lat 47.249
to 47.915, queried 2026-11-23): NCT features in the bbox total 122.94 mi,
of which 116.37 mi are tagged Asphalt, 6.29 mi have blank surface and
0.28 mi Native — so the blank-surface caveat is small in this corridor,
and the overlap is nearly all on asphalt-tagged tread.

## Method

1. Mesabi geometry: OpenStreetMap relation 5326107 ("Mesabi Trail"),
   fetched from the Overpass API 2026-11-23 (OSM base timestamp
   2026-11-23T23:43:06Z). 284 member ways, all with geometry, 7,026
   points. Main-role members (282) chained end-to-end into 20 LineStrings
   (inter-way joints meet within a few metres; see Caveats). The one
   `alternative` member (0.02 mi) and one `route` member (0.06 mi) were
   excluded as negligible. Total OSM Mesabi length: **158.93 mi**.
2. Intersect: the Mesabi line buffered by **50 m** (the same distance the
   viewer's SHT overlap check used), in EPSG:26915 (NAD83 / UTM 15N —
   the whole trail lies in UTM 15N), against the viewer's
   `site/data/centerline-natural.geojson`, Minnesota features only
   (539 features, 729.93 mi).
3. Lengths are geodesic miles on WGS84 (pyproj Geod), matching the
   viewer's mileage basis.

Buffer sensitivity (same method, different buffer): 25 m → 106.45 mi;
50 m → **107.94 mi**; 100 m → 108.81 mi. The number moves ~±1.5 mi
across that range — the two lines are essentially coincident where they
share the corridor, not parallel-offset.

## Verification (recomputed from the saved files)

- Buffer/intersection re-run reading only the saved GeoJSON +
  `centerline-natural.geojson`: **107.94 mi** (exact).
- Independent estimator — NCT Minnesota natural lines densified to 10 m
  samples, counting samples within 50 m of the Mesabi: **110.18 mi**
  (ARW 96.69, ELY 13.49). ~2 mi higher, as expected: sampling counts a
  whole 10 m step when its endpoint falls inside the buffer, so segments
  straddling the boundary inflate it slightly. Same magnitude, same
  chapter split — no factor error, no CRS blunder.
- Scripts: `~/workspace/mesabi-work/mesabi_analyze.py` and
  `~/workspace/mesabi-work/mesabi_verify.py` (venv with shapely 2.2.0 +
  pyproj 3.8.0 in `~/workspace/mesabi-work/.venv`).

## Where the NCT does and does not follow the Mesabi

Measured from the Mesabi side, ~109.3 mi of the 158.93 mi OSM trail lies
within 50 m of NCT natural tread (the NCT-side 107.94 mi is the number
to subtract; the ~1.3 mi gap between the two is parallel-offset tread).
The NCT follows the Mesabi almost throughout Grand Rapids → Virginia →
Biwabik → Aurora and again Tower → Ely (overlap extent lon −93.50 to
−91.83, lat 47.28 to 47.91). It does **not** follow these Mesabi
stretches, and that is genuine route divergence, not missing centerline
data — the nearest NCT natural tread is 2.9–9.6 km away at those
midpoints:

- The Aurora → Tower stretch (OSM chains around lon −92.2, lat 47.6–47.8;
  ~28 mi including the Virginia-area loop south of town): the NCT takes
  its own route north through the forest and rejoins the Mesabi near
  Tower. Nearest NCT natural tread to the midpoint of that stretch is
  9.6 km; nearest NCT road tread 4.3 km.
- The Virginia/Eveleth loop south of town (~2.6 mi, chains near
  −92.52, 47.44): nearest NCT natural tread 6.4 km away.
- The last ~0.7 mi into Ely is only 4% covered — the NCT's Ely approach
  differs slightly from the Mesabi's endpoint at the International Wolf
  Center.

Road-class note: 2.38 mi of NCT **road**-class miles lie within 50 m of
the Mesabi (ARW 2.35, ELY 0.03). Those are already counted as road, not
natural tread, so they are not part of the 107.94 mi subtraction.

SHT note: the centerline file does carry 300.2 mi tagged chapter SHTA
(NCT miles coincident with the Superior Hiking Trail, not a second line);
no SHTA segment is within 50 m of the Mesabi, so no double-count arises
here.

## Caveats — what would change the number

- **Buffer choice**: ±~1.5 mi across 25–100 m (106.45–108.81 mi).
- **Parallel-but-distinct tread**: where the NCT runs on a parallel path
  within 50 m of the bike path rather than on it, those miles count here.
  The sensitivity range bounds that at ~2 mi.
- **OSM currency**: the relation is a 2026-11-23 pull. If OSM gains or
  loses Mesabi segments, re-run. The OSM total (158.93 mi) sits between
  TrailLink's 155 mi open and the 165 mi master-planned figure, consistent
  with the ~6.5 mi still unfinished — no material mapping gap found
  (near-duplicate mapping totals only ~2.7 mi, all on stretches the NCT
  does not follow).
- **The unfinished gap**: if/when the remaining ~6.5 mi is built and the
  NCT is routed onto it, the overlap grows.
- **Blank surface**: 802 off-road miles trail-wide have blank surface in
  the NCTA source, so the 132.11 mi Minnesota paved pool is a floor. That
  does not change the geometric overlap (107.94 mi); it only means the
  Mesabi's share of *true* paved miles is somewhat below 81.7%.
- **Newer NCTA pull**: if the viewer re-derives the centerline from a
  later NCTA pull, NCT geometry shifts could move the overlap slightly.

## Sources

- Mesabi Trail geometry: OpenStreetMap relation 5326107,
  https://www.openstreetmap.org/relation/5326107 — retrieved 2026-11-23
  via Overpass API (https://overpass-api.de/api/interpreter), ODbL.
  Relation source tag: http://www.mesabitrail.com/
- Mesabi Trail length: 165 miles master-planned — Wikipedia,
  https://en.wikipedia.org/wiki/Mesabi_Trail ; Rails-to-Trails
  Conservancy, Oct 2025 Trail of the Month,
  https://www.railstotrails.org/trailblog/minnesotas-mesabi-trail-october-2025-trail-of-the-month/
  (final Embarrass–Tower section completed August 2026; ~6.5 mi gap
  remained). TrailLink lists 155 miles open,
  https://www.traillink.com/classic-gallery/classic-detail/?img=135646&tr=mesabi-trail-
- NCT centerline: viewer `site/data/centerline-natural.geojson` (NCTA
  official centerline pull of November 21, 2026); NCTA source
  https://services2.arcgis.com/UfGVyqUm4GHa2zrj/arcgis/rest/services/nct_public/FeatureServer/2
  (surface tabulation in the Mesabi corridor bbox queried 2026-11-23).
- Viewer headline totals (natural 3,335.09 / road 1,411.47 / urban 124.68 /
  total 4,871.24 mi) from `site/index.html`.

## Files

- This note: `mesabi-overlap-2026-11-23.md`
- Mesabi geometry used: `mesabi-trail-osm-2026-11-23.geojson`
  (20 LineString features, OSM relation 5326107, main-role members only)
- `site/` was not modified and nothing was committed.
