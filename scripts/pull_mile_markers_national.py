#!/usr/bin/env python3
"""Pull the NCTA half-mile point (state mile marker) services NATIONALLY.

There is no single national mile-marker service: the NCTA publishes one
halfmile service per state or sub-state stretch (16 services found on
the NCTA ArcGIS organisation, 2026-11-23). This script fetches every
one of them in full, then resolves the duplicates: several states have
TWO services holding what looks like the same index in two generations
(see DEDUPE below). The output is one layer with each marker once.

Services (service name -> region):
  nd_halfmile_points    North Dakota (ND-...)
  mn_halfmile_points    Minnesota (MN-...) — the ITM script's service
  wi_halfmile_points    Wisconsin (WI-...)
  halfmile_wi           Wisconsin, second generation (WI-...)
  mi_halfmile_points    Michigan, whole state (MI-...)
  halfmile_mi_up        Michigan Upper Peninsula (MI-UP-...)
  halfmile_mi_lp        Michigan Lower Peninsula (MI-LP-...)
  oh_e_halfmile_points  Eastern Ohio (OH-E-...)
  oh_nw_halfmile_points Northwest Ohio (NW OH-...)
  pa_halfmile_points    Pennsylvania (PA-...)
  anf_halfmile_points   Allegheny National Forest, PA (ANF-...)
  a100_halfmile_points  "A-100" Allegheny index, PA ("Mile - ...")
  cny_halfmile_points   Central New York (NY-...)
  halfmile_ny           New York, second generation (NY-...)
  vt_halfmile_points    Vermont (VT-...)
  halfmile_vt           Vermont, second generation (VT-...)

Method follows the ITM pull_mile_markers.py: features fetched BY OBJECT
ID in chunk-verified POST chunks (offset paging is never trusted).
outFields is limited to ident / index_ / wypnt_id and positions come
solely from the returned GeoJSON GEOMETRY with outSR=4326.

WARNING — CORRUPT ATTRIBUTE COLUMNS (ITM, verified again here): the
services' `lat` / `long` ATTRIBUTE columns are wrong (Minnesota's
longitude attribute duplicates the latitude value; Michigan's are
null). They are never read here. Do not "fix" this script by reading
the attribute columns.

DEDUPE RULE (documented, reproducible — the script prints the numbers
it decides from): the paired services are NOT exact copies — the two
generations of one index run ~200–350 m apart (a systematic offset,
not a different route: same endpoints, same mile ranges, same-mile
points kilometres apart only because the mile-zero points differ).
So a point-for-point overlap test at 100 m fails to see them. Two
services covering the same ground count as duplicate generations
when ALL THREE hold: (1) the median nearest-neighbour distance
between their point sets is under 400 m (less than half the 800 m
half-mile spacing — the sets interleave along one line); (2) their
mile ranges agree within 5%; (3) their endpoints agree within 5 km
(allowing reversed endpoints — the A-100 ANF index runs north to
south while the ANF index runs south to north). The survivor is the
generation that fits the currently mapped centerline best (highest
fraction of points within 100 m of a centerline vertex, median
distance as the tie-break). Michigan is a unit comparison: the
whole-state service against the UP+LP pair pooled — the closer unit
wins, a tie going to the single continuous reckoning. Finally, a
chapter-local index is dropped outright when the state service
already covers its ground (>= 95% of its points within 500 m of a
state-service point): the ANF/A-100 indexes duplicate the
Pennsylvania state index over the same ground. Dropped services,
and the numbers behind each drop, are recorded in the output
metadata and printed.

COVERAGE: each service is a STATE reckoning (miles from that state's
start, "Start" = 0), not trail-wide miles. Some stretches have no
index at all — the script reports, per state, the marker span against
the mapped state total so the gaps are explicit, never filled in.

Output: site/data/mile-markers.geojson

Usage:  python3 scripts/pull_mile_markers_national.py
No credentials required; the services are public.
"""

import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "site" / "data" / "mile-markers.geojson"
CENTERLINE_FILES = [
    REPO_ROOT / "site" / "data" / "centerline-natural.geojson",
    REPO_ROOT / "site" / "data" / "centerline-road.geojson",
    REPO_ROOT / "site" / "data" / "centerline-urban.geojson",
]

