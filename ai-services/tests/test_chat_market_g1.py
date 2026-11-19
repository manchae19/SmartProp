import copy
import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
import httpx
from app.rag.config import GroundingError
from app.rag.tools import BackendTools, UpstreamError
from app.rag.tool_registry import ToolRegistry
from app.rag.followup import classification
from app.rag.market import market_query
import test_chat_budget_context as baseline

QUERY = {"transactionType":"SALE", "priceUnit":"TOTAL"}
def snapshot(count=2):
    return {"asOf":datetime.now(timezone.utc).isoformat(),"source":"CURRENT_PUBLISHED_ASKING_PRICES","historyAvailable":False,"transactionType":"SALE","currency":"VND","priceUnit":"TOTAL","overall":{"count":count,"totalAskingPrice":6000000000 if count else None,"averageAskingPrice":3000000000 if count else None,"minimumAskingPrice":2000000000 if count else None,"maximumAskingPrice":4000000000 if count else None,"weightedAskingPricePerSqm":50000000 if count else None}}

class MarketConversationTests(unittest.TestCase):
    chat=baseline.ConversationTests.chat
    def setUp(self):
        baseline.ConversationTests.setUp(self)
        self.market_calls=[]
        self.backend.market_summary=self.market
    def market(self,query):
        self.market_calls.append(copy.deepcopy(query));return snapshot()
    def test_market_no_budget_or_recommendation(self):
        r=self.chat("Giá căn hộ Sơn Trà hiện nay?")
        self.assertEqual(r.evidence['intent'],'MARKET_PRICE')
        self.assertEqual(r.evidence['responseKind'],'MARKET_PRICE_EVIDENCE')
        self.assertEqual(self.backend.calls,[])
        self.assertEqual(self.market_calls[0]['district'],'Sơn Trà')
        self.assertEqual(self.market_calls[0]['propertyType'],'APARTMENT')
        self.assertIn('giá chào',r.answer.lower())
        self.assertEqual(r.citations[0].kind,'MARKET_SUMMARY')
    def test_market_scope_separate_from_search_and_reference(self):
        first=self.chat('Tìm căn hộ 10 tỷ toàn Đà Nẵng')
        ids=first.evidence['session']['context']['lastPropertyIds']
        self.chat('Giá căn hộ ở Hải Châu bao nhiêu?')
        r=self.chat('Còn Sơn Trà thì sao?')
        self.assertEqual(self.market_calls[-1]['district'],'Sơn Trà')
        self.assertNotIn('needs',r.evidence)
        self.assertEqual(r.evidence['session']['context']['lastPropertyIds'],ids)
        r=self.chat('Căn thứ hai giá bao nhiêu?')
        self.assertEqual(r.recommendedProperties[0]['id'],ids[1])
    def test_market_then_places_not_recommendation(self):
        self.chat('Giá căn hộ Sơn Trà?')
        r=self.chat('Ở Sơn Trà có trung tâm thương mại nào?')
        self.assertEqual(r.evidence['intent'],'AREA_AMENITIES')
        self.assertEqual(self.backend.calls,[])
        self.assertEqual(self.backend.place_calls[-1],('Sơn Trà','MALL'))
    def test_trend_not_inferred(self):
        r=self.chat('Xu hướng giá ở Sơn Trà năm 2026?')
        self.assertEqual(r.evidence['responseKind'],'INSUFFICIENT_TREND_DATA')
        self.assertIn('chưa có',r.answer.lower())
        self.assertFalse(r.evidence['marketSummary']['historyAvailable'])
    def test_legal_planning_no_budget_tools(self):
        for q,intent in [('Sổ hồng là gì?','LEGAL_QA'),('Quy hoạch Hòa Vang thế nào?','PLANNING_QA')]:
            r=self.chat(q)
            self.assertEqual(r.evidence['intent'],intent)
            self.assertEqual(r.evidence['responseKind'],'KNOWLEDGE_SOURCE_UNAVAILABLE')
        self.assertEqual(self.backend.calls,[]);self.assertEqual(self.market_calls,[])
    def test_empty_market_not_housing_no_matches(self):
        self.backend.market_summary=lambda q:snapshot(0)
        r=self.chat('Giá căn hộ Hải Châu?')
        self.assertEqual(r.evidence['responseKind'],'INSUFFICIENT_MARKET_DATA')
    def test_source_failure_not_no_matches(self):
        def fail(q):raise UpstreamError(503)
        self.backend.market_summary=fail
        r=self.chat('Giá căn hộ Sơn Trà?')
        self.assertEqual(r.evidence['responseKind'],'DATA_SOURCE_ERROR');self.assertEqual(r.citations,[])
    def test_rental_unit_answer_keeps_scope(self):
        self.chat('Giá thuê căn hộ Sơn Trà?')
        def rental(q):
            self.market_calls.append(copy.deepcopy(q));b=snapshot();b.update(transactionType='RENT',priceUnit='PER_MONTH');return b
        self.backend.market_summary=rental
        r=self.chat('Theo tháng')
        self.assertEqual(r.evidence['intent'],'MARKET_PRICE')
        self.assertEqual(self.market_calls[-1],{'district':'Sơn Trà','propertyType':'APARTMENT','transactionType':'RENT','priceUnit':'PER_MONTH'})
    def test_scope_clarification_no_call(self):
        r=self.chat('Giá thuê căn hộ Sơn Trà?')
        self.assertEqual(r.evidence['clarification'],'MARKET_SCOPE');self.assertEqual(self.market_calls,[])

