#!/usr/bin/env python3
"""Pull ALL tribal lands along the North Country Trail from the BIA
national service — the national version of the Itasca Moraine chapter
viewer's pull_leech_lake_reservation.py and
pull_white_earth_reservation.py
(~/workspace/itasca-trail-map/scripts/ — read-only source).

Source: Bureau of Indian Affairs, American Indian and Alaska Native
Land Area Representation (AIAN-LAR) national dataset:
  https://biamaps.geoplatform.gov/server/rest/services/DivLTR/BIA_AIAN_National_LAR/FeatureServer
layer 0, "BIA AIAN National LAR". Public federal data; no licence
restriction. The ITM scripts fetch one reservation each by LARID
(Leech Lake LAR0033, White Earth LAR0051); this script fetches the
whole layer (335 features, verified 2026-11-23) and keeps every
feature whose geometry comes within 2 miles of the NCT centerline.

Selection rule: a reservation is IN when its polygon intersects the
2-mile corridor around the centerline (site/data/centerline-*.geojson,
natural + road + urban). Distance is tested in a kilometre
equirectangular projection (111.320*cos(44 deg) km/deg lon,
111.195 km/deg lat); the corridor test is a proximity test only,
so the small projection error at the latitude extremes is immaterial.
Full unclipped reservation geometry is published, exactly as the ITM
scripts publish full unclipped boundaries.

Per-reservation trail miles inside are measured by intersecting the
centerline with the reservation polygon and summing geodesic lengths
(pyproj Geod, WGS84) of the inside pieces.

What is NOT used, per the ITM rule: BIA's own GISACRES attribute
contradicts its own geometry (Leech Lake: 1,794,106 vs 823,249 ac
geometry-measured; White Earth: 1,621,000.16 vs 748,098 ac — both
~2.17x), so area_acres here is geometry-measured (geodesic, WGS84)
and GISACRES is carried only as gisacres_attribute for the record.
The Census off-reservation trust-land features are NOT included:
this layer is reservations themselves, as in ITM.

Output: site/data/tribal-lands.geojson (one feature per reservation
within 2 mi of the trail, full geometry, sorted by name).

Usage: python3 scripts/pull_tribal_lands_national.py
No credentials required; the service is public.
"""

import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

# shapely/pyproj live in the user site-packages on this VM
# (PYTHONNOUSERSITE=1); fall back to it when the plain import fails.
try:
    import shapely  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.expanduser(
        "~/.local/lib/python3.12/site-packages"))

from pyproj import Geod  # noqa: E402
from shapely.geometry import shape  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "site", "data", "tribal-lands.geojson")
CENTERLINE = [os.path.join(REPO, "site", "data", f)
              for f in ("centerline-natural.geojson",
                        "centerline-road.geojson",
                        "centerline-urban.geojson")]

BIA = ("https://biamaps.geoplatform.gov/server/rest/services/"
       "DivLTR/BIA_AIAN_National_LAR/FeatureServer/0/query")
UA = {"User-Agent": "Mozilla/5.0 (nct-full-viewer data pull)"}
BUFFER_KM = 3.21869  # 2 miles, same corridor as the other layers
KX = 111.320 * math.cos(math.radians(44.0))  # km per deg lon at 44 N
KY = 111.195  # km per deg lat
GEOD = Geod(ellps="WGS84")
ID_CHUNK = 100


def fetch_json(url, retries=4):
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url[:200]} failed after {retries} tries: "
                       f"{last_err}")


def fetch_all_bia():
    """All BIA AIAN-LAR features, fetched by OBJECTID in chunks."""
    ids_data = fetch_json(BIA + "?where=" + urllib.parse.quote("1=1") +
                          "&returnIdsOnly=true&f=json")
    ids = sorted(ids_data.get("objectIds") or [])
    oid_field = ids_data.get("objectIdFieldName", "OBJECTID")
    print(f"BIA features in layer: {len(ids)}")
    fields = "LARID,LARNAME,CLASSIFICATION,GISACRES,REGION"
    feats = []
    for i in range(0, len(ids), ID_CHUNK):
        chunk = ids[i:i + ID_CHUNK]
        where = f"{oid_field} IN ({','.join(str(x) for x in chunk)})"
        q = (BIA + "?where=" + urllib.parse.quote(where) +
             "&outFields=" + urllib.parse.quote(fields) +
             "&returnGeometry=true&outSR=4326&f=geojson")
        data = fetch_json(q)
        got = data.get("features", [])
        if len(got) != len(chunk):
            raise RuntimeError(
                f"BIA chunk {i}: asked {len(chunk)}, got {len(got)}")
        feats.extend(got)
    return feats


