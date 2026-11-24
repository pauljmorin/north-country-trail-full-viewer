#!/usr/bin/env python3
"""Pull the NCTA public point layer (trail waypoints) NATIONALLY and
split it into the two NCT-viewer layers:

  site/data/camping.geojson      — every waypoint whose wptType is "Camping"
  site/data/ncta-places.geojson  — every other waypoint (Parking, Water,
                                   Shelter, POI, ...)

Adapted from the Itasca Moraine chapter viewer's
scripts/pull_points.py, with the Minnesota clip REMOVED: no envelope,
no bounding box — the whole service, where 1=1, fetched by object id.

Data source: the same public ArcGIS feature service as the official
line ("North Country Trail (Public)", NCTA on behalf of NPS),
LAYER 1 "Point Data - Public" — the waypoint layer behind the public
map / FarOut: campsites, parking, shelters, water, points of interest.

Method (standard library + requests only), following pull_points.py:
features are fetched BY OBJECT ID (returnIdsOnly first, then chunks
of ids, POST so a 500-id IN-list does not overflow the URL — the
GET form was observed to 404 on long IN-lists), with each chunk's
returned count verified against the chunk size (a short chunk is
split and retried) — offset-paged queries on these hosts have
silently truncated before, so paging is never trusted.

Properties are CLEANED (the raw layer carries ~30 fields, several of
them editing scaffolding). Each output feature keeps only:
  name         waypointName
  type         wptType, VERBATIM — never reclassified
  subtype      iconSet2 where meaningful, else null
  extra_types  iconSet3/4/5 where set (further wpType values), else []
  owner        owner (Federal / State), else null
  description  descriptionText, else null
  chapter      chapter tag, else null
  state        state tag, else null
  waypoint_id  waypointID, else null
  source       source, else null
  updated      updated (epoch ms) as an ISO date, else null
Blank strings and the literal string "None" are normalised to null.

Output: site/data/camping.geojson, site/data/ncta-places.geojson

Usage:  python3 scripts/pull_ncta_points_national.py
No credentials required; the service is public.
"""

import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CAMPING = REPO_ROOT / "site" / "data" / "camping.geojson"
OUT_PLACES = REPO_ROOT / "site" / "data" / "ncta-places.geojson"

SERVICE_ROOT = ("https://services2.arcgis.com/UfGVyqUm4GHa2zrj"
                "/arcgis/rest/services/nct_public/FeatureServer")
LAYER_ID = 1
ID_CHUNK = 500


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
    """Fetch features for one chunk of object ids; verify the count
    and split the chunk if the server returns fewer than asked.
    POST (not GET): a 500-id IN-list makes a GET URL long enough
    for the ArcGIS host to reject it."""
    where = f"{oid_field} IN ({','.join(str(i) for i in ids)})"
    params = {
        "where": where,
        "outFields": "*",
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


def page_layer(layer_url):
    """Fetch ALL features in the layer, by object id. No clip."""
    params = {
        "where": "1=1",
        "returnIdsOnly": "true",
        "f": "json",
    }
    data = get_json(f"{layer_url}/query", params=params)
    ids = sorted(data.get("objectIds") or [])
    oid_field = data.get("objectIdFieldName", "OBJECTID")
    feats = []
    for i in range(0, len(ids), ID_CHUNK):
        feats.extend(fetch_chunk(layer_url, oid_field, ids[i:i + ID_CHUNK]))
    return feats


def clean_str(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == "none":
        return None
    return s


def clean_feature(f):
    p = f.get("properties") or {}
    geom = f.get("geometry") or {}
    coords = geom.get("coordinates")
    if not coords:
        lon, lat = p.get("lon"), p.get("lat")
        if lon is None or lat is None:
            return None
        coords = [lon, lat]
    updated = p.get("updated")
    updated_iso = None
    if isinstance(updated, (int, float)) and updated:
        try:
            updated_iso = datetime.fromtimestamp(
                updated / 1000.0, tz=timezone.utc).date().isoformat()
        except (ValueError, OSError):
            updated_iso = None
    extra = [clean_str(p.get(k)) for k in ("iconSet3", "iconSet4", "iconSet5")]
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [round(float(coords[0]), 6),
                            round(float(coords[1]), 6)],
        },
        "properties": {
            "name": clean_str(p.get("waypointName")),
            "type": clean_str(p.get("wptType")),
            "subtype": clean_str(p.get("iconSet2")),
            "extra_types": [e for e in extra if e],
            "owner": clean_str(p.get("owner")),
            "description": clean_str(p.get("descriptionText")),
            "chapter": clean_str(p.get("chapter")),
            "state": clean_str(p.get("state")),
            "waypoint_id": clean_str(p.get("waypointID")),
            "source": clean_str(p.get("source")),
            "updated": updated_iso,
        },
    }


