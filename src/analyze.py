"""Descriptive real-data diagnostics and fixed-origin PUE baselines, not impact forecasts."""
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/geoai-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def baseline_predictions(pue, target_year=2025):
    """Forecast all target quarters using only the immediately preceding year.

    Requires four quarters in both years and unchanged source labels. Excludes
    renamed/new campuses explicitly; no invented historical matches.
    """
    rows = []
    for name, group in pue.groupby('campus_name'):
        train = group[group.year == target_year - 1].set_index('quarter')
        test = group[group.year == target_year].set_index('quarter')
        if len(train) != 4 or len(test) != 4 or set(train.index) != {1, 2, 3, 4} or set(test.index) != {1, 2, 3, 4}:
            continue
        for quarter in range(1, 5):
            for method, prediction in (
                ('last_quarter', train.loc[4, 'quarterly_pue']),
                ('same_quarter_previous_year', train.loc[quarter, 'quarterly_pue']),
                ('previous_year_unweighted_mean', train.quarterly_pue.mean()),
            ):
                rows.append(dict(campus_name=name, target_year=target_year, quarter=quarter,
                                 method=method, predicted_pue=float(prediction),
                                 observed_pue=float(test.loc[quarter, 'quarterly_pue']),
                                 training_end=f'{target_year - 1}-Q4'))
    if not rows:
        raise ValueError('No complete, comparable campus histories for baseline evaluation')
    return pd.DataFrame(rows)


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    processed = ROOT / 'data/processed'
    reports = ROOT / 'reports'
    pue = pd.read_csv(processed / 'google_us_pue_quarterly.csv')
    water = pd.read_csv(processed / 'google_us_water_annual.csv')
    predictions = baseline_predictions(pue)
    predictions['absolute_error'] = (predictions.predicted_pue - predictions.observed_pue).abs()
    predictions.to_csv(reports / 'pue_baseline_predictions.csv', index=False)
    metrics = []
    for method, g in predictions.groupby('method'):
        metrics.append(dict(method=method, n=len(g), n_campuses=g.campus_name.nunique(),
                            mae=float(g.absolute_error.mean()),
                            rmse=float(((g.predicted_pue - g.observed_pue) ** 2).mean() ** 0.5)))
    (reports / 'pue_baseline_metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    counts = water.groupby('year').size().to_dict()
    common = water[water.year.isin([2024, 2025])].pivot(index='location_name', columns='year', values='consumption_mgal').dropna()
    common['change_mgal'] = common[2025] - common[2024]
    common.to_csv(reports / 'water_matched_locations.csv')
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), layout='constrained')
    top = common.sort_values(2025, ascending=False).head(10).sort_values(2025)
    top[[2024, 2025]].plot.barh(ax=axes[0], color=['#8aa5b5', '#176b82'])
    axes[0].set(xlabel='Reported annual consumption (million US gallons)', ylabel='',
                title='Ten largest 2025 values among matched disclosed US locations')
    quarterly = pue[(pue.year == 2025) & pue.campus_name.isin(predictions.campus_name)]
    for name, g in quarterly.groupby('campus_name'):
        axes[1].plot(g.quarter, g.quarterly_pue, alpha=.45, linewidth=1)
    axes[1].set(xticks=[1, 2, 3, 4], xlabel='2025 quarter', ylabel='PUE (facility energy / IT energy)',
                title='Quarterly efficiency at baseline-eligible campuses')
    fig.suptitle('Public Google disclosures: descriptive pilot, not AI-specific impacts', fontsize=12)
    fig.savefig(reports / 'public_data_overview.png', dpi=170)
    fig.savefig(reports / 'public_data_overview.pdf')
    plt.close(fig)
    summary = {
        'water_location_counts': {str(k): int(v) for k, v in counts.items()},
        'matched_water_locations': len(common),
        'matched_2024_consumption_mgal': float(common[2024].sum()),
        'matched_2025_consumption_mgal': float(common[2025].sum()),
        'baseline_metrics': metrics,
        'interpretation': 'Descriptive operator disclosures only. Change is not attributed to AI. PUE errors are not electricity or water forecast errors. Annual water does not validate seasonal water estimates. Historical snapshot may contain revisions.'
    }
    (reports / 'pilot_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
