# Parcels trail-wide — scope note (NCT full viewer)

**Date:** 2026-11-23/24. **Scope only — no build, no commit, no push.** For Paul's §6 decision #1 in the viewer plan (`nct-viewer-itm-based-plan-2026-11-23.md`): is the per-state parcel hunt worth it, or is PAD-US enough for land ownership?

## Answer in brief

- The trail crosses **119 counties in 8 states**, **4,761.03 trail-miles**. A usable free online parcel source exists for **3,599.07 mi (75.6%)**.
- **Six states have a statewide parcel service:** ND, MN, WI, VT (complete); NY (partial, 61% of its trail miles); OH (complete, but a 2023-vintage snapshot).
- Statewide services alone cover **3,034.46 mi (63.7%)**. Adding the verified per-county services (MI's 9, PA's 6 sources, Hubbard fallback) lifts it to 75.6%.
- The gap is **1,161.96 mi (24.4%)**, concentrated in **Michigan (807.90 mi — 17 of 26 counties with nothing usable)**, NY's 5 opt-out counties (267.39 mi), and PA's Clarion / Lawrence / Armstrong (86.67 mi).

## Method

- **County list:** the trail centerline (4,441 features — natural + road + urban merged) intersected with Census TIGER 2024 county boundaries (`cb_2024_us_county_500k`), reprojected to EPSG:5070, lengths in miles. 119 counties. The denominator (4,761.03 mi) is the intersection sum; the centerline itself measures 4,770.34 mi and the walked chainage 4,826.21 mi — the ~9 mi difference is the known duplicate-edge overlap from the chainage work. Coverage % uses the intersection sum.
- **Service checks:** every URL below was verified live on 23–24 Nov 2026 (HTTP 200 + real ArcGIS REST service JSON, or a live portal/download page). "None found" means no usable free online parcel service was located after a county-GIS search plus an ArcGIS Online item search. A viewer-only map does **not** count — a viewer is not a layer the viewer can consume. Third-party aggregators (Regrid, ReportAll, Parcelio, CLILU, LandAI, freeparceldata) were not counted: paid or repackaged mirrors, not county publications.
- **Working files:** `~/workspace/nct-parcels-scope/` — `county_miles.csv` (the intersection), `build_county_table.py` (regenerates the county table below), `state-nd-mn-wi.md`, `state-mi-ny-vt.md`, `state-oh-pa.md` (per-county tables with full URLs, counts, terms, and hard cases).

## Statewide-service verdicts

| State | Statewide parcel service? | Service | Trail counties covered | Vintage / cadence | Terms (where stated) |
|---|---|---|---|---|---|
| ND | **YES** | ND GIS Hub `NDGISHUB_Parcels` | 12 of 12 | Per-county, monthly to yearly; item modified 2026-11-23 | Rural focus — some city parcels missing |
| MN | **YES, one exception** | MnGeo `plan_parcels_open` | 10 of 11 (Hubbard opted out) | Quarterly snapshot (`rundate` 2026-11-09); county source dates Jul–Nov 2026 | No access/use constraints; AS IS; not for boundary determination |
| WI | **YES** | V12 Statewide Parcel Map Database | 4 of 4 | Annual (V12 released Jun 30, 2026) | — |
| VT | **YES** | VCGI Parcel Program | 3 of 3 | Weekly updates; 2025 grand list joined | Free public data; planning purposes only, not a legal survey |
| NY | **YES, partial** | NYS ITS `NYS_Tax_Parcels_Public` | 11 of 16 (38 of 62 counties opted in) | 2025 data, pub. May 2026, annual | Public service, "as is", no warranty |
| OH | **YES** | OGRIP/ODNR `Statewide_Parcels_ODNR_WebMerc` | 38 of 38 | 2023-vintage snapshot (per-county `currentto` Jan 2023–Mar 2024); no refresh cadence stated; slow (maxRecordCount 2000) | — |
| MI | **NO** | — | — | State's internal Michigan Geographic Framework parcel layer is not public | Per-county only |
| PA | **NO** | PASDA "Pennsylvania Parcels (Available)" holds 40 of 67 counties, PIN/Source/Date only, no owner | 4 of 9 trail counties in it | County MapServers patch the rest | — |

## Coverage by state