def write_fc(path, dataset, features, layer_meta):
    doc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": dataset,
            "source_service": SERVICE_ROOT,
            "source_layer_id": LAYER_ID,
            "source_layer_name": layer_meta.get("name"),
            "pulled_utc_date": time.strftime("%Y-%m-%d", time.gmtime()),
            "query": "where 1=1, no bounding-box clip — full national pull",
            "clip_method": "None — full service, object-id fetch, "
                           "chunk-verified; positions from GeoJSON "
                           "geometry requested with outSR=4326",
            "type_note": "wptType carried verbatim; no reclassification. "
                         "Camping split is an exact wptType == 'Camping' "
                         "match, nothing else.",
            "feature_count": len(features),
        },
        "features": features,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1))
    return path


def main():
    layer_url = f"{SERVICE_ROOT}/{LAYER_ID}"
    meta = get_json(SERVICE_ROOT, params={"f": "pjson"})
    layer_meta = next((l for l in meta.get("layers", [])
                       if l["id"] == LAYER_ID), {})
    print(f"Point layer         : id {LAYER_ID} - {layer_meta.get('name')}")

    raw = page_layer(layer_url)
    print(f"Fetched (by obj id) : {len(raw)}")

    features = []
    dropped = 0
    for f in raw:
        cf = clean_feature(f)
        if cf is None:
            dropped += 1
            continue
        features.append(cf)

    camping = [f for f in features
               if (f["properties"]["type"] or "") == "Camping"]
    places = [f for f in features
              if (f["properties"]["type"] or "") != "Camping"]
    camping.sort(key=lambda f: (f["properties"]["state"] or "",
                                f["properties"]["name"] or ""))
    places.sort(key=lambda f: (f["properties"]["type"] or "",
                               f["properties"]["state"] or "",
                               f["properties"]["name"] or ""))

    counts = Counter(f["properties"]["type"] for f in features)
    states = Counter(f["properties"]["state"] for f in features)
    chapters = Counter(f["properties"]["chapter"] for f in features)
    print(f"Retained            : {len(features)} (dropped {dropped} without geometry)")
    print(f"Camping             : {len(camping)}")
    print(f"Other places        : {len(places)}")
    print(f"Counts by type      : {dict(counts)}")
    print(f"Counts by state     : {dict(sorted(states.items(), key=lambda kv: str(kv[0])))}")
    print(f"Chapters present    : {len([c for c in chapters if c])} "
          f"(null chapter: {chapters.get(None, 0)})")
    print(f"Null-type features  : {counts.get(None, 0)} (kept in ncta-places)")
    print(f"Null-name features  : {sum(1 for f in features if not f['properties']['name'])}")

    write_fc(OUT_CAMPING,
             "NCTA camping waypoints, national (wptType == 'Camping')",
             camping, layer_meta)
    write_fc(OUT_PLACES,
             "NCTA places — all public waypoints except Camping, national",
             places, layer_meta)
    print(f"Wrote               : {OUT_CAMPING.relative_to(REPO_ROOT)} "
          f"({len(camping)} features)")
    print(f"Wrote               : {OUT_PLACES.relative_to(REPO_ROOT)} "
          f"({len(places)} features)")
    print("SUMMARY " + json.dumps({
        "features": len(features),
        "camping": len(camping),
        "places": len(places),
        "counts_by_type": {str(k): v for k, v in counts.items()},
        "counts_by_state": {str(k): v for k, v in states.items()},
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
