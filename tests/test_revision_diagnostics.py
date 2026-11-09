import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from revision_diagnostics import metrics


class RevisionMetricsTests(unittest.TestCase):
    def test_wape_uses_total_volume_not_mean_percentage(self):
        sample = pd.DataFrame({'observed': [10., 90.], 'predicted': [20., 90.]})
        result = metrics(sample)
        self.assertEqual(result['n'], 2)
        self.assertEqual(result['mae'], 5.)
        self.assertAlmostEqual(result['wape'], .1)

    def test_zero_total_is_undefined(self):
        result = metrics(pd.DataFrame({'observed': [0.], 'predicted': [1.]}))
        self.assertIsNone(result['wape'])
