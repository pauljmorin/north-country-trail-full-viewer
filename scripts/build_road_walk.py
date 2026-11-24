#!/usr/bin/env python3
"""Build the Road walk layer: the centerline's road class as its own layer.

Output: site/data/road-walk.geojson — LineString features, one per
maximal contiguous run of road-class edges along the ordered west->east
chain (a run breaks at a non-road edge or at a chain gap over 100 m).
Each feature carries the ITM road-walk popup pattern insofar as the
source supports it: segment name, length, surface, plus the chainage
range and the chapters/states it spans.

What the source does NOT carry, this layer does NOT invent: the
centerline features carry no road names, so no road name is given;
no speed limits, shoulder widths, or crash data are attached — those
are undecided measurement programs (plan §3) and stay out.

Method: chainlib.walk_chain; see site/data/SOURCES-step3.md.

Usage: python3 scripts/build_road_walk.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chainlib  # noqa: E402

OUT_PATH = chainlib.DATA_DIR / "road-walk.geojson"
RUN_BREAK_JUMP_M = 100.0


def main():
    edges, stats = chainlib.load_edges()
    walk = chainlib.walk_chain(edges)
    order = walk["order"]
    total = walk["total_mi"]

    # Map (order position) -> jump distance into that edge, if any.
    jump_into = {}
    for (cum, _fr, _to, dist, _c1, _c2, _kind), pos in zip(
            walk["jumps"], _jump_positions(walk, order)):
        jump_into[pos] = dist

    # Collect maximal runs of consecutive road edges.
    runs = []  # (list of (edge_idx, entry_end, start_mi, end_mi))
    current = None
    for pos, (idx, entry_end, start_mi, end_mi) in enumerate(order):
        edge = edges[idx]
        if edge["cls"] != "road":
            current = None
            continue
        if current is None:
            current = []
            runs.append(current)
        elif jump_into.get(pos, 0.0) > RUN_BREAK_JUMP_M:
            current = []
            runs.append(current)
        current.append((idx, entry_end, start_mi, end_mi))

    features = []
    dropped_zero = 0
    for run in runs:
        coords = []
        chapters = []
        states = []
        for idx, entry_end, _s, _e in run:
            edge = edges[idx]
            oriented = (edge["coords"] if entry_end == 0
                        else list(reversed(edge["coords"])))
            for pt in oriented:
                if coords and abs(coords[-1][0] - pt[0]) < 1e-9 \
                        and abs(coords[-1][1] - pt[1]) < 1e-9:
                    continue
                coords.append(pt)
            if edge["chapter"] not in chapters:
                chapters.append(edge["chapter"])
            if edge["state"] not in states:
                states.append(edge["state"])
        length_mi = run[-1][3] - run[0][2]
        if length_mi < 0.005:
            # A sub-26-foot road sliver (a class-boundary artifact
            # with a 0.00 mi `miles` value) is not a road-walk segment:
            # it would render as a dot with a "0.00 mi" popup.
            dropped_zero += 1
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [chainlib.round_pt(pt) for pt in coords],
            },
            "properties": {
                "kind": "line",
                "segment": "Road walk %03d" % (len(features) + 1),
                "surface": "road",
                "length_mi": round(length_mi, 2),
                "chain_start_mi": round(run[0][2], 2),
                "chain_end_mi": round(run[-1][3], 2),
                "chapters": chapters,
                "states": states,
                "source": "NCT centerline, class = road "
                          "(site/data/centerline-road.geojson), ordered "
                          "west to east by the chain walk",
            },
        })

    out = {"type": "FeatureCollection", "features": features}
    OUT_PATH.write_text(json.dumps(out, indent=1) + "\n")

    # ---- self-checks
    road_total = sum(f["properties"]["length_mi"] for f in features)
    assert all(len(f["geometry"]["coordinates"]) >= 2 for f in features)
    assert all(f["properties"]["chain_end_mi"]
               >= f["properties"]["chain_start_mi"] for f in features)
    chainages = [(f["properties"]["chain_start_mi"],
                  f["properties"]["chain_end_mi"]) for f in features]
    assert chainages == sorted(chainages), "road runs not in chain order"
    road_edges_mi = sum(edges[idx]["miles"] for idx, _e, _s, _en in order
                        if edges[idx]["cls"] == "road")
    print("road walk: %d segments, %.2f mi (sum of segment lengths)"
          % (len(features), road_total))
    print("  runs dropped as sub-0.005-mi slivers: %d" % dropped_zero)
    print("  road-class miles on the walked chain: %.2f mi; "
          "difference (rounding): %.2f mi"
          % (road_edges_mi, road_total - road_edges_mi))
    print("  road-class `miles` total in the source files: %.2f mi; "
          "on the walked chain: %.2f mi; excluded with duplicates and "
          "leftover alternatives: %.2f mi"
          % (stats["raw_miles_by_class"]["road"], road_edges_mi,
             stats["raw_miles_by_class"]["road"] - road_edges_mi))
    print("  chainage total: %.2f mi" % total)
    print("wrote %s" % OUT_PATH)


def _jump_positions(walk, order):
    """Order positions at which each recorded jump lands.

    walk['jumps'] records the chain mile at the jump; recover the
    order position as the first edge whose start mile is >= that
    chain mile (the jump lands on the next edge walked).
    """
    positions = []
    for (cum, _fr, _to, _d, _c1, _c2, _kind) in walk["jumps"]:
        for pos, (_idx, _e, start_mi, _en) in enumerate(order):
            if start_mi >= cum - 1e-9:
                positions.append(pos)
                break
        else:
            positions.append(len(order) - 1)
    return positions


if __name__ == "__main__":
    main()
