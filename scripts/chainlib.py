#!/usr/bin/env python3
"""Shared chain builder for the NCT derived layers (plan step 3).

The three centerline files (natural / road / urban) are NOT in trail
order, their endpoints do not snap exactly, and the pull contains
duplicate drawings and alternative alignments. This module turns them
into one ordered west->east chain, which the three layer builders
(build_chainage.py, build_chapter_boundaries.py, build_road_walk.py)
then consume.

RULES (all documented again in site/data/SOURCES-step3.md):
- Length is the source `miles` property per feature, NOT the drawn
  geodesic length: the drawn geometry is simplified (Vincenty length
  of the drawn line is 4,768.56 mi vs 4,871.07 mi of `miles` values),
  while the `miles` values sum to the published totals
  (mileage-table.csv: 4,871.24 mi; the 0.17 mi gap is rounding of the
  per-feature 2-decimal values). Chainage accumulates `miles`.
- MultiLineString features are split into one edge per part, with the
  feature's `miles` apportioned across its parts by drawn length.
- Exact-duplicate parts (identical coordinates, either direction) are
  walked once: 33 duplicate parts, 9.68 mi. The published totals
  double-count them (they were summed without deduping).
- Walk: greedy from the western terminus (westernmost endpoint, Lake
  Sakakawea SP). At each step take an unused edge incident to the
  current point (exact node match first); ties break by same chapter,
  then straightest continuation. A near-miss continuation (endpoint
  within 500 m) is taken as a jump; a genuine gap jumps to the nearest
  unused endpoint (recorded, adds 0 mi to chainage). The walk stops
  when no unused edge lies within 10 km: that is the eastern terminus.
- NO-REVISIT RULE: an edge whose far end is exactly a visited node
  (same 5-decimal coordinate key) is never taken while any other
  continuation exists. Without it the walk traverses both sides of a
  loop (the FLY loop near Lake Sakakawea: natural side 4.10 mi + road
  side 5.77 mi between the same two points) and double-counts the
  loop. The match is EXACT, not a radius: the trail legitimately
  passes within 100 m of itself on hairpins and through town
  clusters, and a radius rule refuses true continuations there
  (proven in the first build run: 543 refusals, walk stranded).
- Edges the walk never reaches are LEFTOVERS, excluded from chainage:
  overlapping duplicate drawings (vertices within 50 m of the walked
  chain) and alternative alignments / spurs. They are listed by the
  builders, never silently dropped.
- Positions along the chain are interpolated by fraction of an edge's
  drawn length (ITM precedent: build_roadwalk.py interpolates by
  fraction of measured length within a feature).

Only the Python standard library is used, so the build is
reproducible anywhere.
"""

import json
import math
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "site" / "data"
CENTERLINE_FILES = [
    "centerline-natural.geojson",
    "centerline-road.geojson",
    "centerline-urban.geojson",
]
CHAPTERS_FILE = DATA_DIR / "chapters.json"

# Walk tolerances (metres).
JUMP_TOL_M = 500.0      # near-miss continuation: endpoint within this is a jump
MAX_JUMP_M = 10000.0    # walk stops if the nearest unused edge is further away
REVISIT_TOL_M = None      # (unused) the no-revisit rule below matches node
                        # keys exactly; see walk_chain. A radius would
                        # misfire on hairpins and town clusters, where the
                        # trail legitimately passes within 100 m of itself.
OVERLAP_TOL_M = 50.0    # leftover edge whose vertices are within this of the
                        # walked chain counts as an overlapping duplicate


