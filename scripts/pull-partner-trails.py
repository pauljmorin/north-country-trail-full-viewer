#!/usr/bin/env python3
"""Pull the concurrent / partner trails for the NCT full viewer (plan step 5).

One script, per-trail functions. Adapted from the Itasca Moraine chapter
viewer's pull scripts (read-only templates):
  - pull-sht.py            (SHT, MN DNR State Park Trails service)
  - pull-brt.py            (BRT, USFS National Forest System Trails)
  - pull-bwca-portages.py  (BWCAW portages, same USFS service)
  - pull-near-brt-sht.py   (named trails near the BRT/SHT, same service)
  - pull-driftless.py      (Driftless Hiking Trail, OSM ways + traced loop)
  - harvest_mesabi_osm.py  (OSM API fetch pattern: Nominatim/OSM API,
                            because Overpass is unreachable from this VM:
                            HTTP 406 on overpass-api.de, timeout on
                            overpass.kumi.systems, 2026-11-23)

New trails (hunted 2026-11-23; no ITM template existed):
  - Buckeye Trail:      OSM super-relation 1738661 (28 section relations,
                        4,495 ways) — longhikes.org/trails/buckeye/ and
                        wiki.openstreetmap.org/wiki/Ohio/Route_relations/Trails
  - Finger Lakes Trail: OSM region relations 12725656 (Allegany),
                        12725657 (Western Finger Lakes), 12725658 (Eastern
                        Finger Lakes), 12725661 (Catskill) —
                        longhikes.org/trails/finger-lakes/
  - Long Trail:         OSM relation 391736 (153 ways, Green Mountain Club)
                        — longhikes.org/trails/long-trail/

Output: site/data/partner-trails.geojson — ONE file, one feature per
chained OSM line or per source segment, with normalized properties:
  trail                 group name (e.g. "Buckeye Trail")
  name                  segment / trail name as the source carries it
  source                short source label
  source_url            relation / service URL
  length_mi             geodesic miles on WGS84 (pyproj Geod)
  concurrent_with_nct   true when >=50% of the feature's LENGTH lies
                        within 50 m of the NCT centerline (same 50 m
                        tolerance the ITM viewer and the Mesabi overlap
                        measurement used); concurrent_miles gives the
                        exact length within 50 m, so a long trail that
                        shares only its end (e.g. the Long Trail) is
                        not hidden by a whole-feature flag
  pct_within_50m        the measured share, for audit
  source_id             objectid / OSM relation id, as applicable

Raw pulls are kept in --workdir (default
~/workspace/nct-step5-work/partner-raw/) so the repo carries only the
script and the merged output; re-running the script re-pulls everything
live and rebuilds the merged file.

Usage: python3 scripts/pull-partner-trails.py [--workdir DIR] [--skip-fetch]
  --skip-fetch reuses the raw pulls already in --workdir (merge only).
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

import numpy as np
import requests
from pyproj import Geod, Transformer
from shapely import transform as shp_xform
from shapely.geometry import LineString, MultiLineString, shape
from shapely.strtree import STRtree

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DATA = os.path.join(REPO, "site", "data")
PULLED = time.strftime("%Y-%m-%d", time.gmtime())
UA = {"User-Agent": "Mozilla/5.0 (nct-viewer data pull; contact: pauljmorin@gmail.com)"}
GEOD = Geod(ellps="WGS84")

# ---------------------------------------------------------------- services
DNR_PARK_FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
               "us_mn_state_dnr/trans_state_park_trails_roads/FeatureServer/0")
TRAILNFS = ("https://apps.fs.usda.gov/arcx/rest/services/EDW/"
            "EDW_TrailNFSPublish_01/MapServer/0")
ENV_MN = {"xmin": -96.8, "ymin": 46.2, "xmax": -89.85, "ymax": 48.15,
          "spatialReference": {"wkid": 4326}}

BWCA_NAMES = [
    "AGAMOK-MUELLER", "BORDER ROUTE CONNECTOR",
    "BRT-CLEARWATER LK CAMPSITE TRL", "BRT-PARTIDGE CAMPSITE",
    "BRT-SOCK LAKE CAMPSITE", "TOPPER LAKE CAMPSITE SPUR",
    "CLEARWATER-WEST PIKE", "CLEARWATER/DANIELS LAKE",
    "CRAB LAKE CUT-OFF", "CRAB LAKE-MAIN BRT",
    "FAY-WARCLUB", "GLEE-BINGSHICK", "GLEE-FAY",
    "HATCHET CREEK-HATCHET POND", "KOBE-THOMAS",
    "MOUNTAIN-CLEARWATER", "ROSE-DUNCAN", "ROSE-ROVE",
    "SOUTH LAKE", "SOUTH LAKE-TOPPER LAKE",
    "WARCLUB-SEAHORSE", "WEST PIKE-PINE", "WOOD LAKE",
    "SOURDOUGH CREEK", "FERNBERG AREA", "KEKEKABIC-STRUP",
]
NEAR_NAMES = [
    "KEKEKABIC", "SNOWBANK", "OLD PINES LOOP",
    "BENEZIE-BECOOSIN LOOP", "MAGNETIC ROCK", "CARIBOU ROCK",
    "BRIDAL VEIL FALLS", "BRYCE BREON", "CENTENNIAL",
    "GUNFLINT LOOKOUT", "KEKEKABIC TO MAGNETIC ROCK",
    "UPPER GUNFLINT WEST END", "UPPER GUNFLINT SOUTH RIM",
    "UPPER GUNFLINT OVERLOOK", "UPPER GUNFLINT CUT ACROSS",
    "UPPER GUNFLINT ASPEN RABBIT", "UPPER GUNFLINT POWER LINE",
    "UPPER GUNFLINT LONELY LAKE", "UPPER GUNFLINT SHORT CUT",
    "UPPER GUNFLINT WARRENS ROAD", "GUNFLINT LAKE G CONNECT",
    "SOUTH FOWL ATV", "SOUTH FOWL SNOWMOBILE",
    "THOMAS LAKE WINTER", "THIRTEEN CORNERS", "MADDEN WINTER",
    "HIDDEN VALLEY TREZONA", "TREZONA",
]

# OSM route relations: trail -> list of (relation id, section label)
OSM_TRAILS = {
    "Buckeye Trail": [
        (1738661, "super-relation (28 section relations)"),
    ],
    "Finger Lakes Trail": [
        (12725656, "Allegany"), (12725657, "Western Finger Lakes"),
        (12725658, "Eastern Finger Lakes"), (12725661, "Catskill"),
    ],
    "Long Trail": [
        (391736, "main"),
    ],
}
# Driftless Hiking Trail: OSM ways + the traced Welsh Hills outer loop
# (ITM data/driftless/driftless-traced-welsh-phoebe.geojson — read, not copied
# into this repo; the pull script reads it as an input file).
DRIFTLESS_WAYS = {
    "1248941083": "Phoebe Point Trail",
    "1248943005": "Welsh Hills Trail (inner chord)",
    "1248953013": "Knobs Road Trail",
}
DRIFTLESS_TRACED = ("/home/hatch/workspace/itasca-trail-map/data/driftless/"
                    "driftless-traced-welsh-phoebe.geojson")

# Relations to skip when recursing: the Finger Lakes Trail's two spur
# relations (Lick Brook, Buttermilk Falls) are alternates, not the main
# track (longhikes.org/trails/finger-lakes/ puts them in alternates).
EXCLUDE_RELATIONS = {11285670, 11285669}

OSM_API = "https://www.openstreetmap.org/api/0.6"


def fetch_json(url, params=None, retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError("GET %s failed: %s" % (url, last))


def fetch_text(url, retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=300)
            r.raise_for_status()
            return r.content
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError("GET %s failed: %s" % (url, last))


# ---------------------------------------------------------------- ArcGIS
def arcgis_query(layer_url, where, extra_params=None):
    params = {
        "where": where,
        "geometry": json.dumps(ENV_MN),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "outSR": "4326",
        "returnGeometry": "true",
        "f": "geojson",
    }
    if extra_params:
        params.update(extra_params)
    return fetch_json(layer_url + "/query", params).get("features", [])


def pull_sht(workdir):
    """Superior Hiking Trail from the MN DNR park-trails service (two-pass,
    as in ITM pull-sht.py: the id list first, then by objectIds)."""
    ids = fetch_json(DNR_PARK_FS + "/query?" + urllib.parse.urlencode({
        "where": "1=1", "geometry": json.dumps(ENV_MN),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "returnIdsOnly": "true", "f": "json",
    })).get("objectIds", [])
    print("SHT: %d features in DNR envelope" % len(ids))
    raw = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        raw.extend(fetch_json(DNR_PARK_FS + "/query?" + urllib.parse.urlencode({
            "objectIds": ",".join(str(x) for x in chunk),
            "outFields": "*", "outSR": "4326",
            "returnGeometry": "true", "f": "geojson",
        })).get("features", []))
    sht = [f for f in raw
           if (f.get("properties") or {}).get("trail_name") == "Superior Hiking Trail"]
    path = os.path.join(workdir, "sht-raw.geojson")
    json.dump({"type": "FeatureCollection", "features": sht}, open(path, "w"))
    print("SHT: %d features -> %s" % (len(sht), path))
    return sht


def pull_trailnfs(workdir, names, stem, label):
    where = "trail_name IN ('" + "','".join(names) + "')"
    feats = arcgis_query(TRAILNFS, where)
    path = os.path.join(workdir, stem + "-raw.geojson")
    json.dump({"type": "FeatureCollection", "features": feats}, open(path, "w"))
    from collections import Counter
    print("%s: %d features -> %s" % (label, len(feats), path))
    print("  names present: %s"
          % dict(Counter((f.get("properties") or {}).get("trail_name")
                         for f in feats)))
    return feats


# ---------------------------------------------------------------- OSM API
def osm_get(path):
    """One OSM API GET, with a 1 s politeness pause (Nominatim/OSM API
    usage policy). Returns raw bytes."""
    time.sleep(1.0)
    return fetch_text(OSM_API + path)


def parse_osm_xml(data):
    """Parse an OSM XML document (relation/full or way/full) into
    (nodes, ways, relations): nodes id->(lon,lat), ways id->(nd list, tags),
    relations id->(members, tags)."""
    root = ET.fromstring(data)
    nodes, ways, rels = {}, {}, {}
    for el in root:
        if el.tag == "node":
            nodes[int(el.get("id"))] = (float(el.get("lon")), float(el.get("lat")))
        elif el.tag == "way":
            tags = {c.get("k"): c.get("v") for c in el if c.tag == "tag"}
            nds = [int(c.get("ref")) for c in el if c.tag == "nd"]
            ways[int(el.get("id"))] = (nds, tags)
        elif el.tag == "relation":
            tags = {c.get("k"): c.get("v") for c in el if c.tag == "tag"}
            members = [(c.get("type"), int(c.get("ref")), c.get("role"))
                       for c in el if c.tag == "member"]
            rels[int(el.get("id"))] = (members, tags)
    return nodes, ways, rels


def collect_relation_ways(rel_id, nodes, ways, seen_rels, depth=0):
    """Recursively collect all member ways of a route relation (the Buckeye
    super-relation holds section relations, not ways). Returns the list of
    way ids found under this relation."""
    if rel_id in seen_rels or depth > 4:
        return []
    if rel_id in EXCLUDE_RELATIONS:
        print("  relation %d: EXCLUDED (spur / alternate, not the main track)"
              % rel_id)
        return []
    seen_rels.add(rel_id)
    data = osm_get("/relation/%d/full" % rel_id)
    n2, w2, r2 = parse_osm_xml(data)
    nodes.update(n2)
    ways.update(w2)
    members, tags = r2.get(rel_id, ([], {}))
    found = []
    for mtype, ref, role in members:
        if mtype == "way":
            if ref in ways:
                found.append(ref)
        elif mtype == "relation":
            found.extend(collect_relation_ways(ref, nodes, ways, seen_rels, depth + 1))
    print("  relation %d (%s): %d member ways, %d sub-relations, "
          "name=%r" % (rel_id, tags.get("name"), len(found),
                       sum(1 for m in members if m[0] == "relation"),
                       tags.get("name")))
    return found


def chain_ways(way_ids, ways, nodes):
    """Chain OSM ways end-to-end (by shared endpoint node id) into
    LineString coordinate lists. A junction (endpoint shared by >1 unused
    way) ends a chain; closed loops stay whole. Returns a list of
    coordinate lists."""
    # endpoint node -> set of way ids touching it at an end
    endpoint = {}
    for wid in way_ids:
        nds, _ = ways[wid]
        if len(nds) < 2:
            continue
        for end in (nds[0], nds[-1]):
            endpoint.setdefault(end, set()).add(wid)
    unused = set(w for w in way_ids if len(ways[w][0]) >= 2)
    chains = []
    while unused:
        start = next(iter(unused))
        unused.discard(start)
        nds = list(ways[start][0])
        # extend forward
        while True:
            cands = [w for w in endpoint.get(nds[-1], set()) if w in unused]
            if len(cands) != 1:
                break
            w = cands[0]
            unused.discard(w)
            wnds = ways[w][0]
            nds.extend(wnds[1:] if wnds[0] == nds[-1] else list(reversed(wnds))[1:])
        # extend backward
        while True:
            cands = [w for w in endpoint.get(nds[0], set()) if w in unused]
            if len(cands) != 1:
                break
            w = cands[0]
            unused.discard(w)
            wnds = ways[w][0]
            nds = (wnds[:-1] if wnds[-1] == nds[0]
                   else list(reversed(wnds))[:-1]) + nds
        coords = [nodes[n] for n in nds if n in nodes]
        if len(coords) >= 2:
            chains.append(coords)
    return chains


def pull_osm_trail(workdir, trail, rels):
    """Fetch a trail's OSM route relation(s) and chain the member ways."""
    nodes, ways = {}, {}
    all_way_ids = []
    for rel_id, section in rels:
        print("%s: relation %d (%s)" % (trail, rel_id, section))
        found = collect_relation_ways(rel_id, nodes, ways, set())
        all_way_ids.extend(found)
        print("  cumulative ways: %d, nodes: %d" % (len(all_way_ids), len(nodes)))
    chains = chain_ways(sorted(set(all_way_ids)), ways, nodes)
    print("%s: %d ways -> %d chained lines, %d nodes"
          % (trail, len(set(all_way_ids)), len(chains), len(nodes)))
    feats = []
    for coords in chains:
        feats.append({
            "type": "Feature",
            "properties": {"osm_way_count": len(coords)},
            "geometry": {"type": "LineString",
                         "coordinates": [[round(a, 6), round(b, 6)]
                                         for a, b in coords]},
        })
    path = os.path.join(workdir, trail.lower().replace(" ", "-") + "-osm.geojson")
    json.dump({"type": "FeatureCollection",
               "metadata": {"trail": trail, "relations": [r for r, _ in rels],
                            "ways": len(set(all_way_ids)), "nodes": len(nodes),
                            "pulled_utc_date": PULLED},
               "features": feats}, open(path, "w"))
    print("%s: wrote %s (%d features)" % (trail, path, len(feats)))
    return feats


