import unittest
from tinix_quality import quality,exact_decimal,canonical,restore_original
from decimal import Decimal

class TinixQualityTests(unittest.TestCase):
    def row(self,**changes):
        return dict(name='Bán nhà tại Hải Châu',description='Chính chủ cần bán nhà. Giá bán 2 tỷ. Diện tích 80m2.',price='2000000000',area=80.0,province_name='Đà Nẵng',district_name='Hải Châu',ward_name='Hải Châu I',property_type_name='Nhà',**changes)
    def test_exact_original_price_no_float(self):
        self.assertEqual(exact_decimal('2350000001',2,24),Decimal('2350000001'))
        self.assertEqual(exact_decimal('80.125',6,18),Decimal('80.125'))
        for v in ['nan','Infinity','-1','2 tỷ','0','12.123']:self.assertIsNone(exact_decimal(v,2,24))
    def test_sale_requires_evidence(self):
        r=self.row();r.update(name='Nhà đẹp trung tâm',description='Nhà diện tích 80m2 đầy đủ công năng.')
        self.assertEqual(quality(r)['transaction_type'],'UNKNOWN')
        self.assertNotEqual(quality(r)['quality_status'],'HYBRID_ELIGIBLE_RESEARCH')
    def test_rental_never_becomes_sale(self):
        r=self.row();r.update(name='Cho thuê nhà Hải Châu',price='12000000',description='Cho thuê giá 12 triệu/tháng')
        self.assertEqual(quality(r)['transaction_type'],'RENT');self.assertEqual(quality(r)['quality_status'],'EXCLUDED')
    def test_baseline_sale_and_ambiguities(self):
        self.assertEqual(quality(self.row())['quality_status'],'HYBRID_ELIGIBLE_RESEARCH')
        for text,flag in [('Giá bán 3 tỷ','EXPLICIT_PRICE_CONFLICT'),('Chỉ cần trả trước 500 triệu','PARTIAL_PRICE_CONTEXT'),('Bán 2 lô đất','MULTIPLE_ASSETS'),('Diện tích 60m2','EXPLICIT_AREA_CONFLICT')]:
            r=self.row();r['description']+=' '+text
            self.assertIn(flag,quality(r)['quality_issues'])
    def test_no_invented_area_transaction_or_geography(self):
        r=self.row();r.update(area=None,district_name=None,price=None)
        q=quality(r);self.assertIsNone(q['area_sqm']);self.assertIsNone(q['district']);self.assertIsNone(q['price_vnd'])
    def test_extra_raw_fields_preserved(self):
        import json
        row=self.row();row['new_field']={'source':'kept','coordinate':None}
        self.assertEqual(json.loads(canonical(row)),row)
    def test_mysql_json_normalization_is_losslessly_reconstructed_and_corruption_rejected(self):
        value=7.5600000000000005
        self.assertEqual(restore_original({'frontage_width':7.56},{'frontage_width':value.hex()})['frontage_width'].hex(),value.hex())
        for wrong in [7.55,None,'7.56']:
            with self.assertRaises(ValueError):restore_original({'frontage_width':wrong},{'frontage_width':value.hex()})
if __name__=='__main__':unittest.main()
