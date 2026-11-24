#!/usr/bin/env python3
"""Pull trail-corridor parcel CANDIDATES from one statewide parcel
service (Option A — statewide services only), normalize to the ITM
display schema, and write them as JSONL for the merge step.

This script does the FETCH only. Corridor selection (crossed parcels
+ the adjoining ring) happens in scripts/merge_parcels.py, globally
across all states, so a crossed parcel in one state can pull in an
adjoining parcel from the neighbouring state.

Sources (verified live 2026-11-24; re-verified at pull time — the
script fails loudly if a layer moved): see STATES below, and
parcels-scope-2026-11-23.md + the three state files in
~/workspace/nct-parcels-scope/ for the evidence base.

Method (ITM pull_parcels_corridor.py + the national NWI pull):
- Candidates: parcels intersecting the 2.5 km band around the NCT
  centerline, queried per 0.25-degree cell whose slice of the band
  is non-empty (NWI pattern). Per cell, returnIdsOnly first, then
  fetch by object-id chunks of 400 with per-chunk count verification
  (the ITM pattern — offset-paged envelope queries on the MnGeo host
  silently truncate, so fetching is by id).
- County filter where the service carries a county field (MN co_name,
  ND CountyName, WI CONAME, NY COUNTY_NAME, OH county). VT has no
  county field — the whole corridor band is queried and the county is
  derived from TIGER in the merge step.
- Output keeps ONLY the ITM display fields (parcel_id, county, state,
  land_class, acres, owner, owner_address) plus source/vintage/src_oid.
  Taxpayer fields (values, taxes, EMV, assessment) are NEVER pulled:
  outFields names exactly the fields the mapping needs.
- Resumable: per-county JSONL append + a done-counties checkpoint, so
  a stall (notably the slow OH service) resumes instead of restarting.

Usage:
  python3 scripts/pull_parcels_state.py ND|MN|WI|VT|NY|OH
  (re-run safely resumes unfinished counties)
"""

import json
import math
import os
import sys
import time

import requests

try:
    import shapely  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.expanduser(
        "~/.local/lib/python3.12/site-packages"))

from shapely.geometry import box as _box  # noqa: E402
from shapely.geometry import mapping, shape  # noqa: E402
from shapely.geometry import Polygon as _Polygon  # noqa: E402
from shapely.geometry import MultiPolygon as _MultiPolygon  # noqa: E402
from shapely.geometry.polygon import orient as _orient  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from shapely.ops import transform as _transform  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(REPO, "working", "parcels")
UA = {"User-Agent": "Mozilla/5.0 (nct-full-viewer data pull)"}
PULLED = time.strftime("%Y-%m-%d", time.gmtime())

BUFFER_KM = 2.5  # candidate band around the line (ITM CANDIDATE_MARGIN_KM)
CELL_DEG = 0.25
WIDEN_KM = 0.5  # query geometry is widened so it is a superset; the
# exact selection happens in Python in the merge step.
ID_CHUNK = 400
KX = 111.320 * math.cos(math.radians(44.0))  # km per deg lon at 44 N
KY = 111.195  # km per degree lat