| State | Counties with source | Trail mi | Covered mi | Coverage |
|---|---|---:|---:|---:|
| ND | 12 / 12 | 463.98 | 463.98 | 100% |
| MN | 11 / 11 (10 statewide + Hubbard fallback) | 852.59 | 852.59 | 100% |
| WI | 4 / 4 | 208.74 | 208.74 | 100% |
| VT | 3 / 3 | 69.60 | 69.60 | 100% |
| OH | 38 / 38 | 1,060.56 | 1,060.56 | 100% |
| NY | 11 / 16 | 686.54 | 419.15 | 61.1% |
| PA | 6 / 9 | 278.60 | 191.93 | 68.9% |
| MI | 9 / 26 | 1,140.42 | 332.52 | 29.2% |
| **Total** | **94 / 119** | **4,761.03** | **3,599.07** | **75.6%** |

Statewide services alone: 3,034.46 mi (63.7%). Uncovered: 1,161.96 mi (24.4%) — MI 807.90, NY 267.39, PA 86.67.

## Verified services (distinct URLs — all verified live 23–24 Nov 2026)

- **ND** — `https://services1.arcgis.com/GOcSXpzwBHyk2nog/arcgis/rest/services/NDGISHUB_Parcels/FeatureServer` — 719,461 parcels statewide; 148,268 in trail counties. Owner info is in a separate tax-roll table (layer 1 `Parcels_TaxRoll`, join on `UniqueGISID`); layer 0 has no owner fields.
- **MN** — `https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_mngeo/plan_parcels_open/FeatureServer` — layer 0 parcels, layer 1 per-county metadata; 2,714,537 parcels. Hubbard fallback: `https://gis.co.hubbard.mn.us/arcgis/rest/services/OpenData/Hubbard_County_Tax_Parcels/FeatureServer` — 29,241 parcels.
- **WI** — `https://services3.arcgis.com/n6uYoouQZW75n5WI/arcgis/rest/services/Wisconsin_Statewide_Parcels_DB/FeatureServer` — 3,574,646 parcels; statewide FGDB download ~492 MB compressed. (Do not use the older `Wisconsin_Statewide_Parcels` URL — dead.)
- **VT** — `https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/FS_VCGI_VTPARCELS_WM_NOCACHE_v2/FeatureServer` — layer 1 active parcels (344,342), owner + grand-list fields; also OGC WFS. Program page: `https://vcgi.vermont.gov/data-and-programs/parcel-program`.
- **NY** — `https://services6.arcgis.com/EbVsqZ18sv1kVJ3k/arcgis/rest/services/NYS_Tax_Parcels_Public/FeatureServer/` — layer 1 parcels, layer 0 county footprint. (The state-hosted copy at `gisservices.its.ny.gov` returned HTTP 500 — use the ArcGIS Online copy.) Point fallback: statewide parcel centroid service, 5,510,061 points, all counties (points, not polygons).
- **OH** — `https://gis.ohiodnr.gov/hosting/rest/services/Hosted/Statewide_Parcels_ODNR_WebMerc/FeatureServer` — layer 10; 2,374,789 parcels across the 38 trail counties. Carries owner names + auditor links, so the viewer must limit displayed fields to match the ITM model. Fresher county services verified for 6 counties: Morgan (`https://services8.arcgis.com/cYuOLPdETvKbspkC/arcgis/rest/services/Morgan_Parcels/FeatureServer`), Columbiana (`https://services8.arcgis.com/234WKrCI77bh5yOY/arcgis/rest/services/CountyParcels/FeatureServer`), Carroll (`https://services8.arcgis.com/dZSJY7MSQPhysZUz/arcgis/rest/services/Carroll_Parcels/FeatureServer`), Lucas (`https://lcaudgis.co.lucas.oh.us/gisaudserver/rest/services/Hosted/OSE_ParcelsAddresses_AREIS/FeatureServer`), Stark (`https://scgisa.starkcountyohio.gov/arcgis/rest/services/Auditor/StarkCountyParcels/MapServer`), Hamilton (`https://cagisonline.hamilton-co.org/arcgis/rest/services/HCE/Cadastral/MapServer`).
- **MI county services (9)** — Marquette `https://services9.arcgis.com/6EuFgO4fLTqfNOhu/ArcGIS/rest/services/MarquetteParcelData/FeatureServer` (layer 2, no owner field); Emmet `https://gis.emmetcounty.org/arcgis/rest/services/taxparcel/MapServer` (layer 13, full fields); Barry `https://services.arcgis.com/i0SsdDzLI3mLGmPR/arcgis/rest/services/Parcels_OpenData_View/FeatureServer` (layer 14, geometry + acres only); Mackinac `https://services7.arcgis.com/wWwid2HdqJ8HIOOi/arcgis/rest/services/MackinacCo_Parcels/FeatureServer` (layer 0, no owner/address); Antrim `https://services6.arcgis.com/ZcCP0G3kEnUDVego/arcgis/rest/services/AllParcels_shp/FeatureServer` (layer 0, full fields incl. owner); Grand Traverse `https://gis.gtcountymi.gov/arcgis/rest/services/Public_Services/Tax_Parcel_Public/MapServer` (layer 0, full fields); Charlevoix `https://services9.arcgis.com/1lVQrZMRGwmkesR4/arcgis/rest/services/2024_Parcel_Layer_/FeatureServer` (layer 0, geometry + PIN only; publisher is an individual AGOL account, not the county); Kalamazoo `https://services3.arcgis.com/RGltUbqpl4h9E3Qh/arcgis/rest/services/Parcels_2025/FeatureServer` (layer 11, full fields; annual layer); Ionia `https://services9.arcgis.com/i2awudUyJK8gxxEe/arcgis/rest/services/Ionia_County_Tax_Parcels_Public/FeatureServer` (layer 0, full fields).
- **PA** — PASDA Butler `https://mapservices.pasda.psu.edu/server/rest/services/pasda/ButlerCounty/MapServer` (full CAMA incl. owner; download zip ~24 MB); PASDA Venango `https://mapservices.pasda.psu.edu/server/rest/services/pasda/VenangoCounty/MapServer` (thin, no owner); PASDA Warren `https://mapservices.pasda.psu.edu/server/rest/services/pasda/WarrenCounty/MapServer` (vintage Mar 2020); McKean `https://gis.mckeancountypa.gov/server/rest/services/ParcelViewer/BPV3_Parcels/FeatureServer`; Beaver `https://gis.beavercountypa.gov/server/rest/services/InfoAtlas/Parcels_with_Owner/FeatureServer`; Forest covered by the PASDA statewide layer (11,320 parcels, Date 202602).

