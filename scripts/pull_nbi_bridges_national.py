#!/usr/bin/env python3
"""Pull bridge structures along the full North Country Trail corridor,
pedestrian/mixed-use first, from the FHWA National Bridge Inventory
(NBI) 2025 — the national version of the Itasca Moraine chapter
viewer's scripts/pull_nbi_bridges.py
(~/workspace/itasca-trail-map/scripts/ — read-only source).

SOURCE: FHWA National Bridge Inventory 2025, all-records delimited
file (2025AllRecordsDelimitedAllStates.txt, from
2025allstatesallrecsdel.zip, 58 MB):
  https://www.fhwa.dot.gov/bridge/nbi/2025allstatesallrecsdel.zip
The all-records file is used, not the per-state highway-only files,
because pedestrian-only bridges (service on = 3) are non-highway
records and are absent from the highway files. NBI is the federal
inventory fed by the states from their own inspection systems, so
the structures and bridge numbers are the same inventory as the
state DOT bridge files. (ITM's intended source, the MnDOT
trans-bridges service, was unreachable from this VM on 2026-11-18;
the same substitution applies nationally — see SOURCES-step2.md.)

STATES: the ten states the NCT crosses — ND (38), MN (27), WI (55),
MI (26), OH (39), PA (42), NY (36), VT (50), NH (33), ME (23).
Only those states' records are extracted from the all-records file.

DEDUPE: one record per structure — keyed by (state, STRUCTURE_NUMBER_008),
preferring record type 1 (route on the structure). SERVICE_ON_042A is
consistent within a structure (verified for MN in ITM: 0 of 13,795
structures carry >1 distinct service-on code); the filter runs on
the kept record. nbi_records carries the merged record count.

COORDINATES: NBI LAT_016 / LONG_017 are DDMMSS.ss
(e.g. 45011920 = 45 deg 01' 19.20" N; 095472832 = 95 deg 47' 28.32"
W). Converted to decimal degrees here — note the seconds are two
digits plus two hundredths (an earlier ITM draft read them as a
plain float and shifted every point up to ~0.8 deg; this is the fix).

CORRIDOR: the NCT centerline in this repo
(site/data/centerline-natural.geojson + centerline-road.geojson +
centerline-urban.geojson). A bridge counts when its point is within
2 miles (3,218.69 m) of the line for Tier 1, within 0.25 mi (400 m)
for Tier 2 — the ITM rule. Distance is computed exactly in a local
tangent plane centred on each bridge (equirectangular at the bridge's
own latitude); a kilometre-projection STRtree pre-filter (generous
radii: 2.2 mi / 450 m) only selects candidates, never decides.
The national line spans UTM zones 14–19, so no single UTM zone is
used. dist_trail_km is the exact local distance, in km.

FILTERING (FHWA Recording and Coding Guide FHWA-PD-96-001,
Items 41/42/43):
  Tier 1 — pedestrian / mixed-use: SERVICE_ON_042A in
    {3 Pedestrian-bicycle, 5 Highway-pedestrian}, within 2 mi,
    and OPEN_CLOSED_POSTED_041 not in {K, G}.
  Tier 2 — vehicular bridges that are a plausible trail crossing
    [JUDGMENT, ITM's]: SERVICE_ON_042A = 1 Highway, within 0.25 mi
    (400 m) of the trail line, OPEN not in {K, G}. A 2-mi vehicular
    net would be every county-road bridge in the corridor and
    unreadable as a crossing-opportunities layer.
  Excluded by status in both tiers: K = bridge closed to all
    traffic, G = new structure not yet open to traffic. Blank OPEN
    codes are KEPT: the field does not apply to non-highway records,
    so a blank is not a closed bridge.
  Not carried: SERVICE_ON 2 Railroad, 4 Highway-railroad, 6/7/8
    interchange levels, 9 Building/plaza, 0 Other.

COUNTY NAMES: decoded from the U.S. Census TIGERweb State_County
service (NAME + COUNTY + STATE per state, fetched live at pull
time), not from a hand-kept table — the ten-state county list is
too large to maintain by hand. The "Saint Louis" FIPS quirk
(St. Louis MN = 137, before Scott 139) is handled by the lookup
itself.

FIELDS carried: as in ITM (bridge_number, facility_carried,
features_crossed, location, state, state_code, county,
county_code, district (raw state DOT district code), owner /
maintenance (decoded agency type), year_built,
year_reconstructed, structure_len_m, deck_width_m,
sidewalk_left_m / sidewalk_right_m (Item 50 curb/sidewalk widths —
the pedestrian accommodation on the structure), service_on /
service_under, open_closed, structure_kind, structure_type, tier,
dist_trail_km, nbi_records, source).

Output: site/data/nbi-bridges.geojson

Raw downloads are cached under working/bridges/ so re-runs do not
re-download the 58 MB zip.

Usage: python3 scripts/pull_nbi_bridges_national.py
"""

