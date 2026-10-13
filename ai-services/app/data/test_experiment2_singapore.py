import unittest
import numpy as np
from experiment2_singapore import select_foreign, fit_transfer
from train_smartprop_baseline import predict


class TransferTests(unittest.TestCase):
    def test_period_duplicate_and_currency_units(self):
        row = dict(month='2026-04', town='A', floor_area_sqm='80', resale_price='500000')
        rows, counts = select_foreign([row, row.copy(), dict(row, month='2026-10'),
            dict(row, resale_price='nan')], 20000)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['price_million'], 10000)
        self.assertEqual(counts['exact_row_duplicate'], 1)
        self.assertEqual(counts['outside_2026_04_to_09'], 1)
        self.assertEqual(counts['invalid_numeric'], 1)

    def test_sample_order_is_reproducible(self):
        rows = [dict(month='2026-09', town='A', floor_area_sqm=str(50+i), resale_price='500000') for i in range(10)]
        self.assertEqual(select_foreign(rows, 20000, 3)[0], select_foreign(rows[::-1], 20000, 3)[0])

    def test_independent_market_intercept_and_weight(self):
        local = [dict(district='D', area_sqm=40+i*10, price_million=1000+i*400) for i in range(10)]
        foreign = [dict(district='S', area_sqm=50+i*5, price_million=5000+i*800) for i in range(20)]
        model, info = fit_transfer(local, foreign, .25)
        rescaled = [dict(r, price_million=r['price_million']*3) for r in foreign]
        other, _ = fit_transfer(local, rescaled, .25)
        key = 'log_area_district_ridge_alpha_1'
        np.testing.assert_allclose(predict(local, model)[key], predict(local, other)[key], rtol=1e-10)
        self.assertAlmostEqual(info['foreign_row_weight']*len(foreign), .25*len(local))
        self.assertAlmostEqual(model['log_area_mean'], np.log([r['area_sqm'] for r in local]).mean())
        self.assertEqual(model['districts'], ['D'])


if __name__ == '__main__':
    unittest.main()