## County table (119 counties)

| State | County | Trail mi | Route | Covered? | Note |
|---|---|---:|---|---|---|
| MI | Alger | 96.86 | None found | No | Viewer-only or paywalled; see state file |
| MI | Marquette | 79.50 | County REST service | Yes | No owner field (address, city, UseClass only) |
| MI | Ontonagon | 78.63 | None found | No | Viewer-only or paywalled; see state file |
| MI | Kent | 74.89 | None found | No | Viewer-only or paywalled; see state file |
| MI | Emmet | 71.81 | County REST service | Yes | Full fields; live count query 400s at check, metadata verified |
| MI | Newaygo | 66.99 | None found | No | Viewer-only or paywalled; see state file |
| MI | Chippewa | 66.31 | None found | No | Viewer-only or paywalled; see state file |
| MI | Calhoun | 58.59 | None found | No | Viewer-only or paywalled; see state file |
| MI | Gogebic | 51.68 | None found | No | Viewer-only or paywalled; see state file |
| MI | Baraga | 51.33 | None found | No | Viewer-only or paywalled; see state file |
| MI | Luce | 48.45 | None found | No | Viewer-only or paywalled; see state file |
| MI | Barry | 46.09 | County REST service | Yes | Geometry + acres only — no owner/address/PIN |
| MI | Hillsdale | 41.88 | None found | No | Viewer-only or paywalled; see state file |
| MI | Mackinac | 41.00 | County REST service | Yes | No owner/address fields |
| MI | Wexford | 40.61 | None found | No | Viewer-only or paywalled; see state file |
| MI | Lake | 38.94 | None found | No | Viewer-only or paywalled; see state file |
| MI | Kalkaska | 34.94 | None found | No | Viewer-only or paywalled; see state file |
| MI | Antrim | 33.98 | County REST service | Yes | Full fields incl. owner |
| MI | Manistee | 32.56 | None found | No | Viewer-only or paywalled; see state file |
| MI | Grand Traverse | 28.50 | County REST service | Yes | Full fields incl. owner |
| MI | Houghton | 19.38 | None found | No | Viewer-only or paywalled; see state file |
| MI | Charlevoix | 19.25 | County REST service | Yes | Geometry + PIN only; publisher is an individual AGOL account, not the county |
| MI | Kalamazoo | 12.38 | County REST service | Yes | Full fields incl. owner; annual layer |
| MI | Mason | 5.25 | None found | No | Viewer-only or paywalled; see state file |
| MI | Cheboygan | 0.61 | None found | No | Viewer-only or paywalled; see state file |
| MI | Ionia | 0.01 | County REST service | Yes | Full fields incl. owner |
| MN | Cook | 184.20 | MnGeo statewide compilation | Yes |  |
| MN | St. Louis | 169.88 | MnGeo statewide compilation | Yes |  |
| MN | Lake | 141.74 | MnGeo statewide compilation | Yes |  |
| MN | Otter Tail | 70.80 | MnGeo statewide compilation | Yes |  |
| MN | Cass | 68.09 | MnGeo statewide compilation | Yes |  |
| MN | Itasca | 63.07 | MnGeo statewide compilation | Yes |  |
| MN | Becker | 57.99 | MnGeo statewide compilation | Yes |  |
| MN | Hubbard | 40.16 | Hubbard Co. fallback service | Yes | Only MN county opted out of the MnGeo compilation |
| MN | Wilkin | 24.71 | MnGeo statewide compilation | Yes |  |
| MN | Carlton | 17.23 | MnGeo statewide compilation | Yes |  |
| MN | Clearwater | 14.72 | MnGeo statewide compilation | Yes |  |
| ND | Ransom | 78.67 | NDGISHUB statewide | Yes |  |
| ND | McLean | 76.19 | NDGISHUB statewide | Yes |  |
| ND | Barnes | 66.46 | NDGISHUB statewide | Yes |  |
| ND | Sheridan | 52.02 | NDGISHUB statewide | Yes |  |
| ND | Griggs | 45.89 | NDGISHUB statewide | Yes |  |
| ND | Richland | 42.33 | NDGISHUB statewide | Yes |  |
| ND | Wells | 40.45 | NDGISHUB statewide | Yes |  |
| ND | Eddy | 24.85 | NDGISHUB statewide | Yes |  |
| ND | Foster | 23.22 | NDGISHUB statewide | Yes |  |
| ND | Burleigh | 8.02 | NDGISHUB statewide | Yes |  |
| ND | Mercer | 3.01 | NDGISHUB statewide | Yes |  |
| ND | Steele | 2.87 | NDGISHUB statewide | Yes |  |
| NY | Cattaraugus | 90.75 | None — viewer only | No | County runs a viewer (Beacon/SDG/Essex GIS); not consumable as a layer |
| NY | Cortland | 68.09 | NYS ITS statewide | Yes |  |
| NY | Steuben | 66.02 | NYS ITS statewide | Yes |  |
| NY | Oneida | 64.88 | NYS ITS statewide | Yes |  |
| NY | Hamilton | 59.59 | NYS ITS statewide | Yes |  |
| NY | Essex | 55.92 | None — viewer only | No | County runs a viewer (Beacon/SDG/Essex GIS); not consumable as a layer |
| NY | Tompkins | 54.97 | NYS ITS statewide | Yes |  |
| NY | Schuyler | 48.09 | NYS ITS statewide | Yes |  |
| NY | Allegany | 40.92 | None — viewer only | No | County runs a viewer (Beacon/SDG/Essex GIS); not consumable as a layer |
| NY | Herkimer | 40.80 | None — viewer only | No | County runs a viewer (Beacon/SDG/Essex GIS); not consumable as a layer |
| NY | Madison | 39.00 | None — viewer only | No | County runs a viewer (Beacon/SDG/Essex GIS); not consumable as a layer |
| NY | Warren | 21.79 | NYS ITS statewide | Yes |  |
| NY | Onondaga | 14.14 | NYS ITS statewide | Yes |  |
| NY | Livingston | 11.94 | NYS ITS statewide | Yes |  |
| NY | Wyoming | 6.93 | NYS ITS statewide | Yes |  |
| NY | Tioga | 2.71 | NYS ITS statewide | Yes |  |
| OH | Adams | 74.22 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Morgan | 61.22 | ODNR statewide (2023 vintage) | Yes | Fresher county REST service also verified |
| OH | Washington | 55.17 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Columbiana | 51.64 | ODNR statewide (2023 vintage) | Yes | Fresher county REST service also verified |
| OH | Clermont | 50.67 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Noble | 48.97 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Hocking | 48.85 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Brown | 42.08 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Harrison | 41.38 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Pike | 39.24 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Ross | 38.64 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Guernsey | 37.20 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Greene | 35.07 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Warren | 32.50 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Fulton | 26.55 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Miami | 25.37 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Carroll | 25.30 | ODNR statewide (2023 vintage) | Yes | Fresher county REST service also verified |
| OH | Lucas | 24.73 | ODNR statewide (2023 vintage) | Yes | Fresher county REST service also verified |
| OH | Tuscarawas | 24.60 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Scioto | 24.25 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Shelby | 24.14 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Auglaize | 23.84 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Henry | 23.62 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Perry | 23.50 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Montgomery | 19.68 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Paulding | 19.32 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Monroe | 16.73 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Defiance | 16.58 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Vinton | 14.58 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Putnam | 14.09 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Athens | 12.65 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Williams | 12.36 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Highland | 10.10 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Allen | 9.67 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Stark | 5.66 | ODNR statewide (2023 vintage) | Yes | Fresher county REST service also verified |
| OH | Hamilton | 3.06 | ODNR statewide (2023 vintage) | Yes | Fresher county REST service also verified |
| OH | Van Wert | 2.84 | ODNR statewide (2023 vintage) | Yes |  |
| OH | Belmont | 0.49 | ODNR statewide (2023 vintage) | Yes |  |
| PA | Clarion | 56.48 | Viewer only / stale copy | No | County viewer live but REST backend unreachable or timed out; only a stale 2021 hosted copy loads |
| PA | Butler | 46.87 | PASDA county MapServer | Yes | Full CAMA incl. owner; download zip ~24 MB |
| PA | McKean | 36.07 | County ArcGIS server | Yes | BPV3_Parcels |
| PA | Warren | 34.13 | PASDA county MapServer | Yes | Vintage Mar 2020 — stale |
| PA | Venango | 33.62 | PASDA county MapServer | Yes | Thin — no owner fields |
| PA | Lawrence | 28.18 | Viewer only / stale copy | No | County viewer live but REST backend unreachable or timed out; only a stale 2021 hosted copy loads |
| PA | Forest | 27.15 | PASDA statewide layer | Yes | 11,320 parcels, Date 202602 — freshest of the four in the layer |
| PA | Beaver | 14.09 | County ArcGIS server | Yes | Parcels_with_Owner |
| PA | Armstrong | 2.01 | None — in-office only | No | No online parcels; data sold by request ($1,200 countywide) |
| VT | Addison | 50.18 | VCGI statewide | Yes |  |
| VT | Rutland | 16.30 | VCGI statewide | Yes |  |
| VT | Windsor | 3.12 | VCGI statewide | Yes |  |
| WI | Douglas | 92.78 | WI V12 statewide | Yes |  |
| WI | Bayfield | 53.63 | WI V12 statewide | Yes |  |
| WI | Ashland | 32.14 | WI V12 statewide | Yes |  |
| WI | Iron | 30.19 | WI V12 statewide | Yes |  |

