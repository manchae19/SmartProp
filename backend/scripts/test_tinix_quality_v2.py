import unittest
from tinix_quality_v2 import evaluate,prices,assets

class TinixV2Tests(unittest.TestCase):
    def row(self,title='Bán lô đất 100m2',description='Giá bán 1 tỷ 150.',price='1150000000',area=100):
        return dict(name=title,description=description,price=price,area=area)
    def test_single_asset_and_future_building_not_portfolio(self):
        for text in ['Bán 1 lô đất diện tích 100m2','Bán 1 căn nhà 100m2','Đất xây được 2 căn nhà','Đất có thể xây 5 căn nhà','Nhà cách ô tô chỉ 1 căn nhà']:
            flags,reasons,_=assets(self.row(description=text),True)
            self.assertNotIn('MULTIPLE_ASSETS',flags,text);self.assertFalse(flags,text)
    def test_counts_and_blocks_remain_review_no_splitting(self):
        for text in ['Bán 2 lô đường A','Bán 5 lô đất','Bán 7lô đường A','Bán 30 lô','Bán cả block dự án','Giỏ hàng nhiều căn','Đã xây 2 căn nhà để bán']:
            result=evaluate(self.row(title=text),[], 'HYBRID_ELIGIBLE_RESEARCH')
            self.assertEqual(result['quality_status'],'NEEDS_REVIEW',text)
            self.assertTrue(result['newly_detected_multi'],text)
    def test_earlier_landmark_does_not_swallow_later_inventory(self):
        r=evaluate(self.row(description='Cách biển 100m, 7 lô đất liền kề giá 1 tỷ 150'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertIn('MULTIPLE_ASSETS',r['quality_issues']);self.assertEqual(r['quality_status'],'NEEDS_REVIEW')
    def test_plot_identifier_not_inventory(self):
        r=evaluate(self.row(description='Bán lô đất block B2.2 lô 23; giá 1 tỷ 150.'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertEqual(r['quality_status'],'HYBRID_ELIGIBLE_RESEARCH');self.assertFalse(r['newly_detected_multi'])
    def test_shorthand_uses_decimal_exact_and_consumes_million_component(self):
        for text,price in [('1 tỷ1','1100000000'),('1 tỷ 150','1150000000'),('2 tỷ 350 triệu','2350000000'),('2 tỷ350tr','2350000000')]:
            r=evaluate(self.row(description='Giá bán '+text,price=price),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
            self.assertEqual(r['quality_status'],'HYBRID_ELIGIBLE_RESEARCH',(text,r))
        r=evaluate(self.row(description='Giá 1 tỷ 150',price='1150000001'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertIn('V2_EXACT_TOTAL_PRICE_CONFLICT',r['quality_issues'])
    def test_short_suffix_requires_independent_text_not_fit_to_numeric_field(self):
        r=evaluate(self.row(description='Giá 6 tỷ 95',price='6950000000'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertEqual(r['quality_status'],'NEEDS_REVIEW')
        r=evaluate(self.row(title='Bán nhà giá 6 tỷ 95',description='Giá bán 6 tỷ 950',price='6950000000'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertEqual(r['quality_status'],'HYBRID_ELIGIBLE_RESEARCH')
    def test_masks_per_lot_per_sqm_and_downpayment_not_totals(self):
        for text in ['Giá 5xx triệu','Giá 7xx triệu/lô','Giá 2 tỷ 7xx triệu','Giá 1 tỷ 150/lô','Giá 11.5 triệu/m2','Trả trước 1 tỷ 150']:
            r=evaluate(self.row(description=text),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
            self.assertEqual(r['quality_status'],'NEEDS_REVIEW',(text,r))
    def test_dimensions_not_masked_price(self):
        r=evaluate(self.row(description='Diện tích 5x20m; Giá 1 tỷ 150'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertEqual(r['quality_status'],'HYBRID_ELIGIBLE_RESEARCH')
    def test_area_per_lot_does_not_invent_a_per_lot_price(self):
        r=evaluate(self.row(description='Một lô 100m2/lô; giá bán 1 tỷ 150'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertEqual(r['quality_status'],'HYBRID_ELIGIBLE_RESEARCH')
    def test_sqm_rate_with_tren_not_a_total(self):
        r=evaluate(self.row(description='Giá 11.5 triệu trên m2'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertEqual(r['quality_status'],'NEEDS_REVIEW')
        self.assertIn('V2_UNIT_PRICE_WITHOUT_EXPLICIT_TOTAL',r['quality_issues'])
    def test_starting_price_not_fixed_total(self):
        r=evaluate(self.row(description='Giá chỉ từ 1 tỷ 150'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertEqual(r['quality_status'],'NEEDS_REVIEW')
        self.assertIn('V2_STARTING_PRICE_NOT_TOTAL',r['quality_issues'])
    def test_year_and_plot_number_are_not_asset_counts(self):
        for text in ['Nhà mới xây 3 năm nhà còn đẹp','Bán đất đường 2 lô góc đẹp']:
            self.assertFalse(assets(self.row(description=text))[0],text)
    def test_proverb_fraction_and_price_suffix_are_not_confirmed_multi(self):
        for text in ['Nhất cận thị nhị cận giang tam cận lộ','Giá bằng 1/2 lô đất khác']:
            self.assertFalse(assets(self.row(description=text))[0],text)
        flags,_,_=assets(self.row(description='Giá 3 tỷ 2 căn 1PN'))
        self.assertNotIn('MULTIPLE_ASSETS',flags);self.assertIn('V2_PRICE_ASSET_BOUNDARY_UNRESOLVED',flags)
    def test_tien_ich_not_billion_and_inventory_singleton_not_confirmed_multi(self):
        flags,_,_=prices(self.row(description='Giá 1 tỷ 150. Có 31 tiện ích.'))
        self.assertFalse(flags)
        flags,_,_=assets(self.row(description='Giỏ hàng CĐT còn một căn đẹp tầng 26'))
        self.assertNotIn('MULTIPLE_ASSETS',flags);self.assertIn('V2_PROJECT_INVENTORY_CONTEXT',flags)
    def test_investment_calendar_rental_abbreviation_and_streams_not_price_risks(self):
        for text in ['Giá đầu tư 1 tỷ 150','Giá 1 tỷ 150, bao quanh bởi 3 dòng sông','Giá 1 tỷ 150. Cho thuê 12tr/th.','Giá 1 tỷ 150. Chốt cọc trước 21/7.']:
            r=evaluate(self.row(description=text),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
            self.assertEqual(r['quality_status'],'HYBRID_ELIGIBLE_RESEARCH',(text,r))
        self.assertFalse(assets(self.row(description='Khai lộc đầu năm cần bán nhà'))[0])
    def test_unknown_raw_price_not_reported_as_exact_conflict(self):
        r=evaluate(self.row(price=None),['MISSING_OR_NONEXACT_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertIn('V2_RAW_PRICE_NOT_COMPARABLE',r['quality_issues']);self.assertNotIn('V2_EXACT_TOTAL_PRICE_CONFLICT',r['quality_issues'])
    def test_money_followed_by_physical_number(self):
        r=evaluate(self.row(title='Bán lô đất 150m2',description='Giá 1 tỷ 150m2',price='1000000000',area=150),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertEqual(r['quality_status'],'HYBRID_ELIGIBLE_RESEARCH')
    def test_sole_shorthand_does_not_hide_new_multiple_lots(self):
        r=evaluate(self.row(title='Bán 7 lô đất',description='Giá 1 tỷ 150'),['SHORTHAND_TOTAL_PRICE'],'NEEDS_REVIEW')
        self.assertIn('MULTIPLE_ASSETS',r['quality_issues']);self.assertEqual(r['quality_status'],'NEEDS_REVIEW')
    def test_unrelated_flags_excluded_holdout_and_raw_values_immutable(self):
        row=self.row();before=row.copy()
        for status,flags,held in [('NEEDS_REVIEW',['EXPLICIT_PRICE_CONFLICT'],False),('EXCLUDED',[],False),('HYBRID_ELIGIBLE_RESEARCH',[],True)]:
            r=evaluate(row,flags,status,held)
            self.assertNotEqual(r['quality_status'],'HYBRID_ELIGIBLE_RESEARCH')
            if flags:self.assertIn(flags[0],r['quality_issues'])
        self.assertEqual(row,before)
    def test_false_multi_reason_does_not_override_real_area_contradiction(self):
        r=evaluate(self.row(title='Bán nhà 86m²',description='Cách ô tô chỉ 1 căn nhà, giá 1 tỷ 150',area=96),['MULTIPLE_ASSETS'],'NEEDS_REVIEW')
        self.assertTrue(r['multi_reason_false_positive']);self.assertIn('V2_TITLE_AREA_CONFLICT',r['quality_issues']);self.assertEqual(r['quality_status'],'NEEDS_REVIEW')
if __name__=='__main__':unittest.main()
