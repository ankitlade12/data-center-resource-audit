"""Post hoc summaries of frozen predictions; no fitting or holdout selection."""
from pathlib import Path

import numpy as np
import pandas as pd

from experiments import cluster_difference
from resource_experiments import summarize

ROOT = Path(__file__).resolve().parents[1]


def metrics(frame):
    error = frame.predicted - frame.observed
    total = frame.observed.sum()
    return dict(n=len(frame), mae=float(error.abs().mean()),
                rmse=float(np.sqrt((error ** 2).mean())),
                wape=None if total == 0 else float(error.abs().sum() / total))


def grouped_metrics(frame, keys, destination):
    rows = [dict(zip(keys, key), **metrics(group))
            for key, group in frame.groupby(keys)]
    pd.DataFrame(rows).to_csv(destination, index=False)


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    reports = ROOT / 'reports'
    resource = pd.read_csv(reports / 'resource_predictions.csv')
    grouped_metrics(resource, ['operator', 'target', 'method', 'year'],
                    reports / 'revision_resource_by_year.csv')
    grouped_metrics(resource, ['operator', 'target', 'method', 'location_name', 'year'],
                    reports / 'revision_resource_by_location_year.csv')
    comparisons = []
    for year, group in resource.groupby('year'):
        _, results = summarize(group)
        comparisons.extend(dict(year=int(year), **row) for row in results)
    pd.DataFrame(comparisons).to_csv(reports / 'revision_resource_year_uncertainty.csv', index=False)

    spatial = pd.read_csv(reports / 'spatial_forecast_predictions.csv')
    normalized = spatial.rename(columns={'observed_pue': 'observed', 'predicted_pue': 'predicted'})
    grouped_metrics(normalized, ['mode', 'model', 'target_year', 'campus_name'],
                    reports / 'revision_spatial_by_location_year.csv')
    comparisons = []
    for (mode, year), group in spatial.groupby(['mode', 'target_year']):
        base = 'same_quarter_previous_year' if mode == 'forward_year' else 'seasonal_trend_ridge'
        comparisons.append(dict(mode=mode, year=int(year),
                                **cluster_difference(group, 'geo_climate_ridge', base)))
    pd.DataFrame(comparisons).to_csv(reports / 'revision_spatial_year_uncertainty.csv', index=False)

    initial = pd.read_csv(reports / 'pue_baseline_predictions.csv').rename(
        columns={'observed_pue': 'observed', 'predicted_pue': 'predicted'})
    grouped_metrics(initial, ['method', 'target_year', 'campus_name'],
                    reports / 'revision_initial_by_location_year.csv')
    base = initial[initial.method == 'same_quarter_previous_year']
    comparisons = []
    for method in ['last_quarter', 'previous_year_unweighted_mean']:
        pairs = initial[initial.method == method].merge(
            base, on=['campus_name', 'target_year', 'quarter'], validate='one_to_one')
        pairs['delta'] = pairs.absolute_error_x - pairs.absolute_error_y
        groups = [g.delta.to_numpy() for _, g in pairs.groupby('campus_name')]
        rng = np.random.default_rng(20261010)
        draws = [np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))]).mean()
                 for _ in range(2000)]
        comparisons.append(dict(method=method, baseline='same_quarter_previous_year',
                                n=len(pairs), campuses=len(groups), delta_mae=pairs.delta.mean(),
                                low=np.quantile(draws, .025), high=np.quantile(draws, .975)))
    pd.DataFrame(comparisons).to_csv(reports / 'revision_initial_uncertainty.csv', index=False)

    electricity = resource[(resource.operator == 'Meta') & (resource.target == 'electricity_mwh')]
    paired = electricity.pivot(index=['location_name', 'year'], columns='method', values='absolute_error')
    paired['trend_minus_persistence'] = paired.nonnegative_linear_trend - paired.persistence
    paired.to_csv(reports / 'revision_electricity_influence.csv')
    water = resource[(resource.operator == 'Meta') & (resource.target == 'withdrawal_m3')]
    grouped_metrics(water, ['method', 'location_name'], reports / 'revision_water_by_location.csv')

    # Compact, auditable analysis table: persistence and trend for every target/year.
    labels = {'electricity_mwh': 'Meta electricity', 'withdrawal_m3': 'Meta withdrawal',
              'consumption_m3': 'Google consumption'}
    rows = []
    for (target, year), group in resource.groupby(['target', 'year']):
        persistence = metrics(group[group.method == 'persistence'])
        trend = metrics(group[group.method == 'nonnegative_linear_trend'])
        rows.append(f"{labels[target]} & {year} & {persistence['n']} & "
                    f"{100*persistence['wape']:.1f} & {100*trend['wape']:.1f} " + r'\\')
    table = (r'\begin{tabular}{llrrr}\toprule Target & Year & $n$ & Persist. & Trend\\\midrule'
             + '\n' + '\n'.join(rows) + '\n' + r'\bottomrule\end{tabular}' + '\n')
    (ROOT / 'reports/tables/generated_year_results.tex').write_text(table)
    print('Wrote frozen-prediction revision diagnostics and annual WAPE table.')


if __name__ == '__main__':
    main()
