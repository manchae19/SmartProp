"""Market research routing + intake readiness; isolated fixtures, no real imports."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from app.rag.followup import classification
from app.rag.document_advisor import DocumentAdvisor
from app.rag.document_store import DocumentStore
from app.rag.hybrid import HybridRetriever
import test_chat_budget_context as baseline
import test_chat_market_g1 as g1
import test_rag_g2 as g2

class ResearchRoutingTests(unittest.TestCase):
    def test_natural_intent_matrix(self):
        examples=[
          ('Bất động sản nào đang thịnh hành ở Đà Nẵng?','MARKET_ANALYSIS'),
          ('Tôi muốn tìm bất động sản đang thịnh hành ở Thanh Khê','MARKET_ANALYSIS'),
          ('Tìm hiểu xu hướng bất động sản Đà Nẵng','MARKET_ANALYSIS'),
          ('Loại hình nào được ưa chuộng ở Thanh Khê?','MARKET_ANALYSIS'),
          ('Phân khúc cho thuê nào đang thịnh hành tại Đà Nẵng?','MARKET_ANALYSIS'),
          ('Giá căn hộ Sơn Trà hiện nay?','MARKET_PRICE'),
          ('Xu hướng giá nhà Sơn Trà năm 2026?','MARKET_ANALYSIS'),
          ('Sổ hồng là gì?','LEGAL_QA'),
          ('Quy hoạch Thanh Khê thế nào?','PLANNING_QA'),
          ('Ở Hải Châu có trung tâm thương mại nào?','AREA_AMENITIES'),
          ('Tìm căn hộ dưới 2 tỷ 600 triệu tại Thanh Khê','SEARCH'),
          ('Tôi có 850 triệu','UPDATE_CRITERIA'),
        ]
        for question,expected in examples:
            with self.subTest(question=question):
                turn=classification(question,None);self.assertEqual(turn['intent'],expected)
                if expected=='MARKET_ANALYSIS':self.assertFalse(turn['searchChange']);self.assertEqual(turn['intentFamily'],'MARKET_ANALYSIS')
    def test_pending_search_does_not_capture_research(self):
        context=SimpleNamespace(last_property_ids=[],last_criteria=None,needs={'pending':'purpose'})
        self.assertEqual(classification('Tôi muốn tìm bất động sản đang thịnh hành ở Thanh Khê',context)['intent'],'MARKET_ANALYSIS')
    def test_concrete_budget_search_is_preserved_without_popularity_claim(self):
        turn=classification('Tìm căn hộ đang thịnh hành dưới 3 tỷ',None)
        self.assertEqual(turn['intentFamily'],'PROPERTY_SEARCH');self.assertTrue(turn['unsupportedPopularityFilter'])

class ResearchConversationTests(unittest.TestCase):
    chat=baseline.ConversationTests.chat
    def setUp(self):
        baseline.ConversationTests.setUp(self);self.market_calls=[]
        def market(query):self.market_calls.append(query);return g1.snapshot()
        self.backend.market_summary=market
    def test_both_reported_questions_no_intake_or_backend_search(self):
        for question in ['Bất động sản nào đang thịnh hành ở Đà Nẵng?','Tôi muốn tìm bất động sản đang thịnh hành ở Thanh Khê']:
            response=self.chat(question)
            self.assertEqual(response.evidence['intent'],'MARKET_ANALYSIS')
            self.assertEqual(response.evidence['responseKind'],'INSUFFICIENT_MARKET_ANALYSIS_DATA')
            self.assertNotIn('clarification',response.evidence);self.assertNotIn('needs',response.evidence)
            self.assertIn('giao dịch',response.answer);self.assertEqual(response.citations,[])
        self.assertEqual(self.backend.calls,[]);self.assertEqual(self.market_calls,[])
    def test_rental_trend_no_price_unit_question(self):
        response=self.chat('Phân khúc cho thuê nào đang thịnh hành tại Đà Nẵng?')
        self.assertEqual(response.evidence['intent'],'MARKET_ANALYSIS');self.assertNotIn('clarification',response.evidence)
    def test_research_followup_keeps_only_market_scope(self):
        self.chat('Tôi muốn tìm bất động sản đang thịnh hành ở Thanh Khê')
        result=self.chat('Còn Hải Châu thì sao?')
        self.assertEqual(result.evidence['intent'],'MARKET_ANALYSIS')
        self.assertEqual(result.evidence['marketAnalysis']['district'],'Hải Châu')
        result=self.chat('Giá căn hộ Sơn Trà hiện nay?')
        self.assertEqual(result.evidence['intent'],'MARKET_PRICE');self.assertEqual(self.market_calls[-1]['district'],'Sơn Trà')
    def test_search_budget_and_references_survive_research(self):
        first=self.chat('Tìm căn hộ dưới 2 tỷ 600 triệu toàn Đà Nẵng');ids=first.evidence['session']['context']['lastPropertyIds']
        count=len(self.backend.calls)
        r=self.chat('Bất động sản nào đang thịnh hành ở Thanh Khê?')
        self.assertEqual(len(self.backend.calls),count);self.assertEqual(r.evidence['session']['context']['lastPropertyIds'],ids)
        r=self.chat('Căn thứ hai giá bao nhiêu?');self.assertEqual(r.recommendedProperties[0]['id'],ids[1])
        self.assertEqual(self.backend.calls[-1]['budgetVnd'],'2600000000')
    def test_missing_store_and_unknown_are_honest(self):
        self.bot.document_advisor=DocumentAdvisor(DocumentStore(None),HybridRetriever(g2.NoDense()),baseline.MissingTool())
        r=self.chat('Bất động sản nào đang thịnh hành ở Đà Nẵng?')
        self.assertEqual(r.evidence['responseKind'],'INSUFFICIENT_MARKET_ANALYSIS_DATA');self.assertIn('lượt tìm kiếm',r.answer)
    def test_mixed_search_warns_popularity_not_verified(self):
        r=self.chat('Tìm căn hộ đang thịnh hành dưới 3 tỷ toàn Đà Nẵng')
        self.assertTrue(r.recommendedProperties)
        self.assertTrue(any('thịnh hành' in line for line in r.dataLimitations))

class ResearchSourceTests(g2.FixtureCase):
    def test_market_documents_used_with_citations(self):
        self.source.update(topic='MARKET',title='TEST ONLY bất động sản thịnh hành')
        (self.root/'fixture.txt').write_text('TEST ONLY bất động sản thịnh hành Thanh Khê trong báo cáo mô phỏng, không phải xu hướng thực tế.',encoding='utf-8')
        self.source['districts']=['Thanh Khê']
        advisor=DocumentAdvisor(self.write(),HybridRetriever(g2.NoDense()),baseline.MissingTool())
        case=ResearchConversationTests();case.setUp();case.bot.document_advisor=advisor
        r=case.chat('Tôi muốn tìm bất động sản đang thịnh hành ở Thanh Khê')
        self.assertEqual(r.evidence['responseKind'],'KNOWLEDGE_EVIDENCE');self.assertEqual(r.citations[0].kind,'SOURCE_DOCUMENT')
        self.assertEqual(case.backend.calls,[]);self.assertIn('TEST ONLY',r.answer)

class IntakeReadinessTests(g2.FixtureCase):
    def test_cli_dry_run_and_reviewed_commit_in_temp(self):
        self.run_intake()
        report=self.root/'report.json';script=Path(__file__).resolve().parents[1]/'scripts/ingest_rag_documents.py'
        command=[sys.executable,'-B',str(script),'--manifest',str(self.manifest),'--output',str(self.output),'--report',str(report)]
        dry=subprocess.run(command,capture_output=True)
        self.assertEqual(dry.returncode,0,dry.stderr);self.assertFalse(self.output.exists())
        self.assertTrue(json.loads(report.read_text(encoding='utf-8'))['dryRun'])
        written=subprocess.run(command+['--write'],capture_output=True)
        self.assertEqual(written.returncode,0,written.stderr);DocumentStore(self.output).load()
    def test_pending_manifest_is_blocked_and_does_not_write(self):
        self.run_intake([{**self.source,'approval':'PENDING'}])
        script=Path(__file__).resolve().parents[1]/'scripts/ingest_rag_documents.py';report=self.root/'blocked.json'
        result=subprocess.run([sys.executable,'-B',str(script),'--manifest',str(self.manifest),'--output',str(self.output),'--report',str(report)],capture_output=True)
        self.assertEqual(result.returncode,2);self.assertFalse(self.output.exists());self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['blocked'],1)
