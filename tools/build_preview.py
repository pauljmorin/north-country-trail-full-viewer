#!/usr/bin/env python3
"""Build the standalone preview of the NCT full viewer.

Reads site/ and writes a single self-contained index.html into
~/workspace/your_files/nct-full-viewer-preview/ :

- leaflet.css + style.css inlined in <style> blocks
- leaflet.js + esri-leaflet.js + app.js inlined in <script> blocks
- every data file app.js fetches that is under ~5 MB embedded in
  window.__NCT_DATA__ behind a fetch shim (the old completeness
  preview's pattern), so the preview works opened directly from disk
- the three files too big to embed (NWI wetlands 174 MB, OSM roads
  109 MB, partner trails 11 MB) are copied to preview/data/ and load
  from relative paths — they work under a local server or the deployed
  site, not from file:// ; a note in the preview and in README.md says so

Re-run after any site/ change: python3 tools/build_preview.py
"""
import json
import os
import shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "site")
OUT = os.path.expanduser("~/workspace/your_files/nct-full-viewer-preview")
EMBED_LIMIT = 5 * 1024 * 1024

# Files app.js fetches (relative to site/). Everything under the limit is
# embedded; the rest are copied to preview/data/ for relative-path loads.
DATA_FILES = [
    "data/centerline-natural.geojson",
    "data/centerline-road.geojson",
    "data/centerline-urban.geojson",
    "data/chapter-extents.json",
    "data/trail-alerts.geojson",
    "data/nct-reroutes.geojson",
    "data/nbi-bridges.geojson",
    "data/tribal-lands.geojson",
    "data/chainage.geojson",
    "data/chapter-boundaries.geojson",
    "data/road-walk.geojson",
    "data/camping.geojson",
    "data/ncta-places.geojson",
    "data/mile-markers.geojson",
    "data/osm-bike-routes.geojson",
    "data/ncta-map-sheets.geojson",
    "data/gazetteer.json",
    "data/nwi-wetlands.geojson",
    "data/osm-roads.geojson",
    "data/partner-trails.geojson",
    "data/parcels.geojson",
]

PREVIEW_NOTE = (
    "Preview note: the Wetlands (174 MB), OSM roads (109 MB), parcels "
    "(98 MB) and partner trails (11 MB) layers are NOT embedded in this "
    "file — they load from data/ when this preview is served by a local "
    "server or from the deployed site. Opened directly from disk they "
    "will fail to load. Everything else on this page is embedded and "
    "works from disk."
)