# ---------------------------------------------------------------- states
# outFields names ONLY the fields the mapping needs (taxpayer fields
# are never requested). county_field=None means no per-county filter
# (VT: no county field on the service).
STATES = {
    "ND": {
        "url": ("https://services1.arcgis.com/GOcSXpzwBHyk2nog/arcgis/rest/"
                "services/NDGISHUB_Parcels/FeatureServer"),
        "layer": 0, "oid": "OBJECTID", "county_field": "CountyName",
        "counties": ["Ransom", "McLean", "Barnes", "Sheridan", "Griggs",
                     "Richland", "Wells", "Eddy", "Foster", "Burleigh",
                     "Mercer", "Steele"],
        "fields": ["GISID", "UniqueGISID", "CountyName", "CalculatedAcres",
                   "Ownership", "SourceDate", "LastUpdateDate"],
        "source": "ND GIS Hub statewide parcels (NDGISHUB_Parcels)",
        "vintage": "Per-county, monthly to yearly; service modified "
                   "2026-11-23; per-parcel SourceDate/LastUpdateDate "
                   "recorded at pull time",
    },
    "MN": {
        "url": ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
                "us_mn_state_mngeo/plan_parcels_open/FeatureServer"),
        "layer": 0, "oid": "objectid", "county_field": "co_name",
        "counties": ["Cook", "St. Louis", "Lake", "Otter Tail", "Cass",
                     "Itasca", "Becker", "Wilkin", "Carlton", "Clearwater"],
        "fields": ["county_pin", "state_pin", "co_name", "useclass1",
                   "xuseclass1", "ownership", "acres_poly", "acres_deed",
                   "owner_name", "own_add_l1", "own_add_l2", "own_add_l3",
                   "own_add_l4"],
        "source": "MnGeo parcels, compiled from opt-in open-data "
                  "counties (quarterly snapshot)",
        "vintage": "Quarterly snapshot; live service rundate 2026-11-09; "
                   "per-county acqdate recorded at pull time",
        "meta_layer": 1,
    },
    "WI": {
        "url": ("https://services3.arcgis.com/n6uYoouQZW75n5WI/arcgis/rest/"
                "services/Wisconsin_Statewide_Parcels_DB/FeatureServer"),
        "layer": 0, "oid": "OBJECTID", "county_field": "CONAME",
        "counties": ["Douglas", "Bayfield", "Ashland", "Iron"],
        "fields": ["PARCELID", "TAXPARCELID", "PROPCLASS", "GISACRES",
                   "ASSDACRES", "OWNERNME1", "OWNERNME2", "PSTLADRESS",
                   "CONAME", "LOADDATE", "TAXROLLYEAR"],
        "source": "Wisconsin Statewide Parcel Map Database V12 (2026)",
        "vintage": "V12 released 2026-06-30, annual; tax roll mostly 2025",
    },
    "VT": {
        "url": ("https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/"
                "services/FS_VCGI_VTPARCELS_WM_NOCACHE_v2/FeatureServer"),
        "layer": 1, "oid": "OBJECTID", "county_field": None,
        "counties": ["Addison", "Rutland", "Windsor"],
        "fields": ["SPAN", "MAPID", "DESCPROP", "ACRESGL", "OWNER1",
                   "OWNER2", "ADDRGL1", "ADDRGL2", "CITYGL", "STGL",
                   "ZIPGL", "TOWN", "SOURCEDATE", "GLYEAR"],
        "source": "VCGI Parcel Program (statewide)",
        "vintage": "Weekly updates; 2025 grand list joined",
    },
    "NY": {
        "url": ("https://services6.arcgis.com/EbVsqZ18sv1kVJ3k/arcgis/rest/"
                "services/NYS_Tax_Parcels_Public/FeatureServer/"),
        "layer": 1, "oid": "OBJECTID", "county_field": "COUNTY_NAME",
        "counties": ["Cortland", "Steuben", "Oneida", "Hamilton",
                     "Tompkins", "Schuyler", "Warren", "Onondaga",
                     "Livingston", "Wyoming", "Tioga"],
        "fields": ["SBL", "PRINT_KEY", "COUNTY_NAME", "PROP_CLASS",
                   "ACRES", "CALC_ACRES", "PRIMARY_OWNER", "MAIL_ADDR",
                   "MAIL_CITY", "MAIL_STATE", "MAIL_ZIP", "ADD_OWNER",
                   "ROLL_YR", "SPATIAL_YR"],
        "source": "NYS ITS NYS_Tax_Parcels_Public (2025 data, pub. May 2026)",
        "vintage": "2025 data, published May 2026, annual",
    },
    "OH": {
        "url": ("https://gis.ohiodnr.gov/hosting/rest/services/Hosted/"
                "Statewide_Parcels_ODNR_WebMerc/FeatureServer"),
        "layer": 10, "oid": "objectid", "county_field": "county",
        "counties": ["Adams", "Morgan", "Washington", "Columbiana",
                     "Clermont", "Noble", "Hocking", "Brown", "Harrison",
                     "Pike", "Ross", "Guernsey", "Greene", "Warren",
                     "Fulton", "Miami", "Carroll", "Lucas", "Tuscarawas",
                     "Scioto", "Shelby", "Auglaize", "Henry", "Perry",
                     "Montgomery", "Paulding", "Monroe", "Defiance",
                     "Vinton", "Putnam", "Athens", "Williams", "Highland",
                     "Allen", "Stark", "Hamilton", "Van Wert", "Belmont"],
        "fields": ["pin", "statewide_pin", "county", "assr_acres",
                   "calc_acres", "owner1", "owner2", "currentto"],
        "source": "OGRIP/ODNR statewide parcels (Statewide_Parcels_ODNR_WebMerc)",
        "vintage": "2023-vintage snapshot (per-parcel currentto "
                   "Jan 2023–Mar 2024); no refresh cadence stated",
    },
}

