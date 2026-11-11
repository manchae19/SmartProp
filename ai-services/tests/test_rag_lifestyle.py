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

    def test_guided_intake_asks_each_step_and_applies_criteria(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tư vấn từng bước")
        self.assertEqual(a.evidence["needs"]["pending"],"purpose")
        self.assertIn("Mua để ở",a.evidence["quickReplies"])
        b.recommend.assert_not_called()
        a=self.send(s,"Mua để ở",a)
        self.assertEqual(a.evidence["needs"]["pending"],"budget")
        a=self.send(s,"3 tỷ",a)
        self.assertEqual(a.evidence["needs"]["pending"],"location")
        a=self.send(s,"Hải Châu",a)
        self.assertEqual(a.evidence["needs"]["pending"],"property_type")
        a=self.send(s,"Căn hộ",a)
        self.assertEqual(a.evidence["needs"]["pending"],"min_area")
        a=self.send(s,"80 m²",a)
        self.assertEqual(a.evidence["needs"]["pending"],"priorities")
        a=self.send(s,"Gần trường học",a)
        self.assertEqual(len(a.recommendedProperties),1)
        c=b.recommend.call_args.args[0]
        self.assertEqual(c["purpose"],"LIVING")
        self.assertEqual(c["propertyType"],"APARTMENT")
        self.assertEqual(c["budgetVnd"],"3000000000")
        self.assertEqual(c["district"],"Hải Châu")
        self.assertEqual(c["minAreaSqm"],"80")
        self.assertEqual(c["amenityPriorities"],["SCHOOL"])
    def test_guided_skip_optional_questions_still_returns_verified_result(self):
        s,b,_,_=self.service()
        a=self.send(s,"Tư vấn từng bước")
        a=self.send(s,"Bỏ qua",a)
        a=self.send(s,"3 tỷ",a)
        a=self.send(s,"Xem gợi ý ngay",a)
        a=self.send(s,"Bỏ qua",a)
        a=self.send(s,"Bỏ qua",a)
        a=self.send(s,"Xem gợi ý ngay",a)
        self.assertEqual(len(a.recommendedProperties),1)
        c=b.recommend.call_args.args[0]
        self.assertEqual(c["budgetVnd"],"3000000000")
        self.assertNotIn("amenityPriorities",c)
    def test_household_questions_are_optional_session_only_and_children_maps_to_school(self):
        s,b,_,_=self.service();profile={"subject":"1","enabled":True,"district":"Cẩm Lệ","selectedNeeds":[],"primaryNeed":None}
        def send(q,prev=None): return s.chat(ChatRequest(question=q,sessionId=prev.evidence["session"]["id"] if prev else None),account=profile)
        a=send("Tư vấn theo hộ gia đình")
        self.assertEqual(a.evidence["needs"]["pending"],"purpose")
        a=send("Mua để ở",a);a=send("3 tỷ",a);a=send("Cẩm Lệ",a);a=send("Căn hộ",a);a=send("60 m²",a)
        self.assertEqual(a.evidence["needs"]["pending"],"family")
        a=send("Bỏ qua",a)
        self.assertEqual(a.evidence["needs"]["pending"],"children")
        a=send("Có trẻ nhỏ",a)
        self.assertEqual(a.evidence["needs"]["pending"],"age")
        a=send("Bỏ qua",a)
        self.assertEqual(a.evidence["needs"]["pending"],"priorities")
        a=send("Xem gợi ý ngay",a)
        c=b.recommend.call_args.args[0]
        self.assertIn("SCHOOL",c["amenityPriorities"])
        self.assertIn("PARK",c["amenityPriorities"])
        self.assertNotIn("hasChildren",str(a.evidence));self.assertNotIn("ageGroup",str(a.evidence))
        self.assertNotIn("hasChildren",str(profile));self.assertNotIn("ageGroup",str(profile))

    def test_saved_children_needs_confirmation_before_school_priority(self):
        s,b,_,_=self.service();profile={"subject":"1","enabled":True,"district":"Hải Châu","selectedNeeds":[],"primaryNeed":None,"hasChildren":True,"childrenCount":2}
        def send(q,prev=None): return s.chat(ChatRequest(question=q,sessionId=prev.evidence["session"]["id"] if prev else None),account=profile)
        a=send("Tư vấn từng bước")
        for q in ["Mua để ở","3 tỷ","Hải Châu","Nhà phố","50 m²"]: a=send(q,a)
        self.assertEqual(a.evidence["needs"]["pending"],"children_needs")
        b.recommend.assert_not_called()
        a=send("Có, ưu tiên trường học và công viên",a)
        self.assertIsNone(a.evidence["needs"]["pending"])
        self.assertIn("SCHOOL",a.evidence["criteria"]["amenityPriorities"])
        self.assertIn("PARK",a.evidence["criteria"]["amenityPriorities"])
        c=b.recommend.call_args.args[0]
        self.assertIn("SCHOOL",c["amenityPriorities"]);self.assertIn("PARK",c["amenityPriorities"])
        self.assertNotIn("hasChildren",str(a.evidence))
    def test_property_cards_are_enriched_with_real_poi_and_image(self):
        s,b,_,_=self.service()
        b.nearby_pois.return_value=[{"name":"Trường A","category":"SCHOOL","distanceMeters":350.0}]
        b.property_image.return_value="/api/v1/properties/property:a/images/x/content"
        a=self.send(s,"Tìm căn hộ dưới 2 tỷ ở Đà Nẵng, ưu tiên trường học")
        p=a.recommendedProperties[0]
        self.assertEqual(p["nearbyPoisStatus"],"AVAILABLE")
        self.assertEqual(p["nearbyPois"][0]["name"],"Trường A")
        self.assertEqual(p["nearbyPoisDistanceType"],"STRAIGHT_LINE")
        self.assertEqual(p["imageUrl"],"/api/v1/properties/property:a/images/x/content")

    def test_external_property_is_not_enriched_with_local_image_or_poi(self):
        p=fixtures.prop("external:x",1600000000,80)
        p["source"]={"kind":"EXTERNAL","recordKey":"ext:x","name":"External"}
        p["qualityStatus"]="VALID";p["verificationStatus"]="VERIFIED"
        s,b,_,_=fixtures.MultiTurnTests().service(props=[p])
        a=self.send(s,"Tìm căn hộ dưới 2 tỷ ở Đà Nẵng")
        card=a.recommendedProperties[0]
        self.assertEqual(card["nearbyPoisStatus"],"NOT_APPLICABLE")
        self.assertNotIn("imageUrl",card);self.assertFalse(card.get("nearbyPois"))
        b.nearby_pois.assert_not_called();b.property_image.assert_not_called()

if __name__ == '__main__': unittest.main()