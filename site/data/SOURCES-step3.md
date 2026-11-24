# Data sources — plan step 3: derived layers (chainage, chapter boundaries, road walk)

**Built:** 2026-11-23. **Builders:** `scripts/chainlib.py` (shared chain
builder) + `scripts/build_chainage.py`,
`scripts/build_chapter_boundaries.py`, `scripts/build_road_walk.py`.
Re-run any builder to reproduce its output exactly (deterministic,
standard library only, no network, no external pull).

**Standing rule applied:** every layer below lists its references AND
its interpretation method — the exact rules used to turn the inputs
into the output — so a later reader can reproduce every feature.

## Shared inputs (all three layers)

| Input | md5 | What it is |
|---|---|---|
| `site/data/centerline-natural.geojson` | `3d657c100137d0c92bcfb0a77c826d12` | NCT centerline, natural-tread class, 3,202 features |
| `site/data/centerline-road.geojson` | `82209a7a5808a0f044bd3123d4498fa6` | NCT centerline, road class, 939 features |
| `site/data/centerline-urban.geojson` | `246f3bd8ad9ef9d8fe6eb3af923f836b` | NCT centerline, urban-sidewalk class, 300 features |
| `site/data/chapters.json` | `42183c8809142dc39a7d2d1d0b3442b4` | Per-chapter mileage by class (44 rows incl. variants/unassigned) |
| `site/data/mileage-table.csv` | — | State/chapter mileage table; TRAIL TOTAL 4,871.24 mi |
| `ncta-chapter-extents-2026-11-23.md` | `04e0ff8663eaedc92a02b927a165f175` | Chapter names, states, endpoints, source URLs (human labels only — see below) |

Centerline provenance (from the extents file): NCTA ArcGIS
`nct_public` FeatureServer layer 2 pull of 2026-11-21. Each feature
carries only `class`, `state`, `chapter`, `miles` — no road names, no
segment names, no speed/shoulder/crash attributes. Nothing in these
layers invents an attribute the source does not carry.

## Shared interpretation method — the west→east chain

All three layers derive from one ordered chain built by
`scripts/chainlib.py`. The rules, in order:

1. **Length is the source `miles` property, never the drawn geodesic
   length.** The drawn geometry is simplified: Vincenty (WGS-84)
   length of the drawn line is 4,759.09 mi after dedupe, vs 4,861.39
   mi of `miles` values — the drawn line is 102 mi (2.1%) short
   (median drawn/`miles` ratio 0.974). The `miles` values sum to the
   published totals (`mileage-table.csv` 4,871.24 mi; the 0.17 mi gap
   to the raw `miles` sum 4,871.07 mi is rounding of the per-feature
   2-decimal values), so `miles` is the authoritative length.
   Chainage accumulates `miles` along the chain.
2. **MultiLineString features are split into one edge per part**,
   with the feature's `miles` apportioned across its parts by drawn
   length. (115 features are MultiLineString; 238 of their adjacent
   part pairs are non-contiguous, so parts must be treated as
   independent edges.) After splitting: 4,756 edges.
3. **Exact-duplicate parts are walked once.** 33 parts (9.68 mi) are
   byte-identical coordinate sequences (either direction) with the
   same class/chapter — the same stretch drawn twice in the pull.
   Largest: a 4.98 mi NMK natural edge near (-90.39, 46.54) in the
   Ottawa National Forest; next: a 1.48 mi SSC road edge and a
   0.85 mi SSC urban edge. By chapter: NMK 4.98, SSC 2.93, BAW 0.50,
   SRV 0.47, None 0.29, BTA 0.22, HSS 0.19, FLTC 0.04, GTC 0.04,
   MWP 0.02. The published totals (4,871.24 / 4,871.23) double-count
   these 9.68 mi — they were summed without deduping. After dedupe:
   4,723 edges, 4,861.39 mi.
