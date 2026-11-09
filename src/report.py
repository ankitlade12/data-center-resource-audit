"""Generate analysis numbers and research figures from saved analysis outputs."""
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/geoai-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    reports = ROOT / 'reports'
    audit = json.loads((reports / 'data_audit.json').read_text())
    spatial = json.loads((reports / 'spatial_data_audit.json').read_text())
    meta = json.loads((reports / 'meta_data_audit.json').read_text())
    comparison = json.loads((reports / 'spatial_forecast_summary.json').read_text())['comparisons']
    water = pd.read_csv(ROOT / 'data/processed/google_us_water_annual.csv')
    balanced = water.pivot(index='location_name', columns='year', values='consumption_mgal').dropna()
    balanced.to_csv(reports / 'water_four_year_fixed_cohort.csv')
    totals = balanced.sum().rename('consumption_mgal').reset_index()
    totals['locations'] = len(balanced)
    totals.to_csv(reports / 'water_four_year_fixed_cohort_totals.csv', index=False)
    baseline = json.loads((reports / 'pue_baseline_metrics.json').read_text())
    values = {'PueRecords': audit['pue_rows'], 'WaterRecords': len(water),
              'CountyCount': spatial['counties'], 'ClimateMonths': spatial['monthly_climate_rows'],
              'ClimatePanelRows': spatial['pue_climate_rows'], 'FixedWaterLocations': len(balanced),
              'MetaSites': meta['location_labels'], 'MetaRecords': meta['location_year_rows'],
              'MetaComplete': meta['complete_electricity_withdrawal_carbon_rows']}
    tex = [f'\\newcommand{{\\{name}}}{{{value}}}' for name, value in values.items()]
    (ROOT / 'reports/tables/generated_numbers.tex').write_text('\n'.join(tex) + '\n')
    labels = {'last_quarter': 'Last quarter', 'same_quarter_previous_year': 'Same quarter of previous year',
              'previous_year_unweighted_mean': 'Previous-year unweighted mean'}
    (ROOT / 'reports/tables/generated_baselines.tex').write_text(r'\begin{tabular}{lrr}\toprule Baseline & MAE & RMSE\\\midrule' + '\n' + '\n'.join(
        f"{labels[row['method']]} & {row['mae']:.5f} & {row['rmse']:.5f} \\\\" for row in baseline) + '\n' + r'\bottomrule\end{tabular}' + '\n')
    modes = {'forward_year': 'Existing-campus forward-year',
             'heldout_county_forward_year': 'Held-out-county forward-year'}
    (ROOT / 'reports/tables/generated_spatial_results.tex').write_text(r'\begin{tabular}{lrrr}\toprule Task & Pairs & $\Delta$MAE & 95\% interval\\\midrule' + '\n' + '\n'.join(
        f"{modes[row['mode']]} & {row['paired_observations']} & {row['mae_difference']:+.5f} & [{row['bootstrap_95_low']:+.5f}, {row['bootstrap_95_high']:+.5f}] \\\\" for row in comparison) + '\n' + r'\bottomrule\end{tabular}' + '\n')
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout='constrained')
    totals.plot.bar(x='year', y='consumption_mgal', ax=axes[0], legend=False, color='#176b82', rot=0)
    axes[0].set(title=f'Same {len(balanced)} disclosed U.S. locations each year',
                ylabel='Reported water consumption (million US gallons)', xlabel='Reporting year')
    for i, row in enumerate(comparison):
        center = row['mae_difference']
        axes[1].errorbar(center, i, xerr=[[center-row['bootstrap_95_low']], [row['bootstrap_95_high']-center]],
                         fmt='o', capsize=5, color='#176b82')
    axes[1].axvline(0, color='black', linewidth=.8, linestyle='--')
    axes[1].set(yticks=[0, 1], yticklabels=['Existing campus\nvs. seasonal naive', 'Held-out county\nvs. seasonal/trend'],
                xlabel='Geo/climate model MAE minus baseline MAE\nNegative favors geo/climate; positive favors baseline',
                title='Exploratory paired differences, county-bootstrap intervals', ylim=(-.7, 1.7))
    fig.suptitle('Disclosure-based pilot: growth is not AI attribution; model improvement is not established')
    fig.savefig(reports / 'longitudinal_and_validation.pdf')
    fig.savefig(reports / 'longitudinal_and_validation.png', dpi=170)
    plt.close(fig)
    counties = pd.read_csv(ROOT / 'data/processed/county_context_crosswalk.csv', dtype={'county_fips': str})
    fig, ax = plt.subplots(figsize=(9, 5), layout='constrained')
    ax.scatter(counties.county_longitude, counties.county_latitude, c='#176b82', s=50)
    for row in counties.itertuples():
        ax.annotate(row.county_label, (row.county_longitude, row.county_latitude),
                    xytext=(5, 8), textcoords='offset points', fontsize=8)
    ax.set(xlabel='Longitude (degrees)', ylabel='Latitude (degrees)', xlim=(-124, -70), ylim=(31, 42),
           title='Seven-county context panel\nCensus representative points; not facility or water-source coordinates')
    ax.grid(alpha=.2)
    fig.savefig(reports / 'county_context.pdf')
    fig.savefig(reports / 'county_context.png', dpi=170)
    plt.close(fig)
    print(f'Generated analysis numbers and figures; fixed water cohort: {len(balanced)} locations')


if __name__ == '__main__':
    main()
