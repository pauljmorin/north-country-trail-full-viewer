#!/usr/bin/env python3
"""Merge the per-state parcel candidate pulls into the viewer layer.

Reads working/parcels/raw-<STATE>.jsonl (ND, MN, WI, VT, NY, OH) and
selects the corridor set, globally across all states, per the ITM
model (pull_parcels_corridor.py):
  - crossed:   a parcel the NCT line crosses/touches, or whose
               boundary comes within 1 m of the line (tolerance
               absorbs digitising offsets between datasets).
  - adjoining: a remaining candidate whose boundary comes within 3 m
               of a crossed parcel's boundary. One ring deep.
Selection runs on the FULL geometry in EPSG:5070 (metres); the output
geometry is simplified (2 m, topology-preserving) afterwards, so a
simplification can never change the selection.

Also:
- dedupes by src_oid (a parcel can be returned by several cells);
- derives the county from TIGER 2024 counties where the service
  carries none (VT) and verifies the service county elsewhere;
- fills acres from the geometry when the service carries none;
- drops invalid/empty geometries (counted, not hidden);
- writes site/data/parcels.geojson + a merge log with per-state and
  per-county counts, coverage miles (from county_miles.csv), and the
  Kent verdict.

Usage: python3 scripts/merge_parcels.py
"""

import csv
import json
import os
import sys
import time

import pyproj
from shapely.geometry import mapping, shape  # noqa: E402
from shapely.geometry import MultiPolygon, Polygon  # noqa: E402
from shapely import make_valid  # noqa: E402
from shapely.ops import transform as _transform  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(REPO, "working", "parcels")
OUT = os.path.join(REPO, "site", "data", "parcels.geojson")
LOG = os.path.join(WORK, "merge-log.md")
PULLED = time.strftime("%Y-%m-%d", time.gmtime())

STATES = ["ND", "MN", "WI", "VT", "NY", "OH"]
LINE_TOL_M = 1.0   # crossed: boundary within 1 m of the line (ITM)
RING_TOL_M = 3.0   # adjoining: boundary within 3 m of a crossed parcel
SIMPLIFY_M = 2.0   # output simplification, metres, topology-preserving
ACRE_M2 = 4046.8564224

TO5070 = pyproj.Transformer.from_crs(
    "EPSG:4326", "EPSG:5070", always_xy=True).transform
TO4326 = pyproj.Transformer.from_crs(
    "EPSG:5070", "EPSG:4326", always_xy=True).transform


def round_coords(geom, ndigits=6):
    """Round all coordinates of a lon/lat geometry to ndigits."""
    def _round(x, y, z=None):
        if z is None:
            return (round(x, ndigits), round(y, ndigits))
        return (round(x, ndigits), round(y, ndigits), round(z, ndigits))
    return _transform(_round, geom)


def load_line_pieces():
    pieces = []
    for fn in ("centerline-natural.geojson", "centerline-road.geojson",
               "centerline-urban.geojson"):
        with open(os.path.join(REPO, "site", "data", fn)) as fh:
            gj = json.load(fh)
        for feat in gj["features"]:
            g = _transform(TO5070, shape(feat["geometry"]))
            if g.is_empty:
                continue
            geoms = list(g.geoms) if g.geom_type == "MultiLineString" \
                else [g]
            pieces.extend(geoms)
    return pieces


def load_counties():
    """TIGER 2024 counties (5070) -> (STRtree, [(STUSPS, NAME)])."""
    path = os.path.expanduser(
        "~/workspace/nct-parcels-scope/counties_5070.geojson")
    geoms = []
    keys = []
    with open(path) as fh:
        gj = json.load(fh)
    for feat in gj["features"]:
        p = feat["properties"]
        geoms.append(shape(feat["geometry"]))
        keys.append((p.get("STUSPS"), p.get("NAME")))
    return STRtree(geoms), geoms, keys


def county_for(geom5070, tree, geoms, keys):
    c = geom5070.centroid
    idx = tree.query(c, predicate="intersects")
    if len(idx) == 0:
        # Centroid outside every polygon (border sliver) — nearest.
        idx = tree.query(c, predicate="dwithin", distance=1000)
        if len(idx) == 0:
            return None
        nearest = min(idx, key=lambda i: geoms[i].distance(c))
        return keys[nearest]
    return keys[idx[0]]


