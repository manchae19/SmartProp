import unittest
import holdout_screening_rules as r


class FixedScopeTests(unittest.TestCase):
    def row(self,title,category='Nhà ở'):
        return dict(title=title,category=category,source='cafeland')

    def test_ordinary_house_passes(self):
        self.assertEqual(r.scope_flags(self.row('Bán nhà 3 tầng 4PN kiệt ô tô')),[])

    def test_existing_rental_building_held(self):
        self.assertTrue(r.scope_flags(self.row('Bán nhà riêng: Bán nhà 2 tầng kèm 6 phòng trọ')))

    def test_future_or_nearby_rental_building_not_subject(self):
        for text in ['Bán nhà, thích hợp xây dãy trọ','Bán nhà gần dãy trọ']:
            self.assertEqual(r.scope_flags(self.row(text)),[])

    def test_residential_land_with_garden_not_auto_agricultural(self):
        self.assertEqual(r.scope_flags(self.row('Bán đất ở có sân vườn',category='Đất nền')),[])
        self.assertTrue(r.scope_flags(self.row('Bán đất thổ cư: Bán đất vườn',category='Đất nền')))

    def test_multiple_assets_not_two_frontages(self):
        self.assertTrue(r.scope_flags(self.row('Bán 3 lô đất liền kề',category='Đất nền')))
        self.assertEqual(r.scope_flags(self.row('Bán nhà lô góc 2 mặt tiền')),[])

    def test_starting_payment_held(self):
        self.assertTrue(r.scope_flags(self.row('Nhà 3 tầng trả trước 500 triệu')))

    def test_footer_not_scope_evidence(self):
        e=dict(identity_verified=True,category='Nhà ở',description='Nhà 3 tầng. Liên hệ chuyên bán khách sạn, dãy trọ.')
        self.assertEqual(r.scope_flags(self.row('Bán nhà 3 tầng'),e),[])

    def test_body_duplicates_ignore_advertised_price(self):
        text=' '.join('word'+str(i) for i in range(65))
        a=dict(identity_verified=True,asset_description=text+' Giá 3 tỷ.')
        b=dict(identity_verified=True,asset_description='51 '+text+' Giá 5 tỷ.')
        self.assertEqual(r.body_signature(a),r.body_signature(b))

    def test_short_bodies_do_not_link(self):
        self.assertEqual(r.body_signature(dict(identity_verified=True,description='Nhà đẹp, giá tốt.')),'')


if __name__=='__main__':unittest.main()
