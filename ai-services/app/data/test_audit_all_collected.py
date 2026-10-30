import unittest
from datetime import date
from pathlib import Path
from audit_all_collected import normalize, checks, mentions, sid_url, dates, rank, distinct_numbers


class FullAuditTests(unittest.TestCase):
    def test_float_roundoff_not_snapshot_conflict(self):
        self.assertEqual(len(distinct_numbers([4179.999999999999,4180.,None])),1)
        self.assertEqual(len(distinct_numbers([4180.,4181.])),2)

    def test_legacy_url_id_and_unknown_evidence(self):
        raw=dict(title='Bán nhà',detail_url='https://nha.chotot.com/123.htm',
            category='Nhà ở',price_million='2500',area_sqm='50',district='Quận Sơn Trà')
        r=normalize(raw,'chotot',Path('danang_chotot_10k_raw2.csv'),2)
        flags,_=checks(r)
        self.assertEqual(r['record_key'],'chotot:123')
        self.assertIn('sale_transaction_unverified',flags)
        self.assertIn('legacy_province_unverified',flags)
        self.assertIn('listing_date_unavailable',flags)
        self.assertNotIn('invalid_source_id',flags)

    def test_homedy_sale_scope_and_unknown_date_distinct(self):
        raw=dict(source_listing_id='123',title='Bán nhà',detail_url='https://homedy.com/ban-nha-rieng-da-nang/x-es123',
            source_category='Nhà riêng',price_raw='2,5 tỷ',price_million='2500',area_sqm='50',area_raw='50m2',
            address_raw='Quận Hải Châu, Đà Nẵng',district='Quận Hải Châu',detail_fetched='True')
        r=normalize(raw,'homedy',Path('data_raw/homedy_batch_3000/homedy_records.csv'),2)
        flags,_=checks(r)
        self.assertEqual(r['transaction_basis'],'source_sale_url_and_detail_snapshot')
        self.assertNotIn('sale_transaction_unverified',flags)
        self.assertIn('listing_date_unavailable',flags)

    def test_money_contexts_and_shorthand(self):
        for text,amount,kind in [('Giá 2tỷ4',2400,'total_candidate'),
          ('Giá 80tr m2',80,'unit_price'),('Giá 1 tỷ 200 triệu',1200,'total_candidate'),
          ('Cho thuê 3,7 triệu/đêm',3.7,'rental_income'),('Chỉ nhỉnh 2 tỷ',2000,'approximate_or_bound')]:
            with self.subTest(text=text):
                m=mentions(text)[0]
                self.assertEqual(m['amount_million'],amount)
                self.assertEqual(m['kind'],kind)

    def test_cross_boundary_new_location_not_forced(self):
        raw=dict(source_listing_id='123',title='Bán nhà',detail_url='https://nhadat.cafeland.vn/a-123.html',
            address_raw='Hòa Khánh, Đà Nẵng',district='Liên Chiểu')
        r=normalize(raw,'cafeland',Path('data_raw/cafeland_batch/cafeland_scope_review.csv'),2)
        self.assertEqual(r['district'],'')
        self.assertEqual(set(r['district_candidates'].split('|')),{'Liên Chiểu','Hòa Vang'})

    def test_recovered_detail_preferred_to_scope_card(self):
        raw=dict(source_listing_id='123',title='Bán đất',detail_url='https://nhadat.cafeland.vn/a-123.html')
        card=normalize(raw,'cafeland',Path('data_raw/cafeland_batch/cafeland_scope_review.csv'),2)
        recovered=normalize(dict(raw,detail_fetched='True'),'cafeland',Path('data_raw/cafeland_batch/cafeland_scope_recovered.csv'),2)
        self.assertGreater(rank(recovered),rank(card))


if __name__=='__main__':unittest.main()
