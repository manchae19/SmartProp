"""Offline regression: real orchestrator/parser/session with deterministic API fixtures."""
import copy
from decimal import Decimal
from types import SimpleNamespace
import unittest
import httpx
from app.rag.money import parse_budget
from app.rag.followup import classification
from app.rag.orchestrator import ChatOrchestrator
from app.rag.session import SessionStore
from app.rag.schemas import ChatRequest
from app.rag.config import RagUnavailable, GroundingError
from app.rag.tools import BackendTools
from app.rag.knowledge import document


class BudgetTests(unittest.TestCase):
    def test_valid_formats(self):
        cases={"2 tỷ 600 triệu":2600000000,"2 tỉ 600 triệu":2600000000,"ngân sách 2600000000":2600000000,"nhỏ hơn 2,6 tỷ":2600000000,"2 ty 400 trieu":2400000000,
               "2.6 tỷ":2600000000,"2,6 tỷ":2600000000,"850 triệu":850000000,
               "2600 triệu":2600000000,"2.600.000.000 VND":2600000000,
               "2 600 000 000 đồng":2600000000,"2600000000":2600000000,
               "2 tỷ rưỡi":2500000000,"2 tỷ 600 triệu 500 nghìn":2600500000,
               "Tôi có 2 tỷ 600 triệu, tìm nhà":2600000000}
        for text,amount in cases.items():
            with self.subTest(text=text):
                result=parse_budget(text)
                self.assertEqual(result.status,"VALID")
                self.assertEqual(result.maximum,Decimal(amount))
    def test_ranges(self):
        for text in ["từ 2 đến 3 tỷ","2-3 tỷ","2 tỷ đến 3 tỷ","2 tỷ 400 triệu đến 2 tỷ 600 triệu"]:
            with self.subTest(text=text):
                result=parse_budget(text)
                self.assertEqual(result.status,"VALID")
                self.assertEqual(result.minimum,Decimal(2400000000 if '400' in text else 2000000000))
                self.assertEqual(result.maximum,Decimal(2600000000 if '600' in text else 3000000000))
    def test_ambiguous_never_falls_back(self):
        for text in ['2 tỷ hay 3 tỷ','3 tỷ đến 2 tỷ','-2 tỷ','0 đồng','2 tỷ 6','2 tỷ 1500 triệu','hơn 2 tỷ','9999999999999999 đồng','2','2.6.4 tỷ','tăng thêm 500 triệu','ngân sách 2']:
            with self.subTest(text=text):self.assertEqual(parse_budget(text).status,'AMBIGUOUS')
    def test_multi_digit_money_is_not_an_ordinal(self):
        for q in ['Tìm căn hộ 10 tỷ','Tìm căn hộ 25 tỷ','Tìm căn hộ 100 triệu','Tìm căn hộ 2,6 tỷ']:
            self.assertIsNone(classification(q,None)['ordinal'])
    def test_no_budget(self):
        self.assertEqual(parse_budget('Căn thứ hai có 2 phòng ngủ').status,'NOT_MENTIONED')
    def test_places_aliases(self):
        from app.rag.intent import poi_categories
        for text,category in [('trung tâm thương mại','MALL'),('TTTM','MALL'),('shopping mall','MALL'),('bến xe','PUBLIC_TRANSPORT'),('trạm bus','PUBLIC_TRANSPORT'),('siêu thị','SUPERMARKET'),('hospital','HOSPITAL'),('công viên','PARK'),('trường tiểu học','SCHOOL')]:
            with self.subTest(text=text):self.assertIn(category,poi_categories(text))
    def test_intent(self):
        context=SimpleNamespace(last_property_ids=['a','b'],last_criteria={'budgetVnd':'10000000000'})
        for text in ['Tôi có 2 tỷ 400 triệu, có bất động sản công khai phù hợp không?', 'Tìm căn hộ dưới 2 tỷ, ưu tiên gần trường và siêu thị']:
            turn=classification(text,context)
            self.assertTrue(turn['searchChange']);self.assertFalse(turn['needsPropertyReference'])
        for text in ['Căn thứ hai giá 4 tỷ có phù hợp không?', 'Căn đó thì sao?']:
            turn=classification(text,context)
            self.assertFalse(turn['budgetChange']);self.assertEqual(turn['intent'],'PROPERTY_FOLLOWUP')