def js_string(text):
    """A JS double-quoted string literal for text, safe inside <script>."""
    return json.dumps(text).replace("<", "\\u003c")


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)

    embedded = {}
    copied = []
    for rel in DATA_FILES:
        path = os.path.join(SITE, rel)
        size = os.path.getsize(path)
        if size < EMBED_LIMIT:
            with open(path, encoding="utf-8") as fh:
                embedded[rel] = fh.read()
        else:
            shutil.copyfile(path, os.path.join(OUT, rel))
            copied.append((rel, size))
    print("embedded %d files (%d bytes total)" % (
        len(embedded), sum(len(v) for v in embedded.values())))
    for rel, size in copied:
        print("copied (too big to embed): %s %d bytes" % (rel, size))

    with open(os.path.join(SITE, "index.html"), encoding="utf-8") as fh:
        html = fh.read()

    def read(name):
        with open(os.path.join(SITE, name), encoding="utf-8") as fh:
            return fh.read()

    html = html.replace(
        '<link rel="stylesheet" href="leaflet.css">',
        "<style>\n" + read("leaflet.css") + "\n</style>", 1)
    html = html.replace(
        '<link rel="stylesheet" href="style.css">',
        "<style>\n" + read("style.css") + "\n</style>", 1)
    html = html.replace(
        '<script src="leaflet.js"></script>',
        "<script>\n" + read("leaflet.js") + "\n</script>", 1)
    html = html.replace(
        '<script src="esri-leaflet.js"></script>',
        "<script>\n" + read("esri-leaflet.js") + "\n</script>", 1)

    shim = (
        "<script>\n"
        "/* Preview-only: the live site fetches these files from data/; "
        "this standalone copy serves them from memory so the page works "
        "opened directly, where fetch() of local files is blocked. "
        "Files over ~5 MB are NOT embedded — they load from data/ "
        "under a local server (see README.md). */\n"
        "window.__NCT_DATA__ = {\n"
        + ",\n".join("  %s: %s" % (json.dumps(k), js_string(v))
                     for k, v in embedded.items())
        + "\n};\n"
        "(function () {\n"
        "  var realFetch = window.fetch.bind(window);\n"
        "  window.fetch = function (url, opts) {\n"
        "    var key = String(url);\n"
        "    if (Object.prototype.hasOwnProperty.call(window.__NCT_DATA__, key)) {\n"
        "      return Promise.resolve(new Response(window.__NCT_DATA__[key], { status: 200 }));\n"
        "    }\n"
        "    return realFetch(url, opts);\n"
        "  };\n"
        "})();\n"
        "</script>"
    )
    html = html.replace(
        '<script src="app.js"></script>',
        shim + "\n<script>\n" + read("app.js") + "\n</script>", 1)

    # Plain note in the preview itself, under the load status line.
    anchor = '<p id="load-status" class="status" role="status">Loading map data&hellip;</p>'
    assert anchor in html
    html = html.replace(
        anchor,
        anchor + '\n  <p class="status preview-note">' + PREVIEW_NOTE + "</p>", 1)

    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    print("wrote %s (%d bytes)" % (
        os.path.join(OUT, "index.html"),
        os.path.getsize(os.path.join(OUT, "index.html"))))

    for name in ("about.html", "data-sources.html", "favicon.svg"):
        shutil.copyfile(os.path.join(SITE, name), os.path.join(OUT, name))
    print("copied about.html, data-sources.html, favicon.svg")

    readme = """# NCT full viewer — standalone preview

Built by `tools/build_preview.py` in the
`north-country-trail-full-viewer` repo (re-run it after any `site/`
change). This is the NEW full trail viewer (ITM-based shell, wave-1
layers wired in Nov 23, 2026) — not the old completeness viewer
(`nct-completeness-viewer-preview/` is that stale product; do not
mix them up).

## What works from disk

Open `index.html` directly in a browser. The CSS and JS are inlined,
and every data file under ~5 MB is embedded in the page behind a
fetch shim, so the base line, chapters, chapter click + zoom, copy
link, legend, basemaps, and these layers all work with no server:
alerts, reroutes, NBI bridges, tribal lands, chainage, chapter
boundaries, road walk, camping, NCTA Places, mile markers, OSM bike
routes, NCTA map sheets, and gazetteer search. PAD-US and Mapbox load
live from their services when online.

## What needs a server (or the deployed site)

Four layers are too big to embed and load from `data/` by relative
path instead — they work when this folder is served by a local server
(e.g. `python3 -m http.server` in this folder) or from the deployed
site, and FAIL when the preview is opened directly from disk:

- Wetlands (NWI) — `data/nwi-wetlands.geojson`, 174 MB
- Roads (OSM) — `data/osm-roads.geojson`, 109 MB
- Parcels — `data/parcels.geojson`, 98 MB
- Partner / concurrent trails — `data/partner-trails.geojson`, 11 MB

Their toggles stay in the panel; switching one on from disk reports
a load error in the status line rather than drawing anything. That
is a limitation of this preview, not of the viewer: on the deployed
site the same files load over HTTP like any other layer (slowly —
they are OFF by default and lazy-load only when toggled on).

## Files

- `index.html` — the whole viewer, self-contained except the four
  big layers above and the live tile/service layers.
- `data/` — the four big layer files only (the small ones are
  embedded in `index.html`).
- `about.html`, `data-sources.html` — the viewer pages, copied from
  `site/` at build time.
"""
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme)
    print("wrote README.md")


if __name__ == "__main__":
    main()