## Hard cases

1. **Michigan is the blocker — 807.90 mi, 17 counties.** Most are viewer-only (Colligo, FetchGIS, BS&A, LIAA) or charge for data. **Kent (74.89 mi) is the single biggest re-check:** its open-data parcel service is documented as verified 20 Oct 2026 but returned Token Required / 404 at check time. If restored, MI coverage rises to 407.41 mi (35.7%).
2. **NY's 5 missing counties are a permission problem, not a data problem** — the counties have viewers and the state program is actively adding counties. A point-level centroid fallback exists (5,510,061 points, all counties) but centroids are not parcels.
3. **Ohio's statewide service is a 2023 snapshot** — a split or sale since early 2024 won't show; 6 counties have fresher county services. It is also slow (maxRecordCount 2000).
4. **Pennsylvania:** Armstrong has nothing online (in-office maps only, data sold by request, $1,200 countywide); Clarion's county server is unreachable from here; Lawrence's CAMA service timed out; Warren PA is stale everywhere (Mar 2020); Venango has no owner fields anywhere public. PASDA's search-index years conflict with dataset pages/layer names for Butler/Venango/Warren — the state file uses layer names as authoritative vintage and flags the conflict.
5. **Field coverage is uneven.** Three of MI's 9 covered counties are geometry-only (Barry, Mackinac, Charlevoix); Marquette has no owner field. The ITM popup (owner name + mailing address) would show blanks there. Owner/taxpayer fields exist in the statewide services and must be filtered per service — field names differ (`owner_name`/`tax_name` in MN, `OwnerName` in ND layer 1, `OWNERNME1/2` in WI).
6. **ND owner info is in a separate tax-roll table** (join on `UniqueGISID`); layer 0 alone likely suffices under the ITM model (taxpayer fields excluded).
7. **MN is a quarterly snapshot, not live county data** (county source dates Jul–Nov 2026); the Commons metadata PDF lags the live service by one quarter — cite the live service (`rundate` 2026-11-09) for currency.
8. **Dead, renamed, or gated services found during the check:** WI's older `Wisconsin_Statewide_Parcels` URL is dead (use `_DB`); ND per-county services are decaying (Ransom/Barnes return 400-in-200; only Benson verified live); Grand Traverse's 2013 service is dead (replaced by `Tax_Parcel_Public`); Kent token-gated; OH's older `maps.ohio.gov` 2022 service is token-locked (499); Cheboygan MI's `chebparcels` service loads but holds only 8 features — not a real source; Emmet's live count query 400s (metadata verified).
9. **Montgomery OH is viewer-only** (no public REST) — covered by the ODNR statewide service regardless.