def candidate(index,price,district='Sơn Trà'):
    uid=f'00000000-0000-4000-8000-{index:012d}'
    return {'id':'property:'+uid,'title':'Fixture '+str(index),'priceVnd':price,'areaSqm':60,
            'propertyType':'APARTMENT','district':district,'ward':None,'score':70,
            'source':{'kind':'PROPERTY','recordKey':uid,'name':'SmartProp'},'qualityStatus':'PLATFORM_PUBLISHED','verificationStatus':'PLATFORM_PUBLISHED','explanations':[],
            'scoreBreakdown':{},'warnings':[]}

class FakeBackend:
    settings=SimpleNamespace(backend_url='http://127.0.0.1:18080')
    def __init__(self):
        self.calls=[];self.place_calls=[];self.rows=[candidate(1,2000000000),candidate(2,2500000000),candidate(3,4000000000)]
    def amenity_summary(self):return {'catalogVersion':'TEST_V1'}
    def recommend(self,criteria,**kwargs):
        self.calls.append(copy.deepcopy(criteria))
        rows=[p for p in self.rows if Decimal(str(criteria.get('minPriceVnd') or 0))<=p['priceVnd']<=Decimal(str(criteria['budgetVnd']))]
        rows=[p for p in rows if not criteria.get('district') or p['district']==criteria['district']]
        rows=[p for p in rows if criteria.get('propertyType','ALL')=='ALL' or p['propertyType']==criteria['propertyType']]
        # Contrasting school/shopping fixtures exercise priorities before top-k.
        if criteria.get('amenityPriorities',[None])[0]=='SUPERMARKET':rows=list(reversed(rows))
        return {'method':'HEURISTIC_V1_1','mode':'SAFE','topProperties':copy.deepcopy(rows),'topAreas':[], 'eligibleCandidateCount':len(rows),'warnings':[]}
    def amenity_map(self,*args):
        self.place_calls.append(args)
        return {'items':[]}
    def property_nearby(self,uid,*args):
        self.last_nearby=uid
        return {'status':'LOCATION_UNAVAILABLE','location':{'accuracy':'UNKNOWN'},'items':[]}

class MissingTool:
    def lookup(self,*a):raise RagUnavailable('READ_ONLY_SQL_NOT_CONFIGURED')
    def search(self,*a,**kw):raise RagUnavailable('E5_RUNTIME_UNAVAILABLE')
    def plan(self,*a):raise RagUnavailable('QWEN_LOCAL_WEIGHTS_MISSING')

