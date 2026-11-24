#!/usr/bin/env python3
"""Split the two oversized viewer layers into GitHub-Pages-safe chunks.

GitHub rejects files over 100 MB (100 MiB = 104,857,600 bytes), so
site/data/nwi-wetlands.geojson (181,713,702 B) and site/data/osm-roads.geojson
(113,632,365 B) could never be pushed and the live viewer 404'd on both.
This script splits them into chunks each safely under 100 MB (aim <=90 MB):

  nwi-wetlands.geojson (352,865 polygons) -> split by the `state` property:
    nwi-wetlands-mn.geojson      MN only
    nwi-wetlands-nd-mi.geojson   ND + MI
    nwi-wetlands-oh-ny.geojson   OH + NY
    nwi-wetlands-wi-vt-pa.geojson WI + VT + PA + state null (264 border
                                 waters whose centroid falls outside the
                                 state polygons)
  osm-roads.geojson (242,491 lines) -> split by centroid longitude at the
  median (-84.253), spatial coherence kept:
    osm-roads-west.geojson       centroid lon < -84.253
    osm-roads-east.geojson       centroid lon >= -84.253

The original single files stay in place, still gitignored (.gitignore):
they remain the local source of truth; only the chunks are committed.
site/app.js loads every chunk for the layer (files: [...]) and merges
them into one FeatureCollection before drawing, so the layer renders
identically. Re-run after any re-pull of either source file.

Usage: python3 scripts/split_oversized_layers.py [--verify-only]
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "site", "data")
MAX_BYTES = 90 * 1024 * 1024  # aim: comfortably under GitHub's 100 MiB cap

WETLAND_GROUPS = [
    ("nwi-wetlands-mn.geojson", {"MN"}),
    ("nwi-wetlands-nd-mi.geojson", {"ND", "MI"}),
    ("nwi-wetlands-oh-ny.geojson", {"OH", "NY"}),
    ("nwi-wetlands-wi-vt-pa.geojson", {"WI", "VT", "PA", None}),
]
ROAD_SPLIT_LON = -84.253  # median centroid longitude of the 242,491 lines


def write_chunk(path, metadata, features):
    fc = {"type": "FeatureCollection", "metadata": metadata,
          "features": features}
    with open(path, "w") as fh:
        json.dump(fc, fh, separators=(",", ":"))
    size = os.path.getsize(path)
    print(f"  {os.path.basename(path)}: {len(features)} features, "
          f"{size} B ({size / 1e6:.1f} MB)")
    if size > 100 * 1024 * 1024:
        raise SystemExit(f"CHUNK TOO BIG: {path} is {size} B — split finer")
    return size


def split_wetlands():
    src = os.path.join(DATA, "nwi-wetlands.geojson")
    print("wetlands:", src)
    with open(src) as fh:
        d = json.load(fh)
    total = len(d["features"])
    groups = {name: [] for name, _ in WETLAND_GROUPS}
    for f in d["features"]:
        st = f["properties"].get("state")
        for name, states in WETLAND_GROUPS:
            if st in states:
                groups[name].append(f)
                break
        else:
            raise SystemExit(f"unassigned state: {st!r}")
    seen = sum(len(v) for v in groups.values())
    assert seen == total, f"wetlands reconcile failed: {seen} != {total}"
    base_meta = dict(d.get("metadata") or {})
    for name, states in WETLAND_GROUPS:
        meta = dict(base_meta)
        meta["split"] = (f"Chunk of nwi-wetlands.geojson "
                         f"({total} features) — states "
                         f"{sorted(s for s in states if s) or ['(none)']}"
                         f"{' + state null (border waters)' if None in states else ''}; "
                         f"split by scripts/split_oversized_layers.py "
                         f"because GitHub rejects files over 100 MB.")
        write_chunk(os.path.join(DATA, name), meta, groups[name])
    print(f"  wetlands total reconciled: {seen} features")


def centroid_lon(geom):
    t = geom["type"]
    if t == "LineString":
        xs = [c[0] for c in geom["coordinates"]]
    elif t == "MultiLineString":
        xs = [c[0] for line in geom["coordinates"] for c in line]
    else:
        raise SystemExit(f"unexpected road geometry: {t}")
    return sum(xs) / len(xs)


def split_roads():
    src = os.path.join(DATA, "osm-roads.geojson")
    print("roads:", src)
    with open(src) as fh:
        d = json.load(fh)
    total = len(d["features"])
    west, east = [], []
    for f in d["features"]:
        (west if centroid_lon(f["geometry"]) < ROAD_SPLIT_LON
         else east).append(f)
    assert len(west) + len(east) == total
    base_meta = dict(d.get("metadata") or {})
    for name, feats, note in [
            ("osm-roads-west.geojson", west,
             "centroid longitude < -84.253 (median)"),
            ("osm-roads-east.geojson", east,
             "centroid longitude >= -84.253 (median)")]:
        meta = dict(base_meta)
        meta["split"] = (f"Chunk of osm-roads.geojson ({total} features) "
                         f"— {note}; split by "
                         f"scripts/split_oversized_layers.py because "
                         f"GitHub rejects files over 100 MB.")
        write_chunk(os.path.join(DATA, name), meta, feats)
    print(f"  roads total reconciled: {len(west) + len(east)} features "
          f"(west {len(west)}, east {len(east)})")


def verify():
    """Reload every chunk and check counts against the originals."""
    ok = True
    for src, chunks in [
            ("nwi-wetlands.geojson", [n for n, _ in WETLAND_GROUPS]),
            ("osm-roads.geojson",
             ["osm-roads-west.geojson", "osm-roads-east.geojson"])]:
        with open(os.path.join(DATA, src)) as fh:
            want = len(json.load(fh)["features"])
        got = 0
        for c in chunks:
            p = os.path.join(DATA, c)
            with open(p) as fh:
                n = len(json.load(fh)["features"])
            size = os.path.getsize(p)
            print(f"  {c}: {n} features, {size} B "
                  f"({'OK' if size <= MAX_BYTES else 'OVER 90 MB'})")
            ok &= size <= MAX_BYTES
            got += n
        print(f"  {src}: chunks sum {got} vs original {want} "
              f"({'OK' if got == want else 'MISMATCH'})")
        ok &= got == want
    return ok


if __name__ == "__main__":
    if "--verify-only" in sys.argv:
        raise SystemExit(0 if verify() else 1)
    split_wetlands()
    split_roads()
    print("verifying...")
    raise SystemExit(0 if verify() else 1)
