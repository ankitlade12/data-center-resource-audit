"""Evaluate actual annual resource disclosures with chronological and regional exclusion."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'resource_experiments.json').read_text())


def state_of(name):
    match = re.search(r'(?:, |\()([A-Z]{2})\)?$', name)
    if not match:
        raise ValueError(f'No unambiguous state: {name}')
    return match.group(1)


def predict(frame, target, years):
    frame = frame[['location_name', 'year', target]].copy()
    frame['state'] = frame.location_name.map(state_of)
    if frame.duplicated(['location_name', 'year']).any():
        raise ValueError('Duplicate resource observations')
    values = frame[target].dropna()
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Invalid resource observation')
    rows = []
    for year in years:
        history = frame[frame.year < year]
        prior = history.rename(columns={target: 'prior', 'year': 'prior_year'})
        prior['year'] = prior.prior_year + 1
        pairs = history.merge(prior[['location_name', 'year', 'prior']], on=['location_name', 'year'])
        pairs = pairs[(pairs.prior > 0) & pairs[target].notna()]
        for row in frame[(frame.year == year) & frame[target].notna()].to_dict('records'):
            own = history[history.location_name == row['location_name']].set_index('year')[target]
            if year-1 not in own or year-2 not in own or not np.isfinite([own[year-1], own[year-2]]).all():
                continue
            training = pairs[pairs.state != row['state']]
            if training.empty:
                continue
            growth = float((training[target] / training.prior).median())
            last, previous = own[year-1], own[year-2]
            predictions = dict(persistence=last, nonnegative_linear_trend=max(0, 2*last-previous),
                               other_state_median_growth=last*growth)
            for method, value in predictions.items():
                rows.append(dict(location_name=row['location_name'], state=row['state'], year=year,
                                 target=target, observed=row[target], predicted=float(value), method=method,
                                 training_latest_year=year-1, growth_training_pairs=len(training),
                                 growth_training_states=training.state.nunique(), growth_factor=growth))
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError('No eligible resource holdouts')
    result['absolute_error'] = (result.observed-result.predicted).abs()
    return result


def summarize(frame):
    metrics, comparisons = [], []
    for (operator, target), sample in frame.groupby(['operator', 'target']):
        for method, g in sample.groupby('method'):
            total = g.observed.sum()
            metrics.append(dict(operator=operator, target=target, method=method, observations=len(g),
                                locations=g.location_name.nunique(), states=g.state.nunique(),
                                mae=float(g.absolute_error.mean()),
                                rmse=float(np.sqrt(((g.predicted-g.observed)**2).mean())),
                                wape=None if total == 0 else float(g.absolute_error.sum()/total)))
        base = sample[sample.method == 'persistence']
        for method in ('nonnegative_linear_trend', 'other_state_median_growth'):
            pair = sample[sample.method == method].merge(base, on=['location_name', 'state', 'year'], validate='one_to_one')
            pair['delta'] = pair.absolute_error_x-pair.absolute_error_y
            groups = [g.delta.to_numpy() for _,g in pair.groupby('state')]
            rng = np.random.default_rng(20261010)
            draws = [np.concatenate([groups[j] for j in rng.integers(0,len(groups),len(groups))]).mean() for _ in range(2000)]
            comparisons.append(dict(operator=operator,target=target,method=method,baseline='persistence',
                                    delta_mae=float(pair.delta.mean()),states=len(groups),
                                    low=float(np.quantile(draws,.025)), high=float(np.quantile(draws,.975))))
    return metrics, comparisons


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    processed = ROOT/'data/processed'
    results=[]
    for operator, filename, targets in (
        ('Meta','meta_us_resource_panel_2020_2024.csv', ['electricity_mwh','withdrawal_m3']),
        ('Google','google_us_water_annual.csv', ['consumption_m3'])):
        frame=pd.read_csv(processed/filename)
        for target in targets:
            result=predict(frame,target,CONFIG['target_years'][operator]);result['operator']=operator
            results.append(result)
    frame=pd.concat(results,ignore_index=True)
    frame.to_csv(ROOT/'reports/resource_predictions.csv', index=False)
    metrics, comparisons=summarize(frame)
    pd.DataFrame(metrics).to_csv(ROOT/'reports/resource_metrics.csv',index=False)
    summary=dict(metrics=metrics,comparisons=comparisons,config=CONFIG)
    (ROOT/'reports/resource_validation.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(comparisons,indent=2))


if __name__=='__main__':
    main()
