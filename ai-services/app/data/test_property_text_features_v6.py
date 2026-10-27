import json
import unittest
import numpy as np
import property_text_features_v6 as f
import training_v3_common as c


class LiteralFeaturesTests(unittest.TestCase):
    def sample(self,title='',body='',category='Nhà ở',rooms=''):
        row=dict(record_key='cafeland:123',source='cafeland',category=category,rooms=rooms,
                 area_sqm='60',location_feature='Hải Châu',ward_source='')
        origin=dict(title=title,raw_json=json.dumps(dict(source_category='ban-nha-rieng')))
        return row,origin,body

    def values(self,*args,**kwargs):
        row,origin,body=self.sample(*args,**kwargs)
        return f.extract(row,origin,body,'abc')[0]

    def test_existing_house_floors_and_bedrooms(self):
        v=self.values('Bán nhà 3 tầng kiệt ô tô',body='Công năng 4 phòng ngủ, 3 WC.')
        self.assertEqual(v['floors_claim'],3)
        self.assertEqual(v['rooms_completed'],4)
        self.assertEqual(v['access_claim'],'alley')

    def test_tower_floors_not_house_floors(self):
        v=self.values('Căn hộ 2PN tầng 12',body='Tòa nhà 30 tầng.',category='Căn hộ chung cư')
        self.assertEqual(v['rooms_completed'],2)
        self.assertEqual(v['floors_claim'],'')

    def test_future_or_nearby_house_not_existing(self):
        for title in ['Đất phù hợp xây nhà 3 tầng 4PN','Lô đất gần nhà 3 tầng 4 phòng ngủ',
                      'Không phải nhà 3 tầng','Dự kiến nhà 3 tầng 4 phòng ngủ']:
            v=self.values(title)
            self.assertEqual(v['floors_claim'],'',title)
            self.assertEqual(v['rooms_completed'],'',title)

    def test_price_changes_do_not_change_features(self):
        a=self.values('Bán nhà 3 tầng kiệt 59, 2PN, giá 3,9 tỷ')
        b=self.values('Bán nhà 3 tầng kiệt 59, 2PN, giá 35 tỷ')
        for field in f.FEATURES:self.assertEqual(a[field],b[field])

    def test_alley_number_and_street_name_are_not_floors(self):
        v=self.values('Bán nhà kiệt 266 Trường Chinh, ngang 5m')
        self.assertEqual(v['floors_claim'],'')
        self.assertEqual(v['rooms_completed'],'')
        self.assertEqual(self.values('Bán nhà đường Võ Văn Kiệt')['access_claim'],'')

    def test_near_frontage_is_not_frontage(self):
        self.assertEqual(self.values('Nhà kiệt cách mặt tiền 20m')['access_claim'],'alley')
        self.assertEqual(self.values('Nhà gần mặt tiền đường')['access_claim'],'')
        self.assertEqual(self.values('Không phải nhà trong kiệt')['access_claim'],'')

    def test_parcel_frontage_width_is_not_street_frontage(self):
        self.assertEqual(self.values('Nhà có mặt tiền 5m')['access_claim'],'')
        self.assertEqual(self.values('Bán nhà mặt tiền đường Nguyễn Văn Linh')['access_claim'],'frontage')

    def test_conflicting_access_is_unknown(self):
        self.assertEqual(self.values('Nhà mặt tiền đường, có kiệt phía sau')['access_claim'],'')

    def test_rental_units_not_bedrooms(self):
        v=self.values('Bán nhà 2 tầng kèm 6 phòng trọ',body='Nhà gồm 8PN.')
        self.assertEqual(v['rooms_completed'],'')
        self.assertEqual(v['floors_claim'],'')

    def test_per_floor_rooms_not_summed_or_total(self):
        v=self.values('Nhà 3 tầng',body='Công năng 4PN. Tầng 1: 1PN. Tầng 2: 2PN.')
        self.assertEqual(v['rooms_completed'],4)
        self.assertEqual(self.values('Nhà 3 tầng 2-3PN')['rooms_completed'],'')

    def test_footer_not_asset_claim(self):
        v=self.values('Bán đất đẹp',body='Liên hệ môi giới nhà 4 tầng 3PN, biệt thự, nhà mặt tiền đường.')
        self.assertEqual(v['rooms_completed'],'')
        self.assertEqual(v['floors_claim'],'')
        self.assertEqual(v['house_subtype_claim'],'')

    def test_structured_bedrooms_not_overwritten_by_conflict(self):
        v=self.values('Nhà 3 tầng 4PN',rooms='3')
        self.assertEqual(v['rooms_completed'],3)
        self.assertIn('rooms_completed',v['conflict_fields'])

    def test_title_body_conflict_without_structure_is_unknown(self):
        v=self.values('Nhà 3 tầng 4PN',body='Nhà 2 tầng 3PN.')
        self.assertEqual(v['rooms_completed'],'')
        self.assertEqual(v['floors_claim'],'')

    def test_subtype_is_existing_house_not_development_plan(self):
        self.assertEqual(self.values('Bán biệt thự 3 tầng')['house_subtype_claim'],'villa')
        self.assertEqual(self.values('Bán nhà cấp 4')['house_subtype_claim'],'house_c4')
        self.assertEqual(self.values('Đất phù hợp xây biệt thự')['house_subtype_claim'],'')
        self.assertEqual(self.values('Bán đất biệt thự',category='Đất nền')['house_subtype_claim'],'')
        self.assertEqual(self.values('Nhà đẹp tại khu biệt thự')['house_subtype_claim'],'')
        self.assertEqual(self.values('Nhà kiên cố',body='Tiềm năng xây căn hộ, khách sạn hoặc biệt thự cho thuê.')['house_subtype_claim'],'')

    def test_evidence_points_to_original_text(self):
        row,origin,body=self.sample('Nhà 3 tầng',body='Công năng 4 phòng ngủ.')
        _,e=f.extract(row,origin,body,'body_hash')
        proof=next(x for x in e if x['field']=='rooms_completed')
        self.assertIn(proof['source_quote'],body)
        self.assertEqual(proof['source_sha256'],'body_hash')

    def test_control_encoding_exact_and_new_features_have_no_price(self):
        row,origin,body=self.sample('Nhà 3 tầng 2PN')
        features={row['record_key']:f.extract(row,origin,body)[0]}
        spec=f.feature_spec([row],row['category'],'control')
        np.testing.assert_allclose(f.encode([row],features,spec),c.encode([row],c.schema([row])),equal_nan=True)
        new=f.feature_spec([row],row['category'],'all')
        matrix=f.encode([row],features,new)
        self.assertEqual(matrix.shape[1],len(new['feature_names']))
        self.assertFalse(any('price' in name or 'title' in name or 'record_key' in name for name in new['feature_names']))


if __name__=='__main__':unittest.main()
