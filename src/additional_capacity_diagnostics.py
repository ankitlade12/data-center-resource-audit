"""Frozen, source-transcribed municipal treatment-screen sensitivity."""
from pathlib import Path
import pandas as pd
from resource_experiments import summarize

ROOT = Path(__file__).resolve().parents[1]


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    rows = []
    for year, average, maximum in [(2022, 3.3515, 4.603), (2023, 3.348, 4.944)]:
        ratio = maximum / average
        rows.append(dict(year=year, gross_average_mgd=average, gross_peak_mgd=maximum,
                         nominal_treatment_mgd=8, assumed_increment_ratio=ratio,
                         average_margin_mgd=8-average, peak_margin_mgd=8-maximum,
                         added_average_peak_ceiling_mgd=(8-maximum)/ratio))
    pd.DataFrame(rows).to_csv(ROOT / 'reports/revision_forest_city_screen.csv', index=False)
    frame = pd.read_csv(ROOT / 'reports/resource_predictions.csv')
    selected = frame[(frame.operator == 'Google') & (frame.location_name != 'The Dalles, OR')]
    _, comparisons = summarize(selected)
    pd.DataFrame(comparisons).to_csv(ROOT / 'reports/revision_google_without_dalles.csv', index=False)


if __name__ == '__main__':
    main()
