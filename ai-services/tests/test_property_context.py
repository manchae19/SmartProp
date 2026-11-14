import unittest
from app.rag.property_context import focused_reply
from app.rag.tools import UpstreamError
from app.rag.config import GroundingError
from app.rag.schemas import ChatRequest
ID="92f76120-ac9b-4b3d-bb9b-a3c387c757a3"
class Backend:
    def public_property(self, ident):
        assert ident==ID
        return dict(id=ID,title="Tin thử riêng",price="2600000000",areaSqm="80",currency="VND",priceUnit="TOTAL",address="Đà Nẵng")
class PropertyContextTests(unittest.TestCase):
    def test_public_facts_without_recommendation_score(self):
        result=focused_reply(Backend(),ID,"căn này")
        self.assertIn("2.600.000.000",result["answer"])
        self.assertEqual([],result["properties"])
        self.assertEqual("PROPERTY_DETAIL",result["citations"][0].kind)
    def test_unavailable_does_not_retain_reference(self):
        class Missing:
            def public_property(self,ident):raise UpstreamError(404)
        self.assertTrue(focused_reply(Missing(),ID,"căn này")["extra"]["clearPropertyContext"])
    def test_provider_error_is_not_no_results(self):
        class Broken:
            def public_property(self,ident):raise UpstreamError(503)
        with self.assertRaises(UpstreamError):focused_reply(Broken(),ID,"căn này")
    def test_reference_is_uuid_not_browser_facts(self):
        with self.assertRaises(ValueError):ChatRequest(question="căn này",propertyId="../../private")
        with self.assertRaises(ValueError):ChatRequest(question="căn này",propertyId=ID,ownerEmail="fake@example.com")

class ListingAnalysisTests(unittest.TestCase):
    def result(self, **overrides):
        class Listing:
            def public_property(self,ident):
                return dict(id=ID,title="Bán Apartment dòng tiền 35tr/1tháng",price="11000000000",areaSqm="400",currency="VND",priceUnit="TOTAL",transactionType="SALE",**overrides)
        return focused_reply(Listing(),ID,"Căn này có nên đầu tư hay không?")
    def test_revenue_scenario_is_explicit_not_verified(self):
        r=self.result();m=r["extra"]["listingAnalysis"]
        self.assertEqual("3.82",m["grossRevenueToAskingPricePercent"])
        self.assertEqual("27500000",m["askingPricePerDeclaredSqmVnd"])
        self.assertFalse(m["independentlyVerified"])
        self.assertIn("chưa phải lợi suất ròng",r["answer"])
    def test_conflicting_income_not_used(self):
        m=self.result(description="Doanh thu 45 triệu/tháng")["extra"]["listingAnalysis"]
        self.assertEqual("CONFLICT",m["rentalClaimStatus"])
        self.assertNotIn("grossRevenueToAskingPricePercent",m)
    def test_missing_income_never_invented(self):
        from app.rag.property_context import listing_analysis
        a,m=listing_analysis(dict(title="Nhà 7 phòng ngủ",priceUnit="TOTAL",transactionType="SALE"),"phân tích",2600000000,80)
        self.assertEqual("MISSING",m["rentalClaimStatus"])
        self.assertNotIn("grossRevenueToAskingPricePercent",m)
    def test_negated_or_forecast_claim_rejected(self):
        from app.rag.property_context import monthly_income_claim
        for title in ("Không có doanh thu 35 triệu/tháng","Doanh thu dự kiến 35 triệu/tháng","Cho thuê tối đa 35tr/tháng"):
            self.assertIsNone(monthly_income_claim(dict(title=title))[0])
    def test_rental_price_not_purchase_denominator(self):
        from app.rag.property_context import listing_analysis
        a,m=listing_analysis(dict(title="Cho thuê 35tr/tháng",priceUnit="PER_MONTH",transactionType="RENT"),"đầu tư",35000000,80)
        self.assertNotIn("grossRevenueToAskingPricePercent",m)
        self.assertNotIn("askingPricePerDeclaredSqmVnd",m)

class DomainBoundaryTests(unittest.TestCase):
    def test_outside_domain_with_existing_property(self):
        from app.rag.scope import domain_reply
        from app.rag.followup import classification
        for question in ("Ngày mai thời tiết Đà Nẵng thế nào?","Tôi nên mua cổ phiếu nào?","Hãy viết code Python giúp tôi","Bệnh viện này chữa bệnh gì?"):
            self.assertIsNotNone(domain_reply(question,classification(question,None)))
    def test_real_estate_questions_remain_supported(self):
        from app.rag.scope import domain_reply
        from app.rag.followup import classification
        for question in ("Căn này có nên đầu tư không?","Tìm nhà dưới 2 tỷ","Ở Hải Châu có bệnh viện nào?","Quy hoạch Đà Nẵng thế nào?"):
            self.assertIsNone(domain_reply(question,classification(question,None)))