class MarketToolTests(unittest.TestCase):
    def tool(self,body=None,status=200):
        t=BackendTools(SimpleNamespace(backend_url='http://127.0.0.1:18080',backend_timeout_seconds=2))
        t.client.close()
        def respond(req):
            self.assertEqual(req.method,'GET');self.assertEqual(req.url.path,'/api/v1/properties/market-summary')
            self.assertNotIn('authorization',req.headers)
            return httpx.Response(status,json=body if body is not None else snapshot())
        t.client=httpx.Client(base_url='http://127.0.0.1:18080',transport=httpx.MockTransport(respond))
        self.addCleanup(t.client.close);return t
    def test_actual_adapter(self):self.assertEqual(self.tool().market_summary(QUERY)['overall']['count'],2)
    def test_empty(self):self.assertEqual(self.tool(snapshot(0)).market_summary(QUERY)['overall']['count'],0)
    def test_invalid_evidence(self):
        for field,value in [('source','WRONG'),('currency','USD'),('historyAvailable',True)]:
            b=snapshot();b[field]=value
            with self.subTest(field=field),self.assertRaises(GroundingError):self.tool(b).market_summary(QUERY)
        for field,value in [('count',True),('count',-1),('averageAskingPrice',5000000000),('minimumAskingPrice',-1)]:
            b=snapshot();b['overall'][field]=value
            with self.subTest(field=field),self.assertRaises(GroundingError):self.tool(b).market_summary(QUERY)
    def test_stale_and_future(self):
        for seconds in [-900,900]:
            b=snapshot();b['asOf']=(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat()
            with self.subTest(seconds=seconds),self.assertRaises(GroundingError):self.tool(b).market_summary(QUERY)
    def test_error_and_timeout(self):
        self.assertEqual(ToolRegistry(self.tool(status=429)).execute('market_summary',QUERY).status,'SOURCE_UNAVAILABLE')
        t=self.tool();t.client.close()
        def fail(req):raise httpx.ReadTimeout('mock timeout')
        t.client=httpx.Client(base_url='http://127.0.0.1:18080',transport=httpx.MockTransport(fail));self.addCleanup(t.client.close)
        self.assertEqual(ToolRegistry(t).execute('market_summary',QUERY).status,'SOURCE_UNAVAILABLE')
    def test_registry_closed_allowlist(self):
        with self.assertRaises(GroundingError):ToolRegistry(self.tool()).execute('https://example.org')
        self.assertEqual(ToolRegistry(SimpleNamespace()).execute('market_summary',QUERY).status,'INSUFFICIENT_DATA')
    def test_query_rejects_arbitrary_targets(self):
        with self.assertRaises(GroundingError):self.tool().market_summary({**QUERY,'url':'https://example.org'})
    def test_query_scope(self):
        q,error=market_query('Giá căn hộ toàn Đà Nẵng',{'district':'Sơn Trà'},'APARTMENT')
        self.assertIsNone(error);self.assertNotIn('district',q)
        self.assertIsNotNone(market_query('Giá nhà phường Hòa Hải')[1])
        self.assertIsNotNone(market_query('Giá căn hộ Sơn Trà và Hải Châu')[1])
