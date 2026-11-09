# Verification record

Checked November 9, 2026 with Python 3.14 and the recorded environment.

- Exact cached originals passed SHA-256 verification. Live source retrieval was not assumed to reproduce historical pages.
- Full parsing, forecasting, capacity analysis and figure generation completed.
- All 33 tests passed, including three downloader checks for changed content, exact snapshots and overwrite prevention.
- 40 regenerated processed/result CSVs matched the original analysis within rtol1e-10 and atol1e-9.
- A clean Git-index export passed included-data diagnostics and core tests without raw provider documents.
- GitHub Actions checks the included-data path; it does not fetch originals or certify their current availability.

No broader statistical validation is implied by software checks.
