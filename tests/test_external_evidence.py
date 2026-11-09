import unittest
from pathlib import Path
import pandas as pd
from src.evidence_validation import compare

ROOT = Path(__file__).resolve().parents[1]


class ExternalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.city = pd.read_csv(ROOT/'data/manual/dalles_city_water_2012_2024.csv')
        f = pd.read_csv(ROOT/'data/processed/google_us_water_annual.csv')
        self.operator = f[f.location_name == 'The Dalles, OR'].copy()

    def test_real_discrepancy_not_silently_reconciled(self):
        out = compare(self.city, self.operator).set_index('year')
        self.assertAlmostEqual(out.loc[2024, 'operator_minus_city_mgal'], 26.67146)
        self.assertFalse(out.eligible_as_facility_validation_target.any())
        self.assertEqual(out.index.tolist(), [2022, 2023, 2024])

    def test_consumption_does_not_enter_withdrawal_comparison(self):
        before = compare(self.city, self.operator)
        self.operator['consumption_mgal'] = 0
        pd.testing.assert_frame_equal(before, compare(self.city, self.operator))

    def test_duplicate_year_cannot_multiply_records(self):
        with self.assertRaises(ValueError):
            compare(self.city, pd.concat([self.operator, self.operator]))

    def test_missing_and_zero_city_values_not_imputed(self):
        for bad in (None, 0):
            city = self.city.copy()
            city.loc[city.year == 2024, 'google_city_reported_gallons'] = bad
            with self.assertRaises(ValueError):
                compare(city, self.operator)
