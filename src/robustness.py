"""Post hoc sensitivity checks on frozen predictions; no model selection or refitting."""
import json
from pathlib import Path
import pandas as pd
from local_constraints import screen

ROOT = Path(__file__).resolve().parents[1]


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    predictions = pd.read_csv(ROOT/'reports/resource_predictions.csv')
    rows = []
    for (operator, target), g in predictions.groupby(['operator', 'target']):
        base = g[g.method == 'persistence']
        for method in ('nonnegative_linear_trend', 'other_state_median_growth'):
            paired = g[g.method == method].merge(base, on=['location_name', 'state', 'year'], validate='one_to_one')
            paired['delta'] = paired.absolute_error_x - paired.absolute_error_y
            subsets = [('all', 'all', paired)]
            subsets += [('year', str(y), f) for y, f in paired.groupby('year')]
            subsets += [('omit_state', state, paired[paired.state != state]) for state in sorted(paired.state.unique())]
            for kind, label, f in subsets:
                rows.append(dict(operator=operator, target=target, method=method, subset=kind,
                                 label=label, n=len(f), delta_mae=f.delta.mean(),
                                 fraction_rows_improved=(f.delta < 0).mean(),
                                 median_location_delta=f.groupby('location_name').delta.mean().median()))
    frame = pd.DataFrame(rows)
    frame.to_csv(ROOT/'reports/resource_robustness.csv', index=False)
    # Compare annual-only efficiency with the original uniform reduction.
    local = json.loads((ROOT/'reports/local_constraints.json').read_text())
    plan = local['allowances'][0]
    low, high = local['historical_peak_bounds']
    cooling = []
    for q in (.75, .8, 1.0):
        for annual_reduction, peak_reduction in ((0, 0), (.2, 0), (.2, .2)):
            cooling.append(dict(year=2029, added_average_mgd=q,
                annual_reduction=annual_reduction, peak_reduction=peak_reduction,
                **screen(plan['annual_margin_mg'], plan['peak_margin_mgd'], q,
                         low, high, annual_reduction, peak_reduction)))
    pd.DataFrame(cooling).to_csv(ROOT/'reports/cooling_peak_sensitivity.csv', index=False)
    electricity = frame[(frame.target == 'electricity_mwh') & (frame.method == 'nonnegative_linear_trend')]
    assert len(electricity[electricity.subset == 'omit_state']) == 13
    assert len(cooling) == 9
    print(electricity.to_string(index=False))
    print(pd.DataFrame(cooling)[['added_average_mgd', 'annual_reduction', 'peak_reduction', 'joint_screen']].to_string(index=False))


if __name__ == '__main__':
    main()
