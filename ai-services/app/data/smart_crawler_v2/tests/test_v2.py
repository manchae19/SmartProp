"""Component tests use pre-existing isolated parser fixtures, never live exports."""
import json,tempfile,unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch,MagicMock
from app.data.smart_crawler_v2 import sources,evidence,quality,index,transport,pipeline
import test_review_source_details as existing_fixtures

def fixture():
    old=existing_fixtures.SourceReviewTests();old.setUp()
    return dict(old.row,price_raw='5 tỷ',area_raw='100m2'),old.body

class MoneyAndQualityTests(unittest.TestCase):
    def test_exact_vnd_and_no_unit_price_guess(self):
        self.assertEqual((Decimal('2350000001'),None),quality.amount('2350000001 VND'))
        self.assertEqual((Decimal('2350000000'),None),quality.amount('2 tỷ 350 triệu'))
        self.assertEqual((Decimal('1'),None),quality.amount('0.000000001 tỷ'))
        self.assertEqual('UNIT_PRICE_NOT_TOTAL',quality.amount('80 triệu/m²')[1])
        self.assertIsNone(quality.amount('3.x tỷ')[0])
        self.assertIsNone(quality.amount('4 tỷ 750')[0])

    def test_floor_and_land_area_are_not_added(self):
        self.assertEqual([('LAND',Decimal('80')),('FLOOR',Decimal('250'))],quality.labelled_areas('Diện tích đất:80m²; DTSD:250m²'))
        self.assertEqual(Decimal('57.1'),quality.area('57,1m²'))
        self.assertIsNone(quality.area('57-60m²'))

    def test_card_update_is_not_claimed_as_first_publication(self):
        parsed=quality.source_dates({'updated_attribute_raw':'02-11-2026 08:00:00'},b'<html></html>')
        self.assertIsNone(parsed['published_at']);self.assertEqual('2026-11-02',parsed['updated_at'])
        self.assertEqual('SOURCE_CARD_DATE_TIMEZONE_UNSPECIFIED',parsed['date_basis'])

    def test_missing_date_location_and_coordinates_do_not_become_invented(self):
        card,body=fixture();e=sources.extract('cafeland',card,body,card['detail_url'])
        r=quality.evaluate('cafeland',card,e,body,'2026-11-02T10:00:00+00:00')
        self.assertEqual('NEEDS_REVIEW',r['quality_status']);self.assertIn('SOURCE_DATE_UNAVAILABLE',r['quality_flags'])
        self.assertEqual('UNVERIFIED',r['verification_status']);self.assertIsNone(r['latitude']);self.assertIsNone(r['longitude'])
        self.assertFalse(r['training_allowed']);self.assertFalse(r['public_display_allowed'])

    def test_negative_source_label_is_rejected(self):
        card,body=fixture();e=sources.extract('cafeland',card,body,card['detail_url']);e['price_raw']='-5 tỷ'
        r=quality.evaluate('cafeland',card,e,body,'2026-11-02T10:00:00+00:00')
        self.assertEqual('REJECTED',r['quality_status']);self.assertIn('INVALID_TOTAL_PRICE_RANGE',r['quality_flags'])

class EvidenceTests(unittest.TestCase):
    def test_redacted_snapshot_is_immutable_hash_verified_and_not_raw_page(self):
        card,body=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store=evidence.EvidenceStore(tmp)
            meta=store.save_detail('cafeland',card['source_listing_id'],card['detail_url'],body)
            self.assertTrue(store.verify(meta));self.assertFalse(meta['original_response_persisted'])
            self.assertEqual('PRIVACY_REDACTED_ASSET_DOM',meta['evidence_type'])
            with self.assertRaises(FileExistsError):store.save_detail('cafeland',card['source_listing_id'],card['detail_url'],body)
            Path(meta['reference']).write_bytes(b'changed');self.assertFalse(store.verify(meta))

    def test_contacts_are_not_exported(self):
        text=evidence.redact('Nhà80m². Giá5 tỷ.\nLiên hệ: Nguyễn Văn A,0901234567 person@example.invalid')
        self.assertNotIn('0901234567',text);self.assertNotIn('person@example.invalid',text);self.assertNotIn('Nguyễn Văn A',text)

