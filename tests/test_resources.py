import unittest
from pathlib import Path
import pandas as pd
from src.resource_experiments import predict
from src.local_constraints import screen, table_rows

ROOT=Path(__file__).resolve().parents[1]

class ResourceTests(unittest.TestCase):
    def test_annual_savings_do_not_imply_peak_savings(self):
        annual_only = screen(500, 1.79, 1, 2.17, 2.39, .2, 0)
        self.assertTrue(annual_only['annual_only_pass'])
        self.assertEqual(annual_only['joint_screen'], 'fails_screen')
        self.assertEqual(screen(500, 1.79, .8, 2.17, 2.39, .2, 0)['joint_screen'], 'sensitive_to_peak_factor')
        self.assertEqual(screen(500, 1.79, .8, 2.17, 2.39, .2, .2)['joint_screen'], 'passes_tested_bounds')
        with self.assertRaises(ValueError):
            screen(500, 1.79, .8, 2.17, 2.39, .2, float('nan'))

    def test_target_year_values_do_not_change_predictions(self):
        f=pd.read_csv(ROOT/'data/processed/meta_us_resource_panel_2020_2024.csv')
        before=predict(f,'electricity_mwh',[2024])
        f.loc[f.year==2024,'electricity_mwh']*=10
        after=predict(f,'electricity_mwh',[2024])
        pd.testing.assert_series_equal(before.predicted,after.predicted)

    def test_target_state_excluded_from_growth_fit(self):
        f=pd.read_csv(ROOT/'data/processed/meta_us_resource_panel_2020_2024.csv')
        before=predict(f,'withdrawal_m3',[2024])
        f.loc[f.location_name=='Altoona (IA)','withdrawal_m3']*=10
        after=predict(f,'withdrawal_m3',[2024])
        pd.testing.assert_series_equal(before[before.state=='IA'].growth_factor,after[after.state=='IA'].growth_factor)

    def test_different_resource_units_not_pooled(self):
        f=pd.read_csv(ROOT/'reports/resource_metrics.csv')
        self.assertEqual(set(f.target),{'electricity_mwh','withdrawal_m3','consumption_m3'})
        self.assertEqual(f[(f.operator=='Meta')&(f.target=='electricity_mwh')].observations.tolist(),[26]*3)

    def test_peak_constraint_reverses_annual_screen(self):
        a=screen(500,1.79,.8,2.17,2.39)
        self.assertTrue(a['annual_only_pass'])
        self.assertEqual(a['joint_screen'],'sensitive_to_peak_factor')
        b=screen(500,1.79,1,2.17,2.39)
        self.assertTrue(b['annual_only_pass'])
        self.assertEqual(b['joint_screen'],'fails_screen')
        c=screen(500,1.79,.8,2.17,2.39,.2)
        self.assertEqual(c['joint_screen'],'passes_tested_bounds')

    def test_no_extra_load_does_not_erase_baseline_deficit(self):
        self.assertEqual(screen(-90,-1.03,0,2.17,2.39)['joint_screen'],'fails_screen')
        with self.assertRaises(ValueError):screen(500,1.79,1,2.17,2.39,1.2)

    def test_plan_parser_rejects_missing_year(self):
        with self.assertRaises(ValueError):table_rows('2024 1 2',['year','a','b'],[2024,2029])

    def test_plan_source_values_and_rounding(self):
        annual=pd.read_csv(ROOT/'data/processed/dalles_annual.csv')
        self.assertEqual(annual.loc[annual.year==2034,'published_margin_mg'].iloc[0],-90)
        peak=pd.read_csv(ROOT/'data/processed/dalles_peak.csv')
        self.assertAlmostEqual(peak.loc[peak.year==2034,'rounding_residual_mgd'].iloc[0],.01)
        self.assertEqual(peak.proposed_wells_mgd.unique().tolist(),[3.88])

if __name__=='__main__':unittest.main()
