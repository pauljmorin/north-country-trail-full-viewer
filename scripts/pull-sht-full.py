#!/usr/bin/env python3
"""Pull the FULL Superior Hiking Trail line for the NCT full viewer.

Source: Lake County, MN ArcGIS Online service
  https://services1.arcgis.com/NlvHF2FHoAfPIDvG/arcgis/rest/services/Superior_Hiking/FeatureServer/3
  (public, keyless — verified live Nov 26, 2026; audit
  docs/lake-county-gis-audit-2026-11-26.md).

Why this source: the NCT viewer's partner-trails layer carries the SHT
only as the MN DNR state-park portions (207.58 mi, 553 features) — the
published trail is ~310 mi. The county's service is the whole trail,
collected by Sundew Technical Services, with per-segment MILES and
SHT_TYPE (MAIN/SPUR/CAMP). In the NCT viewer the NCT runs on the SHT
for ~300 mi in Minnesota-east — the partner-trail stretch where NCTA
has no half-mile index — so this fills the gap visually. It replaces
the DNR park file as the fuller SHT source in this viewer; the
partner-trails layer is left as-is (its SHT entry is now documented
as superseded in SOURCES-step5.md).

Output: site/data/sht-full.geojson — one feature per source segment,
with normalized properties:
  trail       "Superior Hiking Trail"
  sht_type    MAIN / SPUR / CAMP, as the service carries it
  miles       the service's own MILES value (SHT mileage, NOT NCTA
              mileage — never used as chainage or NCTA mileage)
  length_mi   geodesic miles on WGS84 (pyproj Geod), measured on the
              geometry as served
  collector   as the service carries it (Sundew Technical Services)
  source_id   OBJECTID
  source      short source label
  source_url  service URL

Raw pull is kept in --workdir (default ~/workspace/nct-sht-work/raw/)
so the repo carries only the script and the merged output; re-running
the script re-pulls everything live and rebuilds the file.

Usage: python3 scripts/pull-sht-full.py [--workdir DIR] [--skip-fetch]
  --skip-fetch reuses the raw pull already in --workdir (merge only).
"""

import argparse
import json
import os
import sys
import time

import requests
from pyproj import Geod

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DATA = os.path.join(REPO, "site", "data")
SERVICE = ("https://services1.arcgis.com/NlvHF2FHoAfPIDvG/arcgis/rest/"
           "services/Superior_Hiking/FeatureServer/3")
PULLED = time.strftime("%Y-%m-%d", time.gmtime())
UA = {"User-Agent": "Mozilla/5.0 (nct-viewer data pull; contact: pauljmorin@gmail.com)"}
GEOD = Geod(ellps="WGS84")
PAGE = 500


def fetch_all(workdir):
    """Fetch every feature as GeoJSON in WGS84, paged by OBJECTID."""
    count_url = SERVICE + "/query"
    r = requests.get(count_url, params={"where": "1=1", "returnCountOnly": "true",
                                        "f": "json"}, headers=UA, timeout=60)
    r.raise_for_status()
    total = r.json().get("count")
    print(f"service count: {total}")
    feats = []
    offset = 0
    while True:
        params = {"where": "1=1", "outFields": "*",
                  "orderByFields": "OBJECTID", "resultOffset": offset,
                  "resultRecordCount": PAGE, "outSR": 4326, "f": "geojson"}
        r = requests.get(count_url, params=params, headers=UA, timeout=120)
        r.raise_for_status()
        page = r.json().get("features", [])
        if not page:
            break
        feats.extend(page)
        offset += len(page)
        print(f"  fetched {len(feats)} so far")
        if len(page) < PAGE:
            break
    raw_path = os.path.join(workdir, "sht-full-raw.geojson")
    with open(raw_path, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh)
    print(f"raw pull saved: {raw_path} ({len(feats)} features)")
    return feats


def geodesic_mi(geom):
    """Geodesic length in miles of a LineString / MultiLineString."""
    total = 0.0
    parts = []
    if geom["type"] == "LineString":
        parts = [geom["coordinates"]]
    elif geom["type"] == "MultiLineString":
        parts = geom["coordinates"]
    else:
        raise ValueError(f"unexpected geometry type {geom['type']}")
    for coords in parts:
        if len(coords) < 2:
            continue
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        total += GEOD.line_length(lons, lats) / 1609.344
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.path.expanduser("~/workspace/nct-sht-work/raw"))
    ap.add_argument("--skip-fetch", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.workdir, exist_ok=True)

    if args.skip_fetch:
        with open(os.path.join(args.workdir, "sht-full-raw.geojson")) as fh:
            feats = json.load(fh)["features"]
        print(f"reusing raw pull: {len(feats)} features")
    else:
        feats = fetch_all(args.workdir)

    out = []
    by_type = {}
    for f in feats:
        p = f.get("properties", {})
        miles = p.get("MILES")
        gmi = geodesic_mi(f["geometry"])
        # The service carries a blank (single-space) SHT_TYPE on 3
        # segments (OBJECTIDs 574-576, 3.99 mi) and a blank COLLECTOR
        # on the same three. Normalize whitespace-only to None so the
        # file states the gap instead of carrying a space as a type;
        # the viewer styles untyped segments dashed (see SOURCES).
        t = (p.get("SHT_TYPE") or "").strip() or None
        collector = (p.get("COLLECTOR") or "").strip() or None
        by_type.setdefault(t, {"n": 0, "miles": 0.0, "geodesic": 0.0})
        by_type[t]["n"] += 1
        by_type[t]["miles"] += miles or 0.0
        by_type[t]["geodesic"] += gmi
        out.append({
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": {
                "trail": "Superior Hiking Trail",
                "sht_type": t,
                "miles": miles,
                "length_mi": round(gmi, 4),
                "collector": collector,
                "source_id": p.get("OBJECTID"),
                "source": "Lake County MN ArcGIS Online (Sundew Technical Services)",
                "source_url": SERVICE,
            },
        })

    out_path = os.path.join(SITE_DATA, "sht-full.geojson")
    with open(out_path, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": out}, fh)
    print(f"wrote {out_path} ({len(out)} features)")

    # verification summary — compare against the audit's live numbers
    print("\n--- verification (audit: 576 features, 330.0 mi) ---")
    tot_n = tot_m = tot_g = 0
    for t in sorted(by_type, key=lambda x: (x is None, x or "")):
        b = by_type[t]
        print(f"  {t or '(untyped)'}: {b['n']} features, service MILES {b['miles']:.1f}, "
              f"geodesic {b['geodesic']:.2f} mi")
        tot_n += b["n"]
        tot_m += b["miles"]
        tot_g += b["geodesic"]
    print(f"  TOTAL: {tot_n} features, service MILES {tot_m:.1f}, "
          f"geodesic {tot_g:.2f} mi")
    print(f"  pulled: {PULLED}")
    if tot_n != 576 or abs(tot_m - 330.0) > 0.05:
        print("  WARNING: does not match audit (576 features / 330.0 mi)")
        sys.exit(1)
    print("  matches audit: 576 features, 330.0 mi")


if __name__ == "__main__":
    main()
