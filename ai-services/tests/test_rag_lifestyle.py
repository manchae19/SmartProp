import unittest
import test_rag_multiturn as fixtures
from app.rag.schemas import ChatRequest

class LifestyleConversationTests(unittest.TestCase):
    def service(self):
        return fixtures.MultiTurnTests().service(props=[fixtures.prop("property:a",1600000000,90)])
    def send(self, service, question, previous=None):
        return service.chat(ChatRequest(question=question,sessionId=previous.evidence["session"]["id"] if previous else None))
    def test_mixed_search_updates_preferences_and_preserves_hard_filters(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tìm căn hộ dưới 2 tỷ ở Đà Nẵng, ưu tiên trường học")
        self.assertEqual(len(a.recommendedProperties),1)
        self.assertEqual(b.recommend.call_args.args[0]["amenityPriorities"],["SCHOOL"])
        c=self.send(s,"Đổi sang ưu tiên siêu thị",a)
        criteria=b.recommend.call_args.args[0]
        self.assertEqual(criteria["budgetVnd"],"2000000000")
        self.assertEqual(criteria["propertyType"],"APARTMENT")
        self.assertEqual(criteria["amenityPriorities"],["SUPERMARKET"])
        self.assertEqual(c.evidence["needs"]["priorities"],["SUPERMARKET"])
        self.assertEqual(c.evidence["amenityIntent"]["categories"],[])
    def test_one_optional_question_then_free_text_and_school_level_limit(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tôi muốn tìm căn hộ tầm 2 tỷ")
        self.assertEqual(a.evidence["needs"]["pending"],"location")
        self.assertEqual(a.answer.count("?"),1)
        b.recommend.assert_not_called()
        c=self.send(s,"Tôi mua để ở cùng gia đình tại Đà Nẵng",a)
        self.assertEqual(c.evidence["needs"]["pending"],"priorities")
        self.assertIn("Xem gợi ý ngay",c.evidence["quickReplies"])
        d=self.send(s,"Ưu tiên trường tiểu học, có siêu thị thì tốt",c)
        self.assertEqual(b.recommend.call_args.args[0]["amenityPriorities"],["SCHOOL","SUPERMARKET"])
        self.assertTrue(any("chưa xác nhận trường tiểu học" in x for x in d.dataLimitations))
    def test_skip_and_refine_do_not_change_budget(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tìm căn hộ 2 tỷ")
        c=self.send(s,"Xem gợi ý ngay",a)
        self.assertEqual(len(c.recommendedProperties),1)
        d=self.send(s,"Tìm kỹ hơn",c)
        self.assertEqual(d.evidence["needs"]["pending"],"priorities")
        e=self.send(s,"Công viên",d)
        self.assertEqual(b.recommend.call_args.args[0]["amenityPriorities"],["PARK"])
        self.assertEqual(b.recommend.call_args.args[0]["budgetVnd"],"2000000000")
    def test_budget_required_even_when_skipping(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tìm căn hộ ở Đà Nẵng")
        c=self.send(s,"Xem gợi ý ngay",a)
        self.assertEqual(c.evidence["needs"]["pending"],"budget")
        b.recommend.assert_not_called()
    def test_poi_only_and_ordinal_do_not_become_new_intake(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tìm căn hộ dưới 2 tỷ ở Cẩm Lệ, ưu tiên trường học")
        calls=b.recommend.call_count
        self.send(s,"Khu này có trường nào?",a)
        self.assertEqual(b.recommend.call_count,calls)
        c=self.send(s,"Căn thứ hai có gì?",a)
        self.assertEqual(c.evidence["clarification"],"PROPERTY_INDEX_OUT_OF_RANGE")
        self.assertEqual(b.recommend.call_args.args[0]["amenityPriorities"],["SCHOOL"])
    def test_no_matches_has_real_empty_search_not_fake_poi_replacement(self):
        s,b,_,_=self.service();b.recommend.return_value["topProperties"]=[]
        a=self.send(s,"Tìm căn hộ dưới 2 tỷ ở Đà Nẵng, ưu tiên trường học")
        self.assertEqual(a.evidence["responseKind"],"NO_MATCHES")
        self.assertEqual(a.recommendedProperties,[])
    def test_family_does_not_infer_school_preference(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tìm căn hộ 2 tỷ cho gia đình tại Đà Nẵng")
        self.assertEqual(a.evidence["needs"]["priorities"],[])
        self.assertEqual(a.evidence["needs"]["pending"],"priorities")

if __name__ == '__main__': unittest.main()