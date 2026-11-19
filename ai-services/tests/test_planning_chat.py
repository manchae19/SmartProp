"""Synthetic approved snapshot only; no DB/provider access."""
import copy, json, tempfile, unittest
from pathlib import Path
from dataclasses import asdict
from fastapi.testclient import TestClient
from app.rag.api import create_chat_app
from app.rag.config import Settings
from app.rag.planning_chat import PlanningAdvisor, classify_planning
from app.rag.planning_data import build_snapshot
from app.rag.session import Context
from app.rag.checkpoints import CheckpointSessions
import test_planning_data as data_tests
import test_chat_budget_context as conversation_tests

class PlanningChatTests(unittest.TestCase):
    def setUp(self):
        self.fixture=data_tests.PlanningTests();self.fixture.setUp()
        b=self.fixture.b
        project=copy.deepcopy(self.fixture.r);project['id']='HX-RE-001';project['kind']='PROJECT_PROFILE'
        b['records'].append(project)
        other=copy.deepcopy(self.fixture.r);other['id']='HX-LAND-002';other['facts']['phase']['value']='2';b['records'].append(other)
        snapshot,_=build_snapshot(b,self.fixture.approve(b))
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'approved-fixture.json';self.path.write_text(json.dumps(snapshot),encoding='utf-8')
        self.advisor=PlanningAdvisor(self.path,enabled=True)
        self.ctx=Context(scope='PUBLIC',session_id='a'*32,created_at=0,updated_at=0)
    def test_four_intents(self):
        for text,op in [('Dự án Hòa Xuân có gì?','PROJECT_LIST'),('Quy hoạch Hòa Xuân đã phê duyệt chưa?','PLANNING_STATUS'),('Đấu giá Hòa Xuân năm 2026','AUCTION_CATALOG'),('Mã lô A2-1 Hòa Xuân','LOT_LOOKUP')]:
            self.assertEqual(op,classify_planning(text)['operation'])
    def test_other_tools_not_captured(self):
        for q in ['Tìm nhà ở Hòa Xuân dưới 2 tỷ','Hòa Xuân có bệnh viện nào?','Căn thứ hai gần trường học không?','Ngân sách 3 tỷ']:
            self.assertIsNone(classify_planning(q,{'operation':'PROJECT_LIST'}))
    def test_disabled_does_not_override_existing_routing(self):
        self.assertIsNone(PlanningAdvisor('/not/read',enabled=False).reply('Dự án Hòa Xuân',self.ctx))
    def test_source_metadata_and_no_properties(self):
        r=self.advisor.reply('Dự án Hòa Xuân',self.ctx)
        self.assertEqual([],r['properties']);self.assertEqual(1,len(r['citations']))
        s=r['extra']['planningLookup']['sources'][0]
        self.assertEqual('2025-01-01',s['documentDate']);self.assertIsNone(s['publicationDate'])
        self.assertEqual('SOURCE_CHECKED',s['verification'])
        self.assertIn('chưa xác nhận',r['answer'])
    def test_lot_followup_and_checkpoint_preserves_property_ids(self):
        self.ctx.last_property_ids=['property:fixture-house']
        first=self.advisor.reply('Mã lô A2-1 Hòa Xuân',self.ctx)
        self.assertEqual('NEEDS_CLARIFICATION',first['extra']['planningLookup']['status'])
        saved=asdict(self.ctx);saved.pop('scope');saved.pop('session_id')
        store=CheckpointSessions('a'*32,saved);restored,_,_=store.begin('a'*32,scope='PUBLIC')
        r=self.advisor.reply('Giai đoạn 2',restored)
        self.assertEqual(['HX-LAND-002'],[i['id'] for i in r['extra']['planningLookup']['items']])
        self.assertEqual(['property:fixture-house'],restored.last_property_ids)
    def test_unavailable_and_no_matches_differ(self):
        r=PlanningAdvisor(self.path.parent/'missing',enabled=True).reply('Dự án Hòa Xuân',self.ctx)
        self.assertEqual('SOURCE_UNAVAILABLE',r['extra']['planningLookup']['status'])
        r=self.advisor.reply('Dự án AEON Hòa Xuân',self.ctx)
        self.assertEqual('NO_MATCHES',r['extra']['planningLookup']['status'])
    def test_auction_year_required(self):
        self.assertEqual('NEEDS_CLARIFICATION',self.advisor.reply('Đấu giá Hòa Xuân',self.ctx)['extra']['planningLookup']['status'])
        self.assertEqual('OUTSIDE_COVERAGE',self.advisor.reply('Đấu giá Hòa Xuân 2025',self.ctx)['extra']['planningLookup']['status'])
    def test_new_explicit_lot_drops_previous_document_filter(self):
        previous={'operation':'PLANNING_STATUS','document_number':'934'}
        q=classify_planning('Mã lô A1-14 Hòa Xuân',previous)
        self.assertEqual('LOT_LOOKUP',q['operation'])
        self.assertIsNone(q['document_number'])
        q=classify_planning('Lô A1-14',previous)
        self.assertIsNone(q['document_number'])
    def test_document_number_filter(self):
        q=classify_planning('Quy hoạch Hòa Xuân theo QĐ 1804')
        self.assertEqual('1804',q['document_number'])
        snapshot=json.loads(self.path.read_text(encoding='utf-8'))
        for row in snapshot['records']:
            row['facts']['document_number']={'value':'1804/QĐ-UBND' if row['id']=='HX-LAND-001' else '934/QĐ-UBND','source_ids':['s1'],'basis':'FIXTURE','scope':'DOCUMENT_SCOPE'}
        from app.rag.planning_data import digest
        snapshot.pop('content_hash');snapshot['content_hash']=digest(snapshot)
        self.path.write_text(json.dumps(snapshot),encoding='utf-8')
        r=self.advisor.reply('Quy hoạch Hòa Xuân theo QĐ 1804',self.ctx)
        self.assertEqual(['HX-LAND-001'],[i['id'] for i in r['extra']['planningLookup']['items']])
    def test_auction_followup_year(self):
        self.advisor.reply('Đấu giá Hòa Xuân',self.ctx)
        r=self.advisor.reply('Năm 2026',self.ctx)
        self.assertEqual('OK',r['extra']['planningLookup']['status'])
        self.assertEqual(2,r['extra']['planningLookup']['total'])
    def test_http_chat_and_existing_property_context(self):
        fixture=conversation_tests.ConversationTests();fixture.setUp();bot=fixture.bot;bot.planning_advisor=self.advisor
        with TestClient(create_chat_app(Settings(),bot)) as client:
            response=client.post('/chat',json={'question':'Dự án Hòa Xuân'})
            self.assertEqual(200,response.status_code,response.text)
            data=response.json();self.assertEqual('PLANNING_LOOKUP',data['evidence']['responseKind'])
            self.assertEqual([],fixture.backend.calls)
            Path(self.temp.name,'packet.json').write_text(json.dumps(data),encoding='utf-8')
        fixture.chat('Tôi có 10 tỷ, tìm nhà toàn Đà Nẵng')
        result=fixture.chat('Dự án Hòa Xuân')
        self.assertTrue(result.evidence['session']['context']['lastPropertyIds'])

if __name__=='__main__':unittest.main()
