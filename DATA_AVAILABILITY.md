# Data availability and attribution

## Included

Numeric processed CSVs, manually transcribed city totals, saved predictions/results, source locators, and SHA-256 source manifests are included. Missing values remain missing. Original provider documents and full extracted page text are not redistributed in this repository. Derived records preserve provenance; no blanket license is asserted over third-party information.

## Providers

| Provider | Evidence | Locator |
| --- | --- | --- |
| Google | Quarterly efficiency and 2023–2026 environmental reports | `data/raw/manifest.json`; CSV source/page columns |
| Meta | 2025 Environmental Data Index | `data/raw/manifest.json`; electricity p.6, withdrawal p.9, emissions p.4 |
| NOAA NCEI | County temperature and precipitation | `data/raw/manifest.json`; county/variable URL entries |
| U.S. Census Bureau | 2025 county gazetteer | `data/raw/manifest.json` |
| U.S. EPA | eGRID 2023 generation-output emission factors | `data/raw/manifest.json`; not delivered-energy factors without adjustment |
| City of The Dalles / Consor | November 2024 water master plan | `data/raw/manifest.json`; tables 2-2, 2-6, 4-1, 4-3 |
| City of The Dalles via OPB | Calendar-year Google/city use, snapshot January 10, 2025 | `data/manual/dalles_city_water_provenance.json` |
| NC DEQ/DWR and Town of Forest City | Utility-submitted plans and treatment rating | `data/raw/additional_capacity_sources_manifest.json` |
| NC Commerce | Municipal water-line connection serving Facebook cooling | `data/raw/additional_capacity_sources_manifest.json` |
| ICPRB, Prince William Water, Loudoun County | Regional demand and infrastructure context | `data/raw/revision_manifest.json` |

Other contextual evidence is identified by filename and URL in the manifests. Access dates and retrieval timestamps are historical provenance, not claims that URLs still return identical bytes.

## Restore exact inputs

`python3 src/acquire.py` retrieves source URLs and checks bytes against frozen hashes. Existing snapshots are checked and never overwritten. Files that fail retrieval or checksum verification are reported, and the command exits unsuccessfully. It does not rewrite manifests to make changed inputs appear valid.

`python3 src/acquire.py --verify` checks local originals without network access. Full parsing and all tests require these snapshots. The included-data diagnostic path does not.

For a changed or unavailable URL, obtain the matching historical snapshot from the provider or the project maintainers if redistribution is permitted. Do not substitute updated sources and claim an exact reconstruction. A refreshed dataset needs separate provenance and a new evaluation. Provider terms govern original source material; inclusion in a source list does not confer redistribution rights.

## Manual and independent-case evidence

The city image was manually transcribed with visual checks; no second human transcription review is recorded. Its “consumption” label is not established as hydrologic net consumption. The operator/city meter-account boundary remains unreconciled.

Forest City uses reported 2022 mean/maximum 3.3515/4.603 MGD and nominal treatment rating 8 MGD. In 2023 the largest monthly maximum is 4.944 MGD, while the source-table maximum reads zero; the monthly series is explicitly used. The 2024 source/planning means disagree (3.165 versus 3.1564 MGD), so that year is not included in the principal calculation. Gross withdrawals proxy treatment load; paired daily finished-water measurements and firm annual hydrologic yield are not available.