## What a build would take

- **Data volume:** corridor clip only (trail-crossing parcels + adjoining ring), per the ITM model — not whole counties. ITM baselines: chapter corridor 1,038 parcels / 494 KB for ~104 mi of trail; Arrowhead corridor 44,649 parcels / 18 MB. Trail-wide estimate: on the order of **50k–150k parcels, roughly 25–75 MB as GeoJSON**, bulk in OH/MI/NY; the exact count is measurable only by running the clip. Alternative: serve parcels live from the ArcGIS services instead of vendoring — the viewer already does live services for PAD-US; a build decision.
- **Pull scripts:** one per service (~20 distinct services across 8 states), each with its own schema normalization (field names differ per service), corridor clip, and QA. A medium-large build: several focused sessions of pull + normalize + clip + verify, not one sitting.
- **Maintenance:** refresh per source cadence — MN quarterly, WI annual, VT weekly, NY annual, OH unknown (2023 snapshot — re-check), MI/PA per-county ad hoc. A stale layer is worse than a missing one where parcels turn over; the build needs a per-source "as of" date in the layer metadata.
- **Display / privacy, carried from the ITM viewer:** OFF by default, lazy-loaded on first toggle; faint below Z3, full style at Z3+; crossed parcels 2px solid orange outline, adjoining 2px dashed khaki; popup shows parcel ID, county, land class, acres, owner name + mailing address as published in the county records (public record — chapter ruling Nov 10, 2026); **taxpayer fields never carried**; "not suitable for accurate boundary determination" disclaimer per source. Owner names ARE published on the map under that ruling — the national version would need the same ruling per source, since the sources are county publications.
- **PAD-US overlap:** PAD-US already answers public-land ownership trail-wide; parcels add private-parcel ownership (who to talk to / work with). The plan's §6 question stands: is the per-state hunt worth it, or is PAD-US enough?

