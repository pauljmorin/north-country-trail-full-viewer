#!/usr/bin/env python3
"""Build the NCT-viewer gazetteer: site/data/gazetteer.json.

A SEARCH INDEX, not a browsable list (the ITM gazetteer has 257
places; trail-wide this is ~9,000): each entry is a named thing on
or near the trail — an NCTA camping waypoint, an NCTA place (parking,
water, shelter, POI, ford), a state mile marker, or a chapter
boundary / trail terminus — carrying its name, type, coordinates,
chapter, state, and its position along the trail in miles from the
western terminus (chainage_mi) where that can be computed honestly.

Sources (see site/data/SOURCES-step4.md):
  camping + places   site/data/camping.geojson,
                     site/data/ncta-places.geojson (this repo, step 4)
  mile markers       site/data/mile-markers.geojson (this repo, step 4)
  chapter endpoints  ncta-chapter-extents-2026-11-23.md (repo root) for
                     the endpoint NAMES; the boundary COORDINATES and
                     chainages come from the centerline (below)
  centerline         site/data/centerline-{natural,road,urban}.geojson
                     (the mapped trail, 4,871.07 mi)

CHAINAGE METHOD (adapted from the ITM build_gazetteer.py, which
projects onto a chain of adopted sections in chainage order): there
are no sections trail-wide, so the chain is built by walking the
centerline itself — segments joined end-to-end by nearest endpoint
(within 150 m), starting at the western terminus (Lake Sakakawea
State Park), taking the nearest unused continuation at each step.
The walk orders 4,348 of the 4,441 segments into one chain west to
east (chapter sequence FLY ... MALT, GMC last, ending at the
Appalachian Trail junction — the eastern terminus); 93 segments
(69.71 mi, mostly short stubs and parallel alternates) do not join
the walk and are left unchained. A point's chainage is the stored
`miles` of the main-chain segments before its nearest main-chain
segment plus its fraction along that segment (by geometry length),
PLUS the straight-line distance of any unmapped gap the walk jumped
to reach that segment (each jump is listed in the output metadata —
the gaps are an approximation, stated as such, never hidden). A
point whose nearest main-chain segment is more than 250 m away (the
ITM SNAP_LIMIT_M rule) gets chainage_mi = null and off_chain = true
rather than a fabricated position. Points near unchained segments
get their chapter/state from the nearest segment of any kind, but
no chainage.

CHAPTER BOUNDARIES: the boundary between two chapters is the chain
point where the eastern chapter's first main-chain segment starts.
The junction place name is the endpoint string the two chapters
share in the extents table (e.g. "Middlebury Gap" for MALT/GMC);
where the two chapters' wordings differ, both strings are carried
verbatim and junction_name is null. The extents table's west/east
columns are not always in walk direction (GMC and MALT are listed
reversed), so no direction is assumed from the table — the walk
order decides west vs east, and the terminus names are the endpoint
string of the end chapter that does NOT name the neighbouring
junction.

NAME RULE (ITM): a waypoint with no name in the NCTA service takes
its kind as its name ("Parking", "Camping", ...), with named=false
and source_name=null so the fallback is visible, never invented
silently. Mile markers are named by their ident ("MN-187.5").

Output: site/data/gazetteer.json
  {"metadata": {...}, "entries": [ ... ]} — entries sorted by
  chainage (nulls last), then kind, then name. Standard library only.

Usage:  python3 scripts/build_gazetteer_national.py
"""

import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "site" / "data"
OUT_PATH = DATA / "gazetteer.json"
EXTENTS_MD = REPO_ROOT / "ncta-chapter-extents-2026-11-23.md"
CHAPTERS_JSON = DATA / "chapters.json"

CENTERLINE_FILES = [DATA / "centerline-natural.geojson",
                    DATA / "centerline-road.geojson",
                    DATA / "centerline-urban.geojson"]
