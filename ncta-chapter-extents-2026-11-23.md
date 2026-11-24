# NCTA chapter extents — every chapter's section of the North Country Trail

Built 2026-11-23/24. Sources read 2026-11-24 (NCTA pages crawled 00:33–00:35 UTC).
Companion to the NCT completeness viewer (`~/workspace/north-country-trail-completeness-viewer/`).

## Main table — NCTA chapters and affiliates/partners

One row per chapter (30 NCTA chapters) and per affiliate/partner that carries miles
in the viewer's data (9). Endpoints are quoted from the source named in the last
column; "not stated" means the source does not give it. Mileage "NCTA-stated" is
"not stated" for every chapter: **the NCTA's chapter pages state endpoints only
and the NCTA publishes no per-chapter mileage** — it publishes state totals only
(see the state comparison table below). "Computed" is the sum of the `miles` field
across the viewer's three processed GeoJSON files
(`site/data/centerline-natural.geojson`, `centerline-road.geojson`,
`centerline-urban.geojson`), from the NCTA ArcGIS `nct_public` FeatureServer
layer 2 pull of 2026-11-21.

| Chapter | Code | State(s) | Western / southern endpoint | Eastern / northern endpoint | Miles, NCTA-stated | Miles, computed | Source |
|---|---|---|---|---|---|---|---|
| Central Flyway | FLY | ND | Western terminus of the trail, Lake Sakakawea State Park | Eastern end of Lonetree Wildlife Management Area | not stated | 139.62 | https://northcountrytrail.org/trail/north-dakota/fly/ |
| Sheyenne River Valley | SRV | ND | North end of Lake Ashtabula | Eastern boundary of Sheyenne State Forest | not stated | 115.29 | https://northcountrytrail.org/trail/north-dakota/srv/ |
| Dakota Prairie | DPC | ND | Sheyenne State Forest | North Dakota–Minnesota state line at Fort Abercrombie State Park | not stated | 83.73 | https://northcountrytrail.org/trail/north-dakota/dpc/ |
| Minnesota Waters and Prairie | MWP | MN (0.01 ND) | North Dakota–Minnesota state line at Fort Abercrombie State Park | Otter Tail–Becker county line, southwest of Frazee | not stated | 95.00 | https://northcountrytrail.org/trail/minnesota/mwp/ |
| Laurentian Lakes | LLC | MN | Otter Tail–Becker county line, southwest of Frazee | Itasca State Park | not stated | 71.43 | https://northcountrytrail.org/trail/minnesota/llc/ |
| Itasca Moraine | ITM | MN | Itasca State Park | Minnesota Highway 84 | not stated | 78.33 | https://northcountrytrail.org/trail/minnesota/itm/ |
| Star of the North | STN | MN | Minnesota 84 | Highway 6, northeast of Remer | not stated | 10.22 | https://northcountrytrail.org/trail/minnesota/stn/ |
| Arrowhead | ARW | MN | Minnesota Highway 6 | Bear Head Lake State Park | not stated | 178.65 | https://northcountrytrail.org/trail/minnesota/arw/ |
| Ely Northwoods | ELY | MN | Bear Head Lake State Park | Kawishiwi Falls, Superior National Forest | not stated | 19.83 | https://northcountrytrail.org/trail/minnesota/ely/ |
| Kekekabic Trail | KEK | MN | Kawishiwi Falls, Superior National Forest | Gunflint Trail | not stated | 53.95 | https://northcountrytrail.org/trail/minnesota/kek/ |
| Border Route Trail Association (affiliate) | BRT | MN | Gunflint Trail (connects to Kekekabic Trail) | Otter Lake Road / Swamp River, at the northern terminus of the Superior Hiking Trail (270° Overlook) | 65 (affiliate-stated) | 64.88 | https://www.borderroutetrail.org/about-the-trail |
| Superior Hiking Trail Association (affiliate) | SHTA | MN | 270° Overlook near the Canada–US border | Minnesota–Wisconsin border, Jay Cooke State Park | 310 published (300 main trail; affiliate-stated) | 300.29 | https://en.wikipedia.org/wiki/Superior_Hiking_Trail |
| Brule-St. Croix | BSC | WI (2.34 MN) | Mouth of the Minnesota–Wisconsin state line (St. Louis River mouth; NCTA's phrasing, see gaps) | Bayfield County Road A | not stated | 105.67 | https://northcountrytrail.org/trail/wisconsin/bsc/ |
| Chequamegon | CHE | WI | Bayfield County Road A | Sandstone Ledges Spur Trail, Copper Falls State Park | not stated | 67.73 | https://northcountrytrail.org/trail/wisconsin/che/ |
| Heritage | HTG | WI (0.01 MI) | Sandstone Ledges Spur, Copper Falls State Park | Wisconsin–Michigan state line | not stated | 41.91 | https://northcountrytrail.org/trail/wisconsin/htg/ |
| Ni-Miikanaake | NMK | MI | Wisconsin–Michigan state line | M-64, Ottawa National Forest | not stated | 81.62 | https://northcountrytrail.org/trail/michigan/nmk/ |
| Peter Wolfe | PWC | MI | M-64, Ottawa National Forest | Long Lake, west of Craig Lake State Park | not stated | 119.78 | https://northcountrytrail.org/trail/michigan/pwc/ |
| Marquette Area | MAC | MI | Long Lake, west of Craig Lake State Park | Rock River Road, Alger County | not stated | 110.26 | https://northcountrytrail.org/trail/michigan/mac/ |
| Superior Shoreline | SSC | MI | Rock River Road, Alger County | Mouth of the Two Hearted River | not stated | 109.68 | https://northcountrytrail.org/trail/michigan/ssc/ |
| Hiawatha Shore-to-Shore | HSS | MI | Mouth of the Two Hearted River | South end of the Mackinac Bridge | not stated | 138.61 | https://northcountrytrail.org/trail/michigan/hss/ |
| Harbor Springs | HRB | MI | Mackinaw City trailhead | Kipp Road, east of Harbor Springs | not stated | 49.32 | https://northcountrytrail.org/trail/michigan/hrb/ |
| Jordan Valley 45° | J45 | MI | Kipp Road, east of Harbor Springs | Starvation Lake Road, southeast of Mancelona | not stated | 79.63 | https://northcountrytrail.org/trail/michigan/j45/ |
| Grand Traverse | GTC | MI | Starvation Lake Road, southeast of Mancelona | Wexford–Manistee county line at Hodenpyl Dam Pond | not stated | 105.13 | https://northcountrytrail.org/trail/michigan/gtc/ |
| Spirit of the Woods | SPW | MI | Wexford–Manistee county line at Hodenpyl Dam Pond | Lake–Newaygo county line west of M-37 | not stated | 79.33 | https://northcountrytrail.org/trail/michigan/spw/ |
| Western Michigan | WMI | MI | Lake–Newaygo county line west of M-37 | Kent–Barry county line, northeast of Middleville | not stated | 144.33 | https://northcountrytrail.org/trail/michigan/wmi/ |
| Chief Noonday | CND | MI | Kent–Barry county line, northeast of Middleville | Calhoun–Hillsdale county line | not stated | 117.82 | https://northcountrytrail.org/trail/michigan/cnd/ |
| Chief Baw Beese | BAW | MI (9.28 OH) | Calhoun–Hillsdale county line | Wabash Cannonball Trail, Ohio | not stated | 51.97 | https://northcountrytrail.org/trail/michigan/baw/ |
| Northwestern Ohio Rails-to-Trails Association (affiliate) | NORTA | OH | Wabash Cannonball Trail (North Fork), at the Michigan line | Junction with the Buckeye Trail (junction not precisely sourced) | not stated | 44.14 | NCTA 2025 Annual Report map (#28); seg_name "Wabash Cannonball Trail (North Fork)" in the ArcGIS source |
| Buckeye Trail Association (affiliate) | BTA | OH | Junction with the Wabash Cannonball Trail | Zoar, Ohio (where the Wampum Chapter takes over) | not stated (NCTA notes ~900 mi of Buckeye Trail is NCT) | 932.72 | NCTA 2025 Annual Report map (#29); https://en.wikipedia.org/wiki/North_Country_Trail |
| Wampum | WAM | OH 81.44, PA 43.59 | Zoar, Ohio | Lawrence–Butler county line, east of McConnells Mill State Park, PA | not stated | 125.03 | https://northcountrytrail.org/wam |
| Butler County | BUT | PA | Lawrence–Butler county line, east of McConnells Mill State Park | Armstrong–Clarion county line at the Allegheny River (Parker) | not stated | 48.47 | https://northcountrytrail.org/but |
| Clarion County (affiliate) | CLA | PA | Armstrong–Clarion county line at the Allegheny River | Salmon Creek, Allegheny National Forest | not stated | 95.73 | https://northcountrytrail.org/cla |
| Allegheny National Forest | ANF | PA | Southern boundary of the Allegheny National Forest (Salmon Creek) | Pennsylvania–New York state line | not stated | 92.46 | https://northcountrytrail.org/anf |
| Finger Lakes Trail Conference (affiliate) | FLTC | NY | Pennsylvania–New York state line, Allegany State Park | Central junction near Cuyler, NY (NCT leaves the Finger Lakes Trail for the Adirondacks) | ≈422 shared Finger Lakes Trail miles (per I Love NY) | 390.50 | https://www.iloveny.com/listing/north-country-national-scenic-trail-(ncnst)/134158/ ; https://adk-on.org/stewardship/nct/ |
| Adirondack Mountain Club – Onondaga Chapter | ADK-ON | NY | Central junction near Cuyler, NY (Onondaga Trail extension of the Finger Lakes Trail) | End of the Onondaga Trail (northern terminus of the Link Trail area; exact point not stated) | 83 mi of NCT maintained (ADK Onondaga-stated) | 38.42 | https://adk-on.org/stewardship/nct/ |
| Central New York | CNY | NY | Northern terminus of the Link Trail, west of Tuscarora Lake | Oneida–Herkimer county line | not stated | 87.15 | https://northcountrytrail.org/trail/new-york/cny/ |
| Adirondack Mountain Club (affiliate) | ADK | NY (0.01 VT) | Hamlet of Forestport, Oneida County (gateway to Adirondack Park) | Hamlet of Crown Point, Lake Champlain | 158 (Adirondack Park route, per NY DEC) | 186.30 | NY DEC Adirondack Park Trail Plan notice: https://apps.cio.ny.gov/apps/mediacontact/public/view.cfm?parm=392274CA-5056-9D0B-1A195E78FDC6B94B&backButton |
| Green Mountain Club (partner) | GMC | VT | Appalachian Trail junction, Green Mountain National Forest (eastern terminus of the NCT) | Middlebury Gap (Long Trail; boundary with MALT inferred, see gaps) | not stated | 37.44 | https://en.wikipedia.org/wiki/North_Country_Trail_by_state ; https://www.onxmaps.com/backcountry/trails/hiking/us/vermont/north-country-trail-vermont-section-j064kp2e7z15 |
| Middlebury Area Land Trust | MALT | VT | Middlebury Gap (boundary with GMC inferred, see gaps) | Lake Champlain bridge at Crown Point (via Trail Around Middlebury + roads) | not stated | 20.42 | https://www.onxmaps.com/backcountry/trails/hiking/us/vermont/north-country-trail-vermont-section-j064kp2e7z15 |

Chain check (west to east): the stated endpoints dovetail into a continuous
chain except for the two gaps flagged below — the North Dakota gap between
Lonetree WMA and Lake Ashtabula, and the central-New-York gap between the
Oneida–Herkimer county line and Forestport.

## Codes in the viewer's data with no NCTA chapter page

| Code | Miles (computed) | What it is | Status |
|---|---|---|---|
| None (literal string in source) | 130.92 | No chapter assigned in the ArcGIS source | Unassigned — see gaps (mostly ND) |
| None (null chapter field) | 21.84 | No chapter assigned in the ArcGIS source | Unassigned |
| Central NY | 2.47 (NY) | Probable variant spelling of CNY (Central New York) | Unconfirmed variant |
| GTR | 1.56 (MI) | seg_names "Shore to Shore Trail" / "Pere Marquette State Forest" (GTC/SPW ground) | Probable variant of GTC; unconfirmed |
| LON | 1.48 (ND) | seg_name "New Rockford Canal" | Code meaning unconfirmed |

Codes that appear in NCTA documents but carry no miles in the viewer's data:
Rachel Carson Trails Conservancy (RCT/RCTC, PA affiliate, annual report #33)
and Trail Around Middlebury (TAM, VT partner) — no features coded to them in
the 2026-11-21 pull. The MALT-coded miles (20.42) are presumably the
Trail Around Middlebury stretch, but the data does not say so.

## State comparison — NCTA-stated vs computed

NCTA-stated totals are from the NCTA 2025 Trail Progress Report
(https://northcountrytrail.org/files/trail-management/NCTA_Trail-Progress-Report_2025.pdf),
which warns: "All mileage totals are estimates and change frequently."
Computed totals are the same GeoJSON sums as the main table, grouped by state.
The NCTA report is 2025 (as of January 2026); the viewer pull is 2026-11-21,
so small differences are expected.

| State | NCTA 2025 total (off-road + road) | Computed | Delta |
|---|---|---|---|
| ND | 466 (288 + 178) | 466.91 | +0.91 |
| MN | 875 (742 + 133) | 875.15 | +0.15 |
| WI | 210 (145 + 65) | 213.63 | +3.63 |
| MI | 1,186 (912 + 274) | 1,180.92 | −5.08 |
| OH | 1,066 (524 + 542) | 1,072.78 | +6.78 |
| PA | 283 (237 + 46) | 286.00 | +3.00 |
| NY | 704 (467 + 237) | 705.02 | +1.02 |
| VT | 70 (50 + 20) | 70.66 | +0.66 |
| **Total** | **4,860 (3,365 + 1,495)** | **4,871.07** | **+11.07** |

Computed total 4,871.07 vs the viewer's headline 4,871.24: the 0.17 mi is
rounding in the stored per-chapter values (`site/data/chapters.json` sums to
4,871.23).

## How this was built

- **NCTA chapter pages (primary source for extents).** Every chapter page on
  northcountrytrail.org was read 2026-11-23/24: the 27 chapters on the
  "Local Chapters and Affiliates" listing
  (https://northcountrytrail.org/contact/chapters-affiliates/) via their
  `/trail/<state>/<code>/` pages, plus the four Pennsylvania chapters at
  their short URLs (northcountrytrail.org/anf, /wam, /but, /cla — the URL
  scheme is documented in the NCTA Brand Standards and Style Guide 2024),
  plus Central New York at
  https://northcountrytrail.org/trail/new-york/cny/. Each page carries a
  "Section" sentence of the form "The X Chapter's segment of the North
  Country Trail is from A to B." — endpoints above are quoted from those
  sentences (Heritage's page states its extent as a heading instead).
- **Affiliates/partners without NCTA chapter pages** (BRT, SHTA, NORTA, BTA,
  FLTC, ADK, ADK-ON, GMC, MALT): extents from the affiliate's own site or
  the cited secondary source, as listed per row. No NCTA chapter page stating
  an extent was found for any of these nine.
- **Computed mileage:** sum of the `miles` field over the viewer's three
  processed GeoJSON files (3,202 natural + 939 road + 300 urban features),
  grouped by `chapter` and by `chapter` + `state`. Total 4,871.07 mi over
  43 chapter codes (including "None").
- **Code identification:** the NCTA Brand Standards and Style Guide 2024
  (https://northcountryt1.wpenginepowered.com/files/outreach/NCTA%20Brand%20Standards%20and%20Style%20Guide_2024.pdf)
  confirms the chapter/affiliate code list (ANF, BUT, CLA, CNY, WAM, MALT,
  NORTA, BTA, FLTC, ADK, BRT/BRTA, SHT/SHTA, RCT/RCTC, TAM). Where a code
  was still ambiguous, `seg_name` samples were pulled from the ArcGIS
  FeatureServer layer 2 as a cross-check only.
- **NCTA-stated mileage:** the 2025 Trail Progress Report (state totals
  only). No per-chapter mileage was found anywhere on the NCTA site.

## Gaps and discrepancies

1. **No per-chapter mileage from the NCTA.** Chapter pages state endpoints
   only. All mileage comparison is therefore at state level (table above).
   The closest state match is Minnesota (+0.15 mi); the largest gaps are
   Ohio (+6.78) and Michigan (−5.08). The NCTA's own caveat covers this:
   totals are estimates and change frequently, and the report predates the
   viewer's 2026-11-21 pull.
2. **The NCTA chapters listing page is incomplete.** It lists 27
   chapters/affiliates (North Dakota, Minnesota, Wisconsin, Michigan only).
   The Pennsylvania chapters (Wampum, Butler, Clarion, Allegheny National
   Forest), Central New York, and the Ohio/New York/Vermont affiliates
   appear in the 2025 annual report map (numbered 28–39) and the 2024 brand
   guide, but not on the listing page. Conversely, the 2024 brand guide's
   chapter list omits Chief Noonday (CND), which has a live chapter page.
3. **North Dakota gap — ~127 mi with no chapter.** FLY ends at the eastern
   end of Lonetree WMA and SRV starts at the north end of Lake Ashtabula;
   the stretch between them (New Rockford Canal area) carries no chapter
   code in the viewer data. "None" in North Dakota is 126.78 mi, including
   one single 46.14-mi unnamed feature plus New Rockford Canal segments.
4. **152.76 mi unassigned in total** ("None": 130.92 literal string +
   21.84 null field). By state: ND 126.78, VT 12.79, PA 5.75, OH 5.20,
   MI 1.14, WI 0.67, MN 0.24, NY 0.19.
5. **Star of the North is short in the data.** STN computes to 10.22 mi,
   but its stated section (MN 84 to Highway 6 northeast of Remer) is about
   27 mi of trail. Roughly 17 mi of that corridor is not attributed to STN
   in the 2026-11-21 source pull — an attribution question, not a trail gap
   (the trail exists; the code does not say STN).
6. **ADK Onondaga's stated mileage vs the data.** ADK's Onondaga Chapter
   says it maintains 108 miles of Finger Lakes Trail, 83 of it North
   Country — but only 38.42 mi is coded ADK-ON in the viewer data. The
   remaining ~45 mi of Onondaga-maintained NCT is presumably coded FLTC
   or CNY. Same split explains the FLTC gap: ≈422 shared FLT miles per
   I Love NY vs 390.50 computed.
7. **Central New York → Adirondacks gap.** CNY's NCTA page ends at the
   Oneida–Herkimer county line; ADK's section starts at Forestport. The
   Oneida–Herkimer line to Forestport stretch (Black River Canal / Boonville
   area) has no stated maintainer on the NCTA site. The NY DEC Adirondack
   Park Trail Plan says CNY is steward "from the end of the Onondaga Trail
   to the western edge of Adirondack Park," which is broader than the NCTA
   page's endpoints — the two statements do not align precisely.
8. **Vermont boundary is inferred, not NCTA-stated.** No NCTA chapter page
   was found for the Green Mountain Club or the Middlebury Area Land Trust.
   The GMC/MALT boundary at Middlebury Gap is inferred from the onX
   Vermont-section description (Long Trail to Middlebury Gap, then roads +
   Trail Around Middlebury to the Lake Champlain bridge). The 12.79 mi of
   unassigned ("None") Vermont miles are also unexplained.
9. **NORTA → BTA junction not precisely sourced.** The Wabash Cannonball
   Trail (North Fork) hands off to the Buckeye Trail somewhere in northwest
   Ohio; neither NORTA nor BTA has an NCTA chapter page stating its extent.
   The 81.44 mi of WAM-coded Ohio miles are consistent with WAM's stated
   section (Zoar to the Pennsylvania line via the Buckeye Trail, ≈80 mi).
10. **Brule-St. Croix's western endpoint is garbled on the NCTA page.**
    It reads "from the mouth of the Minnesota–Wisconsin state line" — read
    here as the mouth of the St. Louis River at the state line, where the
    Superior Hiking Trail ends and the Wisconsin section begins.
11. **Variant codes.** "Central NY" (2.47 mi) is a probable variant of CNY;
    GTR (1.56 mi, "Shore to Shore Trail" / "Pere Marquette State Forest")
    is a probable variant of GTC; LON (1.48 mi, "New Rockford Canal") is
    unidentified. All three are flagged `unmapped` in
    `site/data/chapters.json`.
12. **SHTA computed vs published.** 300.29 mi computed vs 310 published
    (300 miles of main trail + spurs per the SHTA; the viewer data appears
    to carry main-trail miles only).
13. **Two NCTA URL schemes.** Chapter pages live under both
    `/trail/<state>/<code>/` (27 chapters + CNY) and bare short URLs
    (northcountrytrail.org/anf, /wam, /but, /cla). The Pennsylvania
    "states" page linked from older NCTA material
    (northcountrytrail.org/trail/states/pennsylvania/) now returns 404.
