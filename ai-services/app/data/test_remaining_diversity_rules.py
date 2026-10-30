import json
import unittest
import remaining_diversity_rules as rules
import training_v3_common as c


class AdmissionTests(unittest.TestCase):
    def sample(self,body,title='Bán nhà 3 tầng',p=3950):
        row=dict(source='cafeland',title=title,category='Nhà ở',price_million=str(p),area_sqm='60',
                 district='',pipeline_review_codes='saved_source_review_pending',review_decision='pending')
        e=dict(identity_verified=True,structure_verified=True,sale_verified=True,source_category='ban-nha-rieng',
               category='Nhà ở',price_million=p,area_sqm=60,address_raw='Đà Nẵng',flags=[],
               description=body,asset_description=body,price_raw=f'{p/1000} tỷ')
        return row,e

    def test_two_digit_price_requires_matching_header(self):
        row,e=self.sample('Bán nhà 3 tầng. DT 60m2. Giá 3 tỷ 95.')
        self.assertEqual(rules.evaluate(row,e)['decision'],'keep')
        e['price_million']=3900
        self.assertEqual(rules.evaluate(row,e)['decision'],'pending')

    def test_shorthand_never_consumes_area_or_explicit_millions(self):
        for text in ['3 tỷ 95m2','3 tỷ 95 triệu','3 tỷ 95 x','3 tỷ 95.5','3 tỷ 9x']:
            with self.subTest(text=text):
                self.assertEqual(rules.shorthand(text,3950)[1],[])

    def test_markdown_is_only_formatting(self):
        row,e=self.sample('**Bán nhà 3 tầng**. **Diện tích: 60m2**. **Giá: 3,95 tỷ**.')
        self.assertEqual(rules.evaluate(row,e)['decision'],'keep')
        e['description']=e['asset_description']='**Bán nhà 3 tầng**. **Diện tích: 70m2**. **Giá: 3,95 tỷ**.'
        self.assertEqual(rules.evaluate(row,e)['decision'],'pending')

    def test_masked_price_not_approved_by_unrelated_footer_fix(self):
        for text in ['Giá 3ty9x','Giá 3.9x tỏi','Giá 3.xx tỷ']:
            row,e=self.sample('Bán nhà 3 tầng. DT 60m2. '+text+'. Liên hệ môi giới.')
            self.assertEqual(rules.evaluate(row,e)['decision'],'pending')

    def test_future_special_asset_has_to_be_explicit(self):
        row,e=self.sample('Bán nhà 3 tầng. DT 60m2. Giá 3,95 tỷ. Thích hợp xây tòa căn hộ cao cấp.')
        self.assertEqual(rules.evaluate(row,e)['decision'],'keep')
        e['description']=e['asset_description']='Bán nhà 3 tầng. DT 60m2. Giá 3,95 tỷ. Hiện có tòa căn hộ cao cấp.'
        self.assertEqual(rules.evaluate(row,e)['decision'],'pending')

    def test_future_clause_does_not_hide_an_actual_special_asset(self):
        self.assertEqual(rules.future_only_special('Thích hợp xây tòa căn hộ. Hiện có dãy trọ.'),[])

    def test_footer_does_not_prove_house(self):
        row,e=self.sample('Lô đất. Liên hệ tư vấn nhà kiên cố, biệt thự 4 tầng.')
        self.assertIsNone(rules.asset_proof(e))
        self.assertEqual(rules.evaluate(row,e)['decision'],'pending')

    def test_nearby_house_does_not_prove_subject(self):
        row,e=self.sample('Lô đất gần nhà kiên cố. Giá 3,95 tỷ.')
        self.assertIsNone(rules.asset_proof(e))

    def test_price_area_identity_structure_and_sale_gates(self):
        for field in ['identity_verified','structure_verified','sale_verified']:
            row,e=self.sample('Bán nhà 3 tầng. Giá 3 tỷ 95. DT 60m2.')
            e[field]=False
            self.assertEqual(rules.evaluate(row,e)['decision'],'pending')

    def test_rental_yield_requires_sale_header_and_complete_source_check(self):
        row,e=self.sample('Bán nhà 3 tầng. DT 60m2. Giá bán 3,95 tỷ. Đang cho thuê 10 triệu/tháng. Liên hệ chủ.',
                          title='Bán nhà 3 tầng đang cho thuê 10 triệu/tháng')
        result=rules.evaluate(row,e)
        self.assertIsNotNone(rules.sale_with_rental_context(row,e,result))
        e['sale_verified']=False
        self.assertIsNone(rules.sale_with_rental_context(row,e,result))
        self.assertIsNone(rules.sale_with_rental_context(row,e,dict(decision='pending')))

    def test_multiple_self_contained_units_not_rescued_by_markdown(self):
        row,e=self.sample('Bán nhà 3 tầng gồm 8 căn phòng kép kín. Giá 3,95 tỷ. #nhadat')
        self.assertEqual(rules.evaluate(row,e)['decision'],'pending')

    def test_real_cached_replays(self):
        root=c.PROCESSED/'remaining_3752_review'
        run=root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']
        rows={r['record_key']:r for r in c.read(run/'all_listings_after_review.csv')}
        evidence=json.loads((c.PROCESSED/'collection_source_review/parsed_evidence.json').read_text(encoding='utf-8'))
        expected={'cafeland:3144978':'keep','cafeland:3145041':'pending','cafeland:3145202':'keep',
                  'homedy:2293329':'keep','cafeland:3154274':'pending','homedy:2896718':'pending',
                  'cafeland:2485950':'pending','cafeland:3145053':'pending',
                  'cafeland:3155058':'pending','cafeland:3163843':'pending','nhadat24h:4395419':'pending'}
        for key,decision in expected.items():
            with self.subTest(key=key):
                self.assertEqual(rules.evaluate(rows[key],evidence[key])['decision'],decision)

    def test_reposted_long_prose_matches_without_ordinal(self):
        text=' '.join('word'+str(i) for i in range(65))
        _,a=self.sample(text)
        _,b=self.sample('51 '+text)
        self.assertEqual(rules.description_signature(a),rules.description_signature(b))
        b['identity_verified']=False
        self.assertEqual(rules.description_signature(b),'')

    def test_content_link_to_reserved_group_blocks_new_train_candidate(self):
        from filter_remaining_diversity import guard_cross_group_content
        text=' '.join('word'+str(i) for i in range(65))
        _,e=self.sample(text)
        new=dict(record_key='new:1',pipeline_status='eligible',pipeline_group='a',pipeline_review_codes='',reserved_splits='train')
        reserved=dict(record_key='old:2',pipeline_status='eligible',pipeline_group='b',pipeline_review_codes='',reserved_splits='test')
        original={'new:1':dict(new,pipeline_status='needs_review'),'old:2':dict(reserved)}
        links=guard_cross_group_content([new,reserved],original,{'new:1':e,'old:2':dict(e,description='51 '+text,asset_description='51 '+text)})
        self.assertEqual(new['pipeline_status'],'needs_review')
        self.assertEqual(reserved,original['old:2'])
        self.assertEqual(len(links),1)
        self.assertEqual(links[0]['other_reserved_splits'],'test')


if __name__=='__main__':
    unittest.main()
