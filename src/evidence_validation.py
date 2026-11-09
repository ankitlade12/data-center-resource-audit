"""Cross-source annual comparison, not a same-meter validation dataset."""
import hashlib
import json
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def compare(city, operator):
    if city.year.duplicated().any() or operator.year.duplicated().any():
        raise ValueError('Annual comparison requires unique years within each boundary')
    if city[['google_city_reported_gallons', 'city_total_gallons']].isna().any().any():
        raise ValueError('City observations must be present')
    if ((city.google_city_reported_gallons <= 0) |
            (city.google_city_reported_gallons > city.city_total_gallons)).any():
        raise ValueError('Invalid city accounting totals')
    # Explicitly select withdrawal: the municipal label is not net consumption.
    out = city.merge(operator[['year', 'withdrawal_mgal']], on='year', validate='one_to_one')
    out['city_google_mgal'] = out.google_city_reported_gallons / 1e6
    out['operator_minus_city_mgal'] = out.withdrawal_mgal - out.city_google_mgal
    out['difference_pct_of_city'] = 100 * out.operator_minus_city_mgal / out.city_google_mgal
    out['boundary_status'] = 'unreconciled_candidate_comparison'
    out['eligible_as_facility_validation_target'] = False
    return out.sort_values('year')


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    provenance = json.loads((ROOT/'data/manual/dalles_city_water_provenance.json').read_text())
    raw = ROOT/'data/raw'/provenance['source_file']
    if hashlib.sha256(raw.read_bytes()).hexdigest() != provenance['source_sha256']:
        raise ValueError('City source image checksum changed')
    city = pd.read_csv(ROOT/'data/manual/dalles_city_water_2012_2024.csv')
    if city.year.tolist() != list(range(2012, 2025)):
        raise ValueError('Unexpected city record years')
    operator = pd.read_csv(ROOT/'data/processed/google_us_water_annual.csv')
    operator = operator[operator.location_name == 'The Dalles, OR']
    out = compare(city, operator)
    if out.year.tolist() != [2022, 2023, 2024]:
        raise ValueError('Unexpected overlap; inspect updated source boundaries')
    out.to_csv(ROOT/'reports/dalles_cross_source_water.csv', index=False)
    lines = [r'\begin{tabular}{rrrr}', r'\toprule Year & City (MG) & Google (MG) & Difference (\%)\\\midrule']
    for row in out.itertuples():
        lines.append(f'{row.year} & {row.city_google_mgal:.3f} & {row.withdrawal_mgal:.3f} & {row.difference_pct_of_city:+.3f}' + r'\\')
    lines.extend([r'\bottomrule', r'\end{tabular}'])
    (ROOT/'reports/tables/generated_external_water.tex').write_text('\n'.join(lines)+'\n')
    pages = {'doe_thermosyphon_2019': [1, 2],
             'cec_liquid_cooling_2024': [2, 3, 52, 53],
             'nwascopud_transmission_comments_2025': [1, 2],
             'google_ai_measurement_2025': [6, 7, 10]}
    manifest = json.loads((ROOT/'data/raw/manifest.json').read_text())
    for stem, numbers in pages.items():
        path = ROOT/'data/raw'/f'{stem}.pdf'
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[path.name]['sha256']:
            raise ValueError(f'Source checksum changed: {path.name}')
        reader = PdfReader(path)
        for number in numbers:
            (ROOT/'data/processed'/f'{stem}_page_{number}.txt').write_text(reader.pages[number-1].extract_text())
    print(out[['year', 'city_google_mgal', 'withdrawal_mgal', 'difference_pct_of_city']].to_string(index=False))


if __name__ == '__main__':
    main()
