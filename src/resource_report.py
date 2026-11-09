"""Analysis tables and figures generated from resource validation and planning outputs."""
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/geoai-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    reports=ROOT/'reports';tables=ROOT/'reports/tables'
    metrics=pd.read_csv(reports/'resource_metrics.csv')
    labels={'electricity_mwh':'Meta electricity (MWh)','withdrawal_m3':'Meta withdrawal (m$^3$)', 'consumption_m3':'Google consumption (m$^3$)'}
    methods={'persistence':'Persistence','nonnegative_linear_trend':'Linear trend','other_state_median_growth':'Other-state growth'}
    rows=[r'\begin{tabular}{llrrr}\toprule Outcome & Method & $n$ & MAE & WAPE\\\midrule']
    for r in metrics.itertuples():
        rows.append(f'{labels[r.target]} & {methods[r.method]} & {r.observations} & {r.mae:,.0f} & {r.wape*100:.1f}\\% \\\\')
    rows.append(r'\bottomrule\end{tabular}')
    (tables/'generated_resource_results.tex').write_text('\n'.join(rows)+'\n')
    meta=pd.read_csv(ROOT/'data/processed/meta_us_resource_panel_2020_2024.csv')
    cohort=meta[(meta.year==2024)&(meta.electricity_mwh>0)].copy()
    total_e=float(cohort.electricity_mwh.sum())
    descriptive=dict(year=2024,locations=len(cohort),electricity_mwh=total_e,
        withdrawal_m3=float(cohort.withdrawal_m3.sum()),
        scope2_location_tco2e=float(cohort.scope2_location_tco2e.sum()),
        weighted_withdrawal_l_per_facility_kwh=float(cohort.withdrawal_m3.sum()/total_e),
        weighted_carbon_kg_per_kwh=float(cohort.scope2_location_tco2e.sum()/total_e),
        meaning='Selected disclosed U.S. sites; no AI attribution, independent emissions validation or national extrapolation.')
    (reports/'meta_2024_descriptive.json').write_text(json.dumps(descriptive,indent=2)+'\n')
    cohort[['location_name','electricity_mwh','withdrawal_m3','scope2_location_tco2e','implied_scope2_kg_per_kwh','withdrawal_l_per_facility_kwh']].to_csv(reports/'meta_2024_descriptive.csv',index=False)
    local=json.loads((reports/'local_constraints.json').read_text())
    rows=[r'\begin{tabular}{rrrr}\toprule Year & Annual margin (MG) & Peak margin (MGD) & Additional mean (MGD)\\\midrule']
    for r in local['allowances']:
        rows.append(f"{r['year']} & {r['annual_margin_mg']:.0f} & {r['peak_margin_mgd']:.2f} & {r['joint_additional_mgd_high_peak']:.3f}--{r['joint_additional_mgd_low_peak']:.3f} \\\\")
    rows.append(r'\bottomrule\end{tabular}')
    (tables/'generated_constraints.tex').write_text('\n'.join(rows)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    targets=['electricity_mwh','withdrawal_m3','consumption_m3']
    x=np.arange(3)
    for i,m in enumerate(methods):
        vals=[metrics[(metrics.target==t)&(metrics.method==m)].iloc[0].wape*100 for t in targets]
        axes[0].bar(x+(i-1)*.25,vals,width=.25,label=methods[m])
    axes[0].set(xticks=x,xticklabels=['Meta\nelectricity','Meta\nwithdrawal','Google\nconsumption'],ylabel='WAPE (%)',title='Different outcomes need separate validation')
    axes[0].legend(fontsize=8)
    q=np.linspace(0,1.5,301); r=local['allowances'][0]
    axes[1].axvspan(0,r['joint_additional_mgd_high_peak'],color='#55aa77',alpha=.2,label='Passes tested water bounds')
    axes[1].axvspan(r['joint_additional_mgd_high_peak'],r['joint_additional_mgd_low_peak'],color='orange',alpha=.3,label='Peak-factor sensitive')
    axes[1].axvspan(r['joint_additional_mgd_low_peak'],1.5,color='#dd6677',alpha=.18,label='Fails a tested constraint')
    for factor in local['historical_peak_bounds']:
        axes[1].plot(q,r['peak_margin_mgd']-q*factor,label=f'Peak margin: factor {factor:.2f}')
    axes[1].axhline(0,color='black',linewidth=.8)
    axes[1].axvline(r['annual_only_additional_mgd'],color='black',linestyle='--',label='Annual-only limit')
    axes[1].set(xlim=(0,1.5),xlabel='Additional average water demand (MGD)',ylabel='Remaining peak-day margin (MGD)',title='2029 municipal-plan sensitivity')
    axes[1].legend(fontsize=7,loc='lower left')
    fig.savefig(reports/'resource_validation_and_constraints.pdf')
    fig.savefig(reports/'resource_validation_and_constraints.png',dpi=170)
    plt.close(fig)
    print('Generated resource tables and constraint figure')

if __name__=='__main__':main()