4. **Greedy walk from the western terminus** (westernmost endpoint,
   (-101.45349, 47.51963), Lake Sakakawea SP, ND). At each step take
   an unused edge incident to the current point (exact 5-decimal node
   match first). Ties break by score = jump distance + 1,000 if the
   chapter changes + 2 × turn angle (degrees from the incoming
   bearing): distance dominates, same chapter wins, straightest wins.
   A near-miss continuation — an unused edge endpoint within 500 m —
   is taken as a jump (298 of them, largest 476 m). A genuine gap
   jumps to the nearest unused endpoint (5 of them, 533–1,792 m; see
   §"Gaps"). Jumps add 0 mi to chainage. The walk stops when no
   unused edge lies within 10 km: that is the eastern terminus,
   (-72.83922, 43.67478), the Appalachian Trail junction in the Green
   Mountain National Forest, VT.
5. **No-revisit rule (exact match only).** An edge whose far end is
   exactly a visited node (same 5-decimal key) is never taken while
   another continuation exists. Without it the walk traverses both
   sides of a loop and double-counts it — the FLY loop near Lake
   Sakakawea, where a 4.10 mi natural side and a 5.77 mi road side
   join the same two points. The match is EXACT, not a radius: an
   earlier build used a 100 m radius and it refused 543 true
   continuations (the trail legitimately passes within 100 m of
   itself on hairpins and through town clusters) and stranded the
   walk. Likewise the scoring must be distance-first: an earlier
   build sorted by (chapter, turn, distance) and a straighter edge
   400 m away beat the in-series edge 2 m away, jumping over real
   route miles. Both defects were found by the reconciliation in
   §"Reconciliation" and fixed before delivery; the shipped rules are
   the ones in `chainlib.py`.
6. **Leftovers are excluded, listed, never silently dropped.** 146
   edges (35.18 mi) are never reached by the walk: 8.30 mi of
   overlapping duplicates (≥80% of sampled vertices within 50 m of
   the walked chain — mostly tiny urban/road slivers at class
   boundaries) and 26.88 mi of alternative alignments / spurs (see
   inventory below). They are not additional trail miles.
7. **Positions along the chain are interpolated by fraction of an
   edge's drawn length** (ITM precedent: `build_roadwalk.py`
   interpolates by fraction of measured length within a feature):
   a point at chain mile M inside an edge spanning [S, E] sits at
   fraction (M − S)/(E − S) of that edge's drawn (Vincenty) length.

## Reconciliation (the audit trail)

```
raw `miles` sum over the three files ............ 4,871.07 mi
  exact duplicates removed (§3) ................. -    9.68 mi
  = after dedupe ................................ 4,861.39 mi
  leftovers excluded (§6) ....................... -   35.18 mi
  = walked chain (chainage total) ............... 4,826.21 mi
published totals: mileage-table.csv 4,871.24 mi; chapters.json 4,871.23 mi
  (both exceed the raw sum by ~0.16 mi of per-feature rounding, and
   both double-count the 9.68 mi of duplicates and the 35.18 mi of
   leftovers/alternatives)
drawn geodesic length (Vincenty, after dedupe) .. 4,759.09 mi
  (2.1% short of the `miles` total: simplified geometry, §1)
```

Per-chapter walked miles vs `chapters.json` reconcile exactly as
raw − walked − leftovers = duplicates for every chapter (largest
residuals: NMK 4.98, SSC 2.93 — both exact duplicates, §3).

## Gaps (chain jumps over 500 m — no drawn line between the ends)

| Chain mi | Jump | Chapters | Place (approx.) |
|---|---|---|---|
| 248.08 | 539 m (0.33 mi) | None → None | ND, near (-98.13, 47.45) |
| 315.91 | 533 m (0.33 mi) | SRV → SRV | ND, near (-97.99, 46.83) |
| 353.53 | 1,179 m (0.73 mi) | SRV → SRV | ND, Sheyenne River valley near (-97.92, 46.51) |
| 1191.08 | 1,792 m (1.11 mi) | SHTA → SHTA | MN, Split Rock River area near (-91.44, 47.17) |
| 2746.09 | 623 m (0.39 mi) | NORTA → NORTA | OH, near (-83.76, 41.51) |

No jump crosses a chapter boundary. The two gaps named in the
extents file (ND Lonetree WMA → Lake Ashtabula; NY Oneida–Herkimer
line → Forestport) are bridged in the drawn data by unassigned
(`None`) features with only sub-500 m endpoint mismatches — they do
not appear here as gaps.

## Leftover inventory — alternative alignments / spurs (26.88 mi)

These are drawn in the source but are NOT on the walked chain. The
walk took the other side; the choice rule is §4–§5 above.

