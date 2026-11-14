import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import collect_apartment_pilot as job
from urllib.robotparser import RobotFileParser


def fixture(area='55m2',price='2 tỷ 500 triệu',source_category='ban-can-ho-chung-cu'):
    url=job.ORIGIN+'/can-ho-thu-nghiem-9990001.html'
    row=dict(record_key='cafeland:9990001',source='cafeland',source_listing_id='9990001',detail_url=url,
             listing_title='Căn hộ thử nghiệm',listing_price_raw=price,listing_area_raw=area,listing_address_raw='Sơn Trà, Đà Nẵng',listing_page=job.START)
    ld=json.dumps({'@type':'Product','offers':{'url':url,'priceCurrency':'VND','price':2500000000}})
    page=f'''<html><script type="application/ld+json">{ld}</script><div class="detail-property"><h1>Căn hộ thử nghiệm</h1>
    <div class="infor">Vị trí: <a href="/nha-dat-ban/{source_category}-tai-son-tra-da-nang/">Sơn Trà</a>, <a href="/nha-dat-ban/ban-can-ho-chung-cu-tai-da-nang/">Đà Nẵng</a></div>
    <div class="infor">Mã tài sản: 9990001 / Ngày đăng: 27-10-2026</div>
    <div class="col-item"><span class="infor-note">Giá bán</span><span class="infor-data">{price}</span></div>
    <div class="col-item"><span class="infor-note">Diện tích</span><span class="infor-data">{area}</span></div>
    <div class="col-item"><span class="infor-note">Phòng ngủ</span><span class="infor-data">2 PN</span></div>
    <div class="reals-description">Căn hộ đơn lẻ có thông tin giá và diện tích.</div></div></html>'''
    return page.encode(),row


class ApartmentCollectorTest(unittest.TestCase):
    def test_resume_uses_durable_log_after_interrupt_before_checkpoint(self):
        body,row=fixture()
        class FakeClient:
            def __init__(self,*args):pass
            def fetch(self,url):
                self.last_url=url
                return (b'listing' if url==job.START else body),200
        job.OUT.parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=job.OUT.parent,prefix='pilot-test-') as directory:
            root=Path(directory);history=root/'history.csv'
            history.write_text('record_key\nold:1\n',encoding='utf8')
            args=['collector','--target','1','--output',str(root)]
            original=job.atomic
            def interrupted(path,value):
                if path.name=='checkpoint.json':raise KeyboardInterrupt()
                return original(path,value)
            with patch.object(job,'HISTORY',history),patch('sys.argv',args),patch.object(job,'Client',FakeClient),patch.object(job,'listing_page',return_value=([row],set())),patch.object(job,'atomic',side_effect=interrupted):
                self.assertEqual(job.main(),1)
            self.assertFalse((root/'collector.lock').exists())
            with patch.object(job,'HISTORY',history),patch('sys.argv',args),patch.object(job,'Client',side_effect=AssertionError('Network must not run on completed resume')):
                self.assertEqual(job.main(),0)
            self.assertEqual(len((root/'records.jsonl').read_text(encoding='utf8').splitlines()),1)

    def test_redirect_allows_only_same_id_allowed_https_source(self):
        client=object.__new__(job.Client)
        client.robot=RobotFileParser();client.robot.parse(['User-agent: *','Allow: /','Disallow: /error.html'])
        old=job.ORIGIN+'/old-title-123.html'
        client.validate_redirect(old,job.ORIGIN+'/new-title-123.html')
        for new in [job.ORIGIN+'/new-title-456.html','https://example.com/new-123.html',
                    job.ORIGIN+'/error.html','http://nhadat.cafeland.vn/new-123.html',
                    job.ORIGIN+'/new-123.html?x=1']:
            with self.subTest(new=new),self.assertRaises(ValueError):client.validate_redirect(old,new)

    def test_total_price_area_identity_and_source_date_are_separate(self):
        body,row=fixture();out=job.parse_detail(body,row,'2026-10-28T00:00:00Z')
        self.assertEqual(out['price_million'],2500);self.assertEqual(out['area_sqm'],55)
        self.assertEqual(out['rooms'],2);self.assertEqual(out['source_published_date'],'2026-10-27')
        self.assertNotEqual(out['source_published_date'],out['collected_at'][:10])
        self.assertFalse(out['source_evidence_flags'])

    def test_missing_area_is_not_filled_from_title(self):
        body,row=fixture(area='')
        row['listing_title']='Căn hộ 55m2'
        out=job.parse_detail(body,row,'2026-10-27T00:00:00Z')
        self.assertIsNone(out['area_sqm']);self.assertIn('missing_structured_area',out['source_evidence_flags'])

    def test_wrong_jsonld_identity_stops_parser(self):
        body,row=fixture();row['detail_url']=job.ORIGIN+'/other-9990002.html'
        with self.assertRaises(ValueError):job.parse_detail(body,row,'x')

    def test_unit_price_and_nonapartment_stay_review(self):
        body,row=fixture(price='50 triệu/m2',source_category='ban-khach-san')
        out=job.parse_detail(body,row,'x')
        self.assertIsNone(out['price_million']);self.assertIn('source_category_not_apartment',out['source_evidence_flags'])


if __name__=='__main__':unittest.main()