def pull_driftless(workdir):
    """Driftless Hiking Trail: the three OSM ways (as in ITM
    pull-driftless.py) plus the traced Welsh Hills outer loop, read from
    the ITM working file (input only — this repo does not edit ITM)."""
    feats = []
    for wid, name in DRIFTLESS_WAYS.items():
        data = osm_get("/way/%s/full" % wid)
        nodes, ways, _ = parse_osm_xml(data)
        nds, tags = ways[int(wid)]
        coords = [nodes[n] for n in nds if n in nodes]
        print("Driftless %s (way %s): %d pts" % (name, wid, len(coords)))
        feats.append({
            "type": "Feature",
            "properties": {"name": name, "osm_way_id": int(wid)},
            "geometry": {"type": "LineString",
                         "coordinates": [[round(a, 6), round(b, 6)]
                                         for a, b in coords]},
        })
    if os.path.exists(DRIFTLESS_TRACED):
        traced = json.load(open(DRIFTLESS_TRACED))
        for f in traced["features"]:
            print("Driftless traced: %s, %.3f mi"
                  % (f["properties"].get("name"),
                     f["properties"].get("length_mi", 0)))
            feats.append(f)
    else:
        print("WARNING: traced loop file missing: %s" % DRIFTLESS_TRACED)
    path = os.path.join(workdir, "driftless-osm.geojson")
    json.dump({"type": "FeatureCollection", "features": feats}, open(path, "w"))
    print("Driftless: wrote %s (%d features)" % (path, len(feats)))
    return feats