CAMPING_PATH = DATA / "camping.geojson"
PLACES_PATH = DATA / "ncta-places.geojson"
MARKERS_PATH = DATA / "mile-markers.geojson"

SNAP_LIMIT_M = 250.0
JOIN_TOL_KM = 0.15     # endpoint join tolerance for the chain walk
MAIN_BREAK_KM = 10.0   # a jump over this ends the main chain (mop-up after)
ATTRIBUTION_LIMIT_M = 5000.0  # beyond this, no chapter/state attribution

# ITM geo_util projection (km per degree, centred on latitude 47 N)
KX = 111.320 * math.cos(math.radians(47.0))
KY = 111.195


def to_xy(p):
    return (p[0] * KX, p[1] * KY)


def dist_km(a, b):
    ax, ay = to_xy(a)
    bx, by = to_xy(b)
    return math.hypot(ax - bx, ay - by)


def r2(v):
    return None if v is None else round(float(v), 2)


# ---------------------------------------------------------------- chain
def load_segments():
    segs = []
    for path in CENTERLINE_FILES:
        doc = json.loads(path.read_text())
        for feat in doc["features"]:
            g = feat["geometry"]
            coords = (g["coordinates"] if g["type"] == "LineString"
                      else [c for part in g["coordinates"] for c in part])
            coords = [(c[0], c[1]) for c in coords]
            if len(coords) < 2:
                continue
            segs.append({"props": feat["properties"], "coords": coords})
    return segs


