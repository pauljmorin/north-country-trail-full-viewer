#!/usr/bin/env python3
"""Pull OSM roads + OSM bicycle routes in the NCT corridor (plan step 5).

Route (why not Overpass): Overpass is unreachable from this VM
(HTTP 406 on overpass-api.de, timeout on overpass.kumi.systems,
2026-11-23). The OSM API works but is bbox-limited, so the corridor
pulls run off Geofabrik state extracts instead:
  https://download.geofabrik.de/north-america/us/<state>-latest.osm.pbf
for the eight states the NCT crosses: North Dakota, Minnesota,
Wisconsin, Michigan, Ohio, Pennsylvania, New York, Vermont.
Downloaded to --workdir/geofabrik/ (NOT committed to the repo).

Method:
  1. Build the corridor: the NCT centerline (site/data/centerline-*.geojson)
     buffered by 2 mi (3,218.69 m). Buffering is done per UTM zone
     (zones 13-18 cover the trail) so the 2 mi is true metres, then the
     per-zone buffers are unioned back to WGS84.
  2. Cut each state extract to the corridor with `osmium extract`
     (osmium-tool; GDAL's OSM driver is far too slow on whole-state
     files with a ~12k-vertex clip polygon — ~5 min for North Dakota
     roads alone — while osmium does the same cut in ~20 s).
  3. Roads: GDAL OSM driver, `lines` layer, highway in the road family
     (see ROAD_HIGHWAYS), from the corridor extracts — no ogr2ogr
     -clipsrc (GDAL's clip against the ~12k-vertex corridor polygon
     is pathologically slow: Ohio roads ran 7+ min on a 29 MB
     extract). Exact clipping to the corridor is done in Python
     (shapely) in the merge step, and lengths are measured on the
     clipped geometry.
  3. Bike routes: GDAL OSM driver, `multilinestrings` layer (route
     relations), other_tags containing "route"=>"bicycle", clipped to
     the corridor. The Mesabi Trail comes in here as OSM relation
     5326107, one route among others (its overlap with the NCT was
     measured separately in mesabi-overlap-2026-11-23.md — used only
     as a cross-check, not as this layer's source).

Outputs:
  site/data/osm-roads.geojson
  site/data/osm-bike-routes.geojson
  --workdir/corridor-2mi.geojson (the corridor polygon, for audit)

Ways crossing a state line are split at the Geofabrik state boundary,
so one physical road can appear as two features (one per state);
nothing is de-duplicated across states, and the SOURCES note says so.

Usage: python3 scripts/pull-osm-corridor.py [--workdir DIR] [--skip-download]
  --skip-download reuses the .osm.pbf files already in --workdir/geofabrik/.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

from pyproj import Geod, Transformer
from shapely.geometry import LineString, MultiLineString, shape
from shapely.ops import transform as shp_transform, unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DATA = os.path.join(REPO, "site", "data")
PULLED = time.strftime("%Y-%m-%d", time.gmtime())
GEOD = Geod(ellps="WGS84")
BUFFER_M = 3218.69  # 2 miles

STATES = ["north-dakota", "minnesota", "wisconsin", "michigan",
          "ohio", "pennsylvania", "new-york", "vermont"]
GEOFABRIK = ("https://download.geofabrik.de/north-america/us/"
             "%s-latest.osm.pbf")

# Road-family highway values kept in osm-roads.geojson. Excluded on purpose:
# footway, path, cycleway, steps, bridleway, corridor, construction,
# proposed, raceway, bus_guideway, escape, etc. — those are not roads.
ROAD_HIGHWAYS = [
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "unclassified", "residential",
    "living_street", "service", "track", "road", "pedestrian",
    "busway",
]


def build_corridor(workdir):
    """Buffer the centerline by 2 mi, per UTM zone. Returns the path of
    the corridor GeoJSON (MultiPolygon, EPSG:4326)."""
    segs = []
    for name in ("centerline-natural", "centerline-road", "centerline-urban"):
        d = json.load(open(os.path.join(SITE_DATA, name + ".geojson")))
        for f in d["features"]:
            g = shape(f["geometry"])
            if g.geom_type == "LineString":
                segs.append(g)
            elif g.geom_type == "MultiLineString":
                segs.extend(list(g.geoms))
    print("centerline segments: %d" % len(segs))
    by_zone = {}
    for s in segs:
        cx = (s.bounds[0] + s.bounds[2]) / 2.0
        zone = int((cx + 180.0) / 6.0) + 1
        by_zone.setdefault(zone, []).append(s)
    parts = []
    for zone, zs in sorted(by_zone.items()):
        tr = Transformer.from_crs("EPSG:4326", "EPSG:326%02d" % zone,
                                  always_xy=True)
        back = Transformer.from_crs("EPSG:326%02d" % zone, "EPSG:4326",
                                    always_xy=True)
        projected = [shp_transform(tr.transform, s) for s in zs]
        buffered = unary_union([p.buffer(BUFFER_M) for p in projected])
        parts.append(shp_transform(back.transform, buffered))
        print("zone %d: %d segments buffered" % (zone, len(zs)))
    corridor = unary_union(parts)
    # Simplify for the ogr2ogr -clipsrc step: the raw union has ~55k
    # vertices, which makes GDAL's per-feature clip test very slow.
    # 0.00045 deg (~50 m) simplification moves the corridor edge by at
    # most ~50 m — negligible against a 2 mi buffer — and cuts the
    # vertex count by an order of magnitude.
    n_before = sum(len(r) for r in corridor.exterior.coords) \
        if corridor.geom_type == "Polygon" else 0
    corridor = corridor.simplify(0.00045, preserve_topology=True)
    print("corridor simplified: %s vertices -> %s"
          % (n_before,
             sum(len(p.exterior.coords) for p in
                 ([corridor] if corridor.geom_type == "Polygon"
                  else list(corridor.geoms)))))
    path = os.path.join(workdir, "corridor-2mi.geojson")
    with open(path, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "properties": {"buffer_m": BUFFER_M, "buffer_mi": 2.0,
                           "simplify_tolerance_deg": 0.00045,
                           "method": "per-UTM-zone buffer of the NCT "
                                     "centerline, unioned, simplified "
                                     "to ~50 m for clipping"},
            "geometry": json.loads(json.dumps(corridor.__geo_interface__)),
        }]}, fh)
    print("corridor: %s (type %s)" % (path, corridor.geom_type))
    return path


def download_states(workdir):
    gdir = os.path.join(workdir, "geofabrik")
    os.makedirs(gdir, exist_ok=True)
    import requests
    for st in STATES:
        path = os.path.join(gdir, st + "-latest.osm.pbf")
        if os.path.exists(path):
            print("%s: already present (%d bytes)" % (st, os.path.getsize(path)))
            continue
        url = GEOFABRIK % st
        print("downloading %s ..." % url)
        r = requests.get(url, timeout=1800, stream=True)
        r.raise_for_status()
        with open(path, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
        print("%s: %d bytes" % (st, os.path.getsize(path)))
    return gdir


def extract_corridor_pbf(pbf, corridor, out_path):
    """Fast pre-extraction with osmium: cut the state extract down to
    the corridor before GDAL ever sees it. GDAL's OSM driver scans a
    whole .osm.pbf per layer query and its -clipsrc test against the
    ~12k-vertex corridor polygon is very slow (~5 min for North
    Dakota roads alone); osmium extract does the same cut in ~20 s
    (Vermont) by node location. A way is kept if any of its nodes
    falls inside the polygon; OSM ways are densely noded and the
    corridor is 4 mi wide, so a segment spanning it without a node
    is negligible — and the ogr2ogr -clipsrc step below still clips
    exactly, so any over-long kept way is trimmed to the corridor."""
    if os.path.exists(out_path):
        print("corridor extract exists: %s" % out_path)
        return out_path
    cmd = ["osmium", "extract", "-p", corridor, pbf, "-o", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        print("osmium extract FAILED for %s:\n%s" % (pbf, r.stderr[-2000:]))
        raise SystemExit(1)
    print("osmium extract %s -> %s (%d bytes)"
          % (os.path.basename(pbf), os.path.basename(out_path),
             os.path.getsize(out_path)))
    return out_path


def run_ogr(pbf, layer, where, out_path):
    """ogr2ogr from a corridor extract. NO -clipsrc here: GDAL's clip
    against the ~12k-vertex corridor polygon is pathologically slow
    (Ohio roads ran 7+ min on a 29 MB extract). osmium already cut
    the extract to the corridor; exact clipping to the polygon is
    done in Python (merge(), shapely) which is orders of magnitude
    faster at it."""
    cmd = ["ogr2ogr", "-f", "GeoJSON", out_path, pbf, layer,
           "-where", where,
           "-select", "osm_id,name,highway,other_tags" if layer == "lines"
           else "osm_id,name,other_tags"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        print("ogr2ogr FAILED for %s %s:\n%s" % (pbf, layer, r.stderr[-2000:]))
        raise SystemExit(1)
    return out_path


TAG_RE = re.compile(r'"([^"]+)"=>"(.*?)"(?=,"|$)')

def parse_other_tags(s):
    if not s:
        return {}
    return dict(TAG_RE.findall(s))


def geodesic_miles(geom):
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
        total += GEOD.line_length([c[0] for c in line],
                                  [c[1] for c in line]) / 1609.344
    return total


def merge(files, kind, corridor_poly):
    """Merge per-state ogr2ogr outputs into normalized viewer features,
    clipping each geometry exactly to the corridor polygon (shapely)
    and measuring geodesic miles on the clipped geometry."""
    feats = []
    for path in files:
        if not os.path.exists(path):
            continue
        d = json.load(open(path))
        for f in d.get("features", []):
            p = f.get("properties") or {}
            tags = parse_other_tags(p.get("other_tags"))
            geom = f.get("geometry")
            if not geom:
                continue
            g = shape(geom)
            if g.is_empty:
                continue
            g = g.intersection(corridor_poly)
            if g.is_empty:
                continue
            geom = json.loads(json.dumps(g.__geo_interface__))
            if kind == "roads":
                props = {
                    "osm_id": p.get("osm_id"),
                    "name": p.get("name"),
                    "highway": p.get("highway"),
                    "ref": tags.get("ref"),
                    "surface": tags.get("surface"),
                    "length_mi": round(geodesic_miles(geom), 3),
                }
            else:
                props = {
                    "osm_id": p.get("osm_id"),
                    "name": p.get("name"),
                    "ref": tags.get("ref"),
                    "network": tags.get("network"),
                    "route": "bicycle",
                    "length_mi": round(geodesic_miles(geom), 3),
                }
            feats.append({"type": "Feature", "properties": props,
                          "geometry": geom})
    return feats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.path.expanduser(
        "~/workspace/nct-step5-work"))
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.workdir, exist_ok=True)
    os.makedirs(SITE_DATA, exist_ok=True)

    corridor = build_corridor(args.workdir)
    corridor_poly = shape(json.load(open(corridor))["features"][0]["geometry"])
    gdir = os.path.join(args.workdir, "geofabrik")
    if args.skip_download:
        print("skipping downloads; using extracts in %s" % gdir)
    else:
        download_states(args.workdir)

    road_files, bike_files = [], []
    where_roads = "highway IN (%s)" % ",".join("'%s'" % h for h in ROAD_HIGHWAYS)
    for st in STATES:
        pbf = os.path.join(gdir, st + "-latest.osm.pbf")
        if not os.path.exists(pbf):
            print("WARNING: missing extract %s — skipping state" % pbf)
            continue
        cpbf = os.path.join(args.workdir, "corridor-%s.osm.pbf" % st)
        extract_corridor_pbf(pbf, corridor, cpbf)
        rp = os.path.join(args.workdir, "roads-%s.geojson" % st)
        run_ogr(cpbf, "lines", where_roads, rp)
        road_files.append(rp)
        n = len(json.load(open(rp)).get("features", []))
        print("roads %s: %d features" % (st, n))
        bp = os.path.join(args.workdir, "bike-%s.geojson" % st)
        run_ogr(cpbf, "multilinestrings",
                "other_tags LIKE '%\"route\"=>\"bicycle\"%'", bp)
        bike_files.append(bp)
        n = len(json.load(open(bp)).get("features", []))
        print("bike routes %s: %d features" % (st, n))

    roads = merge(road_files, "roads", corridor_poly)
    bikes = merge(bike_files, "bike", corridor_poly)
    road_mi = sum(f["properties"]["length_mi"] for f in roads)
    bike_mi = sum(f["properties"]["length_mi"] for f in bikes)
    from collections import Counter
    print("ROADS total: %d features, %.2f mi" % (len(roads), road_mi))
    print("  by highway: %s"
          % dict(Counter(f["properties"]["highway"] for f in roads)))
    print("BIKE total: %d features, %.2f mi" % (len(bikes), bike_mi))
    print("  routes named: %d" % sum(1 for f in bikes if f["properties"]["name"]))

    out_roads = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "OSM road centerlines within 2 mi of the NCT centerline",
            "pulled_utc_date": PULLED,
            "source": "OpenStreetMap via Geofabrik state extracts "
                      "(north-dakota, minnesota, wisconsin, michigan, ohio, "
                      "pennsylvania, new-york, vermont), ODbL",
            "corridor": "2 mi buffer of site/data/centerline-*.geojson, "
                        "buffered per UTM zone",
            "highway_values_kept": ROAD_HIGHWAYS,
            "highway_values_excluded": ["footway", "path", "cycleway",
                                        "steps", "bridleway", "corridor",
                                        "construction", "proposed", "raceway",
                                        "bus_guideway", "escape", "elevator",
                                        "crossing", "trailhead", "rest_area",
                                        "services", "speed_camera",
                                        "street_lamp", "turning_circle",
                                        "give_way", "stop", "toll_gantry",
                                        "trailhead", "passing_place"],
            "note": "Ways crossing a state line are split at the Geofabrik "
                    "state boundary (one feature per state).",
            "features": len(roads),
            "total_miles": round(road_mi, 2),
        },
        "features": roads,
    }
    out_bikes = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "OSM bicycle route relations within 2 mi of the NCT centerline",
            "pulled_utc_date": PULLED,
            "source": "OpenStreetMap via Geofabrik state extracts (same eight "
                      "states), ODbL; route relations (type=route, route=bicycle)",
            "corridor": "2 mi buffer of site/data/centerline-*.geojson, "
                        "buffered per UTM zone",
            "note": "The Mesabi Trail (OSM relation 5326107) is one route "
                    "among others here; its NCT overlap was measured "
                    "separately (mesabi-overlap-2026-11-23.md).",
            "features": len(bikes),
            "total_miles": round(bike_mi, 2),
        },
        "features": bikes,
    }
    rp = os.path.join(SITE_DATA, "osm-roads.geojson")
    bp = os.path.join(SITE_DATA, "osm-bike-routes.geojson")
    json.dump(out_roads, open(rp, "w"))
    json.dump(out_bikes, open(bp, "w"))
    print("wrote %s (%d features)" % (rp, len(roads)))
    print("wrote %s (%d features)" % (bp, len(bikes)))


if __name__ == "__main__":
    main()
