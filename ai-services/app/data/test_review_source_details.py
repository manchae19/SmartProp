"""Safety boundaries for evidence parsing and automatic source decisions."""
import unittest
from review_source_details import parse_detail, decide, description_pairs


class SourceReviewTests(unittest.TestCase):
    def setUp(self):
        self.row=dict(source='cafeland',source_listing_id='3168536',
            detail_url='https://nhadat.cafeland.vn/ban-dat-3168536.html',
            title='Bán đất ở Đà Nẵng',price_million='5000',area_sqm='100',
            district='',category='Khác',review_decision='')
        self.meta=dict(http_status=200,state='downloaded',response_url=self.row['detail_url'])
        self.body='''<html><div class="detail-property"><h1>Bán đất ở Đà Nẵng</h1>
            <div class="col-item"><span class="infor-note">Giá bán</span><b class="infor-data">5 tỷ</b></div>
            <div class="col-item"><span class="infor-note">Diện tích</span><b class="infor-data">100m2</b></div>
            <div class="infor">Vị trí: <a href="/nha-dat-ban/ban-dat-tho-cu-tai-da-nang/">Đà Nẵng</a></div>
            <div class="reals-description">Bán lô đất 100m2, giá 5 tỷ, sổ đỏ riêng.</div></div>
            <div class="reals-description">Bán 3 căn hộ chỉ từ 500 triệu</div>
            <div class="col-item"><span class="infor-note">Giá bán</span><b class="infor-data">1 tỷ</b></div>
            </html>'''.encode('utf-8')

    def evidence(self):
        return parse_detail(self.row,self.meta,self.body)

    def test_related_listings_are_not_asset_evidence(self):
        e=self.evidence()
        self.assertTrue(e['identity_verified'] and e['structure_verified'])
        self.assertEqual(e['price_million'],5000)
        self.assertNotIn('3 căn hộ',e['description'])
        self.assertEqual(decide(self.row,e),('correct','Đất nền',[]))

    def test_redirect_to_another_id_cannot_validate(self):
        self.meta['response_url']='https://nhadat.cafeland.vn/ban-dat-999999.html'
        self.assertFalse(self.evidence()['identity_verified'])

    def test_wrong_title_and_multiple_containers_fail_closed(self):
        self.row['title']='Căn hộ mặt biển bàn giao cao cấp'
        self.assertFalse(self.evidence()['identity_verified'])
        self.row['title']='Bán đất ở Đà Nẵng'
        self.body=self.body.replace(b'</html>',b'<div class="detail-property"></div></html>')
        self.assertFalse(self.evidence()['identity_verified'])

    def test_changed_price_remains_proposal_not_automatic_correction(self):
        self.row['price_million']='4900'
        decision,_,flags=decide(self.row,self.evidence())
        self.assertEqual(decision,'pending')
        self.assertIn('current_price_differs_from_collected_snapshot',flags)
        self.assertEqual(self.row['price_million'],'4900')

    def test_financing_inventory_mixed_and_title_price_remain_pending(self):
        for statement,code in (
            ('Thanh toán 30% nhận nhà','partial_or_starting_price_context'),
            ('Bán 2 lô biệt thự','multiple_assets_or_inventory_context'),
            ('Còn 4 lô liền kề','multiple_assets_or_inventory_context'),
            ('Đất tặng nhà 2 tầng','mixed_land_and_building_context'),
            ('Giá 4 tỷ','description_total_price_needs_review')):
            with self.subTest(statement=statement):
                e=self.evidence();e['description']+=' '+statement
                self.assertEqual(decide(self.row,e)[0],'pending')
                self.assertIn(code,decide(self.row,e)[2])
        e=self.evidence();self.row['title']+=' giá 4 tỷ'
        self.assertIn('description_total_price_needs_review',decide(self.row,e)[2])

    def test_ambiguous_and_prior_pending_cannot_be_auto_approved(self):
        e=self.evidence();e.update(category='',source_category='Nhà đất thổ cư',description='Đất có nhà cấp 4')
        self.assertEqual(decide(self.row,e)[0],'pending')
        e=self.evidence();self.row['review_decision']='pending'
        self.assertIn('prior_pending_requires_explicit_resolution',decide(self.row,e)[2])

    def test_source_villa_category_cannot_turn_vacant_land_into_house(self):
        e=self.evidence();e.update(category='Nhà ở',source_category='Nhà biệt thự, liền kề',
                                  description='Đất biệt thự mặt tiền, diện tích đất 100m2, giá 5 tỷ')
        self.row['title']='Đất đẹp mặt tiền Đà Nẵng'
        self.assertIn('source_category_content_conflict',decide(self.row,e)[2])
        self.assertEqual(decide(self.row,e)[0],'pending')

    def test_nearby_apartment_or_future_building_is_not_unit_for_sale(self):
        e=self.evidence();e.update(category='',source_category='Nhà đất thổ cư',
            description='Chính chủ gửi bán đường 7,5m, kề bên chung cư Hòa Xuân, giá 5 tỷ')
        self.row['title']='Chính chủ gửi bán đường trung tâm'
        self.assertEqual(decide(self.row,e)[0],'pending')
        self.assertNotEqual(decide(self.row,e)[1],'Căn hộ chung cư')
        self.row['title']='Nhà C4 gác lửng kiệt ô tô'
        e['description']='Nhà C4 có gác lửng, phù hợp xây căn hộ, diện tích 100m2, giá 5 tỷ'
        self.assertEqual(decide(self.row,e),('correct','Nhà ở',[]))

    def test_project_overview_is_not_a_specific_apartment(self):
        e=self.evidence();e.update(category='Căn hộ chung cư',source_category='ban-can-ho-chung-cu',
            description='Tổng quan dự án SUN PONTE. Chính sách bán hàng và bảng giá mới nhất. Đăng ký thông tin.')
        self.row['title']='SUN PONTE RESIDENCE mặt sông Hàn'
        self.assertIn('project_marketing_requires_specific_asset',decide(self.row,e)[2])
        self.assertEqual(decide(self.row,e)[0],'pending')

    def test_commercial_asset_is_not_saved_by_an_ordinary_source_category(self):
        e=self.evidence()
        self.row['title']='Bán nhà shophouse mặt tiền Đà Nẵng'
        self.assertEqual(decide(self.row,e)[0],'exclude')
        self.row['title']='Bán căn hộ Đà Nẵng'
        e.update(category='Căn hộ chung cư',source_category='ban-can-ho-chung-cu',
                 description='Căn hộ condotel diện tích 100m2, giá 5 tỷ')
        self.assertEqual(decide(self.row,e)[0],'pending')

    def test_unsupported_category_requires_verified_identity(self):
        e=self.evidence();e.update(category='Khác',source_category='ban-dat-nong-lam-nghiep')
        self.assertEqual(decide(self.row,e)[0],'exclude')
        e['identity_verified']=False
        self.assertEqual(decide(self.row,e)[0],'pending')

    def test_whole_building_and_range_never_become_ordinary_house(self):
        for statement in ('Tòa căn hộ 6 tầng 14 phòng', 'Có sẵn dãy nhà trọ',
                          'Diện tích: 300 - 400m²', 'Giá chỉ 5,x tỷ', 'Giá chỉ 1tyxx',
                          'Giá chỉ 8xx triệu', 'Giá chỉ 4.x t.ỷ', 'Gồm 14 căn hộ'):
            e=self.evidence();e['description']+=' '+statement
            self.assertEqual(decide(self.row,e)[0],'pending',statement)
        e=self.evidence();self.row['pipeline_review_codes']='special_or_whole_building'
        self.assertEqual(decide(self.row,e)[0],'pending')
        self.row.pop('pipeline_review_codes')
        e=self.evidence()
        self.row['title']='Chỉ 4.x nhỏ sở hữu lô đất'
        self.assertIn('description_price_or_area_range',decide(self.row,e)[2])

    def test_source_approval_preserves_financial_and_date_gates(self):
        from filter_all_collected import classify
        row=dict(self.row,record_key='cafeland:3168536',review_codes='category_unresolved;partial_starting_or_booking_title',
            category='Chưa xác định',category_basis='unresolved',raw_json='{}',
            transaction_verified='True',geographic_scope_status='accepted_da_nang',displayed_date='',
            address_raw='Đà Nẵng',title_money_evidence='[]')
        review=dict(decision='correct',decision_file='new_source_review',cache_valid=True,
            original_price_million='5000',original_area_sqm='100',detail_sha256='a'*64,
            reviewer='source_detail_rules_not_manual_verification',source_identity_verified='True',
            category_evidence_validated='True',reviewed_category='Đất nền',review_codes='')
        r=classify(row,review)
        self.assertEqual(r['category'],'Đất nền')
        self.assertEqual(r['original_category'],'Chưa xác định')
        self.assertEqual(r['price_million'],'5000')
        self.assertNotIn('unsupported_category',r['pipeline_review_codes'])
        self.assertIn('partial_starting_or_booking_title',r['pipeline_review_codes'])
        self.assertIn('listing_date_unavailable',r['pipeline_review_codes'])
        self.assertEqual(r['pipeline_status'],'needs_review')
        review['source_identity_verified']='False'
        with self.assertRaises(RuntimeError):
            classify(row,review)

    def test_new_apartment_category_is_screened_again_for_price_outliers(self):
        from filter_all_collected import classify
        row=dict(self.row,record_key='cafeland:3168536',review_codes='category_unresolved',
            category='Chưa xác định',category_basis='unresolved',raw_json='{}',
            price_million='300',area_sqm='50',transaction_verified='True',
            geographic_scope_status='accepted_da_nang',displayed_date='2026-10-11',
            address_raw='Đà Nẵng',title_money_evidence='[]')
        review=dict(decision='correct',decision_file='new_source_review',cache_valid=True,
            original_price_million='300',original_area_sqm='50',detail_sha256='a'*64,
            reviewer='source_detail_rules_not_manual_verification',source_identity_verified='True',
            category_evidence_validated='True',reviewed_category='Căn hộ chung cư',review_codes='')
        result=classify(row,review)
        self.assertEqual(result['category'],'Căn hộ chung cư')
        self.assertIn('apartment_price_priority',result['pipeline_review_codes'])
        self.assertEqual(result['pipeline_status'],'needs_review')

    def test_descriptive_area_labels_and_dimensions_are_checked(self):
        for description in ('DT khủng 90m2','Diện tích tối ưu: 90m²','DT: 5 x 18m'):
            e=self.evidence();e['description']=description+' giá 5 tỷ'
            self.assertEqual(decide(self.row,e)[0],'pending',description)
        e=self.evidence();e['description']='Bán đất DT: 5 x 20m, giá 5 tỷ'
        self.assertEqual(decide(self.row,e)[0],'correct')

    def test_nearby_condotel_does_not_exclude_land(self):
        self.row['title']='Bán đất gần condotel Đà Nẵng'
        self.assertNotEqual(decide(self.row,self.evidence())[0],'exclude')

    def test_nhadat_category_and_source_utf8(self):
        row=dict(self.row,source='nhadat24h',source_listing_id='4382452',
                 detail_url='https://nhadat24h.net/ban-dat-ID4382452')
        meta=dict(self.meta,response_url=row['detail_url'])
        body='''<h1 id="txtcontenttieudetin">Bán đất ở Đà Nẵng</h1>
            <span id="lbGiaDienTich">Cần bán: 5 tỷ - 100 m²</span>
            <span id="lbLoaiBDS">Nhà đất thổ cư</span>
            <div class="sub1detailmaincontent"><div>Bán đất 100m2 giá 5 tỷ</div></div>
            <div class="dv-breadcrumb"><a>Đà Nẵng</a></div>'''.encode('utf-8')
        e=parse_detail(row,meta,body)
        self.assertTrue(e['identity_verified'] and e['structure_verified'])
        self.assertEqual(decide(row,e)[1],'Đất nền')

    def test_homedy_and_alonhadat_scope_price_to_selected_property(self):
        row=dict(self.row,source='homedy',source_listing_id='1234567',
                 detail_url='https://homedy.com/ban-dat-es1234567')
        meta=dict(self.meta,response_url=row['detail_url'])
        body='''<ul><li><label>Giá</label><strong>1 tỷ</strong></li></ul>
            <div class="product-item"><div><h1>Bán đất ở Đà Nẵng</h1><div class="address">Đà Nẵng</div></div>
            <ul><li><label>Giá</label><strong>5 tỷ</strong></li>
            <li><label>Diện tích</label><strong>100 m2</strong></li></ul>
            <div class="product-attributes--item"><span>Loại hình</span><span>Đất nền dự án</span></div>
            <div class="description">Bán đất 100m2 giá 5 tỷ</div></div>
            <div class="description">Bán 2 căn nhà giá từ 1 tỷ</div>'''.encode('utf-8')
        e=parse_detail(row,meta,body)
        self.assertTrue(e['structure_verified'])
        self.assertEqual(e['price_million'],5000)
        self.assertNotIn('2 căn',e['description'])
        row.update(source='alonhadat',source_listing_id='12345678',
                   detail_url='https://alonhadat.com.vn/ban-dat-12345678.html')
        meta['response_url']=row['detail_url']
        body='''<div class="more-info"><b itemprop="price">1 tỷ</b></div>
            <main class="property"><input id="hddPropertyId" value="12345678">
            <h1>Bán đất ở Đà Nẵng</h1><div class="more-info"><b itemprop="price">5 tỷ</b>
            <b itemprop="floorSize">100 m²</b></div><div class="moreinfor1"><table>
            <tr><td>Loại BDS</td><td>Đất thổ cư, đất ở</td><td>Loại tin</td><td>Cần bán</td></tr>
            </table></div><section class="text-content"><div itemprop="description">Bán đất 100m2 giá 5 tỷ</div></section>
            <address itemprop="address">Đà Nẵng</address></main>'''.encode('utf-8')
        e=parse_detail(row,meta,body)
        self.assertTrue(e['structure_verified'] and e['identity_verified'])
        self.assertEqual(e['price_million'],5000)

    def test_description_bridges_require_distinctive_content_and_agreeing_numbers(self):
        rows=[dict(self.row,record_key='cafeland:1'),dict(self.row,record_key='cafeland:2')]
        e=self.evidence()
        parsed={r['record_key']:dict(e,description='Bán đất đẹp giá tốt') for r in rows}
        self.assertEqual(description_pairs(rows,parsed),[])
        for v in parsed.values():v['description']=' '.join('detail'+str(i) for i in range(90))
        self.assertEqual(len(description_pairs(rows,parsed)),1)
        rows[1]['area_sqm']='130'
        self.assertEqual(description_pairs(rows,parsed),[])


if __name__=='__main__':
    unittest.main()
