import unittest
import csv
from datetime import date
from smartprop_geography import resolve
from prepare_smartprop_dataset import price, duplicates, screen, BASE


class PreparationTests(unittest.TestCase):
    def test_new_ward_crosses_old_districts(self):
        district, basis, choices = resolve('Hòa Khánh, Đà Nẵng', source='cafeland')
        self.assertEqual(district, '')
        self.assertEqual(basis, 'crosses_historical_districts')
        self.assertIn('Hòa Vang', choices)

    def test_new_commune_unique_and_outside(self):
        self.assertEqual(resolve('Bà Nà, Đà Nẵng', source='cafeland')[0], 'Hòa Vang')
        self.assertEqual(resolve('Hội An, Đà Nẵng', source='cafeland')[1], 'outside_or_unknown')

    def test_explicit_old_label_over_new_name(self):
        self.assertEqual(resolve('Phường Hòa Minh, Quận Liên Chiểu, Đà Nẵng', source='homedy')[0], 'Liên Chiểu')
        self.assertEqual(resolve('Liên Chiểu, Đà Nẵng', source='cafeland')[0], '')

    def test_price_unit_and_missing(self):
        self.assertEqual(price('4 tỷ 500 triệu'), 4500)
        self.assertEqual(price('4,5 Tỷ'), 4500)
        self.assertIsNone(price('35 triệu/m²'))
        self.assertIsNone(price('Thỏa thuận'))

    def test_cross_source_duplicate_group_cannot_cross_holdouts(self):
        a = dict(record_key='cafeland:1', source='cafeland', district='Hải Châu',
                 category='Nhà ở', title='Bán nhà mặt tiền đường Nguyễn Văn Linh trung tâm',
                 area_sqm=100, price_million=5000, detail_url='https://example.com/1')
        b = dict(a, record_key='homedy:2', source='homedy', price_million=5200)
        pairs = duplicates([a,b])
        self.assertEqual(len(pairs),1)
        self.assertTrue(pairs[0]['cross_source'])
        self.assertEqual(a['duplicate_candidate_group'],b['duplicate_candidate_group'])
        self.assertEqual(a['model_split'],b['model_split'])

    def test_nhadat_province_evidence_without_province_in_address(self):
        path=BASE/'data_raw/nhadat24h_batch/nhadat24h_records.csv'
        with path.open(encoding='utf-8-sig',newline='') as f:
            raw=next(csv.DictReader(f))
        row=screen(raw,'nhadat24h',str(path),2,date(2026,10,11))
        self.assertEqual(row['district'],'Hòa Vang')
        self.assertEqual(row['location_basis'],'source_province_flag_and_historical_district')
        bad=dict(raw,listing_page='https://nhadat24h.net/nha-dat-ha-noi')
        self.assertEqual(screen(bad,'nhadat24h',str(path),2,date(2026,10,11))['status'],'outside_or_unknown')


if __name__ == '__main__':
    unittest.main()