# NY ORPTS property-class series (published): first digit of PROP_CLASS.
NY_CLASS_SERIES = {
    "1": "Agricultural", "2": "Residential", "3": "Vacant land",
    "4": "Commercial", "5": "Recreation & entertainment",
    "6": "Community services", "7": "Industrial",
    "8": "Public services",
    "9": "Wild, forested, conservation lands & public parks",
}
# WI property-class codes (SCO V12 schema): 1 Residential, 2 Commercial,
# 3 Manufacturing, 4 Agricultural, 5 Undeveloped, 5m Agricultural forest,
# 6 Productive forest, 7 Other.
WI_CLASS = {
    "1": "Residential", "2": "Commercial", "3": "Manufacturing",
    "4": "Agricultural", "5": "Undeveloped",
    "5m": "Agricultural forest", "6": "Productive forest",
    "7": "Other",
}


def clean_str(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def num(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(float(v), 2)
    return None


def join_parts(vals, sep=" "):
    parts = [clean_str(v) for v in vals]
    parts = [x for x in parts if x]
    return sep.join(parts) or None


def fetch_json(url, params=None, retries=4, post=False, timeout=300):
    last_err = None
    for attempt in range(retries):
        try:
            if post:
                r = requests.post(url, data=params, headers=UA, timeout=timeout)
            else:
                r = requests.get(url, params=params, headers=UA, timeout=timeout)
            r.raise_for_status()
            d = r.json()
            if isinstance(d, dict) and "error" in d:
                raise RuntimeError("service error: %s" % (d["error"],))
            return d
        except Exception as e:  # noqa: BLE001 - report after retries
            last_err = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("request failed after %d tries: %s"
                       % (retries, last_err))


def to_km_geom(geom):
    return _transform(lambda x, y: (x * KX, y * KY), geom)


def to_lonlat_geom(geom):
    return _transform(lambda x, y: (x / KX, y / KY), geom)


def arcgis_rings(geom):
    """Shapely (Multi)Polygon -> ArcGIS JSON rings (exterior clockwise)."""
    rings = []
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    for pg in polys:
        pg = _orient(pg, sign=-1.0)
        rings.append([[round(x, 5), round(y, 5)]
                      for x, y in pg.exterior.coords])
        for hole in pg.interiors:
            rings.append([[round(x, 5), round(y, 5)]
                          for x, y in hole.coords])
    return rings


def load_corridor():
    """Centerline pieces + per-piece 2.5 km buffers (km coords), indexed.
    Never builds one whole-line union (OOM — see the NWI pull header)."""
    pieces = []
    buffers_km = []
    for fn in ("centerline-natural.geojson", "centerline-road.geojson",
               "centerline-urban.geojson"):
        with open(os.path.join(REPO, "site", "data", fn)) as fh:
            gj = json.load(fh)
        for feat in gj["features"]:
            g = shape(feat["geometry"])
            if g.is_empty:
                continue
            geoms = list(g.geoms) if g.geom_type == "MultiLineString" else [g]
            for part in geoms:
                pieces.append(part)
                buffers_km.append(to_km_geom(part).buffer(BUFFER_KM))
    tree = STRtree(buffers_km)
    env = [min(p.bounds[0] for p in pieces),
           min(p.bounds[1] for p in pieces),
           max(p.bounds[2] for p in pieces),
           max(p.bounds[3] for p in pieces)]
    print(f"corridor pieces: {len(pieces)}; envelope lon {env[0]:.4f}.."
          f"{env[2]:.4f} lat {env[1]:.4f}..{env[3]:.4f}", flush=True)
    return pieces, buffers_km, tree, env


def corridor_slice_lonlat(cell, buffers_km, tree):
    """The cell's slice of the corridor band, widened 0.5 km (a superset
    of the exact band — selection happens in Python in the merge step).
    Returns None when the cell holds no corridor."""
    cell_km = to_km_geom(cell)
    idx = tree.query(cell_km, predicate="intersects")
    if len(idx) == 0:
        return None
    union = unary_union([buffers_km[i] for i in idx])
    inter = union.intersection(cell_km)
    if inter.is_empty:
        return None
    widened = inter.buffer(WIDEN_KM)
    if not widened.is_valid:
        from shapely import make_valid
        widened = make_valid(widened)
    return to_lonlat_geom(widened)


def cells_for_bbox(env, buffers_km, tree):
    """0.25-degree cells in env whose corridor slice is non-empty."""
    cells = []
    x = math.floor(env[0] / CELL_DEG) * CELL_DEG
    while x < env[2]:
        y = math.floor(env[1] / CELL_DEG) * CELL_DEG
        while y < env[3]:
            cell = _box(x, y, min(x + CELL_DEG, env[2]),
                        min(y + CELL_DEG, env[3]))
            cells.append(cell)
            y += CELL_DEG
        x += CELL_DEG
    out = []
    for cell in cells:
        sl = corridor_slice_lonlat(cell, buffers_km, tree)
        if sl is not None:
            out.append((cell, sl))
    return out


def query_ids(layer_url, where, slice_geom, depth=0):
    """Object ids intersecting one cell's corridor slice. Cross-checks
    against the service's returnCountOnly; splits the cell when the
    count disagrees (truncation guard)."""
    rings = arcgis_rings(slice_geom)
    geom = {"rings": rings, "spatialReference": {"wkid": 4326}}
    base = {"geometry": json.dumps(geom),
            "geometryType": "esriGeometryPolygon", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects"}
    count = fetch_json(layer_url + "/query",
                       dict(base, where=where, returnCountOnly="true",
                            f="json"), post=True).get("count")
    data = fetch_json(layer_url + "/query",
                      dict(base, where=where, returnIdsOnly="true",
                           f="json"), post=True)
    ids = data.get("objectIds") or []
    if count is not None and len(ids) != count:
        if depth >= 3:
            raise RuntimeError(
                "cell id list truncated (%d ids vs count %d) and too deep "
                "to split" % (len(ids), count))
        # Split the cell into quadrants and recurse.
        minx, miny, maxx, maxy = slice_geom.bounds
        mx, my = (minx + maxx) / 2.0, (miny + maxy) / 2.0
        out = []
        for quad in (_box(minx, miny, mx, my), _box(mx, miny, maxx, my),
                     _box(minx, my, mx, maxy), _box(mx, my, maxx, maxy)):
            q = quad.intersection(slice_geom)
            if q.is_empty or q.geom_type not in (
                    "Polygon", "MultiPolygon"):
                continue
            out.extend(query_ids(layer_url, where, q, depth + 1))
        return out
    return ids


def fetch_chunk(layer_url, oid_field, out_fields, ids):
    """Fetch features for one chunk of object ids; verify the count and
    split the chunk if the server returns fewer than asked (ITM
    pattern — offset-paged queries silently truncate on some hosts)."""
    where = "%s IN (%s)" % (oid_field, ",".join(str(i) for i in ids))
    params = {"where": where, "outFields": ",".join(out_fields),
              "outSR": "4326", "f": "geojson", "returnGeometry": "true"}
    # POST, not GET: a 400-id where clause overflows the server's URL
    # length limit (404 on ArcGIS Online).
    data = fetch_json(layer_url + "/query", params=params, post=True)
    feats = data.get("features", [])
    if len(feats) != len(ids):
        if len(ids) == 1:
            raise RuntimeError(
                "feature %s could not be fetched from %s"
                % (ids[0], layer_url))
        mid = len(ids) // 2
        return fetch_chunk(layer_url, oid_field, out_fields, ids[:mid]) + \
            fetch_chunk(layer_url, oid_field, out_fields, ids[mid:])
    return feats


def normalize(state, raw):
    """Raw service attributes -> the ITM display schema. Taxpayer fields
    are never in outFields, so they cannot leak in here."""
    a = raw or {}
    src = STATES[state]["source"]
    if state == "ND":
        return {
            "parcel_id": clean_str(a.get("GISID")),
            "county": clean_str(a.get("CountyName")),
            "state": "ND",
            "land_class": clean_str(a.get("Ownership")),
            "acres": num(a.get("CalculatedAcres")),
            "owner": None,  # layer 0 carries no owner fields (tax-roll
            # join deliberately not pulled — ITM model)
            "owner_address": None,
            "source": src,
            "vintage": STATES[state]["vintage"],
        }
    if state == "MN":
        return {
            "parcel_id": (clean_str(a.get("county_pin"))
                          or clean_str(a.get("state_pin"))),
            "county": clean_str(a.get("co_name")),
            "state": "MN",
            "land_class": (clean_str(a.get("useclass1"))
                           or clean_str(a.get("xuseclass1"))
                           or clean_str(a.get("ownership"))),
            "acres": num(a.get("acres_poly")) or num(a.get("acres_deed")),
            "owner": clean_str(a.get("owner_name")),
            "owner_address": join_parts([a.get("own_add_l1"),
                                         a.get("own_add_l2"),
                                         a.get("own_add_l3"),
                                         a.get("own_add_l4")], sep=", "),
            "source": src,
            "vintage": STATES[state]["vintage"],
        }
    if state == "WI":
        code = clean_str(a.get("PROPCLASS"))
        land_class = None
        if code:
            label = WI_CLASS.get(code)
            land_class = (label + " (class " + code + ")") if label \
                else "Class " + code
        return {
            "parcel_id": (clean_str(a.get("PARCELID"))
                          or clean_str(a.get("TAXPARCELID"))),
            "county": clean_str(a.get("CONAME")),
            "state": "WI",
            "land_class": land_class,
            "acres": num(a.get("GISACRES")) or num(a.get("ASSDACRES")),
            "owner": join_parts([a.get("OWNERNME1"), a.get("OWNERNME2")],
                                sep=" / "),
            "owner_address": clean_str(a.get("PSTLADRESS")),
            "source": src,
            "vintage": STATES[state]["vintage"],
        }
    if state == "VT":
        return {
            "parcel_id": clean_str(a.get("SPAN")) or clean_str(a.get("MAPID")),
            "county": None,  # derived from TIGER in the merge step
            "state": "VT",
            "land_class": clean_str(a.get("DESCPROP")),
            "acres": num(a.get("ACRESGL")),
            "owner": join_parts([a.get("OWNER1"), a.get("OWNER2")],
                                sep=" / "),
            "owner_address": join_parts([
                join_parts([a.get("ADDRGL1"), a.get("ADDRGL2")], sep=", "),
                join_parts([a.get("CITYGL"),
                            join_parts([a.get("STGL"), a.get("ZIPGL")],
                                       sep=" ")], sep=", ")], sep=", "),
            "source": src,
            "vintage": STATES[state]["vintage"],
        }
    if state == "NY":
        code = clean_str(a.get("PROP_CLASS"))
        land_class = None
        if code:
            series = NY_CLASS_SERIES.get(code[0])
            land_class = ((series + " (class " + code + ")") if series
                          else "Class " + code)
        return {
            "parcel_id": clean_str(a.get("SBL")) or clean_str(a.get("PRINT_KEY")),
            "county": clean_str(a.get("COUNTY_NAME")),
            "state": "NY",
            "land_class": land_class,
            "acres": num(a.get("ACRES")) or num(a.get("CALC_ACRES")),
            "owner": clean_str(a.get("PRIMARY_OWNER")),
            "owner_address": join_parts([
                clean_str(a.get("MAIL_ADDR")),
                join_parts([a.get("MAIL_CITY"),
                            join_parts([a.get("MAIL_STATE"),
                                        a.get("MAIL_ZIP")], sep=" ")],
                           sep=", ")], sep=", "),
            "source": src,
            "vintage": STATES[state]["vintage"],
        }
    if state == "OH":
        return {
            "parcel_id": (clean_str(a.get("pin"))
                          or clean_str(a.get("statewide_pin"))),
            "county": clean_str(a.get("county")),
            "state": "OH",
            "land_class": None,  # no class field on the statewide service
            "acres": num(a.get("assr_acres")) or num(a.get("calc_acres")),
            "owner": join_parts([a.get("owner1"), a.get("owner2")],
                                sep=" / "),
            "owner_address": None,  # no mailing-address field on the service
            "source": src,
            "vintage": STATES[state]["vintage"],
        }
    raise ValueError("unknown state %s" % state)


def county_bboxes():
    """Trail-county bounding boxes from the scope intersection file
    (TIGER 2024 counties, EPSG:5070 -> lon/lat via the scope's
    counties_5070.geojson is 5070; here we read county_miles.csv for
    the county list and bound boxes from the TIGER shapefile through
    the scope's counties_5070.geojson with a 5070->4326 transform)."""
    import pyproj
    from shapely.ops import transform as _t
    to4326 = pyproj.Transformer.from_crs(
        "EPSG:5070", "EPSG:4326", always_xy=True).transform
    path = os.path.expanduser(
        "~/workspace/nct-parcels-scope/counties_5070.geojson")
    with open(path) as fh:
        gj = json.load(fh)
    out = {}
    for feat in gj["features"]:
        p = feat["properties"]
        key = (p.get("STUSPS"), p.get("NAME"))
        g = _t(to4326, shape(feat["geometry"]))
        out[key] = g.bounds
    return out


def mn_metadata(cfg):
    """Per-county acqdate/rundate from the MnGeo metadata layer."""
    try:
        url = cfg["url"] + "/1/query"
        # Layer 1's county field is `countyname`, NOT `co_name`
        # (layer 0's field) — querying co_name 400s (found 2026-11-24).
        where = "countyname IN (%s)" % ",".join(
            "'%s'" % c for c in cfg["counties"])
        d = fetch_json(url, {"where": where,
                             "outFields": "countyname,acqdate,rundate,"
                                          "gac_open_approval",
                             "returnGeometry": "false", "f": "json"})
        rows = {}
        for f in d.get("features", []):
            a = f.get("attributes", {})
            rows[a.get("countyname")] = {
                "acqdate": a.get("acqdate"),
                "rundate": a.get("rundate"),
                "opt_in": a.get("gac_open_approval"),
            }
        return rows
    except Exception as e:  # noqa: BLE001 - metadata is nice-to-have
        print("WARNING: MN metadata layer unreadable: %s" % e, flush=True)
        return {}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in STATES:
        print("usage: pull_parcels_state.py ND|MN|WI|VT|NY|OH", file=sys.stderr)
        return 2
    state = sys.argv[1]
    cfg = STATES[state]
    os.makedirs(WORK, exist_ok=True)
    layer_url = cfg["url"] + "/%d" % cfg["layer"]
    out_jsonl = os.path.join(WORK, "raw-%s.jsonl" % state)
    done_path = os.path.join(WORK, "done-%s.json" % state)
    log_path = os.path.join(WORK, "pull-%s.log" % state)
    vintage_path = os.path.join(WORK, "vintage-%s.json" % state)

    # Re-verify the service at pull time (services change — Kent).
    info = fetch_json(layer_url + "?f=json")
    print("service: %s (layer %d %s, maxRecordCount %s, oid %s)"
          % (cfg["url"], cfg["layer"], info.get("name"),
             info.get("maxRecordCount"), info.get("objectIdField")),
          flush=True)
    if info.get("objectIdField") != cfg["oid"]:
        print("WARNING: oid field is %s, config says %s"
              % (info.get("objectIdField"), cfg["oid"]), flush=True)
    if state == "MN":
        meta = mn_metadata(cfg)
        print("MN metadata: %s" % json.dumps(meta), flush=True)
        with open(vintage_path, "w") as fh:
            json.dump({"state": "MN", "pulled": PULLED,
                       "per_county": meta}, fh, indent=1)

    done = set()
    if os.path.exists(done_path):
        done = set(json.load(open(done_path)))
    print("resuming: %d counties already done: %s"
          % (len(done), sorted(done)), flush=True)
    # Resume hazard (found 2026-11-24, NY pull): a kill mid-county
    # leaves a partial county in the JSONL with no checkpoint, and a
    # naive re-run would re-append it as duplicates. So on resume,
    # load the src_oids already written and skip them when appending.
    existing_oids = set()
    if os.path.exists(out_jsonl):
        with open(out_jsonl) as fh:
            for line in fh:
                try:
                    existing_oids.add(
                        json.loads(line)["properties"].get("src_oid"))
                except Exception:  # noqa: BLE001 - tolerate a torn line
                    pass
    print("resuming: %d features already in %s"
          % (len(existing_oids), out_jsonl), flush=True)

    _, buffers_km, tree, _env = load_corridor()
    bboxes = county_bboxes()
    stusps = {"ND": "ND", "MN": "MN", "WI": "WI", "VT": "VT",
              "NY": "NY", "OH": "OH"}

    log = open(log_path, "a")
    def note(msg):
        print(msg, flush=True)
        log.write(msg + "\n")
        log.flush()

    total_ids = 0
    total_feats = 0
    skipped_geom = 0
    skipped_dupes = 0
    vintage_seen = {}
    for county in cfg["counties"]:
        if county in done:
            continue
        key = (stusps[state], county)
        if key not in bboxes:
            note("WARNING: %s %s has no TIGER bbox — skipping" % (state, county))
            continue
        bbox = bboxes[key]
        cells = cells_for_bbox(bbox, buffers_km, tree)
        if cfg["county_field"]:
            where = "%s='%s'" % (cfg["county_field"],
                                 county.replace("'", "''"))
        else:
            where = "1=1"
        ids = set()
        for cell, sl in cells:
            # Simplify the slice so the query geometry stays small;
            # widening (0.5 km) already made it a superset.
            try:
                sl_simple = sl.simplify(0.0005, preserve_topology=True)
            except Exception:  # noqa: BLE001
                sl_simple = sl
            if sl_simple.is_empty or sl_simple.geom_type not in (
                    "Polygon", "MultiPolygon"):
                continue
            ids.update(query_ids(layer_url, where, sl_simple))
        note("%s %s: %d corridor cells, %d candidate ids"
             % (state, county, len(cells), len(ids)))
        total_ids += len(ids)
        n_written = 0
        id_list = sorted(ids)
        with open(out_jsonl, "a") as out:
            for i in range(0, len(id_list), ID_CHUNK):
                chunk = id_list[i:i + ID_CHUNK]
                # The oid field rides along in outFields (not a display
                # field) so src_oid is real — ArcGIS GeoJSON does not
                # carry the object id unless it is requested.
                feats = fetch_chunk(layer_url, cfg["oid"],
                                    cfg["fields"] + [cfg["oid"]], chunk)
                for feat in feats:
                    geom = feat.get("geometry")
                    if not geom or geom.get("type") not in (
                            "Polygon", "MultiPolygon"):
                        skipped_geom += 1
                        continue
                    props = normalize(state, feat.get("properties") or {})
                    props["src_oid"] = "%s:%s" % (
                        state, feat.get("properties", {}).get(cfg["oid"]))
                    if props["src_oid"] in existing_oids:
                        # Already written by an interrupted earlier run
                        # (resume hazard) — skip the duplicate.
                        skipped_dupes += 1
                        continue
                    existing_oids.add(props["src_oid"])
                    # Vintage evidence carried per feature where present.
                    raw = feat.get("properties") or {}
                    for vk in ("LastUpdateDate", "SourceDate", "LOADDATE",
                               "SOURCEDATE", "currentto"):
                        if raw.get(vk):
                            vintage_seen.setdefault(vk, set()).add(
                                str(raw[vk]))
                    out.write(json.dumps(
                        {"type": "Feature", "geometry": geom,
                         "properties": props}) + "\n")
                    n_written += 1
        total_feats += n_written
        done.add(county)
        with open(done_path, "w") as fh:
            json.dump(sorted(done), fh)
        note("%s %s: wrote %d features" % (state, county, n_written))

    summary = {
        "state": state, "pulled": PULLED,
        "service": cfg["url"], "layer": cfg["layer"],
        "candidate_ids": total_ids, "features_written": total_feats,
        "skipped_non_polygon": skipped_geom,
        "skipped_already_written": skipped_dupes,
        "counties_done": sorted(done),
        "vintage_seen": {k: sorted(v)[:5] + (["..."] if len(v) > 5 else [])
                         for k, v in vintage_seen.items()},
        "raw_file": out_jsonl,
    }
    note("SUMMARY " + json.dumps(summary))
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