# ---------------------------------------------------------------- measure
def geodesic_miles(geom):
    """Geodesic miles of a GeoJSON LineString/MultiLineString on WGS84."""
    total = 0.0
    if geom["type"] == "LineString":
        lines = [geom["coordinates"]]
    elif geom["type"] == "MultiLineString":
        lines = geom["coordinates"]
    else:
        return 0.0
    for line in lines:
        if len(line) < 2:
            continue
        lons = [c[0] for c in line]
        lats = [c[1] for c in line]
        total += GEOD.line_length(lons, lats) / 1609.344
    return total


class CenterlineIndex:
    """NCT centerline segments in a lon/lat STRtree, for the 50 m
    concurrency check. Distances are measured per feature in the UTM
    zone of the feature centroid."""

    def __init__(self):
        segs = []
        for name in ("centerline-natural", "centerline-road", "centerline-urban"):
            path = os.path.join(SITE_DATA, name + ".geojson")
            d = json.load(open(path))
            for f in d["features"]:
                g = shape(f["geometry"])
                if g.geom_type == "LineString":
                    segs.append(g)
                elif g.geom_type == "MultiLineString":
                    segs.extend(list(g.geoms))
        self.tree = STRtree(segs)
        self.segs = segs
        print("centerline index: %d segments" % len(segs))

    def concurrent(self, geom):
        """Length-based concurrency: geodesic miles of the feature within
        50 m of the NCT centerline, measured in the UTM zone of the
        feature centroid, plus the minimum distance (m) from the feature
        to the centerline. Returns (miles_within_50m, min_distance_m).
        The 50 m tolerance matches the ITM viewer and the Mesabi
        overlap measurement. (An earlier vertex-fraction version of
        this check overstated overlap on the long chained OSM lines —
        e.g. it gave the Long Trail 0 concurrent miles while 23.66 mi
        of it lie within 50 m — so the length measure is the one kept.)"""
        g = shape(geom)
        if g.is_empty:
            return 0.0, None
        coords = []
        if g.geom_type == "LineString":
            coords = list(g.coords)
        elif g.geom_type == "MultiLineString":
            for part in g.geoms:
                coords.extend(list(part.coords))
        if not coords:
            return 0.0, None
        cx = sum(c[0] for c in coords) / len(coords)
        cy = sum(c[1] for c in coords) / len(coords)
        zone = int((cx + 180.0) / 6.0) + 1
        tr = Transformer.from_crs("EPSG:4326", "EPSG:326%02d" % zone,
                                  always_xy=True)
        back = Transformer.from_crs("EPSG:326%02d" % zone, "EPSG:4326",
                                    always_xy=True)

        def xf(c):
            xs, ys = tr.transform(c[:, 0], c[:, 1])
            return np.column_stack([xs, ys])

        def bxf(c):
            xs, ys = back.transform(c[:, 0], c[:, 1])
            return np.column_stack([xs, ys])

        from shapely.geometry import box as shapely_box
        minx = min(c[0] for c in coords) - 0.05
        maxx = max(c[0] for c in coords) + 0.05
        miny = min(c[1] for c in coords) - 0.05
        maxy = max(c[1] for c in coords) + 0.05
        cand_idx = self.tree.query(shapely_box(minx, miny, maxx, maxy))
        if len(cand_idx) == 0:
            return 0.0, None
        cand_utm = [shp_xform(self.segs[i], xf) for i in cand_idx]
        from shapely.ops import unary_union as shp_union
        cl_utm = shp_union(cand_utm)
        g_utm = shp_xform(g, xf)
        mind = g_utm.distance(cl_utm)
        inter = g_utm.intersection(cl_utm.buffer(50.0))
        if inter.is_empty:
            return 0.0, round(mind, 1)
        return round(geodesic_miles(json.loads(
            json.dumps(shp_xform(inter, bxf).__geo_interface__))), 3), \
            round(mind, 1)