import csv
import io
import json
import math
import os
import sys
import time
import zipfile

import numpy as np
import requests

# shapely/pyproj live in the user site-packages on this VM
# (PYTHONNOUSERSITE=1); fall back to it when the plain import fails.
try:
    import shapely  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.expanduser(
        "~/.local/lib/python3.12/site-packages"))

from shapely.geometry import Point, shape  # noqa: E402
from shapely import transform as shp_transform  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (nct-full-viewer data pull)"}

ALLRECS_ZIP_URL = ("https://www.fhwa.dot.gov/bridge/nbi/"
                   "2025allstatesallrecsdel.zip")
ALLRECS_MEMBER = "2025AllRecordsDelimitedAllStates.txt"
WORKDIR = os.path.join(REPO, "working", "bridges")
ZIP_PATH = os.path.join(WORKDIR, "2025allstatesallrecsdel.zip")
HEADER_URL = ("https://www.fhwa.dot.gov/bridge/nbi/2025/delimited/"
              "MN25.txt")

CENTERLINE = [os.path.join(REPO, "site", "data", f)
              for f in ("centerline-natural.geojson",
                        "centerline-road.geojson",
                        "centerline-urban.geojson")]
BUFFER_M = 3218.69      # 2 miles, Tier 1
TIER2_M = 400.0         # 0.25 mi — vehicular bridges the trail passes
PREFILTER_T1_KM = 3.54  # 2.2 mi, generous (projection slack)
PREFILTER_T2_KM = 0.45  # 450 m, generous
OUT = os.path.join(REPO, "site", "data", "nbi-bridges.geojson")

# State FIPS -> (postal, name) for the ten NCT states.
STATES = {
    "38": ("ND", "North Dakota"), "27": ("MN", "Minnesota"),
    "55": ("WI", "Wisconsin"), "26": ("MI", "Michigan"),
    "39": ("OH", "Ohio"), "42": ("PA", "Pennsylvania"),
    "36": ("NY", "New York"), "50": ("VT", "Vermont"),
    "33": ("NH", "New Hampshire"), "23": ("ME", "Maine"),
}

# Kilometre equirectangular projection at 44 N, for the STRtree
# pre-filter only (never for the published distance).
KX = 111.320 * math.cos(math.radians(44.0))
KY = 111.195