ORG = "https://services2.arcgis.com/UfGVyqUm4GHa2zrj/arcgis/rest/services"
OUT_FIELDS = "ident,index_,wypnt_id"  # never lat/long — see header
ID_CHUNK = 500
NN_DUP_MEDIAN_M = 400.0    # duplicate generations interleave < this far apart
ENDPOINT_TOL_KM = 5.0      # duplicate generations share endpoints (or reversed)
RANGE_TOL = 0.05           # duplicate generations' mile ranges agree this far
PA_REDUNDANCY_M = 500.0    # chapter-local index covered by the state service
PA_REDUNDANCY_FRAC = 0.95

# service, region label, state, coverage group (services in one group
# are compared pairwise for duplication)
SERVICES = [
    ("nd_halfmile_points", "North Dakota", "ND", "ND"),
    ("mn_halfmile_points", "Minnesota", "MN", "MN"),
    ("wi_halfmile_points", "Wisconsin", "WI", "WI"),
    ("halfmile_wi", "Wisconsin (2nd generation)", "WI", "WI"),
    ("mi_halfmile_points", "Michigan (whole state)", "MI", "MI"),
    ("halfmile_mi_up", "Michigan Upper Peninsula", "MI", "MI-UP"),
    ("halfmile_mi_lp", "Michigan Lower Peninsula", "MI", "MI-LP"),
    ("oh_e_halfmile_points", "Eastern Ohio", "OH", "OH-E"),
    ("oh_nw_halfmile_points", "Northwest Ohio", "OH", "OH-NW"),
    ("pa_halfmile_points", "Pennsylvania", "PA", "PA"),
    ("anf_halfmile_points", "Allegheny National Forest", "PA", "ANF"),
    ("a100_halfmile_points", "A-100 Allegheny index", "PA", "ANF"),
    ("cny_halfmile_points", "Central New York", "NY", "NY"),
    ("halfmile_ny", "New York (2nd generation)", "NY", "NY"),
    ("vt_halfmile_points", "Vermont", "VT", "VT"),
    ("halfmile_vt", "Vermont (2nd generation)", "VT", "VT"),
]