class IndexTests(unittest.TestCase):
    def test_existing_id_url_and_holdout_group_are_checked_without_detail(self):
        old=index.OldIndex();card,_=fixture()
        row=dict(card,record_key='cafeland:'+card['source_listing_id'],pipeline_group='known',protected_holdout='True')
        old.add(row);old.add(dict(row,source_listing_id='3168537',record_key='cafeland:3168537',protected_holdout='False'));old.protect_groups()
        self.assertEqual('KNOWN_SOURCE_ID',old.match_identity('cafeland',card['source_listing_id'],card['detail_url']))
        self.assertIn('cafeland:3168537',old.holdouts)

    def test_price_area_district_alone_do_not_make_a_duplicate(self):
        row=dict(category='Nhà ở',district='Hải Châu',area_sqm='80',price_vnd='2350000000')
        self.assertEqual([],index.fingerprints(row))

    def test_holdout_risk_propagates_across_overlapping_groups(self):
        old=index.OldIndex();old.groups={'a':{'s:1','s:2'},'b':{'s:2','s:3'}};old.holdouts={'s:1'}
        old.protect_groups();self.assertEqual({'s:1','s:2','s:3'},old.holdouts)

class TransportTests(unittest.TestCase):
    def test_restricted_sources_do_not_issue_requests(self):
        with tempfile.TemporaryDirectory() as tmp,patch('requests.Session.get') as get:
            client=transport.Client(sources.SOURCES['homedy'],tmp)
            with self.assertRaises(transport.SourceUnavailable):client.prepare()
            get.assert_not_called()

    def test_403_stops_immediately_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp,patch('time.sleep'),patch('requests.Session.get') as get:
            response=MagicMock();response.status_code=403;get.return_value.__enter__.return_value=response
            c=transport.Client(sources.SOURCES['cafeland'],tmp,retries=2)
            with self.assertRaises(transport.SourceUnavailable):c._request('https://nhadat.cafeland.vn/robots.txt',robots=True)
            self.assertTrue(c.closed);self.assertEqual(1,get.call_count)

    def test_robots_disallow_is_checked_before_fetch(self):
        with tempfile.TemporaryDirectory() as tmp,patch('requests.Session.get') as get:
            c=transport.Client(sources.SOURCES['cafeland'],tmp);c.robot=MagicMock();c.robot.can_fetch.return_value=False
            with self.assertRaises(transport.SourceUnavailable):c.get('https://nhadat.cafeland.vn/ajax/data')
            get.assert_not_called()

class CheckpointTests(unittest.TestCase):
    def test_hard_pilot_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in [0,101]:
                with self.assertRaises(ValueError):pipeline.Pipeline(tmp,index.OldIndex(),max_new=n)

    def test_pilot_cumulative_cap_is_not_reset_by_another_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            state={'version':2,'seen':{str(i):{'status':'NEEDS_REVIEW'} for i in range(99)},'records':{},'evidence':[],'duplicates':[],'policies':[]}
            (Path(tmp)/'checkpoint.json').write_text(json.dumps(state),encoding='utf8')
            run=pipeline.Pipeline(tmp,index.OldIndex(),max_new=100);self.assertEqual(1,run.max_new)

    def test_post_evidence_interruption_resumes_without_refetch_or_false_pass(self):
        card,body=fixture();key='cafeland:'+card['source_listing_id']
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=evidence.EvidenceStore(root/'evidence')
            meta=store.save_detail('cafeland',card['source_listing_id'],card['detail_url'],body)
            state={'version':2,'seen':{key:{'status':'DETAIL_RESERVED','source_url':card['detail_url']}},'records':{},'evidence':[],'duplicates':[],'policies':[]}
            (root/'checkpoint.json').write_text(json.dumps(state),encoding='utf8')
            run=pipeline.Pipeline(root,index.OldIndex(),max_new=1)
            self.assertEqual('NEEDS_REVIEW',run.state['records'][key]['quality_status'])
            self.assertEqual(1,len(run.state['evidence']));self.assertEqual(meta['sha256'],run.state['evidence'][0]['sha256'])
            self.assertEqual(0,run.new_count)

    def test_seen_id_is_skipped_before_detail_and_export_has_no_fake_rows(self):
        card,body=fixture();old=index.OldIndex();old.add(card,'cafeland')
        class FakeClient:
            requests=0;closed=False
            def __init__(self,*args,**kwargs):pass
            def prepare(self):return {'url':'fixture://robots','sha256':'fixture-only'}
            def get(self,url):
                if url!=sources.SOURCES['cafeland'].listing:raise AssertionError('Existing detail must not be fetched')
                self.requests+=1;return b'<html>existing isolated discovery fixture</html>'
        with tempfile.TemporaryDirectory() as tmp,patch.object(pipeline,'discover',return_value=([card],None)):
            run=pipeline.Pipeline(tmp,old,max_new=1,client_factory=FakeClient);run.run_source('cafeland');result=run.export()
            self.assertEqual(0,result['total_new_observations']);self.assertEqual('KNOWN_SOURCE_ID',run.state['duplicates'][0]['reason'])
            self.assertFalse(run.state['duplicates'][0]['detail_requested'])

if __name__=='__main__':unittest.main()
