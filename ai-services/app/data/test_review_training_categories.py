import json
import unittest
from review_training_categories import decide


class CategoryReviewTests(unittest.TestCase):
    def row(self,title,source='Nhà đất thổ cư',category='Đất nền'):
        return dict(title=title,category=category,raw_json=json.dumps(dict(source_category=source)))

    def test_broad_source_explicit_land(self):
        self.assertEqual(decide(self.row('Bán đất mặt tiền đường lớn'))[:2],('keep','Đất nền'))

    def test_house_source_land_conflict_stays_pending(self):
        self.assertEqual(decide(self.row('Bán đất mặt tiền đường lớn','Nhà mặt phố'))[0],'pending')

    def test_existing_building_not_silently_land(self):
        for title in ['Đất có nhà Lý Văn Tố','Bán đất tặng 2 nhà mặt tiền','Đất vàng phố biển sẵn nhà']:
            self.assertEqual(decide(self.row(title))[0],'pending')

    def test_source_prefix_not_house_evidence(self):
        self.assertEqual(decide(self.row('Bán nhà riêng: Quỹ đất gần biển','ban-nha-rieng','Nhà ở'))[0],'pending')

    def test_commercial_and_project_ads(self):
        self.assertEqual(decide(self.row('Bán dãy trọ 12 phòng'))[0],'exclude')
        self.assertEqual(decide(self.row('Mở bán biệt thự khu đô thị','Nhà biệt thự, liền kề','Nhà ở'))[0],'pending')

    def test_clear_house_and_partial_payment(self):
        self.assertEqual(decide(self.row('Bán nhà 3 tầng mới','Nhà đất thổ cư','Nhà ở'))[:2],('keep','Nhà ở'))
        self.assertEqual(decide(self.row('Chỉ 30% vốn hôm nay sở hữu nhà','Nhà biệt thự, liền kề','Nhà ở'))[0],'pending')


if __name__=='__main__':unittest.main()
