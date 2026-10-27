import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect_apartment_followup as job


def fixture():
    url=job.ORIGIN+'/ban-chung-cu/can-ho-thu-nghiem-ID9990001'
    title='Bán căn hộ 55m2 đầy đủ nội thất'
    row=dict(record_key='nhadat24h:9990001',source='nhadat24h',source_listing_id='9990001',detail_url=url,
        listing_title=title,listing_price_raw='2.5 Tỷ',listing_area_raw='55 m²',listing_address_raw='Quận Sơn Trà',
        listing_page=job.START,listing_category_raw='Căn hộ chung cư',listing_rooms='2',listing_date_raw='1 ngày trước.')
    ld=json.dumps({'@type':'Product','name':title,'offers':{'url':url,'price':2500000000,'priceCurrency':'VND'}})
    body=f'''<html><meta charset="utf-8"><script type="application/ld+json">{ld}</script>
    <h1 id="txtcontenttieudetin">{title}</h1><label id="ctl_lbGiaDienTich">Cần bán:2.5 Tỷ -55M²</label>
    <label id="ctl_lbLoaiBDS">Căn hộ chung cư</label><label id="ctl_lbTinhThanh">Phường An Hải, Quận Sơn Trà, Đà Nẵng</label>
    <input id="txtLoaiTin" value="1"><input id="txtNgaydang" value="27/10/2026, lúc: 9 giờ 54 phút">
    <div class="sub1detailmaincontent"><div>Căn hộ 55m2 giá bán 2,5 tỷ. Có hai phòng ngủ và đầy đủ nội thất.</div><div>Thông tin người đăng không phải mô tả</div></div></html>'''
    return body.encode(),row


class FollowupCollectorTest(unittest.TestCase):
    def test_identity_total_price_date_and_description_boundary(self):
        body,row=fixture();out=job.parse_detail(body,row,'2026-10-28T00:00:00Z')
        self.assertEqual((out['price_million'],out['area_sqm']),(2500,55))
        self.assertEqual(out['source_published_date'],'2026-10-27')
        self.assertNotIn('người đăng',out['description']);self.assertEqual(out['source_evidence_flags'],[])

    def test_wrong_product_url_cannot_be_saved_as_this_id(self):
        body,row=fixture();row['detail_url']=job.ORIGIN+'/other-ID9990002'
        with self.assertRaises(ValueError):job.parse_detail(body,row,'2026-10-27T00:00:00Z')

    def test_page_without_product_remains_identity_and_currency_review(self):
        body,row=fixture()
        import re
        body=re.sub(b'<script.*?</script>',b'',body)
        out=job.parse_detail(body,row,'2026-10-27T00:00:00Z')
        self.assertIn('missing_jsonld_product_identity',out['source_evidence_flags'])
        self.assertIn('currency_unverified',out['source_evidence_flags'])

    def test_listing_detail_price_mismatch_is_not_relabelled(self):
        body,row=fixture();row['listing_price_raw']='1 Tỷ'
        out=job.parse_detail(body,row,'2026-10-27T00:00:00Z')
        self.assertEqual(out['price_million'],2500)
        self.assertIn('listing_detail_price_mismatch',out['source_evidence_flags'])

    def test_relative_or_invalid_source_date_is_never_collection_date(self):
        body,row=fixture();body=body.replace(b'27/10/2026',b'32/10/2026')
        out=job.parse_detail(body,row,'2026-10-27T00:00:00Z')
        self.assertEqual(out['source_published_date'],'');self.assertIn('missing_or_invalid_source_date',out['source_evidence_flags'])

    def test_checkpoint_interrupt_resumes_without_duplicate_or_network(self):
        body,row=fixture()
        class FakeClient:
            def __init__(self,*args):pass
            def fetch(self,url):return (b'listing' if url==job.START else body),200
        job.OUT.parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=job.OUT.parent,prefix='followup-test-') as directory:
            output=Path(directory);args=['collector','--target','1','--output',str(output)]
            history=output/'history.csv';history.write_text('record_key\nold:1\n',encoding='utf8')
            pilot=output/'pilot';pilot.mkdir();(pilot/'records.jsonl').write_text('',encoding='utf8')
            atomic=job.common.atomic
            def interrupt(path,value):
                if path.name=='checkpoint.json':raise KeyboardInterrupt()
                atomic(path,value)
            with patch('sys.argv',args),patch.object(job,'Client',FakeClient),patch.object(job,'history_keys',return_value={'old:1'}),patch.object(job,'listing',return_value=([row],set())),patch.object(job.common,'atomic',side_effect=interrupt),patch.object(job.common,'HISTORY',history),patch.object(job.common,'OUT',pilot):
                self.assertEqual(job.main(),1)
            with patch('sys.argv',args),patch.object(job,'history_keys',return_value={'old:1'}),patch.object(job,'Client',side_effect=AssertionError('No request on completed resume')),patch.object(job.common,'HISTORY',history),patch.object(job.common,'OUT',pilot):
                self.assertEqual(job.main(),0)
            self.assertEqual(len((output/'records.jsonl').read_text(encoding='utf8').splitlines()),1)
            self.assertFalse((output/'collector.lock').exists())


if __name__=='__main__':unittest.main()
