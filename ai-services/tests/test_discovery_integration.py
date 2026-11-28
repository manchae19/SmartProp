import copy
import unittest
from decimal import Decimal
import test_chat_budget_context as base
from test_chat_budget_context import candidate
from app.rag.schemas import ChatRequest
class DiscoveryIntegrationTests(unittest.TestCase):
    setUp=base.ConversationTests.setUp
    chat=base.ConversationTests.chat
    def test_address_keeps_budget_and_has_public_citations(self):
        self.chat('Ngân sách của tôi là 2 tỷ 600 triệu')
        rows=[candidate(1,2500000000),candidate(2,4000000000)]
        for row in rows:row['address']='300 Dũng Sĩ Thanh Khê, Đà Nẵng'
        def search(address, *, criteria):
            self.assertEqual(Decimal("2600000000"), Decimal(criteria["budgetVnd"]))
            return {"items": rows, "total": 2, "complete": True}
        self.backend.search_by_address = search
        r=self.chat('Tìm nhà ở 300 Dũng Sĩ Thanh Khê')
        self.assertEqual(1,len(r.recommendedProperties))
        self.assertEqual(1,len(r.citations))
        self.assertLessEqual(r.recommendedProperties[0]['priceVnd'],2600000000)
    def test_nearby_requires_consent_and_choice(self):
        calls=[]
        self.backend.geocode_workplace=lambda address:calls.append(address) or [{'latitude':16.06,'longitude':108.22,'label':'Fixture point'}]
        self.backend.search_nearby=lambda *a,**k:{'items':[{**candidate(1,2000000000),'latitude':16.061,'longitude':108.22}], 'complete':True}
        r=self.chat('Tìm nhà gần 300 Dũng Sĩ Thanh Khê')
        self.assertEqual([],calls)
        self.assertEqual('NEAR_ADDRESS_CONSENT',r.evidence['clarification'])
        r=self.chat('Đồng ý tìm vị trí');self.assertEqual(1,len(calls))
        r=self.chat('1. Fixture point');self.assertEqual(1,len(r.recommendedProperties))
        self.assertLess(r.recommendedProperties[0]['distanceMeters'],1000)
    def test_hard_commute_retains_budget(self):
        self.chat('Tìm căn hộ toàn Đà Nẵng dưới 2 tỷ 600 triệu')
        r=self.chat('Tìm nhà đi làm tối đa 25 phút')
        self.assertEqual('COMMUTE_DESTINATION_REQUIRED',r.evidence['clarification'])
        self.chat('Nhập địa điểm khác')
        self.backend.geocode_workplace=lambda a:[{'latitude':16.06,'longitude':108.22,'label':'Office fixture'}]
        self.backend.commute_matrix=lambda ids,*a:{'provider':'FIXTURE','cells':[{'propertyId':pid,'durationSeconds':(600 if i==0 else 2400),'distanceMeters':1000} for i,pid in enumerate(ids)]}
        r=self.chat('300 Dũng Sĩ Thanh Khê')
        self.assertTrue(all(p['priceVnd']<=2600000000 for p in r.recommendedProperties))
        self.assertTrue(all(p['commute']['durationSeconds']<=1500 for p in r.recommendedProperties))
        self.assertEqual(1,len(r.recommendedProperties))

    def test_amenity_question_interrupts_workplace_prompt(self):
        self.chat('Tìm căn hộ toàn Đà Nẵng dưới 2 tỷ 600 triệu')
        self.chat('Tìm nhà đi làm tối đa 25 phút')
        r=self.chat('Ở Hải Châu có bệnh viện nào?')
        self.assertEqual('AREA_AMENITIES',r.evidence['intent'])
        self.assertNotEqual('COMMUTE_DESTINATION_REQUIRED',r.evidence.get('clarification'))
    def test_route_outage_is_not_empty_market(self):
        from app.rag.config import GroundingError
        self.chat('Tìm căn hộ toàn Đà Nẵng dưới 2 tỷ 600 triệu')
        ctx=self.store.begin(self.sid,scope='PUBLIC')[0]
        ctx.needs['commuteDestination']={'latitude':16.06,'longitude':108.22,'label':'fixture'}
        def unavailable(*args):raise GroundingError('ROUTE_NOT_CONFIGURED')
        self.backend.commute_matrix=unavailable
        r=self.chat('Tìm nhà đi làm tối đa 25 phút')
        self.assertEqual('COMMUTE_DATA_UNAVAILABLE',r.evidence['responseKind'])

    def test_geocoding_failure_is_not_empty_search(self):
        from app.rag.tools import UpstreamError
        def unavailable(address):raise UpstreamError(503)
        self.backend.geocode_workplace=unavailable
        self.chat('Tìm nhà gần 300 Dũng Sĩ Thanh Khê')
        r=self.chat('Đồng ý tìm vị trí')
        self.assertEqual('DATA_SOURCE_ERROR',r.evidence['responseKind'])
        self.assertEqual([],r.recommendedProperties)
