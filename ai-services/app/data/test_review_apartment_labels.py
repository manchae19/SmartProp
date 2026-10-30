"""Audit rules must distinguish price contexts and leave original labels intact."""
import json
import unittest
from review_apartment_labels import money_mentions, audit, detail, OUT, SOURCE
import csv


def row(title, price=2700, area=70):
    return dict(record_key='test:1', source='test', source_listing_id='1',
        title=title, detail_url='https://example.com/1', district='D', model_split='test',
        duplicate_candidate_group='test:1', price_million=str(price), area_sqm=str(area),
        displayed_date='2026-10-01',date_basis='displayed_calendar_date',
        raw_json=json.dumps(dict(price_raw=f'{price} triệu',area_raw=f'{area} m²')))


class AuditTests(unittest.TestCase):
    def test_context_not_every_number_is_total_price(self):
        cases = [('Giá 2,7 tỷ',2700,'total_candidate'),('Giá 1 tỷ 200 triệu',1200,'total_candidate'),
            ('Đang cho thuê 30tr/th',30,'rental_income'),('Thấp hơn thị trường 300tr',300,'discount_or_profit'),
            ('Thanh toán 1.2TY nhận nhà',1200,'partial_or_starting'),('Giá 50 triệu/m²',50,'unit_price'),
            ('Chưa tới 4 tỷ',4000,'bound')]
        for text, amount, kind in cases:
            with self.subTest(text=text):
                mention = money_mentions(text)[0]
                self.assertEqual(mention['amount_million'],amount)
                self.assertEqual(mention['kind'],kind)

    def test_source_conflict_keeps_original_label(self):
        original=row('Bán căn hộ 70m2 giá 2.7 tỷ',189)
        snapshot=original.copy()
        result=audit(original)
        self.assertIn('title_price_conflict',result['review_codes'])
        self.assertEqual(result['price_million'],189)
        self.assertEqual(result['proposed_price_million'],'')
        self.assertEqual(original,snapshot)

    def test_rental_income_does_not_mean_rental_listing(self):
        sale=audit(row('Bán căn hộ 70m2 đang cho thuê 30tr/th'))
        rental=audit(row('Cho thuê căn hộ 70m2',280))
        self.assertNotIn('rental_title',sale['review_codes'])
        self.assertNotIn('title_price_conflict',sale['review_codes'])
        self.assertIn('rental_title',rental['review_codes'])

    def test_description_other_units_are_not_total(self):
        current=dict(state='identity_verified',price_million=2700,area_sqm=70,
            description='Giá bán 2,7 tỷ. Đang cho thuê 30 triệu/tháng.')
        result=audit(row('Bán căn hộ 70m2'),current)
        self.assertNotIn('description_price_conflict',result['review_codes'])
        current['description']='Giá bán 5 tỷ. Giỏ hàng nhiều căn.'
        result=audit(row('Bán căn hộ 70m2'),current)
        self.assertIn('description_price_conflict',result['review_codes'])
        self.assertIn('multiple_properties',result['review_codes'])

    def test_real_cached_page_price_conflict(self):
        manifest=json.loads((OUT/'fetch_manifest.json').read_text(encoding='utf-8'))
        with SOURCE.open(encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream))
        original=next(r for r in rows if r['record_key']=='nhadat24h:4395745')
        current,flags=detail(original,manifest[original['record_key']])
        self.assertEqual(current['state'],'identity_verified')
        self.assertEqual(current['price_million'],189)
        result=audit(original,current,flags)
        self.assertIn('title_price_conflict',result['review_codes'])
        self.assertIn('description_price_conflict',result['review_codes'])


if __name__=='__main__':
    unittest.main()