| Miles | Where | What it is |
|---|---|---|
| 11.61 | ARW, Grand Rapids–Cohasset, MN (~47.20 N, -93.63…-93.77 W) | Southern parallel route through Grand Rapids (natural + urban + road). The walk took the northern route through town, which matches the NCTA official Minnesota line (`trail-minnesota.geojson` in the ITM repo, read-only check: all 14 sampled vertices of the walked side within 50 m of the official line, median 0 m; the leftover side median 1,355 m away). |
| 6.08 | SRV, Sheyenne River valley, ND (~46.50 N, -97.88…-97.90 W) | Spur/loop hanging off the main route at (-97.87885, 46.50966), dead-ending at (-97.90201, 46.50346). |
| 5.77 | FLY, Lake Sakakawea, ND | Road side of the loop (§5); the walk took the 4.10 mi natural side. |
| 1.40 | SHTA, Split Rock River area, MN (~47.17…47.18 N, -91.41…-91.42 W) | Northern branch off the junction at (-91.42348, 47.167); dead-ends about 2 km short of the main route. The official Minnesota line does not cover this stretch, so no arbitration was possible; the walk's side keeps the chain continuous. |
| 0.80 | WMI, near Middleville, MI (~42.78 N, -85.35 W) | Single 0.80 mi natural edge south of the main route, T-junction at its west end, dead end at its east end. |
| 0.71 | BTA, OH | Scattered short pieces. |
| 0.51 | CND, MI | Scattered short pieces. |

