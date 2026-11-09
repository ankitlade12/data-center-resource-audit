"""Small spatial forecasting benchmark with historical-only climate features."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'experiments.json').read_text())


def historical_features(panel, climate, lookback=3):
    rows = []
    for record in panel.to_dict('records'):
        # Keep realized target-period weather out of the feature artifact entirely.
        record.pop('temperature_c', None)
        record.pop('precipitation_mm', None)
        year, quarter, county = record['year'], record['quarter'], record['county_fips']
        past = climate[(climate.county_fips == county) & (climate.quarter == quarter)
                       & (climate.year < year) & (climate.year >= year - lookback)]
        if past.empty:
            continue
        record.update(prior_temperature_c=float(past.temperature_c.mean()),
                      prior_precipitation_mm=float(past.precipitation_mm.mean()),
                      climate_feature_latest_year=int(past.year.max()),
                      climate_feature_years=len(past))
        for q in (2, 3, 4):
            record[f'quarter_{q}'] = int(quarter == q)
        rows.append(record)
    result = pd.DataFrame(rows)
    if result.empty or not (result.climate_feature_latest_year < result.year).all():
        raise ValueError('No valid historical-only climate features')
    return result


def ridge_predict(train, test, columns, penalty=1.0):
    if len(train) < 20 or penalty <= 0:
        raise ValueError('Insufficient training data or invalid ridge penalty')
    x = train[columns].to_numpy(dtype=float)
    z = test[columns].to_numpy(dtype=float)
    y = train.quarterly_pue.to_numpy(dtype=float)
    if not all(np.isfinite(a).all() for a in (x, z, y)):
        raise ValueError('Nonfinite regression input')
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale == 0] = 1
    x = np.column_stack([np.ones(len(x)), (x - mean) / scale])
    z = np.column_stack([np.ones(len(z)), (z - mean) / scale])
    regularizer = np.eye(x.shape[1]) * penalty
    regularizer[0, 0] = 0
    coefficients = np.linalg.solve(x.T @ x + regularizer, x.T @ y)
    return np.maximum(1.0, z @ coefficients)


def run_experiments(features):
    results = []
    def append(test, predictions, mode, model, year, heldout, training_rows):
        for row, prediction in zip(test.to_dict('records'), predictions):
            results.append(dict(mode=mode, model=model, target_year=year,
                                campus_name=row['campus_name'], county_fips=row['county_fips'],
                                quarter=row['quarter'], observed_pue=row['quarterly_pue'],
                                predicted_pue=float(prediction), heldout_county=heldout,
                                training_rows=training_rows, training_end_year=year - 1,
                                climate_feature_latest_year=row['climate_feature_latest_year']))

    for year in CONFIG['temporal_target_years']:
        train = features[features.year < year]
        candidates = features[features.year == year]
        names = []
        for name in candidates.campus_name.unique():
            prior = train[(train.campus_name == name) & (train.year == year - 1)]
            current = candidates[candidates.campus_name == name]
            if set(prior.quarter) == {1, 2, 3, 4} and len(prior) == 4 and len(current) == 4:
                names.append(name)
        test = candidates[candidates.campus_name.isin(names)].sort_values(['campus_name', 'quarter'])
        if test.empty or len(train) < 20:
            continue
        for model, columns in CONFIG['models'].items():
            append(test, ridge_predict(train, test, columns, CONFIG['ridge_penalty']),
                   'forward_year', model, year, '', len(train))
        prior = train[train.year == year - 1].set_index(['campus_name', 'quarter'])
        seasonal = [prior.loc[(r.campus_name, r.quarter), 'quarterly_pue'] for r in test.itertuples()]
        append(test, seasonal, 'forward_year', 'same_quarter_previous_year', year, '', len(prior))

    for year in CONFIG['spatial_target_years']:
        for county in sorted(features.county_fips.unique()):
            train = features[(features.year < year) & (features.county_fips != county)]
            test = features[(features.year == year) & (features.county_fips == county)]
            if test.empty or len(train) < 20:
                continue
            for model, columns in CONFIG['models'].items():
                append(test, ridge_predict(train, test, columns, CONFIG['ridge_penalty']),
                       'heldout_county_forward_year', model, year, county, len(train))
    result = pd.DataFrame(results)
    if result.empty or result.duplicated(['mode', 'model', 'target_year', 'campus_name', 'quarter']).any():
        raise ValueError('Empty or duplicated experiment predictions')
    result['absolute_error'] = (result.predicted_pue - result.observed_pue).abs()
    return result


def cluster_difference(frame, model, baseline):
    keys = ['county_fips', 'target_year', 'campus_name', 'quarter']
    paired = frame[frame.model == model].merge(frame[frame.model == baseline], on=keys, validate='one_to_one')
    paired['delta'] = paired.absolute_error_x - paired.absolute_error_y
    groups = [g.delta.to_numpy() for _, g in paired.groupby('county_fips')]
    if len(groups) < 2:
        raise ValueError('Too few counties for bootstrap')
    rng = np.random.default_rng(20261010)
    draws = [float(np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))]).mean())
             for _ in range(2000)]
    return dict(model=model, baseline=baseline, paired_observations=len(paired), counties=len(groups),
                mae_difference=float(paired.delta.mean()),
                bootstrap_95_low=float(np.quantile(draws, .025)),
                bootstrap_95_high=float(np.quantile(draws, .975)),
                meaning='Negative favors model. Exploratory county-cluster interval; not population-level evidence.')


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    processed, reports = ROOT / 'data/processed', ROOT / 'reports'
    panel = pd.read_csv(processed / 'pue_county_climate_panel.csv', dtype={'county_fips': str})
    climate = pd.read_csv(processed / 'noaa_county_quarterly.csv', dtype={'county_fips': str})
    features = historical_features(panel, climate, CONFIG['climate_normal_lookback_years'])
    features.to_csv(processed / 'pue_historical_features.csv', index=False)
    predictions = run_experiments(features)
    predictions.to_csv(reports / 'spatial_forecast_predictions.csv', index=False)
    metrics = []
    for (mode, model, year), g in predictions.groupby(['mode', 'model', 'target_year']):
        metrics.append(dict(mode=mode, model=model, target_year=int(year), observations=len(g),
                            counties=g.county_fips.nunique(), mae=float(g.absolute_error.mean()),
                            rmse=float(((g.predicted_pue-g.observed_pue)**2).mean()**.5)))
    pd.DataFrame(metrics).to_csv(reports / 'spatial_forecast_metrics.csv', index=False)
    comparisons = []
    for mode, g in predictions.groupby('mode'):
        baseline = 'same_quarter_previous_year' if mode == 'forward_year' else 'seasonal_trend_ridge'
        comparisons.append(dict(mode=mode, **cluster_difference(g, 'geo_climate_ridge', baseline)))
    summary = dict(comparisons=comparisons,
                   interpretation='Exploratory efficiency forecasting only. Temporal and spatial tasks have different baselines. Weather features use historical normals, not observed future weather. No causal or resource-stress claim.',
                   config=CONFIG)
    (reports / 'spatial_forecast_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary['comparisons'], indent=2))


if __name__ == '__main__':
    main()
