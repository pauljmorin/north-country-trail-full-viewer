# North Country Trail completeness viewer

A stripped-down viewer for the whole North Country Trail, North Dakota to
Vermont: how complete the trail is, and what it will take to finish it.
For volunteer chapter leaders planning their chapters' work, and
ultimately for decision-makers weighing the case to fund completion.
**Not for hikers** — no trip-planning features.

Live pattern: GitHub Pages, the viewer at `site/` in the repo root (same
as the Itasca Moraine trail map, live at `…/itasca-moraine-trail-map/site/`).
Source lives on GitHub; a Cloudflare mirror is optional later.

## The headline (three kinds of miles, never lumped)

| | miles | share |
|---|---|---|
| Total existing route | 4,871.24 | 100% |
| Natural tread — built off-road trail | 3,335.09 | 68.5% |
| Urban sidewalk — walkable, not trail | 124.68 | 2.6% |
| Road — trail not yet built | 1,411.47 | 29.0% |

"Walkable" is not "complete": urban sidewalk miles and road miles are
never lumped together, and neither counts as built trail. 1,536.15 miles
(road + urban) are not yet built tread. Measured from the NCTA official
centerline, pull of November 21, 2026; geodesic miles on WGS84. The
urban-sidewalk split is **derived** (see `site/data-sources.html`), not
published by NCTA.

## Files

```
site/
  index.html          map + headline + state/chapter rollup tables
  app.js              Leaflet viewer, tables, copy-link share hash
  style.css
  case.html           "The case" — gap, build rate, scenarios A–H,
                      limits, land needed, phasing, epoch history
  data-sources.html   every layer: references + interpretation method
  leaflet.js / leaflet.css   vendored Leaflet (no CDN)
  favicon.svg
  data/               OWNED BY THE DATA AGENT — see contract below
```

## Run locally

```sh
cd site
python3 -m http.server 8000
# open http://localhost:8000/
```

(Any static server works. Opening `index.html` from `file://` will not
load the GeoJSON/JSON data files — fetch is blocked on file URLs.)

## Deploy

Push the repo to GitHub and enable GitHub Pages on the repo root (or the
`site/` folder, depending on the repo layout — the viewer must be served
from `site/` as the web root so `data/…` resolves). No build step.

## Data contract (`site/data/`)

The viewer-code agent owns only the shell above; the data agent owns
`site/data/` and must not be overwritten by viewer edits. The viewer
builds against these agreed filenames. If a file is absent, the map shows
an empty layer (or a clearly-marked placeholder for PAD-US) and the
tables fall back to the embedded v1 rollup in `app.js`
(mileage-table.csv, Nov 21, 2026) — it never invents data.

| File | Contents |
|---|---|
| `data/centerline-natural.geojson` | Off-road, non-sidewalk centerline segments |
| `data/centerline-urban.geojson` | Urban-sidewalk segments (native `trail_type='Sidewalk'` + on-road miles inside a Census 2020 Urban Area or 2024 incorporated place) |
| `data/centerline-road.geojson` | Remaining on-road segments |
| `data/states.geojson` | State boundaries; per-feature properties `code`, `name`, and `natural` / `urban` / `road` / `total` / `pct` (also accepts `natural_tread_mi`, `urban_sidewalk_mi`, `road_mi`, `total_mi`, `pct_natural_tread`). Click a state for its rollup popup. |
| `data/chapters.json` | Array (or `{"chapters": [...]}`) of `{code, name, natural, urban, road, total, pct}` (same `_mi` alternates accepted). Codes `ADK-ON`, `GTR`, `LON`, `None` are rendered in the flagged "unmapped" group automatically; `unmapped: true` / `variant: true` flags also honoured. |
| `data/scenarios.json` | Array (or `{"scenarios": [...]}`) of `{id, rate, assumption, years, finish}` for scenarios A–H. `case.html` re-renders from it when present; otherwise the embedded table (same numbers) stands. |
| `data/padus-note.md` | PAD-US wiring note, `key: value` lines: `type: geojson` + `file: padus.geojson`, **or** `type: tiles` + `url: https://…/{z}/{x}/{y}.png` + `attribution: …`. Until it lands, PAD-US is a placeholder labelled "(pending — no data yet)". |

## Copy link (sacred)

The icon-only button at the upper right of the map composes
centre/zoom/basemap/layers into the hash, e.g.
`#v=44.20000,-86.00000,5&b=osm&l=natural,urban,road,states,-padus`
(`-` prefix = layer off). It is borrowed from the Itasca Moraine viewer;
do not remove or redesign it.

## Fences

- Never contact NCTA, NPS, or anyone for this project. All data is already
  on disk or in cited public sources.
- Never lump urban sidewalk with road miles; neither counts as built.
- No Minnesota numbers in the case page (the Minnesota packet is separate
  and draft). No trail-wide dollar cost figure — none exists in the
  sources; the case says so plainly.
- Stripped by design: no photo pins/classification, shoulder measurement,
  speed badges, ATV, timber, Cass datasets, census switcher, historical
  maps.
- Every layer carries references + interpretation method
  (`site/data-sources.html`). Flags are shown, not hidden: Cohasset MN
  7.59 mi urban overcount, ~131 mi with no chapter, the Minnesota ~8 mi
  off/on shift vs the 2025 Annual Report, `cert_stat` not usable for
  completeness.
