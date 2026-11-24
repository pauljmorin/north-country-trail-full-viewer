#!/usr/bin/env python3
"""Pull the FULL NCTA map-sheet set for the NCT viewer (plan step 5).

Source: the NCTA's published per-state map-series GeoPDFs, one combined
PDF per state/region, free downloads from northcountrytrail.org/maps/:
  nd_map_series.pdf, mn_map_series.pdf, wi_map_series.pdf,
  mi_map_series_up.pdf, mi_map_series_lp.pdf,
  oh_map_series_northwest.pdf, oh_map_series_eastern.pdf,
  pa_map_series.pdf, ny_map_series.pdf, vt_map_series.pdf
(Links as listed on https://northcountrytrail.org/trail-map/, "Printable"
per state; Ohio is split Northwest / Eastern, Michigan Upper / Lower
Peninsula.)

Method (adapted from the Itasca Moraine viewer's
working/ncta-sheets/build_sheets_full.py, which did Minnesota only):
  - Each PDF page carries one sheet as a GeoPDF viewport (/VP): the
    /Measure /GPTS array gives the map frame's four lat/lon corners in
    LPTS order BL, TL, TR, BR. The footprint polygon is the ring
    BL, BR, TR, TL. pikepdf reads /VP; pages with no /VP (cover/index
    pages, if any) are skipped and recorded.
  - The printed sheet label is read off the page text (pdftotext
    -layout): it sits in the title block just below the "* Section
    Maps" line, e.g. MN-001, MI UP-091, MI LP-089, OH-014. The label
    is verified against the page number (label number == page number
    in every series, spot-checked first/last page of each). NOTE: the
    two Ohio PDFs BOTH number OH-001.. — sheet ids repeat across the
    Northwest and Eastern series, so `series` is part of the identity.
  - trail_miles_in_sheet: geodesic miles of the NCT centerline
    (site/data/centerline-*.geojson) inside the sheet quad. This
    replaces ITM's "miles" string (a Minnesota-mile-range label that
    needs chainage, which does not exist trail-wide yet).
  - Cross-check: the Minnesota footprints are compared corner-for-corner
    against the ITM viewer's pages-geo.json (same source file, Nov 11).

Output: site/data/ncta-map-sheets.geojson — one Polygon per sheet,
properties sheet / state / series / page / bounds / trail_miles_in_sheet.
No sheet IMAGES are built here (that is the shell/viewer step); this
file is footprints only.

Usage: python3 scripts/pull-ncta-map-sheets.py [--workdir DIR] [--skip-download]
  --skip-download reuses the PDFs already in --workdir/ncta-series/.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

import pikepdf
from pyproj import Geod
from shapely.geometry import Polygon, shape
from shapely.strtree import STRtree

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DATA = os.path.join(REPO, "site", "data")
PULLED = time.strftime("%Y-%m-%d", time.gmtime())
GEOD = Geod(ellps="WGS84")

BASE = "https://northcountrytrail.org/maps/"
# (state, series slug, pdf filename, expected label prefix pattern)
SERIES = [
    ("ND", "nd", "nd_map_series.pdf"),
    ("MN", "mn", "mn_map_series.pdf"),
    ("WI", "wi", "wi_map_series.pdf"),
    ("MI", "mi-up", "mi_map_series_up.pdf"),
    ("MI", "mi-lp", "mi_map_series_lp.pdf"),
    ("OH", "oh-northwest", "oh_map_series_northwest.pdf"),
    ("OH", "oh-eastern", "oh_map_series_eastern.pdf"),
    ("PA", "pa", "pa_map_series.pdf"),
    ("NY", "ny", "ny_map_series.pdf"),
    ("VT", "vt", "vt_map_series.pdf"),
]

LABEL_RE = re.compile(r"([A-Z]{2}(?: [A-Z]{2})?)-(\d{3})")


def download_series(sdir, skip):
    import requests
    for _state, _series, fname in SERIES:
        path = os.path.join(sdir, fname)
        if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
            print("%s: already present (%d bytes)" % (fname, os.path.getsize(path)))
            continue
        if skip:
            print("WARNING: %s missing and --skip-download given" % fname)
            continue
        print("downloading %s ..." % (BASE + fname))
        r = requests.get(BASE + fname, timeout=1800, stream=True)
        r.raise_for_status()
        with open(path, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
        print("%s: %d bytes" % (fname, os.path.getsize(path)))


def page_labels(pdf_path):
    """Printed sheet label per page, from pdftotext -layout: the label
    sits in the title block just below the '* Section Maps' line."""
    out = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                         capture_output=True, text=True, timeout=1200)
    if out.returncode != 0:
        raise RuntimeError("pdftotext failed on %s: %s" % (pdf_path, out.stderr[:500]))
    pages = out.stdout.split("\f")
    labels = {}
    for i, text in enumerate(pages):
        pg = i + 1
        lines = text.splitlines()
        label = None
        for j, line in enumerate(lines):
            if "Section Maps" in line:
                for k in range(j, min(j + 4, len(lines))):
                    m = LABEL_RE.search(lines[k])
                    if m:
                        label = m.group(0)
                        break
                break
        if label is None:
            # fall back: any label-shaped token on the page, first one
            for line in lines:
                m = LABEL_RE.search(line)
                if m:
                    label = m.group(0)
                    break
        labels[pg] = label
    return labels


def load_centerline():
    segs = []
    for name in ("centerline-natural", "centerline-road", "centerline-urban"):
        d = json.load(open(os.path.join(SITE_DATA, name + ".geojson")))
        for f in d["features"]:
            g = shape(f["geometry"])
            if g.geom_type == "LineString":
                segs.append(g)
            elif g.geom_type == "MultiLineString":
                segs.extend(list(g.geoms))
    return STRtree(segs), segs


def miles_in_quad(tree, segs, quad):
    idxs = tree.query(quad)
    total = 0.0
    for i in idxs:
        inter = segs[i].intersection(quad)
        if inter.is_empty:
            continue
        geoms = []
        if inter.geom_type == "LineString":
            geoms = [inter]
        elif inter.geom_type == "MultiLineString":
            geoms = list(inter.geoms)
        for g in geoms:
            coords = list(g.coords)
            if len(coords) < 2:
                continue
            total += GEOD.line_length([c[0] for c in coords],
                                      [c[1] for c in coords]) / 1609.344
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.path.expanduser(
        "~/workspace/nct-step5-work"))
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()
    sdir = os.path.join(args.workdir, "ncta-series")
    os.makedirs(sdir, exist_ok=True)
    os.makedirs(SITE_DATA, exist_ok=True)

    download_series(sdir, args.skip_download)
    tree, segs = load_centerline()
    print("centerline segments indexed: %d" % len(segs))

    features = []
    report = []
    for state, series, fname in SERIES:
        path = os.path.join(sdir, fname)
        if not os.path.exists(path):
            print("SKIP %s: no PDF" % fname)
            report.append((state, series, fname, None, None, "missing PDF"))
            continue
        labels = page_labels(path)
        pdf = pikepdf.open(path)
        n_pages = len(pdf.pages)
        kept = skipped = 0
        label_mismatch = []
        for pg in range(1, n_pages + 1):
            page = pdf.pages[pg - 1]
            vp = page.get("/VP")
            if not vp:
                skipped += 1
                continue
            gpts = [float(x) for x in vp[0]["/Measure"]["/GPTS"]]
            # GPTS order (LPTS BL, TL, TR, BR): lat,lon pairs
            bl = (gpts[1], gpts[0])
            tl = (gpts[3], gpts[2])
            tr = (gpts[5], gpts[4])
            br = (gpts[7], gpts[6])
            ring = [list(bl), list(br), list(tr), list(tl), list(bl)]
            lons = [c[0] for c in ring]
            lats = [c[1] for c in ring]
            quad = Polygon(ring)
            label = labels.get(pg)
            if label is None:
                label = "%s-%03d" % (state, pg)
                label_mismatch.append((pg, "no printed label; fell back to page number"))
            else:
                num = int(label.split("-")[-1])
                if num != pg:
                    label_mismatch.append((pg, "label %s != page %d" % (label, pg)))
            mi = miles_in_quad(tree, segs, quad)
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {
                    "sheet": label,
                    "state": state,
                    "series": series,
                    "page": pg,
                    "bounds": [[min(lats), min(lons)], [max(lats), max(lons)]],
                    "trail_miles_in_sheet": round(mi, 3),
                    "source_pdf": BASE + fname,
                },
            })
            kept += 1
        print("%s (%s): %d pages, %d sheets kept, %d skipped (no /VP), "
              "label issues: %d" % (fname, series, n_pages, kept, skipped,
                                    len(label_mismatch)))
        for pg, why in label_mismatch[:10]:
            print("   p%d: %s" % (pg, why))
        report.append((state, series, fname, n_pages, kept,
                       "%d skipped" % skipped if skipped else "ok"))

    out = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "NCTA map-sheet footprints, full trail-wide set",
            "pulled_utc_date": PULLED,
            "source": "NCTA per-state map-series GeoPDFs, "
                      "https://northcountrytrail.org/maps/ (free downloads)",
            "method": ("One Polygon per GeoPDF page carrying a /VP viewport; "
                       "ring from the /Measure /GPTS corners (BL, BR, TR, TL). "
                       "Sheet label from the printed title block. "
                       "trail_miles_in_sheet = geodesic miles of the NCT "
                       "centerline inside the quad."),
            "note": ("The two Ohio series both number OH-001.. — sheet ids "
                     "repeat across oh-northwest and oh-eastern; `series` is "
                     "part of a sheet's identity."),
            "per_series": [
                {"state": s, "series": se, "pdf": f, "pages": p,
                 "sheets": k, "status": st}
                for s, se, f, p, k, st in report],
            "features": len(features),
            "total_trail_miles_in_sheets": round(
                sum(f["properties"]["trail_miles_in_sheet"] for f in features), 2),
        },
        "features": features,
    }
    path = os.path.join(SITE_DATA, "ncta-map-sheets.geojson")
    with open(path, "w") as fh:
        json.dump(out, fh)
    print("TOTAL: %d sheets -> %s" % (len(features), path))


if __name__ == "__main__":
    main()
