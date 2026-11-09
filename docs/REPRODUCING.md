# Reproduction guide

Use Python 3.14 with `requirements-lock.txt`. Exact package versions are recorded, but wheels and operating-system dependencies are not locked. No container validation is claimed.

## Included-data route

After environment installation, `make test-core` exercises resource forecasting, cross-source arithmetic, diagnostic aggregation, and checksum acquisition behavior. `make diagnostics` regenerates PUE and annual resource benchmarks, robustness checks, location/year summaries, the Forest City screen, and a capacity figure from the included inputs. It does not reparse original provider files or independently authenticate their contents.

## Full source route

`make acquire` attempts exact source retrieval. `make verify-sources` verifies cached originals. `make rebuild` reparses raw sources, reconstructs inputs, reruns benchmarks and capacity calculations, and generates tables/figures. `make test` runs the complete suite, including tests that inspect raw source anchors and extracted text. Those tests are intentionally not silently skipped when original inputs are unavailable.

Each target stops on failure. Use a disposable checkout or save the committed outputs before rerunning, because analysis commands overwrite derived files. Tables under `reports/tables/` and figures under `reports/figures/` are generated artifacts. TeX is not required to produce them.

## Expected outputs

- `reports/resource_predictions.csv`: annual site-level predictions and errors.
- `reports/resource_metrics.csv`: target-specific physical-unit metrics and WAPE.
- `reports/revision_resource_year_uncertainty.csv`: yearly paired state intervals.
- `reports/revision_electricity_influence.csv`: location contributions to electricity error changes.
- `reports/local_decision_scenarios.csv`: conditional The Dalles scenarios.
- `reports/revision_forest_city_screen.csv`: independent nominal-treatment calculations.
- `reports/revision_google_without_dalles.csv`: location-exclusion sensitivity.
- `reports/figures/resource_validation_and_constraints.pdf`: conditional capacity figure.

The source manifests identify exact historical inputs; `ARTIFACT_SHA256.json` identifies the released code/data/output files. Numeric reruns may differ in final floating-point digits across environments. A checksum change is not silently relabeled as identical evidence.