class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.backend=FakeBackend()
        docs=[document('area:test','Fixture district','https://example.org/fixture','TEST_V1','AREA_AMENITY',{'district':'Sơn Trà','areaLevel':'DISTRICT','areaId':'test'}),
              document('poi:test','Fixture school source','https://example.org/school','TEST_V1','POI_EVIDENCE',{'district':'Sơn Trà','category':'SCHOOL','areaId':'test'})]
        knowledge=SimpleNamespace(load=lambda:{'summary':{'catalogVersion':'TEST_V1'},'documents':docs,'contentHash':'test'})
        self.store=SessionStore();self.bot=ChatOrchestrator(self.backend,MissingTool(),knowledge,MissingTool(),MissingTool(),sessions=self.store)
        self.sid=None
    def chat(self,text):
        result=self.bot.chat(ChatRequest(question=text,sessionId=self.sid));self.sid=result.evidence['session']['id'];return result
    def test_compound_replaces_old_budget(self):
        self.chat('Tôi có 10 tỷ, tìm bất động sản toàn Đà Nẵng')
        r=self.chat('Tôi có 2 tỷ 600 triệu có bất động sản nào phù hợp hay không')
        self.assertEqual(Decimal(self.backend.calls[-1]['budgetVnd']),Decimal(2600000000))
        self.assertTrue(all(p['priceVnd']<=2600000000 for p in r.recommendedProperties))
        r=self.chat('Tôi có 2 tỷ 400 triệu, có bất động sản công khai phù hợp không?')
        self.assertNotEqual(r.evidence.get('responseKind'),'CLARIFICATION_REQUIRED')
        self.assertTrue(all(p['priceVnd']<=2400000000 for p in r.recommendedProperties))
    def test_ambiguous_no_old_search(self):
        first=self.chat('Tôi có 10 tỷ, tìm nhà toàn Đà Nẵng')
        count=len(self.backend.calls)
        r=self.chat('Ngân sách 2 tỷ hay 3 tỷ')
        self.assertEqual(len(self.backend.calls),count)
        self.assertEqual(r.evidence['clarification'],'BUDGET_AMBIGUOUS')
        self.assertEqual(r.evidence['session']['context']['lastPropertyIds'],first.evidence['session']['context']['lastPropertyIds'])
    def test_range_then_new_ceiling_clears_floor(self):
        self.chat('Tìm căn hộ toàn Đà Nẵng từ 2 tỷ 400 triệu đến 2 tỷ 600 triệu')
        self.assertEqual(self.backend.calls[-1]['minPriceVnd'],'2400000000')
        r=self.chat('Đổi ngân sách tối đa 2 tỷ, tìm lại căn hộ')
        self.assertNotIn('minPriceVnd',self.backend.calls[-1]);self.assertEqual(len(r.recommendedProperties),1)
    def test_amenity_turn_preserves_ids(self):
        r=self.chat('Tìm bất động sản toàn Đà Nẵng 10 tỷ')
        ids=r.evidence['session']['context']['lastPropertyIds']
        self.chat('Ở Sơn Trà có trường nào?')
        self.assertEqual(self.store.begin(self.sid,scope='PUBLIC')[0].last_property_ids,ids)
        r=self.chat('Căn thứ hai cách trường tiểu học bao xa?')
        self.assertEqual(r.recommendedProperties[0]['id'],ids[1])
        self.assertTrue(self.backend.last_nearby.endswith('000000000002'))
        self.assertIn('chưa',r.answer.lower())
    def test_priority_keeps_budget_and_ordinal_identity(self):
        r=self.chat('Tìm căn hộ 10 tỷ toàn Đà Nẵng, ưu tiên trường học')
        original=[p['id'] for p in r.recommendedProperties]
        self.backend.rows=list(reversed(self.backend.rows))
        r=self.chat('Căn thứ hai giá 2 tỷ 500 triệu có phù hợp không?')
        self.assertEqual(r.recommendedProperties[0]['id'],original[1])
        self.assertEqual(Decimal(self.backend.calls[-1]['budgetVnd']),Decimal(10000000000))
        r=self.chat('Đổi sang ưu tiên siêu thị')
        self.assertEqual(self.backend.calls[-1]['amenityPriorities'][0],'SUPERMARKET')
        self.assertEqual(Decimal(self.backend.calls[-1]['budgetVnd']),Decimal(10000000000))
    def test_empty_search_retires_old_reference(self):
        self.chat('Tìm bất động sản toàn Đà Nẵng 10 tỷ')
        r=self.chat('Tôi chỉ có 850 triệu, tìm bất động sản')
        self.assertEqual(r.evidence['responseKind'],'NO_MATCHES')
        self.assertEqual(r.evidence['session']['context']['lastPropertyIds'],[])
    def test_missing_reference_and_rental_budget_do_not_search(self):
        r=self.chat('Căn thứ hai có gì?')
        self.assertEqual(r.evidence['clarification'],'MISSING_PROPERTY_REFERENCE')
        r=self.chat('Tôi muốn thuê căn hộ 10 triệu/tháng')
        self.assertEqual(r.evidence['clarification'],'RENTAL_BUDGET_NOT_SUPPORTED')
        self.assertEqual(self.backend.calls,[])
    def test_profile_consent_is_rechecked(self):
        profile={'subject':'123','enabled':True,'selectedNeeds':['PRIMARY_SCHOOL','SUPERMARKET'],'primaryNeed':'PRIMARY_SCHOOL','district':'Sơn Trà'}
        r=self.bot.chat(ChatRequest(question='Tôi có 10 tỷ tìm căn hộ'),account=profile)
        self.assertEqual(self.backend.calls[-1]['amenityPriorities'][0],'SCHOOL')
        sid=r.evidence['session']['id']
        profile['enabled']=False
        r=self.bot.chat(ChatRequest(question='Tôi có 2 tỷ 600 triệu tìm nhà toàn Đà Nẵng',sessionId=sid),account=profile)
        self.assertNotIn('amenityPriorities',self.backend.calls[-1])
        self.assertNotEqual(sid,r.evidence['session']['id'])
    def test_amenity_district_does_not_change_housing_district(self):
        self.chat('Tìm căn hộ Sơn Trà 10 tỷ')
        self.chat('Hải Châu có bệnh viện nào?')
        self.assertEqual(self.store.begin(self.sid,scope='PUBLIC')[0].last_criteria['district'],'Sơn Trà')
    def test_session_namespaces_and_expiry(self):
        clock=[0];store=SessionStore(clock=lambda:clock[0]);a,sid,_=store.begin(None,scope='ACCOUNT:1')
        self.assertFalse(store.begin(sid,scope='ACCOUNT:2')[2]);clock[0]=1801
        self.assertFalse(store.begin(sid,scope='ACCOUNT:1')[2])
    def test_exact_ward_evidence_no_district_substitution(self):
        corpus=self.bot.knowledge.load()
        corpus['documents'] += [document('area:ward','Ward fixture','http://127.0.0.1:18080/api/v1/amenities/ward','TEST_V1','AREA_AMENITY',{'district':'Liên Chiểu','areaLevel':'WARD','areaName':'Hòa Khánh','areaId':'ward'}),
            document('poi:ward','Trường A thuộc hồ sơ Hòa Khánh; chưa có khoảng cách.','http://127.0.0.1:18080/api/v1/amenities/ward','TEST_V1','POI_EVIDENCE',{'district':'Liên Chiểu','category':'SCHOOL','areaId':'ward'})]
        self.bot.knowledge=SimpleNamespace(load=lambda:corpus)
        r=self.chat('Có trường nào gần Hòa Khánh?')
        self.assertIn('poi:ward',r.evidence['retrievedSourceIds'])
        self.assertNotIn('poi:test',r.evidence['retrievedSourceIds'])
        self.assertEqual(r.evidence['amenityIntent']['ward'],'Hòa Khánh')
        self.assertFalse(r.evidence['amenityIntent']['mapAvailable'])
        r=self.chat('Ở khu này có trường nào nữa?')
        self.assertEqual(r.evidence['amenityIntent']['ward'],'Hòa Khánh')
    def test_unknown_ward_does_not_return_other_district(self):
        self.chat('Tìm bất động sản Sơn Trà 10 tỷ')
        for q in ['Có bệnh viện nào gần Hòa Khánh?', 'Phường Không Có có trường nào?']:
            r=self.chat(q)
            self.assertEqual(r.evidence['clarification'],'AMENITY_LOCALITY_UNRESOLVED')
            self.assertEqual(r.recommendedProperties,[])
    def test_budget_only_updates_without_search(self):
        for q,amount in [('Ngân sách của tôi là 850 triệu',850000000),('Tôi có 7 tỷ 850 triệu',7850000000)]:
            r=self.chat(q)
            self.assertEqual(r.evidence['responseKind'],'CRITERIA_UPDATED')
            self.assertEqual(r.evidence['intent'],'UPDATE_CRITERIA')
            self.assertEqual(r.recommendedProperties,[])
            self.assertEqual(Decimal(r.evidence['session']['context']['criteria']['budgetVnd']),Decimal(amount))
            self.assertEqual(self.backend.calls,[])
        r=self.chat('Tìm bất động sản theo tiêu chí đã lưu')
        self.assertTrue(r.recommendedProperties)
        self.assertEqual(len(self.backend.calls),1)
    def test_mall_question_uses_places_and_preserves_search_district(self):
        self.chat('Tìm căn hộ toàn Đà Nẵng 7 tỷ 850 triệu')
        count=len(self.backend.calls)
        corpus=self.bot.knowledge.load()
        corpus['documents'].append(document('area:hc','District fixture','http://127.0.0.1:18080/api/v1/amenities/hc','TEST_V1','AREA_AMENITY',{'district':'Hải Châu','areaLevel':'DISTRICT','areaId':'hc'}))
        self.bot.knowledge=SimpleNamespace(load=lambda:corpus)
        def places(district,category):
            self.backend.place_calls.append((district,category))
            return {'items':[{'id':'test-mall','name':'Mall fixture','category':category,'district':district,'sourceName':'geoapify','sourceUrl':'https://www.geoapify.com/','observedAt':'2026-11-13T00:00:00Z'}]}
        self.backend.amenity_map=places
        r=self.chat('Ở Hải Châu có những trung tâm thương mại nào?')
        self.assertEqual(r.evidence['intent'],'AREA_AMENITIES')
        self.assertEqual(self.backend.place_calls[-1],('Hải Châu','MALL'))
        self.assertEqual(len(self.backend.calls),count)
        self.assertEqual(r.recommendedProperties,[])
        self.assertIn('Mall fixture',r.answer)
        self.assertNotIn('district',self.store.begin(self.sid,scope='PUBLIC')[0].last_criteria)
        r=self.chat('Có nhà nào dưới 2600 triệu không?')
        self.assertEqual(len(r.recommendedProperties),2)
        self.assertNotIn('district',self.backend.calls[-1])
    def test_knowledge_and_unknown_never_replay_houses(self):
        self.chat('Tìm bất động sản toàn Đà Nẵng 10 tỷ')
        count=len(self.backend.calls)
        for q,intent in [('Sổ hồng là gì?','LEGAL_QA'),('Lãi suất vay ngân hàng hiện bao nhiêu?','KNOWLEDGE'),('Nói chuyện khác nhé','CLARIFY')]:
            r=self.chat(q)
            self.assertEqual(r.evidence['intent'],intent)
            self.assertEqual(len(self.backend.calls),count)
            self.assertEqual(r.recommendedProperties,[])
    def test_query_failure_is_distinct_from_no_matches(self):
        from app.rag.tools import UpstreamError
        def fail(*args,**kwargs):raise UpstreamError()
        self.backend.recommend=fail
        r=self.chat('Tìm bất động sản toàn Đà Nẵng 2 tỷ')
        self.assertEqual(r.evidence['responseKind'],'DATA_SOURCE_ERROR')
        self.assertNotEqual(r.evidence['responseKind'],'NO_MATCHES')
    def test_pharmacy_is_not_a_house_search(self):
        self.chat('Tìm bất động sản toàn Đà Nẵng 10 tỷ')
        count=len(self.backend.calls)
        for q in ['Ở Sơn Trà có nhà thuốc nào?', 'Có nhà trẻ nào ở Sơn Trà không?']:
            r=self.chat(q)
            self.assertEqual(r.evidence['intent'],'AREA_AMENITIES')
            self.assertEqual(len(self.backend.calls),count)
    def test_optional_intake_does_not_capture_area_question(self):
        self.chat('Tìm căn hộ 2 tỷ')
        r=self.chat('Ở Sơn Trà có những bệnh viện nào?')
        self.assertEqual(r.evidence['intent'],'AREA_AMENITIES')
        self.assertNotEqual(r.evidence.get('clarification'),'LIFESTYLE_INTAKE')
    def test_followup_price_does_not_update_budget(self):
        self.chat('Tìm bất động sản toàn Đà Nẵng 10 tỷ')
        r=self.chat('Căn thứ hai giá 2 tỷ 500 triệu có phù hợp không?')
        self.assertEqual(r.evidence['intent'],'PROPERTY_FOLLOWUP')
        self.assertEqual(Decimal(self.backend.calls[-1]['budgetVnd']),Decimal(10000000000))
    def test_http_chat_contract_multiple_turns(self):
        from fastapi.testclient import TestClient
        from app.rag.api import create_chat_app
        from app.rag.config import Settings
        with TestClient(create_chat_app(Settings(),self.bot)) as client:
            first=client.post('/chat',json={'question':'Tôi có 10 tỷ tìm bất động sản toàn Đà Nẵng'})
            self.assertEqual(first.status_code,200)
            second=client.post('/chat',json={'question':'Tôi có 2 tỷ 600 triệu, có bất động sản phù hợp không?', 'sessionId':first.json()['evidence']['session']['id']})
            self.assertEqual(second.status_code,200)
            body=second.json()
            self.assertEqual(Decimal(body['evidence']['criteria']['budgetVnd']),Decimal(2600000000))
            self.assertTrue(all(Decimal(str(p['priceVnd']))<=2600000000 for p in body['recommendedProperties']))
            self.assertEqual(second.headers['cache-control'],'no-store')
            invalid=client.post('/chat',json={'question':'test','budgetVnd':2,'minPriceVnd':3})
            self.assertEqual(invalid.status_code,422)
    def test_area_places_are_current_deduplicated_and_not_budget_intake(self):
        self.backend.amenity_map=lambda district,category: {'items':[{'name':'Bệnh viện A'},{'name':'Bệnh viện A'},{'name':'Bệnh viện B'}]}
        result=self.chat('Ở Hải Châu có những bệnh viện nào?')
        self.assertEqual(result.evidence['responseKind'],'AREA_AMENITIES')
        self.assertEqual(result.answer.count('Bệnh viện A'),1)
        self.assertNotIn('DISTRICT_FACILITY',result.answer)
        self.assertNotIn('poi-evidence',result.answer)
        self.assertNotIn('ngân sách',result.answer)
        self.assertEqual(result.evidence['amenityIntent']['district'],'Hải Châu')

    def test_places_failure_is_not_a_chat_502(self):
        from app.rag.tools import UpstreamError
        def fail(*args):raise UpstreamError()
        self.backend.amenity_map=fail
        r=self.chat('Ở Sơn Trà có bệnh viện nào?')
        self.assertEqual(r.evidence['responseKind'],'INSUFFICIENT_AMENITY_EVIDENCE')
        self.assertTrue(any('Dịch vụ địa điểm' in v for v in r.dataLimitations))
    def test_min_price_schema_validation(self):
        with self.assertRaises(ValueError):ChatRequest(question='test',budgetVnd=2,minPriceVnd=3)

class ToolGuardTests(unittest.TestCase):
    def test_actual_tool_rejects_over_budget_and_under_floor(self):
        for price in [4000000000,1000000000]:
            tool=BackendTools(SimpleNamespace(backend_url='http://127.0.0.1:18080',backend_timeout_seconds=2))
            tool.client.close()
            tool.client=httpx.Client(base_url='http://127.0.0.1:18080',transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'method':'HEURISTIC_V1_1','mode':'SAFE','topProperties':[candidate(1,price)]})))
            try:
                with self.assertRaises(GroundingError):tool.recommend({'budgetVnd':2600000000,'minPriceVnd':2000000000})
            finally:tool.close()

if __name__=='__main__':unittest.main()
