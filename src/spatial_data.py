"""County-level context joins: no precise facility geocoding or water-basin inference."""
import calendar
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
# Exact county/state labels only. Multiple Loudoun campuses share county context,
# not facility identity. Gazetteer coordinates are county representative points.
COUNTIES = {
    'Jackson County, Alabama': ('AL', '01071'),
    'Douglas County, Georgia': ('GA', '13097'),
    'Storey County, Nevada': ('NV', '32029'),
    'Mayes County, Oklahoma': ('OK', '40097'),
    'Berkeley County, South Carolina': ('SC', '45015'),
    'Montgomery County, Tennessee': ('TN', '47125'),
    'Loudoun County, Virginia': ('VA', '51107'),
}


def parse_climate(payload, county_label, variable):
    suffix, units = {'tavg': ('Average Temperature', 'Degrees Fahrenheit'),
                     'pcp': ('Precipitation', 'Inches')}[variable]
    if payload['description'] != {'title': f'{county_label} {suffix}', 'units': units}:
        raise ValueError('NOAA county identity or units differ from request')
    expected = {f'{year}{month:02d}' for year in range(2017, 2026) for month in range(1, 13)}
    if set(payload['data']) != expected:
        raise ValueError('NOAA monthly series is incomplete or has unexpected periods')
    rows = []
    for date, observation in payload['data'].items():
        value = float(observation['value'])
        if not math.isfinite(value) or value <= -99 or (variable == 'pcp' and value < 0):
            raise ValueError(f'Invalid/missing NOAA value: {date}')
        rows.append(dict(year=int(date[:4]), month=int(date[4:]),
                         **{variable: (value - 32) * 5 / 9 if variable == 'tavg' else value * 25.4}))
    return pd.DataFrame(rows)


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    raw = ROOT / 'data/raw'
    out = ROOT / 'data/processed'
    manifest = json.loads((raw / 'manifest.json').read_text())
    needed = ['census_counties_2025.zip'] + [f'noaa_{state}-{fips[-3:]}_{var}_2017_2025.json'
              for state, fips in COUNTIES.values() for var in ('tavg', 'pcp')]
    for name in needed:
        if hashlib.sha256((raw / name).read_bytes()).hexdigest() != manifest[name]['sha256']:
            raise ValueError(f'Raw source changed: {name}')
    with ZipFile(raw / 'census_counties_2025.zip') as archive:
        gazetteer = pd.read_csv(archive.open('2025_Gaz_counties_national.txt'), sep='|', dtype=str)
    gazetteer.columns = gazetteer.columns.str.strip()
    crosswalk, climate = [], []
    for label, (state, fips) in COUNTIES.items():
        match = gazetteer[(gazetteer.GEOID == fips) & (gazetteer.USPS == state)]
        if len(match) != 1 or match.iloc[0].NAME != label.split(', ')[0]:
            raise ValueError(f'County identity mismatch: {label}')
        county = match.iloc[0]
        crosswalk.append(dict(county_label=label, county_fips=fips, state=state,
                              county_latitude=float(county.INTPTLAT), county_longitude=float(county.INTPTLONG),
                              spatial_support='county_representative_point_not_facility_coordinate',
                              coordinate_source='census_counties_2025.zip'))
        frames = []
        for variable in ('tavg', 'pcp'):
            name = f'noaa_{state}-{fips[-3:]}_{variable}_2017_2025.json'
            frame = parse_climate(json.loads((raw / name).read_text()), label, variable)
            frame[f'{variable}_source'] = name
            frames.append(frame)
        merged = frames[0].merge(frames[1], on=['year', 'month'], validate='one_to_one')
        merged['county_fips'] = fips
        climate.append(merged)
    counties = pd.DataFrame(crosswalk)
    monthly = pd.concat(climate, ignore_index=True).rename(columns={'tavg': 'temperature_c', 'pcp': 'precipitation_mm'})
    monthly['quarter'] = (monthly.month - 1) // 3 + 1
    monthly['days'] = [calendar.monthrange(y, m)[1] for y, m in zip(monthly.year, monthly.month)]
    quarterly = []
    for (fips, year, quarter), group in monthly.groupby(['county_fips', 'year', 'quarter']):
        if len(group) != 3:
            raise ValueError('Incomplete climate quarter')
        quarterly.append(dict(county_fips=fips, year=int(year), quarter=int(quarter),
                              temperature_c=float((group.temperature_c * group.days).sum() / group.days.sum()),
                              precipitation_mm=float(group.precipitation_mm.sum())))
    quarterly = pd.DataFrame(quarterly)
    pue = pd.read_csv(out / 'google_us_pue_quarterly.csv')
    pue['county_label'] = pue.campus_name.str.replace(r' \(2nd facility\)$', '', regex=True)
    covered = pue[pue.county_label.isin(COUNTIES)].merge(counties, on='county_label', validate='many_to_one')
    panel = covered.merge(quarterly, on=['county_fips', 'year', 'quarter'], how='inner', validate='many_to_one')
    # 2026 PUE is intentionally outside this climate archive's 2017–2025 window.
    excluded = pue[~pue.county_label.isin(COUNTIES)].copy()
    excluded['reason'] = 'No exact county/state context mapping in this pilot'
    excluded.to_csv(out / 'pue_excluded_from_county_panel.csv', index=False)
    counties.to_csv(out / 'county_context_crosswalk.csv', index=False)
    monthly.to_csv(out / 'noaa_county_monthly.csv', index=False)
    quarterly.to_csv(out / 'noaa_county_quarterly.csv', index=False)
    panel.to_csv(out / 'pue_county_climate_panel.csv', index=False)
    audit = dict(counties=len(counties), monthly_climate_rows=len(monthly),
                 quarterly_climate_rows=len(quarterly), pue_climate_rows=len(panel),
                 pue_campus_labels=panel.campus_name.nunique(),
                 pue_rows_without_county_mapping=len(excluded),
                 pue_rows_outside_climate_window=int((covered.year > 2025).sum()),
                 limitations=['County climate is regional context, not facility weather.',
                              'Representative points are not facility locations or water-source locations.',
                              'Precipitation is not water availability, withdrawals or supply headroom.',
                              'Water disclosure locations have not been merged to individual PUE campuses.',
                              'Boundary/time coverage and operator disclosure selection constrain transfer.'])
    (ROOT / 'reports/spatial_data_audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