SERVICE_ON = {
    "0": "Other", "1": "Highway", "2": "Railroad",
    "3": "Pedestrian-bicycle", "4": "Highway-railroad",
    "5": "Highway-pedestrian",
    "6": "Overpass structure at an interchange or second level",
    "7": "Third level (interchange)", "8": "Fourth level (interchange)",
    "9": "Building or plaza",
}
SERVICE_UNDER = {
    "0": "Other", "1": "Highway, with or without pedestrian",
    "2": "Railroad", "3": "Pedestrian-bicycle",
    "4": "Highway-railroad", "5": "Waterway",
    "6": "Highway-waterway", "7": "Railroad-waterway",
    "8": "Highway-waterway-railroad", "9": "Relief for waterway",
}
OPEN_CLOSED = {
    "A": "Open, no restriction",
    "B": "Open, posting recommended but not legally implemented",
    "D": "Open, would be posted except temporary shoring",
    "E": "Open, temporary structure",
    "G": "New structure not yet open to traffic",
    "K": "Bridge closed to all traffic",
    "P": "Posted for load",
    "R": "Posted for other load-capacity restriction",
}
AGENCY = {
    "01": "State Highway Agency", "02": "County Highway Agency",
    "03": "Town or Township Highway Agency",
    "04": "City or Municipal Highway Agency",
    "11": "State Park, Forest, or Reservation Agency",
    "12": "Local Park, Forest, or Reservation Agency",
    "21": "Other State Agencies", "25": "Other Local Agencies",
    "26": "Private (other than railroad)", "27": "Railroad",
    "31": "State Toll Authority", "32": "Local Toll Authority",
    "60": "Other Federal Agencies", "61": "Indian Tribal Government",
    "62": "Bureau of Indian Affairs",
    "63": "Bureau of Fish and Wildlife",
    "64": "U.S. Forest Service", "66": "National Park Service",
    "67": "Tennessee Valley Authority",
    "68": "Bureau of Land Management",
    "69": "Bureau of Reclamation",
    "70": "Corps of Engineers (Civil)",
    "71": "Corps of Engineers (Military)", "72": "Air Force",
    "73": "Navy/Marines", "74": "Army", "75": "NASA",
    "76": "Metropolitan Washington Airports Service",
    "80": "Unknown",
}
STRUCTURE_KIND = {
    "1": "Concrete", "2": "Concrete continuous", "3": "Steel",
    "4": "Steel continuous", "5": "Prestressed concrete",
    "6": "Prestressed concrete continuous", "7": "Wood or Timber",
    "8": "Masonry", "9": "Aluminum, Wrought Iron, or Cast Iron",
    "0": "Other",
}


