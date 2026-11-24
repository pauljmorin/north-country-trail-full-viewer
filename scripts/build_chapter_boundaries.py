#!/usr/bin/env python3
"""Build the Chapter boundaries layer: one point per chapter junction.

Output: site/data/chapter-boundaries.geojson — Point features:
- one per place where the `chapter` field changes between consecutive
  features of the ordered west->east chain (the boundary coordinate is
  the exit point of the earlier-chapter edge, which sits on the
  centerline; place-name endpoints from
  ncta-chapter-extents-2026-11-23.md are human labels only and are
  NOT geocoded);
- plus the two termini: the western terminus (Lake Sakakawea State
  Park) and the eastern terminus.

Each boundary point carries the two adjoining chapter codes and names
plus the chainage at that point. Each terminus carries its chapter and
chainage (0.00 / total).

NOTE ON THE EASTERN TERMINUS: the brief labels it "Crown Point /
Lake Champlain bridge", but the drawn centerline continues past
Crown Point (the ADK -> MALT junction, which this layer marks) through
Vermont to the Appalachian Trail junction in the Green Mountain
National Forest — the eastern terminus stated on the GMC chapter row
of ncta-chapter-extents-2026-11-23.md and the easternmost point of the
data. The terminus point records this in its `note` property; the
Crown Point crossing is the ADK -> MALT boundary point.

Method: chainlib.walk_chain; see site/data/SOURCES-step3.md.

Usage: python3 scripts/build_chapter_boundaries.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chainlib  # noqa: E402

OUT_PATH = chainlib.DATA_DIR / "chapter-boundaries.geojson"

EAST_NOTE = (
    "Brief labels the eastern terminus Crown Point / Lake Champlain "
    "bridge; the drawn centerline continues past Crown Point (the "
    "ADK -> MALT boundary in this layer) through Vermont to this "
    "point, the Appalachian Trail junction in the Green Mountain "
    "National Forest — the eastern terminus stated on the GMC row of "
    "ncta-chapter-extents-2026-11-23.md and the easternmost point of "
    "the data."
)


def main():
    edges, stats = chainlib.load_edges()
    walk = chainlib.walk_chain(edges)
    order = walk["order"]
    total = walk["total_mi"]
    names = chainlib.chapter_names()
    unknown = set()

    def name(code):
        if code not in names:
            unknown.add(code)
            return code
        return names[code]

    features = []

    # Western terminus.
    first = edges[order[0][0]]
    features.append({
        "type": "Feature",
        "geometry": {"type": "Point",
                     "coordinates": chainlib.round_pt(walk["start_point"])},
        "properties": {
            "kind": "terminus",
            "name": "Western terminus — Lake Sakakawea State Park",
            "chapter_code": first["chapter"],
            "chapter_name": name(first["chapter"]),
            "state": first["state"],
            "chainage_mi": 0.0,
        },
    })

    # Chapter junctions.
    for (idx_a, _e_a, _s_a, end_a), (idx_b, _e_b, _s_b, _e_b) in zip(order, order[1:]):
        a, b = edges[idx_a], edges[idx_b]
        if a["chapter"] == b["chapter"]:
            continue
        # Boundary coordinate: the exit point of the earlier-chapter
        # edge in chain direction (on the centerline by construction).
        exit_pt = (a["coords"][-1] if _e_a == 0 else a["coords"][0])
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": chainlib.round_pt(exit_pt)},
            "properties": {
                "kind": "chapter-boundary",
                "chapter_from_code": a["chapter"],
                "chapter_from_name": name(a["chapter"]),
                "chapter_to_code": b["chapter"],
                "chapter_to_name": name(b["chapter"]),
                "state_from": a["state"],
                "state_to": b["state"],
                "chainage_mi": round(end_a, 2),
            },
        })

    # Eastern terminus.
    last = edges[order[-1][0]]
    features.append({
        "type": "Feature",
        "geometry": {"type": "Point",
                     "coordinates": chainlib.round_pt(walk["stop_point"])},
        "properties": {
            "kind": "terminus",
            "name": "Eastern terminus — Appalachian Trail junction, "
                    "Green Mountain National Forest",
            "chapter_code": last["chapter"],
            "chapter_name": name(last["chapter"]),
            "state": last["state"],
            "chainage_mi": round(total, 2),
            "note": EAST_NOTE,
        },
    })

    out = {"type": "FeatureCollection", "features": features}
    OUT_PATH.write_text(json.dumps(out, indent=1) + "\n")

    # ---- self-checks
    assert all(f["geometry"]["type"] == "Point" for f in features)
    chainages = [f["properties"]["chainage_mi"] for f in features]
    assert chainages == sorted(chainages), "boundary chainages not monotonic"
    assert chainages[0] == 0.0 and abs(chainages[-1] - total) < 0.01
    assert not unknown, "chapter codes missing from chapters.json: %s" % unknown
    n_junctions = sum(1 for f in features
                      if f["properties"]["kind"] == "chapter-boundary")

    # Chapter-stretch analysis: which codes appear in non-contiguous
    # stretches, and how many stretches each code has.
    stretches = []
    for idx, _e, _s, _en in order:
        ch = edges[idx]["chapter"]
        if not stretches or stretches[-1][0] != ch:
            stretches.append([ch, 1])
        else:
            stretches[-1][1] += 1
    counts = Counter(ch for ch, _n in stretches)
    noncontig = {ch: n for ch, n in counts.items() if n > 1}

    print("chapter boundaries: %d points (%d junctions + 2 termini)"
          % (len(features), n_junctions))
    print("  chapter stretches along the chain: %d; distinct codes: %d"
          % (len(stretches), len(counts)))
    print("  non-contiguous chapter codes (code: stretches): %s"
          % (noncontig if noncontig else "none"))
    print("  chainage total: %.2f mi" % total)
    print("wrote %s" % OUT_PATH)


if __name__ == "__main__":
    main()
