#!/usr/bin/env python3
"""Derive site/data/chapter-extents.json for the NCT full trail viewer.

Parses the chapter-extents note (repo root,
ncta-chapter-extents-2026-11-23.md) for chapter names, states, endpoint
descriptions and source URLs, and joins miles to site/data/chapters.json
(the sums of the `miles` field over the three processed centerline
GeoJSON files, NCTA ArcGIS nct_public pull of 2026-11-21).

Output: 40 rows, west to east — the 39 chapters/affiliates in the note's
main table, plus one Unassigned row for miles carrying no chapter code.
Each row: {code, name, states, west, east, miles, url, affiliate}.

Variant codes in chapters.json are NOT separate rows and their miles are
NOT folded into any chapter (they stay visible in the cross-check below):
  "Central NY" (2.46 mi) — variant spelling of CNY
  GTR (1.56 mi) — probable variant of GTC
  LON (1.48 mi) — unidentified (New Rockford Canal, ND)
The two "None" rows (literal string 130.92 + null field 21.84) combine
into the single Unassigned row (152.76 mi).

Cross-checks asserted on every run (from the build brief):
  FLY 139.64, SRV 115.26, DPC 83.73, ARW 178.66, BTA 932.66,
  FLTC 390.63, SHTA 300.35, Unassigned 152.76;
  39 chapter rows sum to 4,712.97;
  4,712.97 + 152.76 + 5.50 (variant codes) = 4,871.23
  (chapters.json total; the headline 4,871.24 is the same sum at
  higher precision — see the extents note, state-comparison section).

Usage: python3 tools/derive_chapter_extents.py
Writes: site/data/chapter-extents.json (paths relative to the repo root,
or pass --root).
"""

import argparse
import json
import re
import sys
from pathlib import Path

# The nine affiliates/partners in the extents note — chapters/affiliates
# without an NCTA chapter page of their own. Everything else in the main
# table is an NCTA chapter.
AFFILIATES = {"BRT", "SHTA", "NORTA", "BTA", "FLTC", "ADK-ON", "ADK",
              "GMC", "MALT"}

# Cross-check values from the build brief (chapters.json totals).
EXPECTED = {
    "FLY": 139.64, "SRV": 115.26, "DPC": 83.73, "ARW": 178.66,
    "BTA": 932.66, "FLTC": 390.63, "SHTA": 300.35,
}
EXPECTED_UNASSIGNED = 152.76
EXPECTED_39_SUM = 4712.97
EXPECTED_VARIANT_SUM = 5.50
EXPECTED_TOTAL = 4871.23

URL_RE = re.compile(r"https?://\S+")

# Variant codes in chapters.json: code -> parent chapter code (highlight
# folding only; miles are NOT folded into the parent row).
VARIANT_OF = {"Central NY": "CNY", "GTR": "GTC", "LON": None}


