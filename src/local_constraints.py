"""Reproduce municipal planning constraints; do not attribute city demand to AI."""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SOURCE='dalles_water_master_plan_2024.pdf'


def table_rows(text, columns, expected_years):
    rows=[]
    for line in text.splitlines():
        tokens=line.split()
        if not tokens or tokens[0] not in {str(y) for y in expected_years}:
            continue
        if len(tokens)!=len(columns):
            raise ValueError(f'Unexpected plan row: {line}')
        rows.append([float(t.replace(',','')) if t!='-' else np.nan for t in tokens])
    frame=pd.DataFrame(rows,columns=columns)
    if set(frame.year)!=set(expected_years) or frame.year.duplicated().any():
        raise ValueError('Incomplete or duplicated plan table')
    frame['year']=frame.year.astype(int)
    return frame


def screen(annual_margin_mg, peak_margin_mgd, added_average_mgd, peaking_low, peaking_high, reduction=0, peak_reduction=None):
    peak_reduction = reduction if peak_reduction is None else peak_reduction
    values=[annual_margin_mg,peak_margin_mgd,added_average_mgd,peaking_low,peaking_high,reduction,peak_reduction]
    if not np.isfinite(values).all() or added_average_mgd<0 or peaking_low<1 or peaking_high<peaking_low or not 0<=reduction<=1 or not 0<=peak_reduction<=1:
        raise ValueError('Invalid constraint input')
    demand=added_average_mgd*(1-reduction)
    annual_ok=demand*365<=annual_margin_mg
    peak_demand=added_average_mgd*(1-peak_reduction)
    low_ok=peak_demand*peaking_low<=peak_margin_mgd
    high_ok=peak_demand*peaking_high<=peak_margin_mgd
    status='passes_tested_bounds' if annual_ok and high_ok else ('sensitive_to_peak_factor' if annual_ok and low_ok else 'fails_screen')
    return dict(added_average_after_reduction_mgd=demand,annual_only_pass=bool(annual_ok),
                joint_screen=status,annual_remaining_mg=annual_margin_mg-demand*365,
                peak_remaining_low_mgd=peak_margin_mgd-peak_demand*peaking_low,
                peak_remaining_high_mgd=peak_margin_mgd-peak_demand*peaking_high)


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    manifest=json.loads((ROOT/'data/raw/manifest.json').read_text())
    path=ROOT/'data/raw'/SOURCE
    if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest[SOURCE]['sha256']:
        raise ValueError('Municipal plan hash mismatch')
    reader=PdfReader(path)
    pages={n:reader.pages[n-1].extract_text() for n in (33,36,47,49,53,54,55)}
    out=ROOT/'data/processed'
    for n,t in pages.items(): (out/f'dalles_plan_page_{n}.txt').write_text(t)
    historical=pages[33].split('Table 2-2 | Historical ADD and MDD')[1].split('Max ')[0].replace('20191 ','2019 ')
    hist=table_rows(historical,['year','average_mgd','maximum_mgd','reported_peak_factor'],range(2017,2023))
    projected=table_rows(pages[36],['year','population','residential_mgd','nonresidential_mgd','average_mgd','maximum_mgd','peak_hour_mgd'],[2024,2029,2034,2039,2044,2074])
    peak=table_rows(pages[49],['year','maximum_mgd','existing_wells_mgd','proposed_wells_mgd','treatment_mgd','total_mgd','published_margin_mgd'],[2024,2029,2034,2039,2044,2074])
    annual_text=pages[55].split('Table 4-3 | Annual Water Balance Summary (MG)')[1].replace('Existing (2024)','2024')
    annual=table_rows(annual_text,['year','demand_mg','groundwater_mg','surface_mg','published_margin_mg','climate_margin_mg'],[2024,2029,2034,2044,2074])
    peak['computed_margin_mgd']=peak.total_mgd-peak.maximum_mgd
    peak['rounding_residual_mgd']=peak.published_margin_mgd-peak.computed_margin_mgd
    if peak.rounding_residual_mgd.abs().max()>.011:
        raise ValueError('Unexpected peak capacity balance')
    for name,frame,page in [('historical',hist,33),('projected',projected,36),('peak',peak,49),('annual',annual,55)]:
        frame['source_file']=SOURCE;frame['pdf_page']=page
        frame.to_csv(out/f'dalles_{name}.csv',index=False)
    # Hindcast conditional on observed annual mean; not an ex ante monthly forecast.
    validations=[]
    for year in (2021,2022):
        prior=hist[(hist.year<year)&hist.maximum_mgd.notna()]
        factor=float((prior.maximum_mgd/prior.average_mgd).max())
        observed=hist[hist.year==year].iloc[0]
        validations.append(dict(year=year,observed_mdd=observed.maximum_mgd,annual_mean=observed.average_mgd,
                               prior_max_peak_factor=factor,estimated_peak=observed.average_mgd*factor,
                               training_end=year-1,conditioning='observed target-year average; not ex ante forecast'))
    pd.DataFrame(validations).to_csv(ROOT/'reports/municipal_peak_hindcast.csv',index=False)
    # Bounds deliberately use rounded published historical system ratios, not site cooling data.
    low,high=float(hist.reported_peak_factor.min()),float(hist.reported_peak_factor.max())
    scenarios=[]
    for year in (2029,2034):
        a=annual[annual.year==year].iloc[0];p=peak[peak.year==year].iloc[0]
        for climate in ('plan_reference','plan_climate_sensitivity'):
            if climate=='plan_climate_sensitivity' and pd.isna(a.climate_margin_mg): continue
            annual_margin=a.published_margin_mg if climate=='plan_reference' else a.climate_margin_mg
            for added in (0,.25,.5,.75,.8,1,1.5):
                for reduction in (0,.2):
                    scenarios.append(dict(year=year,horizon_years=year-2024,climate=climate,
                        added_average_mgd=added,reduction_fraction=reduction,peaking_low=low,peaking_high=high,
                        **screen(annual_margin,p.computed_margin_mgd,added,low,high,reduction)))
    pd.DataFrame(scenarios).to_csv(ROOT/'reports/local_decision_scenarios.csv',index=False)
    allowances=[]
    for year in (2029,2034):
        a=annual[annual.year==year].iloc[0];p=peak[peak.year==year].iloc[0]
        allowances.append(dict(year=year,annual_margin_mg=float(a.published_margin_mg),
            peak_margin_mgd=float(p.computed_margin_mgd),
            annual_only_additional_mgd=max(0,float(a.published_margin_mg)/365),
            joint_additional_mgd_low_peak=max(0,min(float(a.published_margin_mg)/365,float(p.computed_margin_mgd)/low)),
            joint_additional_mgd_high_peak=max(0,min(float(a.published_margin_mg)/365,float(p.computed_margin_mgd)/high))))
    report=dict(allowances=allowances,historical_peak_bounds=[low,high],scenarios=len(scenarios),
        scenario_status='Conditional stress tests added to municipal plan, not predictions of Google expansion.',
        baseline_year=2024,horizons=[2029,2034],
        limitations=['13.87 MGD includes proposed Riverside wells; not verified as-built capacity today.',
        'Maximum-day treatment calculation does not itself ensure seasonal source water availability.',
        'Historical system peak ratios are sensitivity bounds, not calibrated data-center cooling ratios.',
        '20% reduction is an illustrative intervention requirement, not measured technology performance or equivalent-compute proof.',
        'Plan baseline already includes growth. Added loads are incremental beyond that plan and not assigned to Google.',
        'Annual totals are rounded and based on water-year planning; 365 is a planning conversion, not exact calendar-year metering.',
        '2034 climate case adopts the plan sensitivity, not a new downscaled climate model.',
        'Only necessary aggregate water conditions are screened; distribution hydraulics, power, permits and environmental flow remain additional constraints.',
        'A failed aggregate screen warrants further engineering or mitigation; a pass is not permission to connect.'])
    (ROOT/'reports/local_constraints.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
