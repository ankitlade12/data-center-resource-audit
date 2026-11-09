"""Extract matched annual Meta disclosures without conflating withdrawal and consumption."""
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'meta_2025_environmental_data_index.pdf'


def parse_table(text, count):
    # Two long location labels wrap before their state abbreviation.
    text = re.sub(r'([A-Za-z ]+)\n\s*(\(\s*[A-Z]{2}\s*\))', r'\1 \2', text)
    rows = {}
    candidates = re.findall(r'^\s*([^\n()]+)\(\s*([A-Z]{2})\s*\)\s+([^\n]+)', text, re.MULTILINE)
    for name, state, values in candidates:
        name = ' '.join(name.split())
        tokens = values.split()
        if len(tokens) != count or any(not re.fullmatch(r'\d[\d,]*|-', token) for token in tokens):
            raise ValueError(f'Unexpected Meta numeric row: {name}, {state}: {tokens}')
        key = f'{name} ({state})'
        if key in rows:
            raise ValueError(f'Duplicate Meta row: {key}')
        rows[key] = [None if token == '-' else int(token.replace(',', '')) for token in tokens]
    if not rows:
        raise ValueError('No Meta location rows found')
    return rows


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    raw, out = ROOT / 'data/raw', ROOT / 'data/processed'
    manifest = json.loads((raw / 'manifest.json').read_text())
    if hashlib.sha256((raw / SOURCE).read_bytes()).hexdigest() != manifest[SOURCE]['sha256']:
        raise ValueError('Meta source checksum mismatch')
    reader = PdfReader(raw / SOURCE)
    tables = {}
    for metric, page, count in (('electricity', 6, 5), ('water', 9, 5), ('carbon', 4, 10)):
        text = reader.pages[page - 1].extract_text(extraction_mode='layout' if metric == 'water' else 'plain')
        (out / f'meta_{metric}_source_page.txt').write_text(text)
        tables[metric] = parse_table(text, count)
    names = set(tables['electricity'])
    if any(set(table) != names for table in tables.values()):
        raise ValueError('Meta tables have unmatched location labels; do not silently drop them')
    rows = []
    for location in sorted(names):
        for i, year in enumerate(range(2020, 2025)):
            electricity = tables['electricity'][location][i]
            withdrawal = tables['water'][location][i]
            carbon_market, carbon_location = tables['carbon'][location][i*2:i*2+2]
            rows.append(dict(operator='Meta', location_name=location, year=year,
                             electricity_mwh=electricity, withdrawal_megaliters=withdrawal,
                             withdrawal_m3=None if withdrawal is None else withdrawal*1000,
                             scope2_location_tco2e=carbon_location, scope2_market_tco2e=carbon_market,
                             withdrawal_l_per_facility_kwh=None if not electricity or withdrawal is None else withdrawal*1000/electricity,
                             implied_scope2_kg_per_kwh=None if not electricity or carbon_location is None else carbon_location/electricity,
                             direct_consumption_m3=None,
                             evidence_type='operator_reported_including_estimates', source_file=SOURCE,
                             electricity_pdf_page=6, water_pdf_page=9, carbon_pdf_page=4,
                             methodology_pdf_page=18))
    frame = pd.DataFrame(rows)
    frame.to_csv(out / 'meta_us_resource_panel_2020_2024.csv', index=False)
    complete = frame.dropna(subset=['electricity_mwh', 'withdrawal_megaliters', 'scope2_location_tco2e'])
    audit = dict(location_labels=len(names), location_year_rows=len(frame),
                 complete_electricity_withdrawal_carbon_rows=len(complete),
                 complete_rows_by_year={str(y): len(g) for y, g in complete.groupby('year')},
                 years=[2020, 2021, 2022, 2023, 2024],
                 source_missing_marker='Dash retained as missing, never replaced with zero.',
                 limitations=['Annual site electricity and withdrawal available; site consumptive water is not disclosed in the selected table.',
                              'Meta WUE is withdrawal per IT kWh; derived panel intensity is withdrawal per facility kWh, not WUE.',
                              'Scope 2 location-based emissions are accounting disclosures, not an independent causal grid model.',
                              'Market-based zeros do not imply zero physical grid emissions.',
                              'Historical disclosures are revised; publication-vintage reconstruction is not available.',
                              'Reported values are rounded and may include estimates; AI workload shares are unknown.',
                              'No direct facility identity or water-source join to the Google sample is implied.'])
    (ROOT / 'reports/meta_data_audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