# ---------------------------------------------------------------- geodesy
def vincenty_miles(lat1, lon1, lat2, lon2):
    """WGS-84 geodesic distance in miles (Vincenty inverse).

    Falls back to haversine on the rare non-convergent pair (nearly
    antipodal points never occur in this data).
    """
    a = 6378137.0
    f = 1 / 298.257223563
    b = (1 - f) * a
    L = math.radians(lon2 - lon1)
    U1 = math.atan((1 - f) * math.tan(math.radians(lat1)))
    U2 = math.atan((1 - f) * math.tan(math.radians(lat2)))
    s1, c1 = math.sin(U1), math.cos(U1)
    s2, c2 = math.sin(U2), math.cos(U2)
    lam = L
    for _ in range(200):
        sl, cl = math.sin(lam), math.cos(lam)
        ss = math.sqrt((c2 * sl) ** 2 + (c1 * s2 - s1 * c2 * cl) ** 2)
        if ss == 0:
            return 0.0
        cs = s1 * s2 + c1 * c2 * cl
        sig = math.atan2(ss, cs)
        sa = c1 * c2 * sl / ss
        c2s = cs * cs - sa * sa if abs(sa) < 1 else 0.0
        cm = cs - 2 * s1 * s2 / c2s if c2s != 0 else 0.0
        C = f / 16 * c2s * (4 + f * (4 - 3 * c2s))
        lamp = lam
        lam = L + (1 - C) * f * sa * (sig + C * ss * (cm + C * cs * (-1 + 2 * cm * cm)))
        if abs(lam - lamp) < 1e-12:
            break
    else:
        R = 6371000.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        h = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return 2 * R * math.asin(math.sqrt(h)) / 1609.344
    u2 = c2s * (a * a - b * b) / (b * b)
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    ds = B * ss * (cm + B / 4 * (cs * (-1 + 2 * cm * cm)
                  - B / 6 * cm * (-3 + 4 * ss * ss) * (-3 + 4 * cm * cm)))
    return b * A * (sig - ds) / 1609.344


def dist_m(a, b):
    """Approximate flat-earth distance in metres (good to ~0.1% here)."""
    return math.hypot((a[0] - b[0]) * 111320 * math.cos(math.radians((a[1] + b[1]) / 2)),
                      (a[1] - b[1]) * 110540)


