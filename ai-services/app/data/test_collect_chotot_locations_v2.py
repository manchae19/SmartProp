import tempfile
import unittest
from pathlib import Path

import collect_chotot_locations_v2 as c


class LocationCaptureTests(unittest.TestCase):
    def item(self,**extra):
        return dict(list_id=123,category=1020,region_v2=3017,region_name='Đà Nẵng',type='s',
                    price=2_000_000_000,size=60,subject='Nhà đường A',**extra)

    def test_source_optional_text_preserved_without_approving_location(self):
        item=self.item(body='Nhà trong kiệt\nDiện tích 60m2.',address='12/3 đường A')
        record,_=c.legacy.normalize(item,'old_time')
        result=c.capture(item,record,{'file':'source.json'})
        self.assertEqual(result['description_raw'],item['body'])
        self.assertEqual(result['address_detail_raw'],item['address'])
        self.assertFalse(result['model_feature_approved'])
        self.assertFalse(result['location_verified'])

    def test_no_description_fabricated_from_title_or_ward(self):
        item=self.item()
        record,_=c.legacy.normalize(item,'old_time')
        result=c.capture(item,record,{})
        self.assertEqual(result['description_raw'],'')
        self.assertEqual(result['address_detail_raw'],'')

    def test_identity_mismatch_rejected(self):
        item=self.item()
        record,_=c.legacy.normalize(item,'old_time')
        record['source_listing_id']='124'
        with self.assertRaises(ValueError):
            c.capture(item,record,{})

    def test_resume_duplicate_does_not_erase_old_field_evidence(self):
        state=dict(records={},version=2,next_offset=0)
        c.ingest(state,self.item(body='Source description'),{'file':'first'})
        c.ingest(state,self.item(),{'file':'second'})
        self.assertEqual(len(state['records']),1)
        self.assertEqual(state['records']['chotot:123']['description_raw'],'Source description')
        self.assertEqual(state['records']['chotot:123']['location_field_evidence']['description_raw'],{'file':'first'})
        with tempfile.TemporaryDirectory() as directory:
            c.commit(Path(directory),state)
            self.assertEqual(len((Path(directory)/'records.jsonl').read_text(encoding='utf-8').splitlines()),1)


if __name__=='__main__':
    unittest.main()