def build_chain(segs):
    """Greedy endpoint walk from the western terminus. Returns
    (main_order, tail, jumps, terminal_break, west_end) where jumps
    are (position, gap_km, from_props, to_props) for every jump
    inside the main chain, and terminal_break is the (gap_km,
    from_props, to_props) jump that ended the walk — the nearest
    unused segment lay more than MAIN_BREAK_KM away, so the walk
    stopped there and everything after is mop-up, not chain."""
    cell = 0.05
    grid = defaultdict(list)
    for i, s in enumerate(segs):
        for end in (0, -1):
            c = s["coords"][end]
            grid[(int(c[0] // cell), int(c[1] // cell))].append((i, end))

    def near_endpoints(pt, tol_km):
        cx, cy = int(pt[0] // cell), int(pt[1] // cell)
        out = []
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for (i, end) in grid.get((gx, gy), []):
                    d = dist_km(pt, segs[i]["coords"][end])
                    if d <= tol_km:
                        out.append((d, i, end))
        return sorted(out)

    # western terminus: the westernmost segment endpoint in the data
    start = min(range(len(segs)),
                key=lambda i: min(c[0] for c in (segs[i]["coords"][0],
                                                 segs[i]["coords"][-1])))
    s0 = segs[start]
    west_end = (s0["coords"][0] if s0["coords"][0][0] < s0["coords"][-1][0]
                else s0["coords"][-1])
    used = set()
    order = []
    jumps = []
    terminal_break = None
    cur_pt, cur_seg = west_end, start
    while True:
        used.add(cur_seg)
        order.append(cur_seg)
        s = segs[cur_seg]
        if dist_km(s["coords"][0], cur_pt) <= dist_km(s["coords"][-1], cur_pt):
            far = s["coords"][-1]
        else:
            far = s["coords"][0]
        cands = [(d, i, e) for (d, i, e) in near_endpoints(far, JOIN_TOL_KM)
                 if i not in used]
        if cands:
            d, i, e = cands[0]
            cur_seg, cur_pt = i, segs[i]["coords"][e]
            continue
        # no continuation within tolerance: jump to the nearest unused
        # endpoint anywhere
        best = None
        for i, s2 in enumerate(segs):
            if i in used:
                continue
            for e in (0, -1):
                d = dist_km(far, s2["coords"][e])
                if best is None or d < best[0]:
                    best = (d, i, e)
        if best is None:
            break
        d, i, e = best
        if d > MAIN_BREAK_KM:
            # the main chain ends here; the rest is mop-up
            terminal_break = (d, segs[cur_seg]["props"],
                              segs[i]["props"])
            break
        jumps.append((len(order), d, segs[cur_seg]["props"],
                      segs[i]["props"]))
        cur_seg, cur_pt = i, segs[i]["coords"][e]
    tail = [i for i in range(len(segs)) if i not in set(order)]
    return order, tail, jumps, terminal_break, west_end


def segment_geo_len(coords):
    return sum(dist_km(a, b) for a, b in zip(coords, coords[1:]))


class Chain:
    """The ordered main chain with per-segment chainage anchors."""

    def __init__(self, segs, order, jumps, tail):
        self.segs = segs
        self.order = order
        self.main = set(order)
        self.tail = tail
        self.jumps = jumps  # (position, gap_km, from, to)
        self.gap_mi_before = {}  # seg index -> straight-line gap miles
        gap_mi = 0.0
        jump_by_pos = {pos: gap_km for pos, gap_km, _, _ in jumps}
        self.start_chainage = {}
        cum = 0.0
        for pos, idx in enumerate(order):
            if pos in jump_by_pos:
                gap_mi += jump_by_pos[pos] * 0.621371192237334
            self.gap_mi_before[idx] = gap_mi
            self.start_chainage[idx] = cum + gap_mi
            cum += segs[idx]["props"]["miles"]
        self.total_mapped_mi = cum
        self.total_gap_mi = gap_mi
        self.total_chainage_mi = cum + gap_mi
        self.geo_len = {idx: segment_geo_len(segs[idx]["coords"])
                        for idx in order}
        # edge grids: (cell -> [(seg_idx, edge_idx)]) for main-chain
        # edges (chainage), for all edges (chapter/state attribution),
        # and for unchained-tail edges (off-chain diagnosis)
        self.main_grid = self._edge_grid(order, 0.1)
        self.all_grid = self._edge_grid(list(range(len(segs))), 0.1)
        self.tail_grid = self._edge_grid(tail, 0.1)

    def _edge_grid(self, seg_indices, cell):
        grid = defaultdict(list)
        for idx in seg_indices:
            cs = self.segs[idx]["coords"]
            for ei in range(len(cs) - 1):
                mx = (cs[ei][0] + cs[ei + 1][0]) / 2
                my = (cs[ei][1] + cs[ei + 1][1]) / 2
                grid[(int(mx // cell), int(my // cell))].append((idx, ei))
        return grid

    def _nearest_edge(self, pt, grid, cell=0.1):
        """(seg_idx, edge_idx, t, dist_m) of the nearest edge, or None.

        Edges are indexed by midpoint, so a long edge can sit several
        cells from a point near its end: the search covers a fixed
        neighbourhood (span 2, ~22 km) with no early exit, and widens
        to span 6 (~66 km) when nothing is found there."""
        cx, cy = int(pt[0] // cell), int(pt[1] // cell)
        px, py = to_xy(pt)
        for span in (2, 6):
            best = None
            for gx in range(cx - span, cx + span + 1):
                for gy in range(cy - span, cy + span + 1):
                    for (idx, ei) in grid.get((gx, gy), []):
                        cs = self.segs[idx]["coords"]
                        a, b = cs[ei], cs[ei + 1]
                        ax, ay = to_xy(a)
                        bx, by = to_xy(b)
                        dx, dy = bx - ax, by - ay
                        len2 = dx * dx + dy * dy
                        t = 0.0 if len2 == 0 else max(
                            0.0, min(1.0, ((px - ax) * dx
                                           + (py - ay) * dy) / len2))
                        fx, fy = ax + t * dx, ay + t * dy
                        d = math.hypot(px - fx, py - fy) * 1000.0
                        if best is None or d < best[3]:
                            best = (idx, ei, t, d)
            if best is not None:
                return best
        return None

    def project(self, pt):
        """(chainage_mi or None, snap_m, chapter, state, off_chain).
        snap_m is the distance to the nearest main-chain edge;
        chapter/state come from the nearest edge of any kind."""
        main = self._nearest_edge(pt, self.main_grid)
        snap_m = main[3] if main else None
        chainage = None
        if main is not None and main[3] <= SNAP_LIMIT_M:
            idx, ei, t, _ = main
            cs = self.segs[idx]["coords"]
            geo = self.geo_len[idx]
            if geo > 0:
                before = sum(
                    dist_km(a, b)
                    for a, b in zip(cs[:ei + 1], cs[1:ei + 1]))
                # geometry length along the segment to the projection
                edge_len = dist_km(cs[ei], cs[ei + 1])
                frac = (before + t * edge_len) / geo
            else:
                frac = 0.0
            chainage = (self.start_chainage[idx]
                        + frac * self.segs[idx]["props"]["miles"])
        overall = self._nearest_edge(pt, self.all_grid)
        chapter = state = None
        if overall is not None and overall[3] <= ATTRIBUTION_LIMIT_M:
            props = self.segs[overall[0]]["props"]
            chapter = props.get("chapter")
            state = props.get("state")
            if chapter in (None, "None"):
                chapter = None
        off_chain = chainage is None
        tail_snap = None
        if off_chain:
            nearest_tail = self._nearest_edge(pt, self.tail_grid)
            tail_snap = nearest_tail[3] if nearest_tail else None
        return (r2(chainage), r2(snap_m), chapter, state, off_chain,
                r2(tail_snap))


# ------------------------------------------------------- chapter extents
def parse_extents_md(path):
    """Main table of ncta-chapter-extents-2026-11-23.md, in file order:
    [(code, name, west_endpoint, east_endpoint)]."""
    rows = []
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        # ['', Chapter, Code, State(s), Western, Eastern, Miles, Miles, Source, '']
        if len(parts) != 10:
            continue
        if parts[1] in ("Chapter", "") or set(parts[1]) <= {"-", " "}:
            continue
        if set(parts[2]) <= {"-", " "}:
            continue
        rows.append({"code": parts[2], "name": parts[1],
                     "west": parts[4] or None, "east": parts[5] or None})
    return rows


def shared_endpoint(prev_row, row):
    """The junction name two consecutive chapters share, from their
    endpoint strings — the extents table's west/east columns are not
    always in walk direction (GMC and MALT are listed reversed), so
    pairings are tried facing-first, then crossed. Returns
    (junction_name, west_string, east_string) or (None, None, None).

    Two strings name the same junction when they share >= 2 content
    tokens, or a token containing a digit (a highway/mile number is
    a strong identifier). The junction name is the longest common
    leading word-run of the pair when it carries >= 2 content
    words, else the shorter string verbatim. Genuine gaps (FLY/SRV
    — Lonetree WMA vs Lake Ashtabula; CNY/ADK — the county line vs
    Forestport) share nothing and correctly return None."""
    STOP = {"the", "of", "at", "near", "and", "or", "a", "an", "in",
            "on", "to", "for", "with", "see", "county", "trail"}
    GENERIC = STOP | {"junction", "end", "north", "south", "east",
                      "west", "northern", "southern", "eastern",
                      "western"}

    def tokens(s):
        s = (s or "").lower()
        s = re.sub(r"[—–\-/(),.;:]", " ", s)
        return [t for t in s.split() if t not in STOP]

    def content(s):
        return set(tokens(s))

    def pair_match(a, b):
        if not a or not b:
            return None
        if a == b:
            return (a, a, b)
        # one wording contained in the other ("Gunflint Trail" in
        # "Gunflint Trail (connects to Kekekabic Trail)")
        if a in b or b in a:
            shorter = a if len(a) <= len(b) else b
            return (shorter, a, b)
        shared = content(a) & content(b)
        digit_shared = any(any(ch.isdigit() for ch in t)
                           for t in shared)
        if len(shared) >= 2 or digit_shared:
            ta = a.split()
            tb = b.split()
            run = []
            for x, y in zip(ta, tb):
                if x.lower().strip(",.;:") == y.lower().strip(",.;:"):
                    run.append(x)
                else:
                    break
            run_content = [w for w in run
                           if w.lower().strip(",.;:") not in GENERIC]
            name = (" ".join(run) if len(run_content) >= 2
                    else (a if len(a) <= len(b) else b))
            return (name, a, b)
        return None

    # facing pair first (walk direction), then crossed pairings
    for a, b in ((prev_row["east"], row["west"]),
                 (prev_row["east"], row["east"]),
                 (prev_row["west"], row["west"]),
                 (prev_row["west"], row["east"])):
        hit = pair_match(a, b)
        if hit:
            return hit
    return (None, None, None)


# ------------------------------------------------------------------ build
def main():
    segs = load_segments()
    order, tail, jumps, terminal_break, west_end = build_chain(segs)
    chain = Chain(segs, order, jumps, tail)
    print(f"centerline segments : {len(segs)}")
    print(f"main chain          : {len(order)} segments, "
          f"{chain.total_mapped_mi:.2f} mapped mi + "
          f"{chain.total_gap_mi:.2f} straight-line gap mi = "
          f"{chain.total_chainage_mi:.2f} chainage mi")
    print(f"unchained (tail)    : {len(tail)} segments, "
          f"{sum(segs[i]['props']['miles'] for i in tail):.2f} mi")
    print(f"jumps in main chain : {len(jumps)}")
    if terminal_break:
        print(f"terminal break      : {terminal_break[0]:.2f} km "
              f"({terminal_break[0] * 0.621371192237334:.2f} mi) "
              f"{terminal_break[1]['chapter']}/{terminal_break[1]['state']} "
              f"-> {terminal_break[2]['chapter']}/"
              f"{terminal_break[2]['state']} — walk ends here")
    for pos, gap_km, frm, to in jumps:
        print(f"  jump after #{pos}: {gap_km:.2f} km "
              f"({gap_km * 0.621371192237334:.2f} mi) "
              f"{frm['chapter']}/{frm['state']} -> "
              f"{to['chapter']}/{to['state']}")

    extents = parse_extents_md(EXTENTS_MD)
    print(f"extents chapters    : {len(extents)}")
    codes = [r["code"] for r in extents]
    by_code = {r["code"]: r for r in extents}

    # first occurrence of each canonical chapter in walk order
    first_pos = {}
    for pos, idx in enumerate(order):
        code = segs[idx]["props"].get("chapter")
        if code in by_code and code not in first_pos:
            first_pos[code] = pos
    missing = [c for c in codes if c not in first_pos]
    if missing:
        print(f"WARNING chapters with no main-chain segment: {missing}")
    walk_codes = [c for c in codes if c in first_pos]
    walk_codes.sort(key=lambda c: first_pos[c])
    print(f"chapter walk order  : {' > '.join(walk_codes)}")

    # per-chapter walk miles vs chapters.json (validation)
    chapters_json = json.loads(CHAPTERS_JSON.read_text())
    totals = defaultdict(float)
    for row in chapters_json:
        totals[row["code"]] += row["total_mi"]
    walk_miles = Counter()
    for idx in order:
        walk_miles[segs[idx]["props"].get("chapter")] += \
            segs[idx]["props"]["miles"]
    chapter_check = []
    for code in walk_codes:
        diff = walk_miles[code] - totals.get(code, 0.0)
        chapter_check.append({"code": code,
                              "walk_mi": round(walk_miles[code], 2),
                              "chapters_json_mi": round(totals.get(code, 0.0), 2),
                              "diff_mi": round(diff, 2)})
        if abs(diff) > 5:
            print(f"  CHAPTER CHECK {code}: walk {walk_miles[code]:.2f} mi "
                  f"vs chapters.json {totals.get(code, 0.0):.2f} mi "
                  f"(diff {diff:+.2f})")

    # ---- chapter boundary + terminus entries -----------------------
    def chain_point_at(pos):
        """(coord, chainage) at the entry end of the segment at pos."""
        idx = order[pos]
        cs = segs[idx]["coords"]
        # entry end: the end nearer the previous segment's far end
        if pos == 0:
            coord = cs[0] if dist_km(cs[0], west_end) <= \
                dist_km(cs[-1], west_end) else cs[-1]
        else:
            prev = segs[order[pos - 1]]["coords"]
            prev_far = prev[-1]
            coord = cs[0] if dist_km(cs[0], prev_far) <= \
                dist_km(cs[-1], prev_far) else cs[-1]
        return coord, chain.start_chainage[idx]

    entries = []

    def add(name, kind, source, coord, chainage, snap_m, chapter, state,
            off_chain, extra=None, named=True):
        props = {
            "name": name,
            "kind": kind,
            "source": source,
            "chapter": chapter,
            "state": state,
            "chainage_mi": r2(chainage),
            "from_east_mi": (r2(chain.total_chainage_mi - chainage)
                             if chainage is not None else None),
            "snap_m": r2(snap_m),
            "off_chain": bool(off_chain),
            "named": bool(named),
        }
        if extra:
            props.update(extra)
        bits = [name, kind, chapter or "", state or ""]
        if extra:
            for k in ("state_ident", "junction_name", "prev_endpoint",
                      "next_endpoint"):
                if extra.get(k):
                    bits.append(str(extra[k]))
        props["search_text"] = " ".join(b for b in bits if b).lower()
        entries.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(coord[0], 5),
                                         round(coord[1], 5)]},
            "properties": props,
        })

    # termini
    first_ch = by_code[walk_codes[0]]
    last_ch = by_code[walk_codes[-1]]
    # termini: the end chapter's endpoint NOT used in the neighbouring
    # junction pair (for GMC that is the AT junction — its row is
    # listed reversed, so the "west" column is the eastern terminus).
    first_junction = shared_endpoint(
        first_ch, by_code[walk_codes[1]])
    west_name = (first_ch["east"]
                 if first_junction[1] == first_ch["west"]
                 else first_ch["west"])
    last_junction = shared_endpoint(
        by_code[walk_codes[-2]], last_ch)
    east_name = (last_ch["east"]
                 if last_junction[2] == last_ch["west"]
                 else last_ch["west"])
    end_idx = order[-1]
    end_coord = segs[end_idx]["coords"][-1]
    add(f"Western terminus — {west_name}", "Terminus",
        "chapter-extents", west_end, 0.0, 0.0,
        walk_codes[0], segs[order[0]]["props"].get("state"), False,
        {"chapter_name": first_ch["name"]})
    add(f"Eastern terminus — {east_name}", "Terminus",
        "chapter-extents", end_coord, chain.total_chainage_mi, 0.0,
        walk_codes[-1], segs[end_idx]["props"].get("state"), False,
        {"chapter_name": last_ch["name"]})
    # boundaries between consecutive chapters in walk order
    for prev_code, code in zip(walk_codes, walk_codes[1:]):
        pos = first_pos[code]
        coord, ch = chain_point_at(pos)
        prev_row, row = by_code[prev_code], by_code[code]
        junction, prev_ep, next_ep = shared_endpoint(prev_row, row)
        # prev/next_endpoint are the two wordings of the junction
        # place (the matched pair — the table's west/east columns
        # are reversed for GMC/MALT, so the facing cells are NOT
        # used here); with no match they fall back to the facing
        # strings, which name the two sides of a genuine gap.
        add(f"{prev_row['name']} / {row['name']} boundary",
            "Chapter boundary", "chapter-extents", coord, ch, 0.0,
            code, segs[order[pos]]["props"].get("state"), False,
            {"west_chapter": prev_code, "east_chapter": code,
             "junction_name": junction,
             "prev_endpoint": prev_ep or prev_row["east"],
             "next_endpoint": next_ep or row["west"]})

    # ---- NCTA points + mile markers --------------------------------
    def add_points(path, kind_map, source):
        doc = json.loads(Path(path).read_text())
        n_off = 0
        tail_near = []
        for f in doc["features"]:
            p = f["properties"]
            coord = f["geometry"]["coordinates"]
            chainage, snap_m, chapter, state, off_chain, tail_snap = \
                chain.project((coord[0], coord[1]))
            if off_chain:
                n_off += 1
                if tail_snap is not None and tail_snap <= SNAP_LIMIT_M:
                    tail_near.append(p.get("name") or p.get("ident")
                                     or kind_map(p))
            # mile markers carry no "name" field — their ident IS
            # their name ("MN-187.5"); a waypoint with neither takes
            # its kind as its name (ITM rule), with named=false.
            name = p.get("name") or p.get("ident")
            kind = kind_map(p)
            extra = {}
            if source == "mile-markers":
                extra["state_mile"] = p.get("mile")
                extra["state_ident"] = p.get("ident")
                extra["source_service"] = p.get("source_service")
            else:
                extra["subtype"] = p.get("subtype")
                extra["waypoint_id"] = p.get("waypoint_id")
                # chapter/state from the service record when the
                # geometry attribution fails (far off-chain points)
                if chapter is None and p.get("chapter"):
                    chapter = p.get("chapter")
                if state is None and p.get("state"):
                    state = p.get("state")
            add(name or kind, kind, source, coord, chainage, snap_m,
                chapter, state, off_chain, extra, named=bool(name))
        return len(doc["features"]), n_off, tail_near

    n_camp, off_camp, tail_camp = add_points(
        CAMPING_PATH, lambda p: "Camping", "ncta-points")
    n_places, off_places, tail_places = add_points(
        PLACES_PATH, lambda p: p.get("type") or "POI", "ncta-points")
    n_mark, off_mark, tail_mark = add_points(
        MARKERS_PATH, lambda p: "Mile marker", "mile-markers")
    print(f"camping entries     : {n_camp} (off-chain {off_camp})")
    print(f"places entries      : {n_places} (off-chain {off_places})")
    print(f"mile-marker entries : {n_mark} (off-chain {off_mark})")
    tail_near_names = sorted(set(tail_camp + tail_places + tail_mark))
    tail_near_count = len(tail_camp) + len(tail_places) + len(tail_mark)
    print(f"off-chain but within 250 m of an unchained segment: "
          f"{tail_near_count} entries (chain defect, not point defect)")

    # ---- assemble ---------------------------------------------------
    entries.sort(key=lambda e: (
        e["properties"]["chainage_mi"] is None,
        e["properties"]["chainage_mi"] if
        e["properties"]["chainage_mi"] is not None else 0,
        e["properties"]["kind"], e["properties"]["name"]))
    by_kind = Counter(e["properties"]["kind"] for e in entries)
    by_source = Counter(e["properties"]["source"] for e in entries)
    by_state = Counter(e["properties"]["state"] for e in entries)
    with_chainage = sum(1 for e in entries
                        if e["properties"]["chainage_mi"] is not None)
    # every entry must carry name + kind + coordinates (assert, don't ship a bad index)
    for e in entries:
        assert e["properties"]["name"], e
        assert e["properties"]["kind"], e
        assert len(e["geometry"]["coordinates"]) == 2, e

    out = {
        "metadata": {
            "dataset": "NCT gazetteer — search index of named things on "
                       "the North Country Trail (NCTA points, state mile "
                       "markers, chapter boundaries, termini)",
            "built_by": "scripts/build_gazetteer_national.py",
            "built_utc_date": __import__("time").strftime(
                "%Y-%m-%d", __import__("time").gmtime()),
            "inputs": {
                "camping": "site/data/camping.geojson",
                "places": "site/data/ncta-places.geojson",
                "mile_markers": "site/data/mile-markers.geojson",
                "chapter_extents":
                    "ncta-chapter-extents-2026-11-23.md (names only; "
                    "coordinates/chainages from the centerline)",
                "centerline": ["site/data/centerline-natural.geojson",
                               "site/data/centerline-road.geojson",
                               "site/data/centerline-urban.geojson"],
            },
            "chainage_method": "Greedy endpoint walk of the centerline "
                "from the western terminus (150 m join tolerance); "
                "chainage = stored segment miles before the point plus "
                "its fraction along its segment, plus straight-line "
                "miles for any unmapped gap the walk jumped. Points "
                "more than 250 m from the main chain get chainage null "
                "(off_chain=true) rather than a fabricated position.",
            "chain": {
                "segments_total": len(segs),
                "segments_in_main_chain": len(order),
                "segments_unchained": len(tail),
                "unchained_miles": round(
                    sum(segs[i]["props"]["miles"] for i in tail), 2),
                "mapped_miles": round(chain.total_mapped_mi, 2),
                "gap_straight_line_miles": round(chain.total_gap_mi, 2),
                "total_chainage_miles": round(chain.total_chainage_mi, 2),
                "jumps": [{"after_segment": pos,
                           "gap_km": round(gap_km, 3),
                           "gap_mi": round(gap_km * 0.621371192237334, 3),
                           "from_chapter": frm.get("chapter"),
                           "from_state": frm.get("state"),
                           "to_chapter": to.get("chapter"),
                           "to_state": to.get("state")}
                          for pos, gap_km, frm, to in jumps],
                "terminal_break": (
                    {"gap_km": round(terminal_break[0], 3),
                     "gap_mi": round(terminal_break[0]
                                     * 0.621371192237334, 3),
                     "from_chapter": terminal_break[1].get("chapter"),
                     "from_state": terminal_break[1].get("state"),
                     "to_chapter": terminal_break[2].get("chapter"),
                     "to_state": terminal_break[2].get("state"),
                     "note": "The walk ends here (eastern terminus "
                             "reached); the jump is NOT counted in the "
                             "gap miles above."}
                    if terminal_break else None),
                "off_chain_within_250m_of_unchained_segment": {
                    "count": tail_near_count,
                    "names": tail_near_names},
                "chapter_check_walk_vs_chapters_json": chapter_check,
            },
            "chapter_walk_order": walk_codes,
            "entries": len(entries),
            "with_chainage": with_chainage,
            "off_chain": len(entries) - with_chainage,
            "counts_by_kind": dict(sorted(by_kind.items())),
            "counts_by_source": dict(sorted(by_source.items())),
            "counts_by_state": {str(k): v
                                for k, v in sorted(by_state.items(),
                                                   key=lambda kv: str(kv[0]))},
            "name_rule": "A waypoint with no name in the NCTA service "
                         "takes its kind as its name, with named=false.",
        },
        "entries": [e["properties"] | {"coordinates":
                                        e["geometry"]["coordinates"]}
                    for e in entries],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=1))
    # verify: re-read and check it parses + every entry is complete
    back = json.loads(OUT_PATH.read_text())
    assert len(back["entries"]) == len(entries)
    assert all(e.get("name") and e.get("kind")
               and len(e.get("coordinates", [])) == 2
               for e in back["entries"])
    print(f"gazetteer           : {len(entries)} entries -> "
          f"{OUT_PATH.relative_to(REPO_ROOT)} "
          f"({OUT_PATH.stat().st_size / 1e6:.2f} MB)")
    print(f"with chainage       : {with_chainage}/{len(entries)}")
    print("by kind:", dict(sorted(by_kind.items())))
    print("SUMMARY " + json.dumps({
        "entries": len(entries),
        "with_chainage": with_chainage,
        "counts_by_kind": dict(sorted(by_kind.items())),
        "total_chainage_mi": round(chain.total_chainage_mi, 2),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