def fetch(url, path, retries=3):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"using cached {path}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=300, stream=True)
            r.raise_for_status()
            with open(path, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
            print(f"downloaded {url} -> {path} "
                  f"({os.path.getsize(path)} bytes)")
            return
        except Exception as e:  # noqa: BLE001 — retry then raise
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise last_err


def fetch_county_names():
    """County FIPS -> name per NCT state, from Census TIGERweb."""
    base = ("https://tigerweb.geo.census.gov/arcgis/rest/services/"
            "TIGERweb/State_County/MapServer/1/query")
    lookup = {}
    for code in sorted(STATES):
        params = {"where": f"STATE='{code}'", "outFields": "NAME,COUNTY",
                  "returnGeometry": "false", "returnCountOnly": "true",
                  "f": "json"}
        n = requests.get(base, params=params, headers=UA,
                         timeout=120).json().get("count")
        params["returnCountOnly"] = "false"
        params["resultRecordCount"] = str(n)
        data = requests.get(base, params=params, headers=UA,
                            timeout=120).json()
        feats = data.get("features", [])
        if len(feats) != n:
            raise RuntimeError(f"TIGERweb state {code}: count {n}, "
                               f"fetched {len(feats)}")
        for f in feats:
            a = f["attributes"]
            lookup[(code, a["COUNTY"])] = a["NAME"].replace(
                " County", "").replace(" Parish", "")
        print(f"  counties {STATES[code][1]}: {len(feats)}")
    return lookup


def ddmmss_to_deg(s, lon=False):
    """NBI LAT_016 (DDMMSS.ss) / LONG_017 (DDDMMSS.ss) to decimal deg.

    The field is fixed-width with exactly two decimal digits on the
    seconds: lat is 8 chars DD MM SS ss, lon is 9 chars DDD MM SS ss.
    """
    s = s.strip()
    if lon:
        deg = int(s[:3])
        minutes = int(s[3:5])
        seconds = int(s[5:7]) + int(s[7:9]) / 100.0
    else:
        deg = int(s[:2])
        minutes = int(s[2:4])
        seconds = int(s[4:6]) + int(s[6:8]) / 100.0
    return deg + minutes / 60.0 + seconds / 3600.0


def num(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def unquote(s):
    """NBI delimited files quote text fields in single quotes
    ('MN 200'); strip one surrounding pair."""
    s = (s or "").strip()
    if len(s) >= 2 and s.startswith("'") and s.endswith("'"):
        return s[1:-1].strip()
    return s


def main():
    fetch(ALLRECS_ZIP_URL, ZIP_PATH)
    fetch(HEADER_URL, os.path.join(WORKDIR, "MN25_header.txt"))
    with open(os.path.join(WORKDIR, "MN25_header.txt")) as fh:
        header = fh.readline().strip().split(",")

    print("county names from TIGERweb:")
    counties = fetch_county_names()

    # Extract the ten NCT states' records from the all-records zip.
    state_txt = {c: os.path.join(WORKDIR, f"state_{c}_all.txt")
                 for c in STATES}
    need_extract = any(not (os.path.exists(p) and
                            os.path.getsize(p) > 0)
                       for p in state_txt.values())
    if need_extract:
        handles = {c: open(p, "w") for c, p in state_txt.items()}
        counts = {c: 0 for c in STATES}
        with zipfile.ZipFile(ZIP_PATH) as zf:
            with zf.open(ALLRECS_MEMBER) as raw:
                for line in io.TextIOWrapper(raw, errors="replace"):
                    code = line[:2]
                    if code in handles:
                        handles[code].write(line)
                        counts[code] += 1
        for h in handles.values():
            h.close()
        print("extracted records by state:", counts)
    else:
        print("using cached per-state extracts")

    # Dedupe by (state, structure number); prefer record type 1.
    structs = {}
    for code, path in state_txt.items():
        with open(path, newline="") as fh:
            reader = csv.DictReader(fh, fieldnames=header)
            for row in reader:
                key = (code, row["STRUCTURE_NUMBER_008"].strip())
                if key not in structs:
                    structs[key] = (row, 1)
                else:
                    prev, cnt = structs[key]
                    structs[key] = (prev, cnt + 1)
                    if (prev["RECORD_TYPE_005A"] != "1"
                            and row["RECORD_TYPE_005A"] == "1"):
                        structs[key] = (row, cnt + 1)
    print(f"distinct structures (10 states): {len(structs)}")

    # Corridor index: centerline pieces in km coords (pre-filter
    # only); exact distances are measured per bridge below.
    def _to_km(coords):
        import numpy as np
        return np.column_stack([coords[:, 0] * KX, coords[:, 1] * KY])

    pieces = []       # lon/lat, for exact per-bridge distances
    pieces_km = []    # km coords, STRtree pre-filter only
    for path in CENTERLINE:
        with open(path) as fh:
            gj = json.load(fh)
        for feat in gj["features"]:
            g = shape(feat["geometry"])
            if g.is_empty:
                continue
            geoms = list(g.geoms) if g.geom_type == "MultiLineString" \
                else [g]
            for part in geoms:
                pieces.append(part)
                pieces_km.append(shp_transform(part, _to_km))
    tree = STRtree(pieces_km)
    print(f"centerline pieces indexed: {len(pieces)}")

    def exact_dist_km(lon, lat, cand_idx):
        """Point-to-line distance (km) in a tangent plane centred on
        the bridge — exact to <0.1% locally. Uses the lon/lat pieces,
        NOT the km pre-filter pieces."""
        kx = 111.320 * math.cos(math.radians(lat))
        ky = 111.195
        origin = Point(0.0, 0.0)
        best = None
        for i in cand_idx:
            g = pieces[i]
            local = shp_transform(
                g, lambda c: np.column_stack(
                    [(c[:, 0] - lon) * kx, (c[:, 1] - lat) * ky]))
            d = origin.distance(local)
            if best is None or d < best:
                best = d
        return best

    kept = []
    counts = {"tier1": 0, "tier2": 0, "dropped_status": 0,
              "dropped_service": 0, "dropped_distance": 0,
              "bad_coords": 0}
    for (state_code, key), (row, nrec) in structs.items():
        try:
            lat = ddmmss_to_deg(row["LAT_016"])
            lon = -ddmmss_to_deg(row["LONG_017"], lon=True)
        except (ValueError, IndexError):
            counts["bad_coords"] += 1
            continue
        if not (-180 <= lon <= -60 and 25 <= lat <= 55):
            counts["bad_coords"] += 1
            continue
        service = row["SERVICE_ON_042A"].strip()
        status = row["OPEN_CLOSED_POSTED_041"].strip()
        if status in ("K", "G"):
            counts["dropped_status"] += 1
            continue
        if service in ("3", "5"):
            tier = 1
            pre = PREFILTER_T1_KM
            limit = BUFFER_M / 1000.0
        elif service == "1":
            tier = 2
            pre = PREFILTER_T2_KM
            limit = TIER2_M / 1000.0
        else:
            counts["dropped_service"] += 1
            continue
        pt_km = Point(lon * KX, lat * KY)
        cand = tree.query(pt_km, predicate="dwithin", distance=pre)
        if len(cand) == 0:
            counts["dropped_distance"] += 1
            continue
        dist_km = exact_dist_km(lon, lat, cand)
        if dist_km is None or dist_km > limit:
            counts["dropped_distance"] += 1
            continue
        if tier == 1:
            counts["tier1"] += 1
        else:
            counts["tier2"] += 1
        county_code = row["COUNTY_CODE_003"].strip()
        props = {
            "bridge_number": key,
            "facility_carried": unquote(row["FACILITY_CARRIED_007"]),
            "features_crossed": unquote(row["FEATURES_DESC_006A"]),
            "location": unquote(row["LOCATION_009"]),
            "state": STATES[state_code][1],
            "state_code": STATES[state_code][0],
            "county": counties.get((state_code, county_code),
                                   "County " + county_code),
            "county_code": county_code,
            "district": (row["HIGHWAY_DISTRICT_002"] or "").strip(),
            "owner": AGENCY.get(row["OWNER_022"].strip(),
                                "Code " + row["OWNER_022"].strip()),
            "owner_code": row["OWNER_022"].strip(),
            "maintenance": AGENCY.get(row["MAINTENANCE_021"].strip(),
                                      "Code " + row["MAINTENANCE_021"].strip()),
            "maintenance_code": row["MAINTENANCE_021"].strip(),
            "year_built": num(row["YEAR_BUILT_027"]),
            "year_reconstructed": num(row["YEAR_RECONSTRUCTED_106"]),
            "structure_len_m": num(row["STRUCTURE_LEN_MT_049"]),
            "deck_width_m": num(row["DECK_WIDTH_MT_052"]),
            "sidewalk_left_m": num(row["LEFT_CURB_MT_050A"]),
            "sidewalk_right_m": num(row["RIGHT_CURB_MT_050B"]),
            "service_on": SERVICE_ON.get(service, "Code " + service),
            "service_on_code": service,
            "service_under": SERVICE_UNDER.get(
                row["SERVICE_UND_042B"].strip(),
                "Code " + row["SERVICE_UND_042B"].strip()),
            "open_closed": (OPEN_CLOSED.get(status, "Not applicable")
                            if status else "Not applicable"),
            "open_closed_code": status,
            "structure_kind": STRUCTURE_KIND.get(
                row["STRUCTURE_KIND_043A"].strip(),
                "Code " + row["STRUCTURE_KIND_043A"].strip()),
            "structure_type": row["STRUCTURE_TYPE_043B"].strip(),
            "tier": tier,
            "dist_trail_km": round(dist_km, 2),
            "nbi_records": nrec,
            "source": "FHWA NBI 2025",
        }
        for k in ("year_built", "year_reconstructed"):
            if props[k] is not None:
                props[k] = int(props[k])
        kept.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": props,
        })

    kept.sort(key=lambda f: (f["properties"]["tier"],
                             f["properties"]["dist_trail_km"]))
    doc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("FHWA National Bridge Inventory 2025 — "
                        "crossing opportunities along the North Country "
                        "Trail (10 states)"),
            "source": ALLRECS_ZIP_URL,
            "pulled_utc_date": time.strftime("%Y-%m-%d", time.gmtime()),
            "corridor": ("2-mile corridor around site/data/"
                         "centerline-*.geojson for Tier 1 "
                         "(pedestrian/mixed-use); 400 m for Tier 2 "
                         "(highway bridges the trail passes)"),
            "feature_count": len(kept),
            "counts": counts,
        },
        "features": kept,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"wrote {len(kept)} features -> {OUT}")
    print("counts:", counts)
    from collections import Counter
    print("by tier:", Counter(f["properties"]["tier"] for f in kept))
    print("by state:",
          Counter(f["properties"]["state"] for f in kept).most_common())
    print("by service_on:",
          Counter(f["properties"]["service_on"] for f in kept))
    print("by open_closed:",
          Counter(f["properties"]["open_closed"] for f in kept))


if __name__ == "__main__":
    main()