def bearing(a, b):
    """Bearing in degrees, 0 = north, from point a to point b."""
    dx = (b[0] - a[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    dy = b[1] - a[1]
    return math.degrees(math.atan2(dx, dy)) % 360


def angle_diff(b1, b2):
    d = abs(b1 - b2) % 360
    return min(d, 360 - d)


def _key(c):
    return (round(c[0], 5), round(c[1], 5))


def _drawn_miles(coords):
    total = 0.0
    for a, b in zip(coords, coords[1:]):
        total += vincenty_miles(a[1], a[0], b[1], b[0])
    return total


# ---------------------------------------------------------------- loading
def _parts_of(feat):
    g = feat["geometry"]
    if g["type"] == "LineString":
        return [g["coordinates"]]
    if g["type"] == "MultiLineString":
        return g["coordinates"]
    raise ValueError("unexpected geometry type %s" % g["type"])


def load_edges():
    """Load the three centerline files as deduped edges.

    Returns (edges, stats) where each edge is a dict with:
    src (file#feature-index p part-index), chapter, state, cls,
    coords (list of (lon, lat) tuples), miles (apportioned `miles`
    value), drawn (Vincenty length of the drawn part, miles).
    stats records the dedupe (count, miles) and the raw sums.
    """
    edges = []
    raw_miles = 0.0
    raw_features = 0
    raw_miles_by_class = {"natural": 0.0, "road": 0.0, "urban": 0.0}
    for fn in CENTERLINE_FILES:
        data = json.loads((DATA_DIR / fn).read_text())
        raw_features += len(data["features"])
        for i, feat in enumerate(data["features"]):
            props = feat["properties"]
            raw_miles_by_class[props["class"]] += props["miles"]
            props = feat["properties"]
            parts = _parts_of(feat)
            drawn = [_drawn_miles(p) for p in parts]
            total_drawn = sum(drawn) or 1.0
            raw_miles += props["miles"]
            for pi, part in enumerate(parts):
                edges.append({
                    "src": "%s#%d p%d" % (fn, i, pi),
                    "chapter": props["chapter"],
                    "state": props["state"],
                    "cls": props["class"],
                    "coords": [tuple(c) for c in part],
                    "miles": props["miles"] * drawn[pi] / total_drawn,
                    "drawn": drawn[pi],
                })
    seen = {}
    kept = []
    dup_count = 0
    dup_miles = 0.0
    for idx, edge in enumerate(edges):
        fwd = tuple(edge["coords"])
        rev = tuple(reversed(fwd))
        k = min(fwd, rev)
        if k in seen:
            dup_count += 1
            dup_miles += edge["miles"]
            continue
        seen[k] = idx
        kept.append(idx)
    edges = [edges[i] for i in kept]
    stats = {
        "raw_features": raw_features,
        "raw_miles_sum": raw_miles,
        "raw_miles_by_class": raw_miles_by_class,
        "miles_by_class": {
            cls: sum(e["miles"] for e in edges if e["cls"] == cls)
            for cls in ("natural", "road", "urban")
        },
        "edges_after_split": len(kept) + dup_count,
        "dup_parts": dup_count,
        "dup_miles": dup_miles,
        "edges": len(edges),
        "miles": sum(e["miles"] for e in edges),
        "drawn_miles": sum(e["drawn"] for e in edges),
    }
    return edges, stats


def chapter_names():
    """code -> name from chapters.json (first row wins; 'None' has two
    rows with the same name, '?? UNMAPPED CODE ??')."""
    rows = json.loads(CHAPTERS_FILE.read_text())
    names = {}
    for row in rows:
        code = row["code"]
        if code not in names:
            names[code] = row["name"]
    return names


# ---------------------------------------------------------------- the walk
def walk_chain(edges):
    """Order the edges west -> east from the western terminus.

    Returns a dict with:
    order: [(edge_idx, entry_end, start_mi, end_mi)] where entry_end 0
        means the chain enters at coords[0] (exits at coords[-1]).
    jumps: [(chain_mi, from_pt, to_pt, dist_m, from_chapter,
        to_chapter, kind)] with kind 'near-miss' (<= 500 m) or 'gap'.
    leftovers: [edge_idx] never reached by the walk.
    total_mi: chainage at the eastern terminus.
    stop_point: (lon, lat) of the eastern terminus.
    loop_skips: [(chain_mi, edge_idx)] edges refused by the no-revisit
        rule while another continuation existed.
    """
    node_edges = defaultdict(list)
    for idx, edge in enumerate(edges):
        node_edges[_key(edge["coords"][0])].append(idx)
        node_edges[_key(edge["coords"][-1])].append(idx)

    # Western terminus: the westernmost endpoint in the data.
    all_ends = [(c, idx) for idx, e in enumerate(edges)
                for c in (e["coords"][0], e["coords"][-1])]
    start_pt = min(all_ends, key=lambda t: t[0][0])[0]
    start_cands = node_edges[_key(start_pt)]
    if len(start_cands) != 1:
        raise RuntimeError("western terminus node has %d edges, expected 1"
                           % len(start_cands))
    start_edge = start_cands[0]
    entry = 0 if _key(edges[start_edge]["coords"][0]) == _key(start_pt) else 1

    used = [False] * len(edges)
    visited_keys = set()
    order = []
    jumps = []
    loop_skips = []
    cum = 0.0

    def oriented(edge, entry_end):
        """(coords in chain direction, exit point, entry point)."""
        coords = edge["coords"]
        if entry_end == 0:
            return coords, coords[-1], coords[0]
        return list(reversed(coords)), coords[0], coords[-1]

    def far_end_visited(edge, entry_end):
        """True when the edge's far end is exactly a visited node
        (same 5-decimal key). Exact only: a radius misfires on
        hairpins and town clusters."""
        far = edge["coords"][-1] if entry_end == 0 else edge["coords"][0]
        return _key(far) in visited_keys

    def take_edge(idx, entry_end, jump):
        nonlocal cum
        edge = edges[idx]
        used[idx] = True
        order.append((idx, entry_end, cum, cum + edge["miles"]))
        visited_keys.add(_key(edge["coords"][0]))
        visited_keys.add(_key(edge["coords"][-1]))
        cum += edge["miles"]
        if jump is not None:
            jumps.append(jump)
        return oriented(edge, entry_end)

    # First edge.
    _, cur_pt, _ = take_edge(start_edge, entry, None)
    prev_pt = (edges[start_edge]["coords"][-2] if entry == 0
               else edges[start_edge]["coords"][1])
    in_bearing = bearing(prev_pt, cur_pt)
    stop_point = cur_pt

    while True:
        cur_chapter = edges[order[-1][0]]["chapter"]
        # Exact-node candidates (a degenerate point edge, whose two
        # ends share one key, is listed once).
        cands = []
        seen_cand = set()
        for ei in node_edges.get(_key(cur_pt), []):
            if used[ei] or ei in seen_cand:
                continue
            seen_cand.add(ei)
            edge = edges[ei]
            end = 0 if _key(edge["coords"][0]) == _key(cur_pt) else 1
            cands.append((ei, end, 0.0))
        open_cands = [(ei, end, d) for (ei, end, d) in cands
                      if not far_end_visited(edges[ei], end)]
        skipped = [ei for (ei, end, d) in cands
                   if far_end_visited(edges[ei], end)]
        for ei in skipped:
            loop_skips.append((cum, ei))
        jump = None
        if open_cands:
            pick = _best_continuation(open_cands, edges, cur_pt,
                                      in_bearing, cur_chapter)
            ei, end, _d = pick
        else:
            # Spatial search: unused edge endpoint within 500 m.
            spatial = []
            for ei, edge in enumerate(edges):
                if used[ei]:
                    continue
                for end in (0, 1):
                    pt = edge["coords"][0] if end == 0 else edge["coords"][-1]
                    d = dist_m(cur_pt, pt)
                    if d <= JUMP_TOL_M and not far_end_visited(edge, end):
                        spatial.append((ei, end, d))
            if spatial:
                pick = _best_continuation(spatial, edges, cur_pt,
                                          in_bearing, cur_chapter)
                ei, end, d = pick
                jump = (cum, cur_pt,
                        edges[ei]["coords"][0] if end == 0
                        else edges[ei]["coords"][-1],
                        d, cur_chapter, edges[ei]["chapter"], "near-miss")
            else:
                # Nearest unused endpoint at any distance; stop if far.
                best = None
                for ei, edge in enumerate(edges):
                    if used[ei]:
                        continue
                    for end in (0, 1):
                        pt = (edge["coords"][0] if end == 0
                              else edge["coords"][-1])
                        d = dist_m(cur_pt, pt)
                        if best is None or d < best[0]:
                            best = (d, ei, end)
                if best is None or best[0] > MAX_JUMP_M:
                    stop_point = cur_pt
                    break
                d, ei, end = best
                jump = (cum, cur_pt,
                        edges[ei]["coords"][0] if end == 0
                        else edges[ei]["coords"][-1],
                        d, cur_chapter, edges[ei]["chapter"], "gap")
        coords, cur_pt, _entry_pt = take_edge(ei, end, jump)
        prev_pt = coords[-2] if len(coords) >= 2 else cur_pt
        in_bearing = bearing(prev_pt, cur_pt)

    leftovers = [i for i, u in enumerate(used) if not u]
    return {
        "order": order,
        "jumps": jumps,
        "leftovers": leftovers,
        "total_mi": cum,
        "stop_point": stop_point,
        "loop_skips": loop_skips,
        "start_point": start_pt,
    }


def _best_continuation(cands, edges, cur_pt, in_bearing, cur_chapter):
    """Pick (edge_idx, entry_end, dist) from candidates.

    Score = distance + (1000 if the chapter changes) + 2 * turn angle.
    Distance dominates: a near-miss endpoint 2 m away must beat a
    straighter one 400 m away (a distance-last sort skips the
    in-series micro-edges between them and jumps over real route
    miles — proven in the second build run). The chapter penalty
    keeps the walk in the same chapter; the turn term breaks ties
    toward the straightest continuation. For exact-node candidates
    (all distances 0) this reduces to same-chapter, then straightest.
    Candidates are (edge_idx, entry_end, dist_m).
    """
    scored = []
    for ei, end, d in cands:
        edge = edges[ei]
        ch_pen = 0 if edge["chapter"] == cur_chapter else 1000
        out_pt = edge["coords"][1] if end == 0 else edge["coords"][-2]
        ent_pt = edge["coords"][0] if end == 0 else edge["coords"][-1]
        turn = angle_diff(in_bearing, bearing(ent_pt, out_pt))
        scored.append((d + ch_pen + turn * 2, ei, end, d))
    scored.sort()
    _score, ei, end, d = scored[0]
    return ei, end, d


# ---------------------------------------------------------------- chainage
def chain_vertices(order, edges):
    """Flatten the ordered chain to [(lon, lat, chain_mi)] at every
    vertex, distributing each edge's `miles` uniformly over its drawn
    length. Consecutive duplicate points are dropped.
    """
    out = []
    for idx, entry_end, start_mi, end_mi in order:
        edge = edges[idx]
        coords = (edge["coords"] if entry_end == 0
                  else list(reversed(edge["coords"])))
        span_mi = end_mi - start_mi
        drawn = edge["drawn"]
        acc_drawn = 0.0
        for j, pt in enumerate(coords):
            if j > 0:
                acc_drawn += vincenty_miles(coords[j - 1][1], coords[j - 1][0],
                                            pt[1], pt[0])
            frac = (acc_drawn / drawn) if drawn > 0 else 0.0
            mi = start_mi + span_mi * frac
            if out and abs(out[-1][0] - pt[0]) < 1e-9 and abs(out[-1][1] - pt[1]) < 1e-9:
                continue
            out.append((pt[0], pt[1], mi))
    return out


def point_at_mile(vertices, mile):
    """Interpolate the coordinate at a chain mile.

    Vertices must be the output of chain_vertices (chain miles
    non-decreasing). Linear interpolation between the bracketing
    vertices.
    """
    lo, hi = 0, len(vertices) - 1
    if mile <= vertices[0][2]:
        return (vertices[0][0], vertices[0][1])
    if mile >= vertices[-1][2]:
        return (vertices[-1][0], vertices[-1][1])
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if vertices[mid][2] <= mile:
            lo = mid
        else:
            hi = mid
    (x0, y0, m0), (x1, y1, m1) = vertices[lo], vertices[hi]
    if m1 == m0:
        return (x1, y1)
    t = (mile - m0) / (m1 - m0)
    return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))


