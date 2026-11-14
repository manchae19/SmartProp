import unittest
from unittest.mock import Mock
from fastapi.testclient import TestClient
import test_rag_multiturn as fixtures
from app.rag.schemas import ChatRequest
from app.rag.api import create_chat_app
from app.rag.config import Settings
from app.rag.tools import BackendTools, UpstreamError
import httpx

class AccountPreferencesTests(unittest.TestCase):
    def service(self):
        return fixtures.MultiTurnTests().service(props=[fixtures.prop("property:a",1600000000,90)])
    def profile(self, **kw):
        return {"subject":"1","enabled":True,"district":"Cẩm Lệ","selectedNeeds":["PRIMARY_SCHOOL","SUPERMARKET","PARK"],"primaryNeed":"PRIMARY_SCHOOL",**kw}
    def send(self,s,q,p,previous=None):
        return s.chat(ChatRequest(question=q,sessionId=previous.evidence["session"]["id"] if previous else None),account=p)
    def test_saved_needs_seed_and_chat_override_does_not_mutate_profile(self):
        s,b,_,_=self.service();p=self.profile()
        a=self.send(s,"Tôi muốn tìm căn hộ tầm 2 tỷ",p)
        self.assertEqual(len(a.recommendedProperties),1)
        c=b.recommend.call_args.args[0]
        self.assertEqual(c["district"],"Cẩm Lệ")
        self.assertEqual(c["amenityPriorities"],["SCHOOL","SUPERMARKET","PARK"])
        self.assertIn("Đang dùng nhu cầu đã lưu",str(a.evidence["needs"]["summary"]))
        self.assertTrue(any("chưa xác nhận trường tiểu học" in v for v in a.dataLimitations))
        self.send(s,"Lần này ưu tiên siêu thị hơn trường học",p,a)
        c=b.recommend.call_args.args[0]
        self.assertEqual(c["amenityPriorities"][0],"SUPERMARKET")
        self.assertEqual(c["budgetVnd"],"2000000000")
        self.assertEqual(c["propertyType"],"APARTMENT")
        self.assertEqual(p["primaryNeed"],"PRIMARY_SCHOOL")
    def test_consent_off_and_clear_drop_profile_context_on_next_turn(self):
        for change in ({"enabled":False},{"selectedNeeds":[],"primaryNeed":None,"enabled":False}):
            s,b,_,_=self.service()
            a=self.send(s,"Tìm căn hộ 2 tỷ",self.profile())
            b.recommend.reset_mock()
            p=self.profile(**change)
            reply=self.send(s,"Tìm căn hộ 2 tỷ ở Đà Nẵng",p,a)
            c=b.recommend.call_args.args[0]
            self.assertNotIn("amenityPriorities",c)
            self.assertNotIn("district",c)
            self.assertNotEqual(a.evidence["session"]["id"],reply.evidence["session"]["id"])
    def test_account_switch_and_guest_cannot_resume_profile_session(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tìm căn hộ 2 tỷ",self.profile())
        b.recommend.reset_mock()
        reply=self.send(s,"Tìm căn hộ 2 tỷ ở Đà Nẵng",self.profile(subject="2",enabled=False),a)
        self.assertNotIn("amenityPriorities",b.recommend.call_args.args[0])
        self.assertNotEqual(a.evidence["session"]["id"],reply.evidence["session"]["id"])
        guest=s.chat(ChatRequest(question="Tìm căn hộ 2 tỷ ở Đà Nẵng",sessionId=a.evidence["session"]["id"]))
        self.assertNotIn("amenityPriorities",b.recommend.call_args.args[0])
        self.assertNotEqual(a.evidence["session"]["id"],guest.evidence["session"]["id"])
    def test_unsupported_preferences_are_not_scored_and_family_not_inferred(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tìm căn hộ 2 tỷ",self.profile(selectedNeeds=["GYM","CAFE"],primaryNeed="GYM"))
        self.assertNotIn("amenityPriorities",b.recommend.call_args.args[0])
        self.assertIn("Phòng gym",str(a.dataLimitations))
    def test_mixed_search_and_poi_question_still_distinct(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tìm nhà dưới 2 tỷ, ưu tiên gần siêu thị",self.profile())
        self.assertEqual(b.recommend.call_args.args[0]["amenityPriorities"],["SUPERMARKET"])
        calls=b.recommend.call_count
        self.send(s,"Khu này có siêu thị nào?",self.profile(),a)
        self.assertEqual(b.recommend.call_count,calls)
    def test_route_reads_authenticated_backend_context_each_turn(self):
        s,b,_,_=self.service();b.account_context.return_value=self.profile()
        client=TestClient(create_chat_app(Settings(),s))
        self.assertEqual(client.post("/chat/personalized",json={"question":"Tìm căn hộ 2 tỷ"}).status_code,401)
        for _ in range(2):
            r=client.post("/chat/personalized",headers={"Authorization":"Bearer valid"},json={"question":"Tìm căn hộ 2 tỷ"})
            self.assertEqual(r.status_code,200)
        self.assertEqual(b.account_context.call_count,2)
        self.assertNotIn("authorization",str(b.recommend.call_args).lower())
        self.assertEqual(client.post("/chat",json={"question":"hi","account":{"subject":"1"}}).status_code,422)
    def test_invalid_token_is_not_downgraded_to_profile_or_research(self):
        s,b,_,_=self.service();b.account_context.side_effect=UpstreamError(401)
        client=TestClient(create_chat_app(Settings(),s))
        r=client.post("/chat/personalized",headers={"Authorization":"Bearer expired"},json={"question":"Tìm căn hộ 2 tỷ"})
        self.assertEqual(r.status_code,401)
        b.recommend.assert_not_called()
    def test_backend_request_only_forwards_bearer_to_fixed_profile_endpoint(self):
        settings=Settings();b=BackendTools(settings)
        requests=[]
        def handle(request):
            requests.append(request)
            return httpx.Response(200,json=self.profile())
        b.client.close()
        b.client=httpx.Client(base_url=settings.backend_url,transport=httpx.MockTransport(handle))
        self.assertEqual(b.account_context("Bearer test")["subject"],"1")
        self.assertEqual(requests[0].url.path,"/api/v1/users/me/advisor-context")
        self.assertEqual(requests[0].headers["authorization"],"Bearer test")
        self.assertNotIn("X-SmartProp-Demo-Key",requests[0].headers)
