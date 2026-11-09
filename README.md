# Data-Center Resource Audit

Reproducible analysis of U.S. data-center efficiency, electricity, water, and municipal capacity using public disclosures. The project tests what these records can support, preserves unsuccessful forecasts, and distinguishes annual resource totals from peak-day infrastructure constraints.

[Reproduction guide](docs/REPRODUCING.md) · [Data and attribution](DATA_AVAILABILITY.md) · [Methods and limits](docs/METHODS.md)

## Research question

Can annual operator disclosures support resource forecasting and local capacity decisions when water definitions, reporting periods, location boundaries, and peak demand are kept explicit?

The analysis combines Google and Meta disclosures with NOAA climate, Census county context, and municipal water records. The datasets are selected disclosed cohorts, not a census of U.S. data centers. No workload share is attributed to AI.

## Data and evaluation

| Input | Retained coverage | Boundary |
| --- | --- | --- |
| Google PUE | 520 quarterly observations, 27 source labels | Labels are not verified distinct buildings; PUE is an efficiency ratio |
| Google water | 83 location-year rows, 2022–2025 | Withdrawal, discharge, and consumption remain separate |
| Meta resources | 75 location-year rows, 2020–2024; 61 complete triples | Electricity, withdrawal, and location-based Scope 2 emissions |
| Climate/context | Seven counties, 180 campus-quarters | County context is not facility weather or a water-source boundary |
| Municipal evidence | The Dalles and Forest City | Conditional planning margins and nominal treatment screens |

Annual resource forecasts use chronological holdouts: 2023–2024 for Meta and 2024–2025 for Google. Every method uses the same eligible observations within a target. The growth-transfer baseline excludes all sites in the target state when estimating growth. Current source snapshots do not reconstruct historical publication availability.

## Findings

| Comparison | Result | Interpretation |
| --- | --- | --- |
| Meta electricity | Persistence WAPE 21.1%; linear trend 10.8% | Improvement within this selected sample; 11/13 sites improve, with unequal gains |
| Meta withdrawal | Persistence WAPE 33.4%; linear trend 38.8% | Electricity gains do not imply water-forecast accuracy |
| The Dalles, 2029 plan | Annual-only allowance 1.370 MGD; joint annual/peak screen 0.749–0.825 MGD | Conditional on plan capacity and historical system peaking assumptions |
| Forest City, 2022 | Average-throughput margin 4.6485 MGD; assumed peak-screen added-average ceiling 2.4734 MGD | Nominal treatment screen using gross system load; not firm supply |
| The Dalles, 2024 records | Operator withdrawal exceeds city-reported use by 26.67146 million gallons, or 6.14% of the city total | Reporting boundaries remain unreconciled; not matched-meter validation |

MGD means million U.S. gallons per day. Water prediction intervals do not establish consistent pooled superiority. The isolated 2025 Google growth-transfer result is post hoc and not multiplicity-adjusted. Geographic/climate features do not improve on existing-campus seasonal persistence in the tested setting.

Evidence: [resource metrics](reports/resource_metrics.csv), [electricity influence](reports/revision_electricity_influence.csv), [local scenarios](reports/local_decision_scenarios.csv), [Forest City calculations](reports/revision_forest_city_screen.csv), and [cross-source comparison](reports/dalles_cross_source_water.csv).

## Quick start: included data

Python 3.14 is the demonstrated environment. The dependency file pins package versions but is not a portable lock with distribution hashes. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
make test-core
make diagnostics
```

These commands work with the included processed data and saved outputs; no source downloads or TeX installation are needed. `make diagnostics` recomputes forecasts and diagnostic summaries and writes a capacity figure under `reports/figures/`. Commands overwrite derived outputs: use a fresh checkout when comparing against saved results.

## Full source reconstruction

Original provider reports and webpages are not bundled. Restore their exact recorded snapshots before rebuilding:

```sh
make acquire
make verify-sources
make rebuild
make test
```

Live pages may change or become inaccessible. Acquisition fails on a checksum mismatch instead of adopting new data. See [data availability](DATA_AVAILABILITY.md) for the distinction between an included-data rerun and reconstruction from original sources, and [reproduction](docs/REPRODUCING.md) for checked commands.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/` | Parsing, accounting, forecasts, sensitivity checks, and figure generation |
| `tests/` | Accounting, leakage, aggregation, provenance, and acquisition checks |
| `data/processed/` | Numeric analysis inputs with source/page identifiers |
| `data/manual/` | Transcribed city water totals and provenance |
| `data/raw/*manifest.json` | Provider URLs, snapshot hashes, and locators |
| `reports/` | Frozen predictions, metrics, uncertainty, and scenario outputs |
| `experiments.json`, `resource_experiments.json` | Evaluation settings and availability assumptions |
| `docs/` | Reproduction steps and scientific boundaries |

## Interpretation limits

- Withdrawal is not net consumption, and PUE is not facility electricity demand.
- Small, selected cohorts and short histories limit generalization. Bootstrap intervals describe variation across sampled states or campuses, not guaranteed future coverage.
- Whole-system peaking factors are scenario assumptions for added demand. Peak coincidence, raw/finished-water differences, outages, distribution limits, and environmental flows require additional evidence.
- A passing capacity screen is not engineering approval. Proposed supplies are not verified current as-built headroom.
- Hypothetical 20% demand reductions are sensitivity calculations, not measured cooling interventions.
- The 2024 city/operator difference is retained without inventing a correction or cause.

## Contributors and reuse

Ankit Hemant Lade and Venkata Rao Kondepati.

No software license has been selected for the original code. Public availability does not itself grant an open-source license. Third-party source materials retain their providers' terms; see [data attribution](DATA_AVAILABILITY.md). OpenAI Codex assisted with source discovery, code, checks, and documentation; responsibility remains with the human contributors.