def normalize(trail, name, source, source_url, geom, source_id, idx):
    mi = geodesic_miles(geom)
    conc_mi, mind = idx.concurrent(geom)
    return {
        "type": "Feature",
        "properties": {
            "trail": trail,
            "name": name,
            "source": source,
            "source_url": source_url,
            "length_mi": round(mi, 3),
            "concurrent_with_nct": bool(mi > 0 and conc_mi / mi >= 0.5),
            "concurrent_miles": conc_mi,
            "concurrent_pct": round(100.0 * conc_mi / mi, 1) if mi > 0 else 0.0,
            "min_distance_m": mind,
            "source_id": source_id,
        },
        "geometry": geom,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.path.expanduser(
        "~/workspace/nct-step5-work/partner-raw"))
    ap.add_argument("--skip-fetch", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.workdir, exist_ok=True)
    os.makedirs(SITE_DATA, exist_ok=True)

    def load_raw(stem):
        return json.load(open(os.path.join(args.workdir, stem)))["features"]

    groups = []  # (trail, [(name, source, source_url, geom, source_id)])

    # --- Superior Hiking Trail (MN DNR) ---
    if args.skip_fetch:
        sht = load_raw("sht-raw.geojson")
    else:
        sht = pull_sht(args.workdir)
    groups.append(("Superior Hiking Trail", [
        ((f.get("properties") or {}).get("trail_name") or "Superior Hiking Trail",
         "Minnesota DNR State Park Trails and Roads",
         DNR_PARK_FS, f["geometry"],
         (f.get("properties") or {}).get("objectid"))
        for f in sht if f.get("geometry")]))

    # --- Border Route Trail (USFS TrailNFS) ---
    if args.skip_fetch:
        brt = load_raw("brt-raw.geojson")
    else:
        brt = pull_trailnfs(args.workdir, ["BORDER ROUTE"], "brt", "BRT")
    groups.append(("Border Route Trail", [
        ((f.get("properties") or {}).get("trail_name") or "BORDER ROUTE",
         "USDA Forest Service National Forest System Trails (EDW_TrailNFSPublish_01)",
         TRAILNFS, f["geometry"],
         (f.get("properties") or {}).get("objectid"))
        for f in brt if f.get("geometry")]))

    # --- BWCAW portages (USFS TrailNFS) ---
    if args.skip_fetch:
        bwca = load_raw("bwca-portages-raw.geojson")
    else:
        bwca = pull_trailnfs(args.workdir, BWCA_NAMES, "bwca-portages", "BWCA")
    groups.append(("BWCA portages", [
        ((f.get("properties") or {}).get("trail_name") or "BWCA portage",
         "USDA Forest Service National Forest System Trails (EDW_TrailNFSPublish_01)",
         TRAILNFS, f["geometry"],
         (f.get("properties") or {}).get("objectid"))
        for f in bwca if f.get("geometry")]))

    # --- Trails near the BRT & SHT (USFS TrailNFS) ---
    if args.skip_fetch:
        near = load_raw("near-brt-sht-raw.geojson")
    else:
        near = pull_trailnfs(args.workdir, NEAR_NAMES, "near-brt-sht", "near-BRT/SHT")
    groups.append(("Trails near Border Route & SHT", [
        ((f.get("properties") or {}).get("trail_name") or "trail",
         "USDA Forest Service National Forest System Trails (EDW_TrailNFSPublish_01)",
         TRAILNFS, f["geometry"],
         (f.get("properties") or {}).get("objectid"))
        for f in near if f.get("geometry")]))

    # --- Driftless Hiking Trail (OSM ways + traced loop) ---
    if args.skip_fetch:
        drift = load_raw("driftless-osm.geojson")
    else:
        drift = pull_driftless(args.workdir)
    groups.append(("Driftless Hiking Trail", [
        ((f.get("properties") or {}).get("name") or "Driftless Hiking Trail",
         "OpenStreetMap (ODbL)" + (" + traced from DALC trifold"
                                   if "traced" in str(f.get("properties") or {})
                                   else ""),
         "https://www.openstreetmap.org/way/%s"
         % (f.get("properties") or {}).get("osm_way_id", ""),
         f["geometry"],
         (f.get("properties") or {}).get("osm_way_id"))
        for f in drift if f.get("geometry")]))

    # --- OSM route relations: Buckeye, Finger Lakes, Long Trail ---
    for trail, rels in OSM_TRAILS.items():
        stem = trail.lower().replace(" ", "-") + "-osm.geojson"
        if args.skip_fetch:
            feats = load_raw(stem)
        else:
            feats = pull_osm_trail(args.workdir, trail, rels)
        url = ("https://www.openstreetmap.org/relation/%d" % rels[0][0]
               if len(rels) == 1 else
               "https://www.openstreetmap.org/relation/%d (+ %d more)"
               % (rels[0][0], len(rels) - 1))
        groups.append((trail, [
            (trail, "OpenStreetMap (ODbL)", url, f["geometry"],
             "relation %s" % ",".join(str(r) for r, _ in rels))
            for f in feats if f.get("geometry")]))

    # --- merge + measure + concurrency flag ---
    idx = CenterlineIndex()
    out_feats = []
    summary = {}
    for trail, items in groups:
        n = 0
        miles = 0.0
        conc_miles = 0.0
        for name, source, url, geom, sid in items:
            feat = normalize(trail, name, source, url, geom, sid, idx)
            out_feats.append(feat)
            n += 1
            miles += feat["properties"]["length_mi"]
            if feat["properties"]["concurrent_with_nct"]:
                conc_miles += feat["properties"]["length_mi"]
        summary[trail] = {"features": n, "miles": round(miles, 2),
                          "concurrent_miles": round(conc_miles, 2)}
        print("%s: %d features, %.2f mi (%.2f concurrent)"
              % (trail, n, miles, conc_miles))

    out = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Concurrent / partner trails of the North Country Trail",
            "pulled_utc_date": PULLED,
            "sources": {
                "Superior Hiking Trail": DNR_PARK_FS,
                "Border Route Trail": TRAILNFS,
                "BWCA portages": TRAILNFS,
                "Trails near Border Route & SHT": TRAILNFS,
                "Driftless Hiking Trail": "OpenStreetMap ways 1248941083, "
                                          "1248943005, 1248953013 + traced loop",
                "Buckeye Trail": "OSM super-relation 1738661",
                "Finger Lakes Trail": "OSM relations 12725656, 12725657, "
                                      "12725658, 12725661",
                "Long Trail": "OSM relation 391736",
            },
            "concurrent_rule": ("concurrent_with_nct is true when >=50% of "
                                "a feature's length lies within 50 m of the "
                                "NCT centerline (UTM, per-feature zone); "
                                "concurrent_miles is the geodesic length "
                                "within that 50 m buffer"),
            "length_method": "geodesic miles on WGS84 (pyproj Geod)",
            "per_trail": summary,
        },
        "features": out_feats,
    }
    path = os.path.join(SITE_DATA, "partner-trails.geojson")
    with open(path, "w") as fh:
        json.dump(out, fh)
    print("TOTAL: %d features, %.2f mi -> %s"
          % (len(out_feats),
             sum(s["miles"] for s in summary.values()), path))


if __name__ == "__main__":
    main()
