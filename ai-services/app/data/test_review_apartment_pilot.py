import tempfile
from pathlib import Path
import unittest
import review_apartment_pilot as job

CATALOG={'legacy':{'Sơn Trà':'Sơn Trà','Hải Châu':'Hải Châu'},'expanded':{'new_unit:hoa xuan':'Hòa Xuân'}}


def sample(key='cafeland:9990001',**changes):
    row=dict(record_key=key,source='cafeland',title='Bán căn hộ chung cư ven biển Sơn Trà đầy đủ nội thất hai phòng ngủ',
        category='Căn hộ chung cư',source_category='ban-can-ho-chung-cu',transaction_type='sale',currency='VND',
        price_million=2500,area_sqm=55,source_evidence_flags=[],source_published_date='2026-10-27',
        collected_at='2026-10-27T17:01:00+00:00',address_raw='Sơn Trà, Đà Nẵng',source_location_parts=['Sơn Trà','Đà Nẵng'],
        description='Bán căn hộ chung cư diện tích 55m2. Giá bán 2,5 tỷ. Căn hộ gồm hai phòng ngủ và phòng khách, nội thất đầy đủ.')
    row.update(changes);return row


class ReviewTest(unittest.TestCase):
    def test_unflagged_is_locked_and_never_training(self):
        rows,_=job.decide([sample()],[],{},CATALOG)
        self.assertEqual(rows[0]['cohort_split'],'collection_holdout')
        self.assertFalse(rows[0]['training_allowed']);self.assertFalse(rows[0]['review_codes'])

    def test_missing_labels_not_repaired_by_prose(self):
        row=sample(area_sqm=None,source_evidence_flags=['missing_structured_area'])
        out,_=job.decide([row],[],{},CATALOG)
        self.assertEqual(out[0]['cohort_split'],'quarantine')
        self.assertIsNone(out[0]['area_sqm'])

    def test_repriced_and_historical_bridge_cannot_leak(self):
        old=sample('cafeland:100',pipeline_group='old:bridge')
        bridge=sample('nhadat24h:200',title='Một tiêu đề khác của tài sản cũ có hồ sơ trong tập giữ riêng',pipeline_group='old:bridge')
        new=sample(title=old['title']+' mới',price_million=4500)
        out,_=job.decide([new],[old,bridge],{},CATALOG)
        self.assertIn('linked_to_historical_collection',out[0]['group_review_codes'])
        self.assertEqual(out[0]['cohort_split'],'quarantine')

    def test_one_unresolved_member_quarantines_whole_group(self):
        a=sample();b=sample('cafeland:9990002',source_evidence_flags=['jsonld_price_mismatch'])
        out,_=job.decide([a,b],[],{},CATALOG)
        self.assertTrue(all(r['cohort_split']=='quarantine' for r in out))

    def test_clean_duplicate_contributes_only_one_group(self):
        out,_=job.decide([sample(),sample('cafeland:9990002')],[],{},CATALOG)
        self.assertEqual(sorted(r['cohort_split'] for r in out),['collection_holdout','suppressed_duplicate'])

    def test_optional_canonical_url_does_not_lose_csv_rows(self):
        rows=[sample(),sample('cafeland:9990002',requested_detail_url='https://nhadat.cafeland.vn/old-9990002.html')]
        fields=list(dict.fromkeys(k for row in rows for k in row))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'records.csv';job.write_csv(path,rows,fields)
            actual=job.read_csv(path)
        self.assertEqual(len(actual),2)
        self.assertEqual(actual[0]['requested_detail_url'],'')
        self.assertEqual(actual[1]['requested_detail_url'],rows[1]['requested_detail_url'])

    def test_cross_boundary_new_ward_not_forced_to_old_district(self):
        row=sample(address_raw='Hòa Xuân, Đà Nẵng',source_location_parts=['Hòa Xuân','Đà Nẵng'])
        result=job.quality(row,CATALOG)
        self.assertEqual(result['location_feature'],'new_unit:hoa xuan')

    def test_booking_inventory_other_city_and_conflicting_prices_held(self):
        for text,flag in [('Nhận booking căn hộ','partial_starting_or_booking_price'),
                          ('Giỏ hàng nhiều căn hộ','multiple_units_or_inventory'),
                          ('Căn hộ tại TP Huế','content_outside_da_nang_requires_review'),
                          ('Bán căn hộ giá 1,2 tỷ','description_total_price_conflict')]:
            with self.subTest(text=text):
                row=sample(description=sample()['description']+' '+text)
                self.assertIn(flag,job.quality(row,CATALOG)['review_codes'])

    def test_building_hidden_behind_apartment_title_is_quarantined(self):
        row=sample(description='Bán tòa căn hộ 3 tầng gồm 7 phòng khép kín. Diện tích đất 55m2. Giá bán 2,5 tỷ.')
        out,_=job.decide([row],[],{},CATALOG)
        self.assertIn('whole_building_or_land_area_in_seller_description',out[0]['review_codes'])
        self.assertEqual(out[0]['cohort_split'],'quarantine')

    def test_title_body_bedrooms_must_not_disagree(self):
        row=sample(title=sample()['title']+' 2PN',description=sample()['description']+' Thiết kế 3 phòng ngủ.')
        self.assertIn('bedroom_claims_conflict',job.quality(row,CATALOG)['review_codes'])

    def test_project_generic_copy_does_not_corroborate_a_priced_unit(self):
        row=sample(description='Dự án căn hộ ở trung tâm, tiện ích đầy đủ và tầm nhìn đẹp. Không gian sống sang trọng cho gia đình.')
        self.assertIn('single_unit_price_area_not_corroborated_in_seller_description',job.quality(row,CATALOG)['review_codes'])

    def test_long_near_duplicate_prose_links_even_when_repriced(self):
        body=' '.join('từ'+str(i) for i in range(100))
        new=sample(description=body+' đoạn mới',price_million=4500)
        old=sample('old:123',title='Tiêu đề hoàn toàn khác với dữ liệu mới được đăng lại',price_million=2500)
        evidence={'old:123':{'identity_verified':True,'description':body}}
        pairs=job.extra_pairs([new],[old],evidence)
        self.assertTrue(any(p['rule']=='long_seller_prose_near_duplicate_or_template' for p in pairs))


if __name__=='__main__':unittest.main()