Overlapping duplicates (8.30 mi) are the remaining leftovers: tiny
urban/road/natural slivers at class boundaries whose vertices lie
within 50 m of the walked chain — e.g. ITM 2.05 mi (a second drawing
of a walked stretch, also on the official Minnesota line), MALT 0.62,
MWP 0.70, BAW 0.82, BTA 1.24, CND 0.68, MAC 0.26, FLTC 0.21, CLA
0.32, WAM 0.27, J45 0.10, NORTA 0.15, and smaller pieces. Nine degenerate point edges
(start = end, 0.00–0.02 mi: FLTC ×4, MWP ×2, SHTA ×2, BTA ×1) are
leftovers because the no-revisit rule refuses an edge whose far end
is the node the walk stands on, and one further 0.03 mi SRV edge
(#1117) is a tiny loop-closing edge at a junction; they carry
effectively no miles either way.

## Layer 1 — Chainage (`site/data/chainage.geojson`)

**References:** the three centerline files + the chain (§"Shared
interpretation method"). Schema mirrors the ITM viewer's
`chainage.geojson` (`kind`, `miles_from_west`, `every10`).

**Interpretation method:** one Point per integer mile 1..4,826
(total chainage 4,826.21 mi, so mile 4,826 is the last whole mile).
`miles_from_west` is the integer mile; `every10` is true when the
mile is a multiple of 10. Each point is interpolated along the
ordered chain (§7). No mile-0 point (the western terminus covers it,
in the boundaries layer).

**Verification:** 4,826 points; `miles_from_west` is exactly 1..4,826
(monotonic by construction, asserted in the builder); `every10`
flags checked; 10 randomly sampled points lie 0.0–0.6 m from the
centerline (point-to-segment distance). Chainage total 4,826.21 mi
vs the 4,871.24 mi headline: −45.02 mi, fully reconciled above
(−9.68 duplicates, −35.18 leftovers, −0.16 rounding).

## Layer 2 — Chapter boundaries (`site/data/chapter-boundaries.geojson`)

**References:** the three centerline files + the chain +
`chapters.json` (code → name) + `ncta-chapter-extents-2026-11-23.md`
(chapter names/endpoints as human labels only).

**Interpretation method:** walk the ordered chain; wherever the
`chapter` field changes between consecutive edges, place a Point at
the exit point of the earlier-chapter edge (that point is on the
centerline by construction — all 88 points measure 0.0 m from the
nearest centerline segment). Each point carries
`chapter_from_code`, `chapter_from_name`, `chapter_to_code`,
`chapter_to_name`, `state_from`, `state_to`, `chainage_mi`
(cumulative `miles` at that point, 2 dp). The place-name endpoints
in the extents file are NOT geocoded — the boundary coordinate comes
only from the chapter change in the data. Plus the two termini
(`kind` = `terminus`): western terminus, Lake Sakakawea State Park,
chainage 0.00 at (-101.45349, 47.51963); eastern terminus,
Appalachian Trail junction, Green Mountain National Forest, chainage
4,826.21 at (-72.83922, 43.67478).

**Eastern-terminus correction (read this before reusing the layer):**
the brief labels the eastern terminus "Crown Point / Lake Champlain
bridge", but the drawn centerline continues past Crown Point — the
ADK → MALT junction sits at chainage 4,756.18 mi, (-73.42313,
44.03296) — through Vermont (MALT → GMC at 4,788.77 mi) to the
Appalachian Trail junction, the eastern terminus stated on the GMC
row of the extents file and the easternmost point of the data. The
terminus point carries this in its `note` property. Crown Point is
a chapter junction in this layer, not the terminus.

**Counts:** 88 points (86 junctions + 2 termini). The chain has 87
chapter stretches over 43 distinct codes — far more than the ~38
junctions a one-stretch-per-chapter reading would predict, because
unassigned and variant codes interleave with the named chapters (see
below). Chainages are monotonic 0.00 → 4,826.21 (asserted).

**Non-contiguous chapter codes** (code: number of stretches along
the chain): `None`: 16 (unassigned ground, mostly ND, plus the
11.59 mi Vermont stretch between MALT pieces and small slivers
elsewhere), `GTC`: 5 / `GTR`: 4 (GTR is a variant code on GTC ground
in Michigan — the extents file already flags it as a probable GTC
variant), `BTA`: 3, `BSC`: 3, `CLA`: 3, `ANF`: 3, `CNY`: 3, `FLY`:
3, `MAC`: 3, `MALT`: 3, `LLC`: 2, `ITM`: 2 (a 0.01 mi LLC sliver
inside ITM ground), `PWC`: 2, `BUT`: 2, `Central NY`: 2 (variant
spelling of CNY; one 1.02 mi and one 1.45 mi piece), `ADK`: 2 (a
1.45 mi `Central NY` piece sits inside ADK ground at the NY
transition). Every other code appears in a single contiguous
stretch. The `None` code in the GeoJSON is the literal string
`"None"`; `chapters.json` carries two `None` rows (literal string,
130.92 mi; null field in the source, 21.84 mi) under the same name
(`?? UNMAPPED CODE ??`), which this layer uses verbatim — the two
rows cannot be told apart in the GeoJSON.

## Layer 3 — Road walk (`site/data/road-walk.geojson`)

**References:** the centerline road class
(`site/data/centerline-road.geojson`, 939 features) + the chain.

**Interpretation method:** one LineString per maximal contiguous run
of road-class edges along the ordered chain. A run breaks at a
non-road edge or at a chain gap over 100 m. Each feature carries the
ITM road-walk popup pattern insofar as the source supports it:
`segment` ("Road walk 001" … west to east), `surface` ("road"),
`length_mi`, `chain_start_mi`, `chain_end_mi`, `chapters` (codes
spanned, in order), `states`, `source`. The source carries no road
names, so no road name is given. **No speed limits, shoulder widths,
or crash data are attached** — those are undecided measurement
programs (plan §3, items 5–7) and stay out; no such keys exist in the
file (verified). One sub-0.005-mi road sliver (a 5 m class-boundary
artifact with a 0.00 mi `miles` value) is dropped rather than
published as a 0.00 mi segment.

**Verification:** 573 segments, 1,393.98 mi total; segments in chain
order; every segment ≥ 0.01 mi with ≥ 2 coordinates. Road-class
miles on the walked chain are 1,393.97 mi (segment lengths sum to
1,393.98 mi; the 0.01 mi is rounding). Source road total is
1,411.77 mi; the 17.80 mi gap is road exact-duplicates (2.50 mi) +
road leftovers (15.30 mi: FLY loop side 5.77, ARW south side 6.09,
SRV spur 0.49, and small pieces) — vs the 1,411.47 mi figure in the
brief, which is the pre-dedupe CSV total.

## What was NOT built (out of scope, per the brief)

No speed-limit, shoulder-width, or crash layers; no sections /
adoption layers; no inventory / asset pins; no external pulls. The
shell agent owns `site/index.html`, `site/app.js`, `site/style.css`
— untouched by this step.