## Build options for Paul's call

- **A. Statewide-services-only:** 6 services, 3,034.46 mi (63.7%), uniform, simplest — one pull script per state, no per-county hunting. MI entirely blank, NY 5 counties blank, PA mostly blank.
- **B. Everything verified:** add MI's 9 county services, PA's 6 sources, Hubbard fallback → 3,599.07 mi (75.6%). Patchy in MI (29%) and NY (61%); three MI covered counties show geometry without owner names.
- **C. Leave parcels out; PAD-US carries ownership.** Zero build, zero maintenance.
- **Recommendation:** A first — a clean, uniform layer and the only part that is one script per state — then backfill MI/NY/PA counties case by case if the layer proves its worth. Re-check Kent first: one restored service is worth 74.89 mi.

## Limits of this scope

- Checks were live on 23–24 Nov 2026; services change (Kent proves it). Any build must re-verify each URL at pull time.
- "None found" means not found by the methods used (county GIS search + ArcGIS Online search); a county could publish parcels under a name the search missed. The MI file lists the viewer-only routes checked.
- Trail miles are the TIGER intersection; border-touch counties (Ionia 0.01 mi, Cheboygan 0.61, Belmont 0.49) are real crossings with trivial mileage.
- Parcel counts are service-wide or county-wide totals from live count queries, not corridor-clip counts.
- The three state files (`~/workspace/nct-parcels-scope/state-*.md`) are the evidence base for every URL and count in this note; the three headline statewide services (OH ODNR, VCGI, MnGeo) were additionally re-verified live by the coordinator.
