import importlib.util,json,unittest,csv,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('collector',P/'collect_chotot_incremental.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class CollectionTests(unittest.TestCase):
    def sample(self):
        return dict(list_id=123,category=1020,region_v2=3017,region_name='Đà Nẵng',type='s',price=2_000_000_000,size=60,latitude=16.05,longitude=108.2)
    def test_scope(self):
        for field,value in [('type','u'),('category',1030),('region_v2',99),('region_name','Other')]:
            item=self.sample();item[field]=value
            self.assertIsNone(c.normalize(item,'now')[0])
    def test_units_missing_values(self):
        r,_=c.normalize(self.sample(),'now')
        self.assertEqual(r['price_million'],2000)
        self.assertIsNone(r['toilets'])
        self.assertEqual(r['target_type'],'asking_price')
    def test_review_not_silent_correction(self):
        item=self.sample();item['price']=59_000_000;item['latitude']=1000
        r,_=c.normalize(item,'now')
        self.assertEqual(r['price_vnd'],59_000_000)
        self.assertEqual(r['quality_status'],'review')
        self.assertIsNone(r['latitude'])
    def test_legacy_url_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'legacy.csv';p.write_text('detail_url\nhttps://nha.chotot.com/123.htm\n',encoding='utf-8')
            ids,inv=c.read_existing([p]);self.assertEqual(ids,{'123'});self.assertEqual(inv[0]['rows'],1)
if __name__=='__main__':unittest.main()
