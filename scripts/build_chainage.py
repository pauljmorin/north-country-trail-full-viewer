#!/usr/bin/env python3
"""Build the Chainage layer: one point per mile from the western terminus.

Output: site/data/chainage.geojson — Point features, one per integer
mile 1..floor(total chainage), mirroring the ITM viewer's chainage
schema (kind, miles_from_west, every10).

Method (see site/data/SOURCES-step3.md for the full record):
- Order the centerline west -> east with chainlib.walk_chain.
- Chainage accumulates the source `miles` property, never the drawn
  geodesic length (the drawn line is simplified; see chainlib).
- Each mile point is interpolated along the ordered chain by fraction
  of the containing edge's drawn length.

Usage: python3 scripts/build_chainage.py
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chainlib  # noqa: E402

OUT_PATH = chainlib.DATA_DIR / "chainage.geojson"


def main():
    edges, stats = chainlib.load_edges()
    walk = chainlib.walk_chain(edges)
    order = walk["order"]
    total = walk["total_mi"]
    vertices = chainlib.chain_vertices(order, edges)

    n_miles = int(math.floor(total))
    features = []
    for mile in range(1, n_miles + 1):
        lon, lat = chainlib.point_at_mile(vertices, float(mile))
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": chainlib.round_pt((lon, lat))},
            "properties": {
                "kind": "chainage",
                "miles_from_west": mile,
                "every10": (mile % 10 == 0),
            },
        })

    out = {"type": "FeatureCollection", "features": features}
    OUT_PATH.write_text(json.dumps(out, indent=1) + "\n")

    # ---- self-checks
    assert len(features) == n_miles
    miles = [f["properties"]["miles_from_west"] for f in features]
    assert miles == list(range(1, n_miles + 1)), "chainage not monotonic 1..N"
    assert all(f["geometry"]["type"] == "Point" for f in features)
    # Every point lies on (within 100 m of) the centerline by
    # construction; spot-verify the first, a middle and the last point
    # against the nearest walked SEGMENT (not vertex: a mile point
    # interpolated mid-segment can sit far from either vertex).
    for check in (features[0], features[len(features) // 2], features[-1]):
        lon, lat = check["geometry"]["coordinates"]
        best = min(chainlib._pt_seg_dist_m(
            (lon, lat), (vertices[i][0], vertices[i][1]),
            (vertices[i + 1][0], vertices[i + 1][1]))
            for i in range(len(vertices) - 1))
        assert best <= 100.0, "chainage point %.1f m off the line" % best

    dups, alts = chainlib.classify_leftovers(edges, walk, order)
    print("chainage: %d points (miles 1..%d), total chainage %.2f mi"
          % (len(features), n_miles, total))
    print("  walked edges: %d of %d (%.2f mi)"
          % (len(order), len(edges), total))
    print("  jumps: %d (near-miss <=500 m: %d, gap >500 m: %d); "
          "largest jump %.0f m"
          % (len(walk["jumps"]),
             sum(1 for j in walk["jumps"] if j[6] == "near-miss"),
             sum(1 for j in walk["jumps"] if j[6] == "gap"),
             max((j[3] for j in walk["jumps"]), default=0.0)))
    print("  loop-closing edges refused by the no-revisit rule: %d"
          % len(walk["loop_skips"]))
    print("  leftovers excluded: %d edges, %.2f mi "
          "(overlapping duplicates %.2f mi, alternatives/spurs %.2f mi)"
          % (len(walk["leftovers"]),
             sum(edges[i]["miles"] for i in walk["leftovers"]),
             sum(m for _i, m in dups), sum(m for _i, m in alts)))
    print("  input sums: raw `miles` total %.2f mi; after dedupe %.2f mi; "
          "drawn geodesic %.2f mi"
          % (stats["raw_miles_sum"], stats["miles"], stats["drawn_miles"]))
    print("wrote %s" % OUT_PATH)


if __name__ == "__main__":
    main()
