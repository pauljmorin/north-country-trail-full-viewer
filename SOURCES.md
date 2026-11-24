# Data sources — North Country Trail full trail viewer (index)

This file is an index, not a second copy: the per-step build notes are the
record, and `site/data-sources.html` is the readable page built from them.
Do not duplicate layer detail here by hand — add it to the per-step file
and to the page, and link it from the table below.

## The record

| File | What it documents |
|---|---|
| `site/data/SOURCES-step2.md` | Step 2 — national live-service layers: trail alerts (83), NCT reroutes (15), NBI bridges (1,415), NWI wetlands (352,865), BIA tribal lands (11), PAD-US (live service, no file). Common corridor: 2-mi buffer around the centerline. |
| `site/data/SOURCES-step3.md` | Step 3 — derived layers: chainage (4,826 pts, 4,826.21 mi), chapter boundaries (88 pts), road walk (573 segs, 1,393.98 mi). Shared chain builder `scripts/chainlib.py`; full reconciliation (raw 4,871.07 − 9.68 duplicates − 35.18 leftovers). |
| `site/data/SOURCES-step4.md` | Step 4 — NCTA points + gazetteer: camping (502), NCTA Places (2,044), mile markers (6,344; coverage gaps MN/OH/NY), gazetteer (8,930 entries; independent chain walk, 4,827.41 mi). |
| `site/data/SOURCES-step5.md` | Step 5 — partner trails (687), OSM roads (242,491), OSM bike routes (132; Mesabi present), NCTA map sheets (523; coverage gaps OH 13% / NY 40% / MN 67%). |
| `site/data/padus-note.md` + `site/data/padus-layer.json` | PAD-US: live-service wiring (combined raster + Manager Name vector), why no local pull, and the recipe for one later. |
| `site/data-sources.html` | The readable data-sources page (linked from the shell footer). Built from the four step files + the plan + the wiring cross-checks. |

## Standing rule (applies to this viewer too)

Every layer lists BOTH its references AND its interpretation method — the
exact rules used to turn raw data into the published classification — so a
later reader can reproduce every classification from the references plus
the stated rules, with nothing resting on undocumented judgment. Judgment
stays labeled as judgment; gaps stay stated as gaps.

## Cross-checks (wiring, 2026-11-23)

Two independent builds derived chapter boundaries and chainage from the
same centerline by different methods; both are kept, neither was altered
to match the other. Full write-up on the data-sources page ("Cross-checks
run when the layers were wired in"):

- **Boundaries:** 37 of the gazetteer's 38 named boundaries match a
  step-3 junction with the same chapter pair; max distance 0.002 mi.
  The one exception (FLY → SRV, chainage 258.34) has no step-3
  counterpart because 114 mi of unassigned (`None`) centerline runs
  between the two chapters. The other 49 step-3 junctions are real data
  junctions — interleavings of unassigned/variant codes (None, GTR,
  "Central NY", LON, the 0.01 mi LLC sliver, the CLA/BUT reversal).
  Map layer = step 3 (86 junctions + 2 termini); search = gazetteer's 38.
- **Chainage:** step 3 totals 4,826.21 mi; the gazetteer chain walk
  totals 4,827.41 mi — 1.20 mi apart, cause determined: step 3 removes
  44.86 mi net (9.68 duplicates + 35.18 leftovers); the gazetteer
  removes 43.66 mi net (69.71 unchained − 26.05 gap miles added back).
  Map layer = step 3; gazetteer results carry gazetteer chainage.

## Not built yet

- **Soils (SSURGO), plan step 6.** NRCS Soil Data Access was HTTP 502
  on both hosts (2026-11-18); retried once at wiring (2026-11-23) and
  both hosts answered HTTP 200 — the service has recovered, but the
  national pull has not been run. No soils data is shown; the shell
  keeps the soils stub with this note. Intended method: the ITM
  viewer's `scripts/pull_ssurgo_corridor.py` pattern, corridor built in
  chunks (a whole-line union + buffer was OOM-killed on this VM).
- **Undecided (plan §3/§6, 13 items)** — parcels, motorized trails,
  timber, state campgrounds, speed limits, crash data, shoulder
  measurement, Street View point generation, photos, reroute corridors
  generally, easements via NCED, forest health / invasives (national
  equivalents), tree height / contours via USGS 3DEP. Listed in full on
  the data-sources page. Nothing in that list is built until Paul
  answers the question beside it.

## Coverage gaps (honest, not filled)

Soils (not built); mile markers — MN east of mile 558.5 (~317 mi), OH
Buckeye portion (~932 mi), NY Finger Lakes portion (~390 mi); NCTA map
sheets — OH 13%, NY 40%, MN 67%; wetlands W2 overlay not applied, no
numeric W4 "large" threshold; partner trails — SHT ~100 mi missing from
the DNR park file, BRT 46.07 vs ~65 mi published, Driftless Weaver Road
missing, Long Trail OSM 249.50 vs 272 mi published; PAD-US easements
untagged; chapter mileage — 152.76 mi unassigned, Star of the North
10.21 tagged miles vs ~27 maintained.