def parse_main_table(md_text):
    """Yield dicts for each row of the note's main table, in file order
    (west to east)."""
    rows = []
    in_table = False
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("| Chapter | Code |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break  # end of the main table
        if line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 8:
            raise ValueError("main-table row has %d cells, expected 8: %r"
                             % (len(cells), line))
        name, code, states, west, east, _stated, computed, source = cells
        # Strip the "(affiliate)" / "(partner)" suffix from the name cell;
        # affiliation is carried by the `affiliate` field instead.
        name = re.sub(r"\s*\((affiliate|partner)\)\s*$", "", name)
        m = URL_RE.search(source)
        rows.append({
            "code": code,
            "name": name,
            "states": states,
            "west": west,
            "east": east,
            "miles_md": float(computed),
            "url": m.group(0).rstrip(")") if m else None,
            "affiliate": code in AFFILIATES,
        })
    if len(rows) != 39:
        raise ValueError("main table parsed %d rows, expected 39" % len(rows))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None,
                    help="repo root (default: parent of tools/)")
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    md_path = root / "ncta-chapter-extents-2026-11-23.md"
    chapters_path = root / "site" / "data" / "chapters.json"
    out_path = root / "site" / "data" / "chapter-extents.json"

    rows = parse_main_table(md_path.read_text(encoding="utf-8"))
    chapters = json.loads(chapters_path.read_text(encoding="utf-8"))

    miles_by_code = {}
    unassigned = 0.0
    variant_miles = {}
    for entry in chapters:
        code = entry["code"]
        total = round(float(entry["total_mi"]), 2)
        if code == "None":
            unassigned += total
        elif code in VARIANT_OF:
            variant_miles[code] = total
        else:
            if code in miles_by_code:
                raise ValueError("duplicate code in chapters.json: %s" % code)
            miles_by_code[code] = total

    out = []
    for row in rows:
        code = row["code"]
        if code not in miles_by_code:
            raise ValueError("code %s in extents note but not in "
                             "chapters.json" % code)
        out.append({
            "code": code,
            "name": row["name"],
            "states": row["states"],
            "west": row["west"],
            "east": row["east"],
            "miles": miles_by_code[code],
            "url": row["url"],
            "affiliate": row["affiliate"],
        })
    out.append({
        "code": "Unassigned",
        "name": "Unassigned",
        "states": "ND, MN, WI, MI, OH, PA, NY, VT",
        "west": "No chapter assigned in the NCTA source data",
        "east": "No chapter assigned in the NCTA source data",
        "miles": round(unassigned, 2),
        "url": None,
        "affiliate": False,
        "note": "Miles carrying no chapter code in the NCTA ArcGIS "
                "source (literal 'None' 130.92 mi + null field 21.84 mi); "
                "mostly North Dakota (126.78 mi).",
    })

    # ---- cross-checks (fail loudly rather than write a wrong file) ----
    errors = []
    for code, want in EXPECTED.items():
        got = miles_by_code.get(code)
        if got is None or abs(got - want) > 0.005:
            errors.append("%s: got %s, expected %s" % (code, got, want))
    if abs(round(unassigned, 2) - EXPECTED_UNASSIGNED) > 0.005:
        errors.append("Unassigned: got %.2f, expected %.2f"
                      % (unassigned, EXPECTED_UNASSIGNED))
    sum39 = round(sum(r["miles"] for r in out[:39]), 2)
    if abs(sum39 - EXPECTED_39_SUM) > 0.005:
        errors.append("39-row sum: got %.2f, expected %.2f"
                      % (sum39, EXPECTED_39_SUM))
    var_sum = round(sum(variant_miles.values()), 2)
    if abs(var_sum - EXPECTED_VARIANT_SUM) > 0.005:
        errors.append("variant-code sum: got %.2f, expected %.2f"
                      % (var_sum, EXPECTED_VARIANT_SUM))
    total = round(sum39 + round(unassigned, 2) + var_sum, 2)
    if abs(total - EXPECTED_TOTAL) > 0.005:
        errors.append("grand total: got %.2f, expected %.2f"
                      % (total, EXPECTED_TOTAL))
    # Miles in the extents note are the same sums at lower precision;
    # flag any row where note and chapters.json disagree by > 0.2 mi.
    for row, built in zip(rows, out):
        if abs(row["miles_md"] - built["miles"]) > 0.2:
            errors.append("%s: note says %.2f, chapters.json says %.2f"
                          % (row["code"], row["miles_md"], built["miles"]))
    if errors:
        print("CROSS-CHECK FAILED:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        sys.exit(1)

    out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print("wrote %s (%d rows)" % (out_path, len(out)))
    print("39 chapters sum %.2f; Unassigned %.2f; variant codes %.2f "
          "(%s); total %.2f"
          % (sum39, round(unassigned, 2), var_sum,
             ", ".join("%s %.2f" % kv for kv in sorted(variant_miles.items())),
             total))


if __name__ == "__main__":
    main()