def main():
    os.makedirs(WORK, exist_ok=True)
    # --- load candidates, dedupe by src_oid ---------------------------
    feats = []
    seen = set()
    dupes = 0
    per_state_raw = {}
    for state in STATES:
        path = os.path.join(WORK, "raw-%s.jsonl" % state)
        if not os.path.exists(path):
            print("MISSING raw file for %s: %s" % (state, path))
            return 1
        n = 0
        with open(path) as fh:
            for line in fh:
                f = json.loads(line)
                oid = f["properties"].get("src_oid")
                if oid in seen:
                    dupes += 1
                    continue
                seen.add(oid)
                feats.append(f)
                n += 1
        per_state_raw[state] = n
        print("%s: %d candidates" % (state, n), flush=True)
    print("total candidates: %d (deduped %d)" % (len(feats), dupes),
          flush=True)

    # --- line + counties ------------------------------------------------
    pieces = load_line_pieces()
    line_tree = STRtree(pieces)
    print("line pieces (5070): %d" % len(pieces), flush=True)
    county_tree, county_geoms, county_keys = load_counties()

    # --- selection in 5070 ----------------------------------------------
    crossed = []
    rest = []
    invalid = 0
    for f in feats:
        try:
            g = _transform(TO5070, shape(f["geometry"]))
        except Exception:  # noqa: BLE001
            invalid += 1
            continue
        if g.is_empty:
            invalid += 1
            continue
        if not g.is_valid:
            g = make_valid(g)
        if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            invalid += 1
            continue
        # Crossed: the 1 m-buffered parcel touches a line piece.
        hits = line_tree.query(g.buffer(LINE_TOL_M), predicate="intersects")
        if len(hits):
            crossed.append((f, g))
        else:
            rest.append((f, g))
    print("crossed: %d; remaining: %d; invalid/dropped: %d"
          % (len(crossed), len(rest), invalid), flush=True)

    crossed_geoms = [g for _, g in crossed]
    crossed_tree = STRtree(crossed_geoms)
    adjoining = []
    for f, g in rest:
        hits = crossed_tree.query(g.buffer(RING_TOL_M),
                                  predicate="intersects")
        if len(hits):
            adjoining.append((f, g))
    print("adjoining (ring): %d" % len(adjoining), flush=True)

    # --- build output features ------------------------------------------
    out_features = []
    counts = {}   # (state, county, class) -> n
    county_mismatch = []
    for group, items in (("crossed", crossed), ("adjoining", adjoining)):
        for f, g in items:
            p = dict(f["properties"])
            p["corridor"] = group
            # County: derive from TIGER; fill VT, verify the rest. The
            # service county wins on substance, but TIGER supplies the
            # proper case (WI returns CONAME in ALL CAPS).
            derived = county_for(g, county_tree, county_geoms, county_keys)
            derived_name = derived[1] if derived else None
            if not p.get("county"):
                p["county"] = derived_name
            elif derived_name and derived_name.lower() == \
                    p["county"].lower():
                p["county"] = derived_name
            elif derived_name:
                county_mismatch.append(
                    (p["state"], p["county"], derived_name,
                     p.get("parcel_id")))
            # Acres from the geometry when the service carries none.
            if p.get("acres") is None:
                p["acres"] = round(g.area / ACRE_M2, 2)
            # Simplify + back to lon/lat, rounded.
            gs = g.simplify(SIMPLIFY_M, preserve_topology=True)
            if gs.is_empty:
                continue
            gl = round_coords(_transform(TO4326, gs))
            out_features.append({"type": "Feature", "geometry": mapping(gl),
                                 "properties": p})
            key = (p["state"], p.get("county"), group)
            counts[key] = counts.get(key, 0) + 1

    # --- coverage miles ---------------------------------------------------
    miles = {}
    with open(os.path.expanduser(
            "~/workspace/nct-parcels-scope/county_miles.csv")) as fh:
        for row in csv.DictReader(fh):
            miles[(row["state"], row["county"])] = float(row["trail_miles"])
    covered_miles = 0.0
    covered_counties = set()
    for (state, county, _group) in counts:
        if (state, county) in miles and (state, county) not in covered_counties:
            covered_counties.add((state, county))
            covered_miles += miles[(state, county)]

    metadata = {
        "dataset": "Trail corridor parcels (Option A — statewide services "
                   "only): parcels the NCT line crosses, plus the adjoining "
                   "ring (one parcel deep)",
        "pulled_utc_date": PULLED,
        "method": (
            "Candidates pulled per state from the six statewide parcel "
            "services (ND NDGISHUB, MN MnGeo quarterly snapshot, WI V12, "
            "VT VCGI, NY NYS ITS, OH ODNR) within 2.5 km of the NCT "
            "centerline; crossed = line crosses/touches the parcel or "
            "passes within 1 m of its boundary; adjoining = boundary "
            "within 3 m of a crossed parcel. Selection in EPSG:5070 on "
            "full geometry; output simplified 2 m, topology-preserving. "
            "Owner name + mailing address as published in the county "
            "records (public record); taxpayer fields (values, taxes, "
            "EMV, assessment) never pulled."),
        "display": (
            "OFF by default, lazy-loaded on first toggle; faint below "
            "zoom 3, full style at zoom 3+; crossed parcels 2px solid "
            "orange outline, adjoining 2px dashed khaki. Not suitable "
            "for accurate boundary determination (per-source disclaimer "
            "in each feature's source/vintage)."),
        "kent_mi": (
            "Kent County MI re-checked 2026-11-24: service root returns "
            "HTTP 200 but the body is {\"error\":{\"code\":499,\"message\":"
            "\"Token Required\"}} with no layers — still gated, NOT in "
            "this layer. Backfill if restored (+74.89 mi)."),
        "backfill": (
            "Not in this layer (Option A scope): MI 9 county services "
            "(+332.52 mi), PA 6 sources (+191.93 mi), Hubbard County MN "
            "fallback (+40.16 mi) — together +564.61 mi, lifting coverage "
            "from 63.7% to 75.6%. NY's 5 opt-out counties (267.39 mi) and "
            "MI's 17 no-source counties (807.90 mi) remain uncovered."),
        "total_features": len(out_features),
        "crossed": len(crossed),
        "adjoining": len(adjoining),
        "candidates_pulled": len(feats),
        "duplicates_deduped": dupes,
        "invalid_dropped": invalid,
        "candidates_per_state": per_state_raw,
        "counts_by_state_county_class": {
            "%s|%s|%s" % k: v for k, v in sorted(counts.items())},
        "covered_trail_miles": round(covered_miles, 2),
        "covered_counties": sorted("%s %s" % c for c in covered_counties),
        "county_mismatches_service_vs_tiger": len(county_mismatch),
        "county_mismatch_examples": county_mismatch[:10],
    }
    out_fc = {"type": "FeatureCollection", "metadata": metadata,
              "features": out_features}
    with open(OUT, "w") as fh:
        json.dump(out_fc, fh)
    print("wrote %s: %d features, %d bytes"
          % (OUT, len(out_features), os.path.getsize(OUT)), flush=True)
    print("covered trail miles: %.2f across %d counties"
          % (covered_miles, len(covered_counties)), flush=True)
    if county_mismatch:
        print("WARNING: %d county mismatches (service vs TIGER centroid)"
              % len(county_mismatch), flush=True)
    with open(LOG, "w") as fh:
        fh.write("# Parcels merge log — %s\n\n" % PULLED)
        fh.write("Candidates per state: %s\n\n"
                 % json.dumps(per_state_raw))
        fh.write("Crossed: %d; adjoining: %d; total features: %d\n\n"
                 % (len(crossed), len(adjoining), len(out_features)))
        fh.write("Covered trail miles: %.2f across %d counties\n\n"
                 % (covered_miles, len(covered_counties)))
        fh.write("Duplicates deduped: %d; invalid dropped: %d\n\n"
                 % (dupes, invalid))
        fh.write("County mismatches (service vs TIGER): %d\n\n"
                 % len(county_mismatch))
        for m in county_mismatch[:20]:
            fh.write("- %s\n" % (m,))
        fh.write("\nCounts by state|county|class:\n\n")
        for k in sorted(counts):
            fh.write("- %s|%s|%s: %d\n" % (k[0], k[1], k[2], counts[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