def classify_leftovers(edges, walk, order):
    """Split leftover edges into overlapping duplicates vs alternative
    alignments / spurs.

    An edge is an overlapping duplicate when at least 80% of its
    sampled vertices lie within OVERLAP_TOL_M of a walked segment.
    Returns (duplicates, alternatives) as lists of (edge_idx, miles).
    """
    walked_segs = []
    for idx, entry_end, _s, _e in order:
        coords = (edges[idx]["coords"] if entry_end == 0
                  else list(reversed(edges[idx]["coords"])))
        for a, b in zip(coords, coords[1:]):
            walked_segs.append((a, b))
    # Grid index over walked segments (cell ~0.05 deg).
    grid = defaultdict(list)
    for si, (a, b) in enumerate(walked_segs):
        for cell in _cells_for_segment(a, b, 0.05):
            grid[cell].append(si)

    def near_walked(pt):
        cx, cy = int(math.floor(pt[0] / 0.05)), int(math.floor(pt[1] / 0.05))
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for si in grid.get((cx + dx, cy + dy), ()):
                    a, b = walked_segs[si]
                    d = _pt_seg_dist_m(pt, a, b)
                    if best is None or d < best:
                        best = d
        return best is not None and best <= OVERLAP_TOL_M

    duplicates, alternatives = [], []
    for idx in walk["leftovers"]:
        edge = edges[idx]
        coords = edge["coords"]
        step = max(1, len(coords) // 10)
        sample = coords[::step]
        if not sample:
            sample = coords
        near = sum(1 for pt in sample if near_walked(pt))
        frac = near / len(sample) if sample else 0.0
        if frac >= 0.8:
            duplicates.append((idx, edge["miles"]))
        else:
            alternatives.append((idx, edge["miles"]))
    return duplicates, alternatives


def _cells_for_segment(a, b, cell):
    x0, x1 = sorted([a[0], b[0]])
    y0, y1 = sorted([a[1], b[1]])
    cx0, cx1 = int(math.floor(x0 / cell)), int(math.floor(x1 / cell))
    cy0, cy1 = int(math.floor(y0 / cell)), int(math.floor(y1 / cell))
    for cx in range(cx0, cx1 + 1):
        for cy in range(cy0, cy1 + 1):
            yield (cx, cy)


def _pt_seg_dist_m(p, a, b):
    kx = 111320 * math.cos(math.radians(p[1]))
    ky = 110540
    dx, dy = (b[0] - a[0]) * kx, (b[1] - a[1]) * ky
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot((p[0] - a[0]) * kx, (p[1] - a[1]) * ky)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * kx * dx
                           + (p[1] - a[1]) * ky * dy) / L2))
    return math.hypot((p[0] - (a[0] + t * (b[0] - a[0]))) * kx,
                      (p[1] - (a[1] + t * (b[1] - a[1]))) * ky)


def round_pt(pt):
    return [round(pt[0], 5), round(pt[1], 5)]
