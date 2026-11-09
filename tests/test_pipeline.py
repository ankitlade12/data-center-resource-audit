import unittest
from pathlib import Path

import pandas as pd

from src.accounting import operational_footprint
from src.analyze import baseline_predictions
from src.build_data import check_water, parse_pue, parse_water
from src.spatial_data import parse_climate
from src.experiments import historical_features, run_experiments
from src.meta_data import parse_table
import json

ROOT = Path(__file__).resolve().parents[1]


class AccountingTests(unittest.TestCase):
    def test_units_and_it_denominator(self):
        r = operational_footprint(1000, 1.2, direct_consumption_l_per_it_kwh=2,
                                  grid_water_l_per_facility_kwh=.5,
                                  grid_carbon_kg_per_facility_kwh=.4)
        self.assertEqual(r['facility_energy_kwh'], 1200)
        self.assertEqual(r['direct_consumption_l'], 2000)
        self.assertEqual(r['indirect_consumption_l'], 600)
        self.assertEqual(r['total_consumption_l'], 2600)
        self.assertEqual(r['electricity_carbon_kg'], 480)

    def test_missing_is_not_zero(self):
        r = operational_footprint(1000, 1.1, direct_consumption_l_per_it_kwh=0)
        self.assertEqual(r['direct_consumption_l'], 0)
        self.assertIsNone(r['total_consumption_l'])
        self.assertIsNone(r['electricity_carbon_kg'])

    def test_invalid_values(self):
        for value in (-1, float('nan'), float('inf'), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                operational_footprint(value, 1.1)
        with self.assertRaises(ValueError):
            operational_footprint(100, .9)
        with self.assertRaises(ValueError):
            operational_footprint(100, 1.1, direct_consumption_l_per_it_kwh=-1)


class DataTests(unittest.TestCase):
    def test_meta_missing_and_zero_remain_distinct(self):
        rows = parse_table('Example (VA) 0 - 1,234 5 6', 5)
        self.assertEqual(rows['Example (VA)'], [0, None, 1234, 5, 6])
        with self.assertRaises(ValueError):
            parse_table('Example (VA) 0 broken 1,234 5 6', 5)

    def test_meta_source_anchor_and_accounting_boundary(self):
        frame = pd.read_csv(ROOT / 'data/processed/meta_us_resource_panel_2020_2024.csv')
        row = frame[(frame.location_name == 'Altoona (IA)') & (frame.year == 2024)].iloc[0]
        self.assertEqual(row.electricity_mwh, 1585392)
        self.assertEqual(row.withdrawal_megaliters, 242)
        self.assertEqual(row.scope2_location_tco2e, 666434)
        self.assertEqual(row.withdrawal_m3, 242000)
        self.assertAlmostEqual(row.withdrawal_l_per_facility_kwh, 242000/1585392)
        self.assertTrue(frame.direct_consumption_m3.isna().all())
        self.assertEqual(len(frame.dropna(subset=['electricity_mwh', 'withdrawal_megaliters', 'scope2_location_tco2e'])), 61)

    def test_rounding_and_water_balance(self):
        check_water(.2, .2, .03)
        with self.assertRaises(ValueError):
            check_water(100, 50, 20)

    def test_pue_source_anchors_and_missing_marker(self):
        frame = parse_pue((ROOT / 'data/raw/google_efficiency.html').read_text())
        row = frame[(frame.campus_name == 'Loudoun County, Virginia') & (frame.year == 2024) & (frame.quarter == 1)].iloc[0]
        self.assertEqual(row.quarterly_pue, 1.08)
        self.assertEqual(row.ttm_pue, 1.09)
        self.assertTrue(frame.ttm_pue.isna().any())
        self.assertFalse(frame.campus_name.str.contains('Dublin').any())

    def test_water_source_anchors_and_units(self):
        water = pd.read_csv(ROOT / 'data/processed/google_us_water_annual.csv')
        for year, expected in ((2024, 1010.2), (2025, 1346.0)):
            row = water[(water.location_name == 'Council Bluffs, IA') & (water.year == year)].iloc[0]
            self.assertEqual(row.consumption_mgal, expected)
            self.assertAlmostEqual(row.consumption_m3, expected * 3785.411784)
        douglas = water[(water.location_name == 'Douglas County, GA') & (water.year == 2025)].iloc[0]
        self.assertEqual(douglas.withdrawal_mgal, 440.6)
        self.assertEqual(douglas.consumption_mgal, 367.1)

    def test_egrid_conversion(self):
        frame = pd.read_csv(ROOT / 'data/processed/egrid_subregions_2023.csv')
        row = frame[frame.grid_region == 'AKGD'].iloc[0]
        self.assertEqual(row.co2e_lb_per_mwh, 905.109)
        self.assertAlmostEqual(row.co2e_kg_per_kwh, 905.109 * .45359237 / 1000)

    def test_forecast_does_not_use_test_values(self):
        pue = pd.read_csv(ROOT / 'data/processed/google_us_pue_quarterly.csv')
        original = baseline_predictions(pue)
        modified = pue.copy()
        modified.loc[modified.year >= 2025, 'quarterly_pue'] += 10
        altered = baseline_predictions(modified)
        pd.testing.assert_series_equal(original.predicted_pue, altered.predicted_pue)
        self.assertTrue((original.training_end == '2024-Q4').all())

    def test_older_pdf_spacing_and_counts(self):
        water = pd.read_csv(ROOT / 'data/processed/google_us_water_annual.csv')
        self.assertEqual(water.groupby('year').size().to_dict(), {2022: 16, 2023: 18, 2024: 23, 2025: 26})
        lenoir = water[(water.location_name == 'Lenoir, NC') & (water.year == 2022)].iloc[0]
        self.assertEqual(lenoir.consumption_mgal, 320.5)
        albany = water[(water.location_name == 'New Albany, OH') & (water.year == 2023)].iloc[0]
        self.assertEqual(albany.consumption_mgal, 127.1)

    def test_malformed_water_row_cannot_silently_disappear(self):
        text = (ROOT / 'data/processed/google_2025_water_page.txt').read_text()
        text = text.replace('59.5 3.5 56.0', '59.5 missing 56.0')
        with self.assertRaises(ValueError):
            parse_water(text, 2025)

    def test_noaa_identity_units_completeness(self):
        original = json.loads((ROOT / 'data/raw/noaa_SC-015_tavg_2017_2025.json').read_text())
        frame = parse_climate(original, 'Berkeley County, South Carolina', 'tavg')
        self.assertAlmostEqual(frame.iloc[0].tavg, (54.4 - 32) * 5 / 9)
        with self.assertRaises(ValueError):
            parse_climate(original, 'Jackson County, Alabama', 'tavg')
        original['data'].pop('202501')
        with self.assertRaises(ValueError):
            parse_climate(original, 'Berkeley County, South Carolina', 'tavg')

    def test_future_climate_not_used(self):
        panel = pd.read_csv(ROOT / 'data/processed/pue_county_climate_panel.csv', dtype={'county_fips': str})
        climate = pd.read_csv(ROOT / 'data/processed/noaa_county_quarterly.csv', dtype={'county_fips': str})
        before = historical_features(panel, climate)
        self.assertNotIn('temperature_c', before.columns)
        self.assertNotIn('precipitation_mm', before.columns)
        climate.loc[climate.year >= 2025, ['temperature_c', 'precipitation_mm']] += 10000
        after = historical_features(panel, climate)
        pd.testing.assert_frame_equal(before, after)

    def test_spatial_holdout_excludes_all_county_outcomes(self):
        features = pd.read_csv(ROOT / 'data/processed/pue_historical_features.csv', dtype={'county_fips': str})
        original = run_experiments(features)
        features.loc[features.county_fips == '51107', 'quarterly_pue'] += 10
        modified = run_experiments(features)
        left = original[(original['mode'] == 'heldout_county_forward_year') & (original.heldout_county == '51107')]
        right = modified[(modified['mode'] == 'heldout_county_forward_year') & (modified.heldout_county == '51107')]
        self.assertEqual(left.campus_name.nunique(), 2)
        pd.testing.assert_series_equal(left.predicted_pue, right.predicted_pue)

    def test_target_outcomes_not_used_in_forward_fit(self):
        features = pd.read_csv(ROOT / 'data/processed/pue_historical_features.csv', dtype={'county_fips': str})
        before = run_experiments(features)
        features.loc[features.year == 2025, 'quarterly_pue'] += 10
        after = run_experiments(features)
        pd.testing.assert_series_equal(before.predicted_pue, after.predicted_pue)


if __name__ == '__main__':
    unittest.main()