def to_km(geom):
    from shapely.ops import transform as _t
    return _t(lambda x, y: (x * KX, y * KY), geom)


def trail_miles_inside(poly_lonlat, tree, pieces_lonlat):
    """Geodesic miles of centerline inside the polygon."""
    idx = tree.query(poly_lonlat, predicate="intersects")
    total_m = 0.0
    for i in idx:
        inter = pieces_lonlat[i].intersection(poly_lonlat)
        if inter.is_empty:
            continue
        lines = list(inter.geoms) if inter.geom_type in (
            "MultiLineString", "GeometryCollection") else [inter]
        for ln in lines:
            if ln.geom_type != "LineString" or ln.is_empty:
                continue
            coords = list(ln.coords)
            if len(coords) < 2:
                continue
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            total_m += GEOD.line_length(lons, lats)
    return round(total_m / 1609.344, 2)


def main():
    # ---- centerline, indexed in km coords for the corridor test
    pieces_lonlat = []
    for path in CENTERLINE:
        with open(path) as fh:
            gj = json.load(fh)
        for feat in gj["features"]:
            g = shape(feat["geometry"])
            if g.is_empty:
                continue
            if g.geom_type == "MultiLineString":
                pieces_lonlat.extend(list(g.geoms))
            elif g.geom_type == "LineString":
                pieces_lonlat.append(g)
    print(f"centerline pieces: {len(pieces_lonlat)}")
    pieces_km = [to_km(g) for g in pieces_lonlat]
    tree_km = STRtree(pieces_km)
    tree_lonlat = STRtree(pieces_lonlat)

    # ---- BIA fetch
    raw = fetch_all_bia()
    print(f"fetched BIA features: {len(raw)}")

    kept = []
    for f in raw:
        p = f.get("properties") or {}
        try:
            geom = shape(f["geometry"])
        except Exception:  # noqa: BLE001
            continue
        if geom.is_empty or not geom.is_valid:
            try:
                geom = geom.buffer(0)
            except Exception:  # noqa: BLE001
                continue
            if geom.is_empty:
                continue
        gkm = to_km(geom)
        idx = tree_km.query(gkm, predicate="dwithin",
                            distance=BUFFER_KM)
        if len(idx) == 0:
            continue
        # Closest approach, for the record.
        dist_km = min(pieces_km[i].distance(gkm) for i in idx)
        area_m2, _ = GEOD.geometry_area_perimeter(geom)
        miles = trail_miles_inside(geom, tree_lonlat, pieces_lonlat)
        kept.append({
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": {
                "name": p.get("LARNAME"),
                "larid": p.get("LARID"),
                "classification": p.get("CLASSIFICATION"),
                "region": p.get("REGION"),
                "area_acres": round(abs(area_m2) / 4046.8564224, 1),
                "gisacres_attribute": p.get("GISACRES"),
                "trail_miles_inside": miles,
                "dist_trail_km": round(dist_km, 2),
                "source": ("Bureau of Indian Affairs, AIAN Land Area "
                           "Representation (AIAN-LAR)"),
                "note": ("Federal reservation boundary as published — "
                         "not a legal survey."),
            },
        })
        print(f"  {p.get('LARNAME')} ({p.get('LARID')}): "
              f"{miles} trail mi inside, {dist_km:.2f} km from trail")

    kept.sort(key=lambda f: (f["properties"]["name"] or ""))
    doc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("BIA AIAN Land Area Representation — every "
                        "reservation within 2 miles of the North Country "
                        "Trail centerline (full unclipped geometry)"),
            "service": BIA,
            "pulled_utc_date": time.strftime("%Y-%m-%d", time.gmtime()),
            "corridor": ("2-mile corridor around site/data/"
                         "centerline-natural.geojson + "
                         "centerline-road.geojson + "
                         "centerline-urban.geojson"),
            "area_note": ("area_acres is geometry-measured (geodesic, "
                          "WGS84). BIA's GISACRES attribute contradicts "
                          "its own geometry by ~2.17x on the two "
                          "Minnesota reservations checked in ITM and is "
                          "NOT used; it is carried as "
                          "gisacres_attribute for the record."),
            "feature_count": len(kept),
            "bia_features_total": len(raw),
        },
        "features": kept,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(doc, fh)
    print(f"WROTE {OUT}: {len(kept)} features "
          f"({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