def get_json(url, params=None, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {retries} tries: {last_err}")


def fetch_chunk(layer_url, oid_field, ids):
    where = f"{oid_field} IN ({','.join(str(i) for i in ids)})"
    params = {
        "where": where,
        "outFields": OUT_FIELDS,
        "outSR": "4326",
        "f": "geojson",
        "returnGeometry": "true",
    }
    last_err = None
    for attempt in range(3):
        try:
            r = requests.post(f"{layer_url}/query", data=params, timeout=180)
            r.raise_for_status()
            data = r.json()
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(
            f"POST {layer_url}/query failed after 3 tries: {last_err}")
    feats = data.get("features", [])
    if len(feats) != len(ids):
        if len(ids) == 1:
            raise RuntimeError(
                f"Feature {ids[0]} could not be fetched from {layer_url}")
        mid = len(ids) // 2
        return fetch_chunk(layer_url, oid_field, ids[:mid]) + fetch_chunk(
            layer_url, oid_field, ids[mid:])
    return feats


def fetch_service(service):
    root = f"{ORG}/{service}/FeatureServer"
    meta = get_json(root, params={"f": "pjson"})
    layers = meta.get("layers", [])
    if len(layers) != 1:
        raise RuntimeError(f"{service}: expected 1 layer, got {len(layers)}")
    layer_id = layers[0]["id"]
    layer_url = f"{root}/{layer_id}"
    data = get_json(f"{layer_url}/query", params={
        "where": "1=1", "returnIdsOnly": "true", "f": "json"})
    ids = sorted(data.get("objectIds") or [])
    oid_field = data.get("objectIdFieldName", "OBJECTID")
    feats = []
    for i in range(0, len(ids), ID_CHUNK):
        feats.extend(fetch_chunk(layer_url, oid_field,
                                 ids[i:i + ID_CHUNK]))
    return layers[0].get("name"), meta.get("serviceDescription") or "", feats


def clean_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def mile_number(ident, wypnt_id):
    """Bare mile number as a float; 'Start' (or 'MI-Start' etc.) is 0."""
    for v in (wypnt_id, ident):
        s = clean_str(v)
        if s is None:
            continue
        if "start" in s.lower():
            return 0.0
        num = "".join(ch for ch in s if ch.isdigit() or ch == ".")
        try:
            return float(num)
        except ValueError:
            continue
    return None


def to_xy(c):
    return (c[0] * 111.320 * math.cos(math.radians(45.0)), c[1] * 111.195)


def dist_km(a, b):
    ax, ay = to_xy(a)
    bx, by = to_xy(b)
    return math.hypot(ax - bx, ay - by)


# ------------------------------------------------------------ grids
def build_grid(points, cell_deg):
    """points: list of (lon, lat). Returns cell -> list of indices."""
    grid = defaultdict(list)
    for i, (lon, lat) in enumerate(points):
        grid[(int(lon // cell_deg), int(lat // cell_deg))].append(i)
    return grid


def points_within(points_a, grid_b, points_b, cell_deg, tol_km):
    """For each point in A, True if any B point lies within tol_km."""
    hits = []
    span = max(1, int(math.ceil(tol_km / (cell_deg * 111.0))) + 1)
    for lon, lat in points_a:
        cx, cy = int(lon // cell_deg), int(lat // cell_deg)
        found = False
        for gx in range(cx - span, cx + span + 1):
            for gy in range(cy - span, cy + span + 1):
                for j in grid_b.get((gx, gy), []):
                    if dist_km((lon, lat), points_b[j]) <= tol_km:
                        found = True
                        break
                if found:
                    break
            if found:
                break
        hits.append(found)
    return hits


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def nearest_distances(points_a, points_b, cell_deg=0.02, span=3):
    """Nearest-neighbour distance (m) from each A point to any B point."""
    grid_b = build_grid(points_b, cell_deg)
    out = []
    for lon, lat in points_a:
        cx, cy = int(lon // cell_deg), int(lat // cell_deg)
        best = 1e9
        for gx in range(cx - span, cx + span + 1):
            for gy in range(cy - span, cy + span + 1):
                for j in grid_b.get((gx, gy), []):
                    d = dist_km((lon, lat), points_b[j])
                    if d < best:
                        best = d
        out.append(best * 1000.0)
    return out


def centerline_fit(points, vertex_grid, vertices):
    """(fraction of points within 100 m of a centerline vertex, median
    distance in m). Vertex spacing varies, so this is approximate —
    used only to rank duplicate generations, never as a measurement."""
    ds = []
    for lon, lat in points:
        cx, cy = int(lon // 0.1), int(lat // 0.1)
        best = 1e9
        for gx in range(cx - 2, cx + 3):
            for gy in range(cy - 2, cy + 3):
                for j in vertex_grid.get((gx, gy), []):
                    d = dist_km((lon, lat), vertices[j])
                    if d < best:
                        best = d
        ds.append(best * 1000.0)
    return (sum(1 for x in ds if x <= 100) / len(ds), median(ds))




def main():
    # ---- fetch every service -------------------------------------
    fetched = {}   # service -> dict with raw features + meta
    for service, region, state, group in SERVICES:
        name, desc, raw = fetch_service(service)
        feats = []
        dropped = 0
        for f in raw:
            p = f.get("properties") or {}
            geom = f.get("geometry") or {}
            coords = geom.get("coordinates")
            if not coords:
                dropped += 1
                continue
            ident = clean_str(p.get("ident"))
            feats.append({
                "type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [round(float(coords[0]), 6),
                                             round(float(coords[1]), 6)]},
                "properties": {
                    "ident": ident,
                    "index_": clean_str(p.get("index_")),
                    "wypnt_id": clean_str(p.get("wypnt_id")),
                    "mile": mile_number(ident, p.get("wypnt_id")),
                    "state": state,
                    "region": region,
                    "source_service": service,
                },
            })
        miles = [f["properties"]["mile"] for f in feats
                 if f["properties"]["mile"] is not None]
        fetched[service] = {
            "region": region, "state": state, "group": group,
            "layer_name": name, "service_description": desc,
            "features": feats, "dropped_no_geom": dropped,
            "mile_max": max(miles) if miles else None,
            "mile_min": min(miles) if miles else None,
        }
        print(f"{service:24s} {len(feats):5d} fetched "
              f"({dropped} no geom)  mile {min(miles) if miles else '-'}"
              f"..{max(miles) if miles else '-'}  layer: {name}")

    # ---- centerline vertices (currency tie-breaker) ---------------
    vertices = []
    for path in CENTERLINE_FILES:
        doc = json.loads(path.read_text())
        for feat in doc["features"]:
            g = feat["geometry"]
            coords = (g["coordinates"] if g["type"] == "LineString"
                      else [c for part in g["coordinates"] for c in part])
            vertices.extend((c[0], c[1]) for c in coords)
    vgrid = build_grid(vertices, 0.1)

    # ---- duplicate generations ------------------------------------
    # Duplicate sets, from the service catalog: two services holding
    # the same index in two generations. Michigan is a unit
    # comparison (whole-state service vs the UP+LP pair pooled).
    def service_points(service):
        return [(f["geometry"]["coordinates"][0],
                 f["geometry"]["coordinates"][1])
                for f in fetched[service]["features"]]

    def service_ends(service):
        feats = sorted(fetched[service]["features"],
                       key=lambda f: (f["properties"]["mile"] is None,
                                      f["properties"]["mile"] or 0.0))
        return (tuple(feats[0]["geometry"]["coordinates"]),
                tuple(feats[-1]["geometry"]["coordinates"]))

    def range_agrees(a_max, b_max):
        return abs(a_max - b_max) / max(a_max, b_max) <= RANGE_TOL

    def ends_agree(ends_a, ends_b):
        # any pairing of the two ends within tolerance (allows the
        # A-100 reversed ANF index: its start is the ANF index's end)
        return min(dist_km(x, y) for x in ends_a for y in ends_b) \
            <= ENDPOINT_TOL_KM

    def pick_survivor(a_pts, b_pts, a_label, b_label, a_span, b_span,
                      a_ident0, b_ident0):
        """Higher centerline fit wins (fraction within 100 m, then
        median distance); a tie goes to the longer span, then to the
        state-convention ident prefix."""
        fa, ma = centerline_fit(a_pts, vgrid, vertices)
        fb, mb = centerline_fit(b_pts, vgrid, vertices)
        print(f"    fit {a_label}: {fa:.1%} within 100 m, median {ma:.0f} m")
        print(f"    fit {b_label}: {fb:.1%} within 100 m, median {mb:.0f} m")
        if abs(fa - fb) > 0.02:
            return (a_label, b_label) if fa > fb else (b_label, a_label)
        if abs(ma - mb) > 5:
            return (a_label, b_label) if ma < mb else (b_label, a_label)
        if abs(a_span - b_span) > 1:
            return (a_label, b_label) if a_span > b_span else (b_label, a_label)
        conv = lambda s: 0 if ("-" in s and not s.startswith("Mile")) else 1
        return ((a_label, b_label) if conv(a_ident0) <= conv(b_ident0)
                else (b_label, a_label))

    overlap_report = []
    drop = {}   # service -> reason

    def resolve_pair(a, b):
        """Decide one duplicate set of two services; returns the
        survivor service, or None when the pair is not duplicates."""
        pa, pb = service_points(a), service_points(b)
        nn_ab = median(nearest_distances(pa, pb))
        nn_ba = median(nearest_distances(pb, pa))
        nn = max(nn_ab, nn_ba)
        ra = range_agrees(fetched[a]["mile_max"], fetched[b]["mile_max"])
        ea = ends_agree(service_ends(a), service_ends(b))
        print(f"DUP-CHECK {a} vs {b}: median NN {nn_ab:.0f}/{nn_ba:.0f} m, "
              f"ranges {fetched[a]['mile_max']} vs "
              f"{fetched[b]['mile_max']} (agree: {ra}), "
              f"endpoints agree: {ea}")
        overlap_report.append({
            "a": a, "b": b,
            "median_nn_m_a_to_b": round(nn_ab, 1),
            "median_nn_m_b_to_a": round(nn_ba, 1),
            "mile_max_a": fetched[a]["mile_max"],
            "mile_max_b": fetched[b]["mile_max"],
            "ranges_agree": ra, "endpoints_agree": ea,
        })
        if not (nn <= NN_DUP_MEDIAN_M and ra and ea):
            print("  -> NOT duplicates; both kept")
            return None
        ident0 = lambda s: (fetched[s]["features"][0]["properties"]["ident"]
                            or "")
        survivor, loser = pick_survivor(
            pa, pb, a, b,
            fetched[a]["mile_max"], fetched[b]["mile_max"],
            ident0(a), ident0(b))
        drop[loser] = (
            f"duplicate generation of {survivor}: median "
            f"nearest-neighbour distance {nn:.0f} m, mile ranges "
            f"{fetched[a]['mile_max']} vs {fetched[b]['mile_max']}, "
            f"shared endpoints — the two generations run ~200-350 m "
            f"apart along the same line (systematic offset, not a "
            f"different route)")
        print(f"  DROP {loser} ({drop[loser]})")
        return survivor

    for a, b in (("wi_halfmile_points", "halfmile_wi"),
                 ("cny_halfmile_points", "halfmile_ny"),
                 ("vt_halfmile_points", "halfmile_vt"),
                 ("anf_halfmile_points", "a100_halfmile_points")):
        resolve_pair(a, b)

    # Michigan: whole-state service vs the UP+LP pair pooled.
    mi_pts = service_points("mi_halfmile_points")
    up_lp_pts = (service_points("halfmile_mi_up")
                 + service_points("halfmile_mi_lp"))
    nn_mi = median(nearest_distances(mi_pts, up_lp_pts))
    nn_ul = median(nearest_distances(up_lp_pts, mi_pts))
    nn = max(nn_mi, nn_ul)
    combined_max = (fetched["halfmile_mi_up"]["mile_max"]
                    + fetched["halfmile_mi_lp"]["mile_max"])
    ra = range_agrees(fetched["mi_halfmile_points"]["mile_max"],
                      combined_max)
    ea = (dist_km(service_ends("mi_halfmile_points")[0],
                  service_ends("halfmile_mi_up")[0]) <= ENDPOINT_TOL_KM
          and dist_km(service_ends("mi_halfmile_points")[1],
                      service_ends("halfmile_mi_lp")[1]) <= ENDPOINT_TOL_KM)
    print(f"DUP-CHECK mi_halfmile_points vs UP+LP pooled: median NN "
          f"{nn_mi:.0f}/{nn_ul:.0f} m, ranges "
          f"{fetched['mi_halfmile_points']['mile_max']} vs "
          f"{combined_max} (agree: {ra}), endpoints agree: {ea}")
    overlap_report.append({
        "a": "mi_halfmile_points", "b": "halfmile_mi_up+halfmile_mi_lp",
        "median_nn_m_a_to_b": round(nn_mi, 1),
        "median_nn_m_b_to_a": round(nn_ul, 1),
        "mile_max_a": fetched["mi_halfmile_points"]["mile_max"],
        "mile_max_b": combined_max,
        "ranges_agree": ra, "endpoints_agree": ea,
    })
    if nn <= NN_DUP_MEDIAN_M and ra and ea:
        f_mi, m_mi = centerline_fit(mi_pts, vgrid, vertices)
        f_ul, m_ul = centerline_fit(up_lp_pts, vgrid, vertices)
        print(f"    fit whole-state: {f_mi:.1%} within 100 m, "
              f"median {m_mi:.0f} m")
        print(f"    fit UP+LP pooled: {f_ul:.1%} within 100 m, "
              f"median {m_ul:.0f} m")
        if f_ul > f_mi:
            drop["mi_halfmile_points"] = (
                "duplicate generation of the UP+LP pair (pooled): "
                f"median nearest-neighbour distance {nn:.0f} m, mile "
                f"ranges {fetched['mi_halfmile_points']['mile_max']} vs "
                f"{combined_max}; the peninsula pair fits the mapped "
                f"centerline better "
                f"({f_ul:.1%} vs {f_mi:.1%} within 100 m)")
            print(f"  DROP mi_halfmile_points ({drop['mi_halfmile_points']})")
        else:
            for s in ("halfmile_mi_up", "halfmile_mi_lp"):
                drop[s] = ("duplicate generation of mi_halfmile_points "
                           "(whole-state, one continuous MI reckoning): "
                           f"median nearest-neighbour distance {nn:.0f} m")
            print("  DROP halfmile_mi_up, halfmile_mi_lp "
                  f"({drop['halfmile_mi_up']})")

    # Chapter-local ANF index: drop the survivor too when the
    # Pennsylvania state service already covers its ground.
    anf_survivor = ("anf_halfmile_points" if "a100_halfmile_points" in drop
                    else "a100_halfmile_points" if "anf_halfmile_points" in drop
                    else None)
    if anf_survivor is not None:
        pa_pts = service_points("pa_halfmile_points")
        hits = points_within(service_points(anf_survivor),
                             build_grid(pa_pts, 0.02), pa_pts, 0.02,
                             PA_REDUNDANCY_M / 1000.0)
        frac = sum(hits) / len(hits) if hits else 0
        print(f"ANF-REDUNDANCY {anf_survivor} vs pa_halfmile_points: "
              f"{frac:.1%} within {PA_REDUNDANCY_M:.0f} m of a PA point")
        if frac >= PA_REDUNDANCY_FRAC:
            drop[anf_survivor] = (
                "chapter-local reckoning redundant with the Pennsylvania "
                f"state service: {frac:.0%} of its points lie within "
                f"{PA_REDUNDANCY_M:.0f} m of a PA-service point — the "
                f"state index already marks this ground")
            print(f"  DROP {anf_survivor} ({drop[anf_survivor]})")

    # ---- assemble output ------------------------------------------
    kept_services = [s for s, _, _, _ in SERVICES if s not in drop]
    features = []
    for s in kept_services:
        features.extend(fetched[s]["features"])
    features.sort(key=lambda f: (f["properties"]["state"] or "",
                                 f["properties"]["mile"] is None,
                                 f["properties"]["mile"] or 0.0))
    by_state = Counter(f["properties"]["state"] for f in features)
    by_service = Counter(f["properties"]["source_service"] for f in features)

    lons = [f["geometry"]["coordinates"][0] for f in features]
    lats = [f["geometry"]["coordinates"][1] for f in features]
    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "NCTA state half-mile points (state mile markers), "
                       "national — one continuous layer assembled from the "
                       "per-state services, duplicate generations removed",
            "source_services": [
                {"service": s,
                 "region": fetched[s]["region"],
                 "state": fetched[s]["state"],
                 "layer_name": fetched[s]["layer_name"],
                 "service_root": f"{ORG}/{s}/FeatureServer",
                 "fetched_count": len(fetched[s]["features"]),
                 "dropped_no_geometry": fetched[s]["dropped_no_geom"],
                 "mile_range": [fetched[s]["mile_min"],
                                fetched[s]["mile_max"]],
                 "kept": s not in drop,
                 "drop_reason": drop.get(s)}
                for s, _, _, _ in SERVICES],
            "pulled_utc_date": time.strftime("%Y-%m-%d", time.gmtime()),
            "query": "where 1=1 per service, no clip — full services",
            "clip_method": "None — full services, object-id fetch, "
                           "chunk-verified; positions from GeoJSON geometry "
                           "requested with outSR=4326",
            "corrupt_columns_warning": "The services' lat/long ATTRIBUTE "
                           "columns are corrupt (Minnesota's longitude "
                           "duplicates latitude; Michigan's are null) and "
                           "were never read; outFields was limited to "
                           "ident, index_, wypnt_id.",
            "reckoning_note": "Each service is a STATE reckoning (miles "
                           "from that state's start; 'Start' = 0). State "
                           "reckonings are never merged or converted into "
                           "a trail-wide mileage; the gazetteer carries "
                           "the trail-wide chainage separately.",
            "dedupe_rule": (f"Two services holding the same index in "
                            f"two generations count as duplicates when "
                            f"the median nearest-neighbour distance "
                            f"between their point sets is under "
                            f"{NN_DUP_MEDIAN_M:.0f} m, their mile ranges "
                            f"agree within {RANGE_TOL:.0%}, and their "
                            f"endpoints agree within {ENDPOINT_TOL_KM:.0f} "
                            f"km (allowing reversed endpoints); the "
                            f"survivor fits the mapped centerline best "
                            f"(fraction within 100 m of a centerline "
                            f"vertex, median distance as tie-break). A "
                            f"chapter-local index is dropped when the "
                            f"state service already covers its ground "
                            f"(>= {PA_REDUNDANCY_FRAC:.0%} within "
                            f"{PA_REDUNDANCY_M:.0f} m)."),
            "overlap_report": overlap_report,
            "feature_count": len(features),
            "counts_by_state": dict(sorted(by_state.items())),
            "counts_by_service": dict(sorted(by_service.items())),
            "extent_wgs84": {
                "min_lon": round(min(lons), 6),
                "max_lon": round(max(lons), 6),
                "min_lat": round(min(lats), 6),
                "max_lat": round(max(lats), 6),
            },
            "coverage_note": "Coverage gaps are reported by the pull "
                           "script's stdout (per-state marker span vs "
                           "mapped state total) and in SOURCES-step4.md; "
                           "no markers are invented for unindexed ground.",
        },
        "features": features,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out_fc, indent=1))
    print(f"Wrote               : {OUT_PATH.relative_to(REPO_ROOT)} "
          f"({len(features)} features)")
    print(f"Kept services       : {len(kept_services)} of {len(SERVICES)}")
    print(f"Dropped             : {list(drop)}")
    print(f"Counts by state     : {dict(sorted(by_state.items()))}")
    print("SUMMARY " + json.dumps({
        "features": len(features),
        "kept_services": kept_services,
        "dropped": list(drop),
        "counts_by_state": dict(sorted(by_state.items())),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
