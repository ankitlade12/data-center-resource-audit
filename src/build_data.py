"""Extract primary-source observations. No imputation or inferred facility matching."""
import hashlib
import json
import math
import re
from pathlib import Path

import openpyxl
import pandas as pd
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = ROOT / 'data/processed'
US_STATES = set('Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware Florida Georgia Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky Louisiana Maine Maryland Massachusetts Michigan Minnesota Mississippi Missouri Montana Nebraska Nevada New_Hampshire New_Jersey New_Mexico New_York North_Carolina North_Dakota Ohio Oklahoma Oregon Pennsylvania Rhode_Island South_Carolina South_Dakota Tennessee Texas Utah Vermont Virginia Washington West_Virginia Wisconsin Wyoming'.replace('_', '~').split())
US_STATES = {s.replace('~', ' ') for s in US_STATES}
NUMBER = r'[\d,]+(?:\.\d+)?'
WATER_PAGES = {2023: 95, 2024: 80, 2025: 114, 2026: 97}


def parse_pue(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = []
    for index, table in enumerate(soup.find_all('table'), 1):
        year_heading = table.find_previous(lambda e: e.name == 'h2' and 'PUE Yearly Report' in e.get_text())
        if year_heading is None:
            raise ValueError('Table without year heading')
        year = int(re.search(r'\d{4}', year_heading.get_text())[0])
        # Named campus tables are consistently available from 2017 onward.
        if year < 2017:
            continue
        heading = table.find_previous('h2').get_text(' ', strip=True)
        match = re.fullmatch(r'Quarter 0?([1-4])', heading)
        if not match:
            raise ValueError(f'Unexpected quarter heading: {heading}')
        quarter = int(match[1])
        for tr in table.find_all('tr'):
            cells = [c.get_text(' ', strip=True) for c in tr.find_all(['td', 'th'])]
            if not cells or cells[0] in {'Fleet wide PUE', 'Campuses', 'Fleet'}:
                continue
            if len(cells) != 3:
                raise ValueError(f'Unexpected PUE row: {cells}')
            name, quarterly, ttm = cells
            state = re.sub(r' \(\d+(?:st|nd|rd|th) facility\)$', '', name.rsplit(', ', 1)[-1])
            if state not in US_STATES:
                continue
            values = [float(v) if v not in {'', '*'} else None for v in (quarterly, ttm)]
            if values[0] is None or any(v is not None and (not math.isfinite(v) or v < 1) for v in values):
                raise ValueError(f'Invalid PUE: {cells}')
            rows.append(dict(campus_name=name, state=state, year=year, quarter=quarter,
                             quarterly_pue=values[0], ttm_pue=values[1],
                             evidence_type='operator_reported', source_file='google_efficiency.html',
                             source_locator=f'HTML table {index}; {year} Q{quarter}'))
    result = pd.DataFrame(rows)
    if result.empty or result.duplicated(['campus_name', 'year', 'quarter']).any():
        raise ValueError('Empty or duplicated PUE extraction')
    return result.sort_values(['campus_name', 'year', 'quarter'])


def check_water(withdrawal, discharge, consumption):
    if not all(math.isfinite(v) and v >= 0 for v in (withdrawal, discharge, consumption)):
        raise ValueError('Invalid water value')
    # Each of three reported quantities can be rounded to the nearest 0.1 Mgal.
    if abs(withdrawal - discharge - consumption) > 0.151:
        raise ValueError('Water balance differs beyond source rounding tolerance')


def parse_water(text, report_year):
    text = '\n'.join(line.strip() for line in text.splitlines())
    if report_year in (2023, 2024):
        # PDF text extraction splits New Albany's 127.1 as "1 27.1" in FY2023.
        text = re.sub(r'(?m)^(24\.9) 1 27\.1\s*$', r'\1 127.1', text)
        pattern = rf'^([^\n]+, +(?:[A-Z]{{2}}|Virginia))\s*\n(?:(?:Potable water|Reclaimed wastewater|\d+)\s*\n)+Million\s+gallons\s+([\d,.\s]+)'
        matches = []
        for location, numbers in re.findall(pattern, text, re.MULTILINE):
            values = re.findall(NUMBER, numbers)
            if len(values) not in (4, 5):
                raise ValueError(f'Unexpected water-source block: {location}: {values}')
            if abs(float(values[0].replace(',', '')) - sum(float(x.replace(',', '')) for x in values[1:-2])) > .151:
                raise ValueError(f'Water sources do not reconcile: {location}')
            matches.append((location, values[0], values[-2], values[-1]))
    elif report_year == 2025:
        pattern = rf'^(.+?, [A-Z]{{2}})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s*$'
    elif report_year == 2026:
        pattern = rf'^(.+?, [A-Z]{{2}})(?:\s+\d{{3}})?\s+Million gallons\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})(?:\s|$)'
    else:
        raise ValueError('Unsupported report layout')
    if report_year >= 2025:
        matches = re.findall(pattern, text, re.MULTILINE)
    if report_year == 2026:
        # Douglas County breaks across lines to disclose its water-source mix.
        special = re.search(rf'Douglas County, GA\s+Potable water\s+Reclaimed wastewater\s+Million gallons\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})', text)
        if special is None:
            raise ValueError('Douglas County water-source layout changed')
        withdrawal, potable, reclaimed, discharge, consumption = [float(x.replace(',', '')) for x in special.groups()]
        if abs(withdrawal - potable - reclaimed) > 0.151:
            raise ValueError('Douglas County withdrawal components do not reconcile')
        matches.append(('Douglas County, GA', str(withdrawal), str(discharge), str(consumption)))
    rows = []
    for location, w, d, c in matches:
        original_location = location
        location = re.sub(r'\s+', ' ', location).replace('Ashburn, Virginia', 'Ashburn, VA')
        w, d, c = [float(v.replace(',', '')) for v in (w, d, c)]
        check_water(w, d, c)
        rows.append(dict(location_name=location, source_location_name=original_location, year=report_year - 1,
                         withdrawal_mgal=w, discharge_mgal=d, consumption_mgal=c,
                         withdrawal_m3=w * 3785.411784, discharge_m3=d * 3785.411784,
                         consumption_m3=c * 3785.411784,
                         evidence_type='operator_reported_including_estimated_components',
                         water_scope='total_water_not_freshwater_only',
                         source_file=f'google_{report_year}_environmental_report.pdf',
                         source_pdf_page=WATER_PAGES[report_year]))
    result = pd.DataFrame(rows)
    if result.empty or result.duplicated(['location_name', 'year']).any():
        raise ValueError('Empty or duplicated water extraction')
    expected = {re.sub(r'\s+', ' ', name).replace('Ashburn, Virginia', 'Ashburn, VA')
                for name in re.findall(r'^([^\n]+, +(?:[A-Z]{2}|Virginia))(?=\s|$)', text, re.MULTILINE)}
    actual = set(result.location_name)
    if expected != actual:
        raise ValueError(f'Water extraction incomplete: missing={expected-actual}, extra={actual-expected}')
    return result.sort_values('location_name')


def parse_egrid(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook['SRL23']
    names = list(next(sheet.iter_rows(min_row=2, max_row=2, values_only=True)))
    rows = []
    for row in sheet.iter_rows(min_row=3, values_only=True):
        entry = dict(zip(names, row))
        if entry['YEAR'] is None:
            continue
        value = float(entry['SRC2ERTA'])
        if not math.isfinite(value) or value < 0:
            raise ValueError('Invalid eGRID CO2e factor')
        rows.append(dict(year=int(entry['YEAR']), grid_region=entry['SUBRGN'],
                         region_name=entry['SRNAME'], co2e_lb_per_mwh=value,
                         co2e_kg_per_kwh=value * 0.45359237 / 1000,
                         source_file=path.name, source_locator='SRL23/SRC2ERTA',
                         factor_basis='annual_generation_output_average_not_marginal'))
    workbook.close()
    result = pd.DataFrame(rows)
    if result.empty or result.duplicated(['year', 'grid_region']).any():
        raise ValueError('Empty or duplicated eGRID extraction')
    return result


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RAW / 'manifest.json').read_text())
    for name, info in manifest.items():
        if hashlib.sha256((RAW / name).read_bytes()).hexdigest() != info['sha256']:
            raise ValueError(f'Source checksum mismatch: {name}')
    pue = parse_pue((RAW / 'google_efficiency.html').read_text())
    water_frames = []
    for report_year, page in WATER_PAGES.items():
        text = PdfReader(RAW / f'google_{report_year}_environmental_report.pdf').pages[page - 1].extract_text()
        # Extracted text is derived, not an independently downloaded source.
        (OUT / f'google_{report_year}_water_page.txt').write_text(text)
        water_frames.append(parse_water(text, report_year))
    water = pd.concat(water_frames, ignore_index=True)
    egrid = parse_egrid(RAW / 'egrid2023_data_rev2.xlsx')
    pue.to_csv(OUT / 'google_us_pue_quarterly.csv', index=False)
    water.to_csv(OUT / 'google_us_water_annual.csv', index=False)
    egrid.to_csv(OUT / 'egrid_subregions_2023.csv', index=False)
    audit = {
        'pue_rows': len(pue), 'pue_distinct_source_labels': pue.campus_name.nunique(),
        'pue_year_min': int(pue.year.min()), 'pue_year_max': int(pue.year.max()),
        'pue_missing_ttm': int(pue.ttm_pue.isna().sum()),
        'water_rows_by_year': {str(y): len(g) for y, g in water.groupby('year')},
        'water_max_balance_residual_mgal': float((water.withdrawal_mgal - water.discharge_mgal - water.consumption_mgal).abs().max()),
        'egrid_subregions': len(egrid), 'source_manifest_sha256': hashlib.sha256((RAW / 'manifest.json').read_bytes()).hexdigest(),
        'limitations': ['Google subset: one operator; not a representative US inventory.',
                       'Campus/source labels are not canonical facility IDs; no inferred joins.',
                       'Annual water must not be represented as observed monthly water.',
                       'Water includes reported estimates and nonfreshwater sources.',
                       'PUE does not measure absolute electricity or cooling alone.',
                       'Google subset: AI workload share, facility electricity and resource headroom are not established.',
                       '2023 eGRID factors are not temporally matched to 2024/2025 water data.',
                       'Current disclosure snapshots may revise historical values; not vintage backtesting.']}
    (ROOT / 'reports/data_audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
