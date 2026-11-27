from decimal import Decimal
import re
import unicodedata
from .config import GroundingError, RagUnavailable
from .knowledge import digest
from .schemas import ChatResponse, Citation
from .validator import render_answer, validate_plan, validate_generated_answer, validate_generated_relevance
from urllib.parse import quote
from .gis import gis_evidence
from .diagnostics import traced, event, reason
from .intent import asks_for_amenities, empty_search_answer, poi_categories, CATEGORY_LABELS, insufficient_amenity_answer
from .followup import (classification, detect_district, budget_from_followup)
from .session import SessionStore, MAX_PROPERTY_IDS
from .money import parse_budget, format_vnd
from .locality import amenity_locality, is_listing_location_edit
from .tool_registry import ToolRegistry
from .market import market_query, market_response
from .property_context import focused_reply
from .scope import domain_reply
from .discovery import AREA_RANGE_PROMPT, AdvisorDiscoveryMixin
from . import commute_destination, commute_ranking
from .personalization import describe_area, intake, merge_area, projection


LIMITATIONS = [
    "Giá là giá rao, không phải giá giao dịch hoặc kết quả định giá mới.",
    "Điểm Recommendation là heuristic Hybrid V1.1, không phải AI cá nhân hóa đã huấn luyện hoặc dự báo sinh lời.",
    "Tiện ích là bằng chứng cấp khu vực; không suy ra GPS, khoảng cách hoặc thời gian đi từ từng bất động sản.",
    "RAG không xác minh pháp lý, tình trạng còn bán hoặc mức độ an toàn của bất động sản.",
]


def norm(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d")) if not unicodedata.combining(c))


def number(value):
    return format(Decimal(str(value)), "f").rstrip("0").rstrip(".") if "." in format(Decimal(str(value)), "f") else format(Decimal(str(value)), "f")


def budget_from_question(question):
    parsed = parse_budget(question)
    return parsed.maximum if parsed.status == "VALID" else None


from .account_preferences import fingerprint, seed

# Districts the public catalog covers; used to seed a saved profile before any branch returns.
SUPPORTED_DISTRICTS = ["Hải Châu", "Sơn Trà", "Thanh Khê", "Cẩm Lệ", "Ngũ Hành Sơn", "Liên Chiểu", "Hòa Vang"]
from .tools import UpstreamError

class ChatOrchestrator(AdvisorDiscoveryMixin):
    def __init__(self, backend, repository, knowledge, retriever, llm, sessions=None, document_advisor=None):
        self.backend, self.repository, self.knowledge = backend, repository, knowledge
        self.retriever, self.llm = retriever, llm
        # Bounded in-memory conversation memory. Never persisted, never authoritative.
        self.sessions = sessions or SessionStore()
        self.tools = ToolRegistry(backend)
        self.document_advisor=document_advisor
        from .planning_chat import PlanningAdvisor
        settings=getattr(backend,"settings",None)
        self.planning_advisor=PlanningAdvisor(getattr(settings,"planning_snapshot_path",None),enabled=getattr(settings,"planning_enabled",False))

    def _enrich(self, properties):
        """Attach real image + straight-line POI evidence to visible platform properties.

        The existing public property/POI endpoints remain the source of truth. Missing or
        non-public evidence is marked explicitly; nothing is invented and no travel time
        is estimated.
        """
        for p in properties:
            if not isinstance(p, dict):
                continue
            source = p.get("source") or {}
            if source.get("kind") != "PROPERTY":
                p["nearbyPoisStatus"] = "NOT_APPLICABLE"
                continue
            property_id = source.get("recordKey")
            p["nearbyPois"] = []
            p["nearbyPoisStatus"] = "UNAVAILABLE"
            p["nearbyPoisDistanceType"] = "STRAIGHT_LINE"
            p["nearbyPoisRadiusMeters"] = 1000
            p["nearbyPoisLimitations"] = ["Khoảng cách là đường chim bay từ toạ độ tin đăng; chưa tính thời gian di chuyển thực tế."]
            image_fn = getattr(self.backend, "property_image", None)
            if callable(image_fn):
                try:
                    image = image_fn(property_id)
                    if isinstance(image, str):
                        p["imageUrl"] = image
                except Exception:
                    p["imageUrl"] = None
            poi_fn = getattr(self.backend, "nearby_pois", None)
            if callable(poi_fn):
                try:
                    items = poi_fn(property_id)
                    if isinstance(items, list):
                        p["nearbyPois"] = items
                        p["nearbyPoisStatus"] = "AVAILABLE" if items else "NO_POIS_IN_RADIUS"
                except UpstreamError as error:
                    if error.status == 404:
                        p["nearbyPoisStatus"] = "PROPERTY_NOT_PUBLIC"
                except GroundingError:
                    pass

    # ------------------------------------------------------------------
    def _reply(self, request, session_id, context, criteria, *, properties, citations, research,
               answer, responseKind=None, limitations=None, response=None, extra=None,
               evidence=None, generation_mode="EVIDENCE_ONLY", retrieval_mode="TOOL_EVIDENCE_ONLY",
               result_properties=None, reference_id=None):
        """Single exit point: every reply records bounded state and returns the session id.

        `properties` is what the user sees; `result_properties` is the full verified
        result set of this turn, which is what the next turn must be able to reference.
        """
        address_search = bool(extra and extra.get("addressQuery"))
        if properties and address_search:
            for p in properties:
                uid=p["id"].split(":")[-1]
                p.setdefault("source",{"kind":"PROPERTY","recordKey":uid,"name":"SmartProp"})
                p.setdefault("qualityStatus","PLATFORM_PUBLISHED");p.setdefault("verificationStatus","PLATFORM_PUBLISHED")
                p.setdefault("score",0);p.setdefault("explanations",[]);p.setdefault("warnings",[])
                p["matchBasis"]="ADDRESS"
            citations=[Citation(sourceId="property:"+p["source"]["recordKey"],url="/api/v1/properties/"+p["source"]["recordKey"],version=str(p.get("contentVersion") or "1"),contentHash=digest(p),scope="PUBLIC",kind="PROPERTY_DETAIL",title=p["title"]) for p in properties]
        if properties:
            self._enrich(properties)
        # Only a completed search replaces result references; POI/clarification replies preserve them.
        if result_properties is None and not properties and (response or {}).get("topProperties") is not None:
            result_properties = response["topProperties"]
        if address_search:
            criteria = {**criteria, "lastSearchEmpty": not properties and extra["addressSearchComplete"]}
        preserve_references = response is None and not properties and not address_search
        full = list(result_properties if result_properties is not None else properties)
        property_ids = [p["id"] for p in full][:MAX_PROPERTY_IDS]
        self.sessions.record(context,
            criteria={**{k: v for k, v in (criteria or {}).items() if k not in ("sessionTurn", "_propertyIds")},
                      "_propertyIds": list(context.last_property_ids) if preserve_references else property_ids} if criteria else None,
            property_ids=None if preserve_references else property_ids,
            area_ids=None if preserve_references else [a.get("amenityAreaId") for a in (response or {}).get("topAreas", []) if a.get("amenityAreaId")],
            evidence_ids=[c.sourceId for c in citations],
            referenced_property_id=reference_id,
            question=request.question)
        payload = dict(evidence or {})
        payload["intent"] = context.needs.get("turnIntent")
        payload["intentFamily"]=context.needs.get("turnIntentFamily")
        if context.needs.get("unsupportedPopularityFilter"):
            limitations=list(limitations or [])+["Chưa có bằng chứng để xác nhận tin nào đang thịnh hành; kết quả chỉ theo bộ lọc tin đăng có thể kiểm chứng."]
        if responseKind:
            payload["responseKind"] = responseKind
        payload["session"] = {"id": session_id, "turn": context.turns, "context": context.public()}
        if extra:
            payload.update(extra)
        if responseKind not in ("FOCUSED_PROPERTY_EVIDENCE","PROPERTY_UNAVAILABLE","OUT_OF_SCOPE") and context.needs.get("active") and context.needs.get("turnIntent") not in ("MARKET_ANALYSIS","MARKET_PRICE","MARKET_TREND","LEGAL_QA","PLANNING_QA","KNOWLEDGE","AREA_AMENITIES","PLANNING_LOOKUP"):
            needs = projection(context, criteria or {})
            payload["needs"] = needs
            if not payload.get("quickReplies"):
                payload["quickReplies"] = ["Tìm kỹ hơn"] if properties else []
            limitations = list(dict.fromkeys(list(limitations or []) + needs["limitations"]))
        return ChatResponse(answer=answer, mode="INTERNAL_RESEARCH" if research else "SAFE",
            generationMode=generation_mode, retrievalMode=retrieval_mode, citations=list(citations),
            recommendedProperties=list(properties), evidence=payload, dataLimitations=list(limitations or []))

    def chat(self, request, *, research=False, token=None, account=None):
        # Authorization happens BEFORE corpus retrieval or backend/sql tools.
        if research:
            traced("research_authorization", lambda: self.backend.authorize_research(token))
        # Session scope comes from the authenticated route, never from the client payload,
        # so a public caller cannot address (or read) a research context.
        scope = "INTERNAL_RESEARCH" if research else ("ACCOUNT:"+account["subject"] if account else "PUBLIC")
        context, session_id, resumed = traced("session_begin",
            lambda: self.sessions.begin(request.sessionId, scope=scope))
        if account:
            current_fingerprint=fingerprint(account)
            if context.needs.get("accountFingerprint") not in (None,current_fingerprint):
                # Revoke every profile-derived reference on consent/profile change, including an open session.
                self.sessions.drop(context)
                context,session_id,resumed=self.sessions.begin(None,scope=scope)
            context.needs["accountFingerprint"]=current_fingerprint
        turn = classification(request.question, context if resumed else None, districts=SUPPORTED_DISTRICTS)
        context.needs["turnIntent"]=turn["intent"]
        context.needs["turnIntentFamily"]=turn["intentFamily"]
        context.needs["unsupportedPopularityFilter"]=turn["unsupportedPopularityFilter"]
        event("intent_decision", intent=turn["intent"], budgetMentioned=turn["budgetMentioned"],
              tool="KNOWLEDGE_MARKET" if turn["intent"]=="MARKET_ANALYSIS" else "MARKET_SUMMARY" if turn["intent"] in ("MARKET_PRICE","MARKET_TREND") else "PLACES" if turn["intent"]=="AREA_AMENITIES" else "RECOMMENDATION" if turn["searchChange"] or turn["intent"]=="PROPERTY_FOLLOWUP" else "NONE")
        # The saved profile must be seeded before any branch can return, otherwise a
        # focused or commute turn runs without the account context it needs.
        if account and not resumed:
            seed(context,account,SUPPORTED_DISTRICTS)
        planning=self.planning_advisor.reply(request.question,context)
        if planning is not None:
            context.needs["turnIntent"]="PLANNING_LOOKUP"
            return self._reply(request,session_id,context,context.criteria(),research=research,**planning)
        # While the session waits for a commute destination, the three official replies
        # belong to that flow and must reach the state machine, not the scope filter.
        pending = ("COMMUTE_DESTINATION_REQUIRED"
                   if context.needs.get("commuteStage") == commute_destination.ASK_SOURCE else None)
        outside=domain_reply(request.question,turn,pending=pending)
        if outside and not (context.needs.get("listingAddressScope") and is_listing_location_edit(request.question)):
            return self._reply(request,session_id,context,{},properties=[],citations=[],research=research,
                answer=outside,responseKind="OUT_OF_SCOPE",extra={"quickReplies":["Tìm nhà theo ngân sách","Phân tích đầu tư căn này" ] if request.propertyId or context.needs.get("focusedPropertyId") else ["Tìm nhà theo ngân sách","Ở Hải Châu có bệnh viện nào?"]})
        discovery_reply=self.dispatch_discovery(request,session_id,context,turn,districts=SUPPORTED_DISTRICTS,
                                                research=research,token=token,account=account)
        if discovery_reply is not None:return discovery_reply
        resuming_commute_search = context.needs.pop("commuteResumeSearch", False)
        if resuming_commute_search:
            turn["intent"]="REFINE_SEARCH";turn["searchChange"]=True
        focus=request.propertyId or context.needs.get("focusedPropertyId")
        if focus and not turn["searchChange"] and turn["intent"] not in ("MARKET_ANALYSIS","MARKET_PRICE","MARKET_TREND","AREA_AMENITIES","UPDATE_CRITERIA","PLANNING_QA","KNOWLEDGE"):
            context.needs["focusedPropertyId"]=focus
            result=focused_reply(self.backend,focus,request.question)
            if result.get("extra",{}).get("clearPropertyContext"): context.needs.pop("focusedPropertyId",None)
            return self._reply(request,session_id,context,{},research=research,**result)
        if focus and turn["searchChange"]:
            context.needs.pop("focusedPropertyId",None)
        if turn["intent"]=="MARKET_ANALYSIS":
            # Popularity/demand research is not a listing query or a price snapshot.
            # Reuse district parsing, without asking for a rental pricing unit.
            query,question=market_query(request.question,context.needs.get("marketScope"),turn["propertyType"],price_statistics=False)
            if question:
                return self._reply(request,session_id,context,context.criteria(),properties=[],citations=[],research=research,
                    answer=question,responseKind="CLARIFICATION_REQUIRED",extra={"clarification":"MARKET_SCOPE"})
            context.needs["marketScope"]=query
            scope=query.get("district") or "Đà Nẵng"
            missing="Cần báo cáo theo phân khúc tại "+scope+", kỳ thống kê/so sánh, số liệu lượt tìm kiếm hoặc quan tâm, lượng giao dịch/hấp thụ và nguồn cùng thời điểm cập nhật. Giá chào và số tin hiện có không chứng minh mức độ thịnh hành."
            if self.document_advisor:
                reply=self.document_advisor.reply(request.question,"MARKET",district=query.get("district"))
                reply.setdefault("extra",{})["marketAnalysis"]={"district":query.get("district"),"topic":"DEMAND_AND_TRENDS"}
                if reply["responseKind"] in ("KNOWLEDGE_EVIDENCE","KNOWLEDGE_SOURCE_CONFLICT","STALE_KNOWLEDGE_DATA","CLARIFICATION_REQUIRED") or reply["extra"].get("toolResult",{}).get("status") in ("SOURCE_UNAVAILABLE","INVALID_EVIDENCE"):
                    reply["limitations"].append(missing)
                    return self._reply(request,session_id,context,context.criteria(),research=research,**reply)
            return self._reply(request,session_id,context,context.criteria(),properties=[],citations=[],research=research,
                answer="Đây là câu hỏi phân tích thị trường, không cần ngân sách mua nhà. Hiện chưa đủ bằng chứng để kết luận loại bất động sản nào đang thịnh hành tại "+scope+". "+missing,
                responseKind="INSUFFICIENT_MARKET_ANALYSIS_DATA",limitations=[missing],
                extra={"marketAnalysis":{"district":query.get("district"),"topic":"DEMAND_AND_TRENDS"},"toolResult":{"name":"knowledge","status":"INSUFFICIENT_DATA"}})
        if turn["intent"] in ("MARKET_PRICE","MARKET_TREND"):
            query,question=market_query(request.question,context.needs.get("marketScope"),turn["propertyType"])
            if question:
                if query is not None:context.needs["marketScope"]=query
                return self._reply(request,session_id,context,context.criteria(),properties=[],citations=[],research=research,
                    answer=question,responseKind="CLARIFICATION_REQUIRED",extra={"clarification":"MARKET_SCOPE"})
            context.needs["marketScope"]=query
            result=self.tools.execute("market_summary",query)
            reply=market_response(result,query,trend=turn["intent"]=="MARKET_TREND")
            if turn["intent"]=="MARKET_TREND" and self.document_advisor:
                document_reply=self.document_advisor.reply(request.question,"MARKET",district=query.get("district"))
                if document_reply["responseKind"] in ("KNOWLEDGE_EVIDENCE","KNOWLEDGE_SOURCE_CONFLICT"):
                    return self._reply(request,session_id,context,context.criteria(),research=research,**document_reply)
            return self._reply(request,session_id,context,context.criteria(),properties=[],citations=reply["citations"],research=research,
                answer=reply["answer"],responseKind=reply["kind"],limitations=reply["limitations"],extra=reply["extra"])
        if turn["intent"] in ("LEGAL_QA","PLANNING_QA","KNOWLEDGE") and self.document_advisor:
            topic={"LEGAL_QA":"LEGAL","PLANNING_QA":"PLANNING"}.get(turn["intent"],"INFRASTRUCTURE" if re.search(r"ha tang|tien do|cau duong",norm(request.question)) else "GENERAL")
            reply=self.document_advisor.reply(request.question,topic)
            return self._reply(request,session_id,context,context.criteria(),research=research,**reply)
        if turn["intent"] in ("LEGAL_QA","PLANNING_QA"):
            context.needs["knowledgeTopic"]=turn["intent"]
            topic="quy hoạch" if turn["intent"]=="PLANNING_QA" else "pháp lý"
            return self._reply(request,session_id,context,context.criteria(),properties=[],citations=[],research=research,
                answer="Tôi nhận đây là câu hỏi "+topic+". Kho tri thức hiện chưa có tài liệu chính thức phù hợp để kết luận. Bạn cung cấp văn bản hoặc nêu rõ địa bàn/vấn đề cần đối chiếu; tôi không dùng giá rao hay hồ sơ tiện ích để xác nhận nội dung này.",
                responseKind="KNOWLEDGE_SOURCE_UNAVAILABLE",extra={"knowledgeTopic":turn["intent"],"toolResult":{"name":"knowledge","status":"INSUFFICIENT_DATA","reason":"NO_APPROVED_DOCUMENTS"}})
        if turn["intent"] in ("KNOWLEDGE","CLARIFY"):
            if turn["intent"]=="KNOWLEDGE":
                answer="Tôi nhận đây là câu hỏi kiến thức/tư vấn, không phải yêu cầu tìm nhà. Kho bằng chứng hiện tại chủ yếu có tin đăng và tiện ích; chưa có tài liệu nguồn phù hợp để trả lời chắc chắn nội dung này. Bạn nêu rõ vấn đề hoặc cung cấp tài liệu để đối chiếu nhé."
            else:
                answer="Bạn muốn tìm bất động sản, xem tiện ích ở khu vực nào, cập nhật tiêu chí hay hỏi về một căn đã xem? Tôi chưa gọi công cụ tìm nhà khi mục đích chưa rõ."
            return self._reply(request,session_id,context,context.criteria(),properties=[],citations=[],research=research,
                answer=answer,responseKind="KNOWLEDGE_SOURCE_UNAVAILABLE" if turn["intent"]=="KNOWLEDGE" else "CLARIFICATION_REQUIRED",
                extra={"quickReplies":["Tìm bất động sản theo tiêu chí đã lưu","Ở Hải Châu có bệnh viện nào?"]})
        event("session_turn", resumed=resumed, turn=context.turns,
              followup=bool(turn["searchChange"] or turn["ordinal"] or turn["mapRequest"] or turn["analytic"]))
        if turn["searchChange"]:
            context.needs.pop("amenityScope",None)
        limitations = list(LIMITATIONS)
        corpus = traced("corpus_load", self.knowledge.load)
        if traced("amenity_summary", self.backend.amenity_summary)["catalogVersion"] != corpus["summary"]["catalogVersion"]:
            raise GroundingError("PUBLIC_CORPUS_VERSION_DRIFT")
        documents = corpus["documents"]
        names = sorted({d["metadata"].get("district", "") for d in documents} | set(SUPPORTED_DISTRICTS),
                       key=len, reverse=True)
        # The profile was already seeded before any early-return branch; seeding again
        # here would only repeat the same work.
        # A confirmed workplace address is a route destination, not a listing filter.
        explicit_district = request.district or (None if resuming_commute_search else detect_district(request.question, names))
        # A follow-up that only refines one criterion keeps every other stored criterion.
        prior = context.criteria()
        district = explicit_district or prior.get("district")
        # Explicit POI categories are a routing rule, never a similarity guess.
        categories = poi_categories(request.question)
        amenity_scope = None
        if categories and not turn["searchChange"] and turn["ordinal"] is None and not turn["needsPropertyReference"]:
            amenity_scope = amenity_locality(request.question,documents)
            # An explicit district-only question must not be misread as an unresolved ward.
            if explicit_district and not re.search(r"\b(phuong|xa|duong|street)\b",unicodedata.normalize("NFD",request.question.lower().replace("đ","d")).encode("ascii","ignore").decode()):
                amenity_scope = None
            if amenity_scope and (amenity_scope.get("unresolved") or (explicit_district and explicit_district != amenity_scope.get("district"))):
                return self._reply(request,session_id,context,prior,properties=[],citations=[],research=research,
                    answer="Chưa có hồ sơ nguồn xác định đúng phường/xã hoặc tuyến đường bạn hỏi. Tôi không tự mở rộng kết quả sang cả quận. Bạn nêu rõ địa bàn hoặc chọn một căn có ghim để tìm tiện ích xung quanh nhé.",
                    responseKind="CLARIFICATION_REQUIRED",extra={"clarification":"AMENITY_LOCALITY_UNRESOLVED","amenityIntent":{"district":explicit_district,"categories":list(categories),"mapAvailable":False}})
            if amenity_scope:
                district=amenity_scope["district"]
                context.needs["amenityScope"]=amenity_scope
            elif explicit_district:
                context.needs.pop("amenityScope",None)
            elif context.needs.get("amenityScope"):
                amenity_scope=context.needs["amenityScope"]
                district=amenity_scope["district"]
        parsed_budget = parse_budget(request.question)
        if turn["budgetMentioned"] and parsed_budget.status == "AMBIGUOUS":
            return self._reply(request, session_id, context, prior, properties=[], citations=[], research=research,
                answer="Tôi chưa xác định rõ giới hạn ngân sách mới nên chưa tìm bằng ngân sách cũ. Bạn nhập mức tối đa, ví dụ 2 tỷ 600 triệu, hoặc khoảng từ 2 đến 3 tỷ nhé.",
                responseKind="CLARIFICATION_REQUIRED", extra={"clarification":"BUDGET_AMBIGUOUS", "budgetReason":parsed_budget.reason})
        if parsed_budget.status != "NOT_MENTIONED" and re.search(r"(?:/\s*(?:thang|nam)|moi thang|moi nam)",norm(request.question)):
            return self._reply(request, session_id, context, prior, properties=[], citations=[], research=research,
                answer="Bạn đang nói tới tiền thuê theo tháng/năm. Công cụ tư vấn này hiện lọc theo tổng giá mua, nên tôi chưa dùng số tiền thuê để tìm nhà bán. Bạn có thể tìm tin cho thuê tại trang Bất động sản.",
                responseKind="CLARIFICATION_REQUIRED",extra={"clarification":"RENTAL_BUDGET_NOT_SUPPORTED"})
        if (turn["ordinal"] is not None or turn["intent"]=="PROPERTY_FOLLOWUP") and not context.last_property_ids:
            return self._reply(request,session_id,context,prior,properties=[],citations=[],research=research,
                answer="Chưa có danh sách căn để đối chiếu trong phiên này. Bạn gửi mã tin hoặc tìm lại bằng ngân sách và khu vực nhé.",
                responseKind="CLARIFICATION_REQUIRED",extra={"clarification":"MISSING_PROPERTY_REFERENCE"})
        asked_budget = parsed_budget.maximum if turn["budgetChange"] else None
        budget = request.budgetVnd if request.budgetVnd is not None else (asked_budget if asked_budget is not None else (
            Decimal(str(prior["budgetVnd"])) if prior.get("budgetVnd") is not None else None))
        criteria = request.model_dump(exclude={"question", "requireGeneration", "sessionId", "propertyId"}, exclude_none=True)
        if asked_budget is not None:
            if parsed_budget.minimum is not None:
                criteria["minPriceVnd"] = str(parsed_budget.minimum)
        elif request.budgetVnd is None and prior.get("minPriceVnd") is not None:
            criteria["minPriceVnd"] = prior["minPriceVnd"]
        # Defaults are not client intent: carry the stored value unless the caller overrides it.
        if criteria.get("purpose") == "LIVING" and prior.get("purpose"):
            criteria["purpose"] = prior["purpose"]
        if criteria.get("propertyType") == "ALL" and prior.get("propertyType"):
            criteria["propertyType"] = prior["propertyType"]
        if not merge_area(criteria, prior, request.question if turn["searchChange"] or turn["intent"] == "UPDATE_CRITERIA" else "",
                          allow_bare=context.needs.get("pending") == "min_area"):
            return self._reply(request, session_id, context, prior, properties=[], citations=[], research=research,
                answer=AREA_RANGE_PROMPT, responseKind="CLARIFICATION_REQUIRED",
                extra={"clarification": "AREA_RANGE_INVALID"})
        if turn["purpose"]:
            criteria["purpose"] = turn["purpose"]
        if turn["propertyType"]:
            criteria["propertyType"] = turn["propertyType"]
        if not request.ward and prior.get("ward") and (
            not explicit_district or norm(explicit_district).split() == norm(prior.get("district") or "").split()
        ):
            criteria["ward"] = prior["ward"]
        pure_amenity = bool(categories) and not turn["searchChange"] and turn["ordinal"] is None and not turn["needsPropertyReference"]
        if district is not None and not pure_amenity:
            criteria["district"] = district
        elif pure_amenity:
            if prior.get("district"): criteria["district"] = prior["district"]
            else: criteria.pop("district", None)
        if prior.get("amenityPriorities"):
            criteria["amenityPriorities"] = list(prior["amenityPriorities"])
        response = None
        properties = []
        # An amenity-only follow-up must not spend a Recommendation call.
        amenity_only = bool(categories) and not turn["searchChange"] and turn["ordinal"] is None
        referral = turn["needsPropertyReference"]
        if budget is not None:
            criteria["budgetVnd"] = str(budget)
        if turn["intent"]=="UPDATE_CRITERIA":
            context.needs["active"]=True
            text="Đã cập nhật tiêu chí cho phiên trò chuyện này."
            if budget is not None:text+=" Ngân sách tối đa: "+format_vnd(budget)+"."
            if criteria.get("minPriceVnd"):text+=" Giá tối thiểu: "+format_vnd(criteria["minPriceVnd"])+"."
            text+=" Tôi chưa tự tìm nhà; bạn có thể yêu cầu tìm theo tiêu chí này. Hồ sơ tài khoản không thay đổi."
            return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=research,
                answer=text,responseKind="CRITERIA_UPDATED",extra={"quickReplies":["Tìm bất động sản theo tiêu chí đã lưu"]})
        if turn["intent"]=="AREA_AMENITIES" and district and categories and not amenity_scope:
            # Area questions use current Places evidence, never recommendation intake or raw corpus prose.
            found=[]; provider_errors=0
            for category in categories:
                try:
                    mapped=self.tools.data("places",district,category)
                    found.extend(mapped.get("items",[]))
                except (UpstreamError,GroundingError):
                    provider_errors+=1
            names=list(dict.fromkeys(i["name"].strip() for i in found if i.get("name")))
            label=", ".join(CATEGORY_LABELS.get(c,c) for c in categories)
            answer=(f"Tại {district}, dữ liệu địa điểm có: "+"; ".join(names[:12])+". Chọn ghim trên bản đồ để xem địa điểm và nguồn.") if names else f"Chưa lấy được địa điểm {label} có tọa độ phù hợp tại {district}. Bạn có thể thử lại sau."
            citations=[Citation(sourceId="poi-evidence:"+digest({"district":district,"categories":list(categories)})[:16],url="/api/v1/amenities/"+next((d["metadata"]["areaId"] for d in documents if d["kind"]=="AREA_AMENITY" and d["metadata"].get("areaLevel")=="DISTRICT" and d["metadata"].get("district")==district),"district"),version="POI_MAP_V1",contentHash=digest(found),kind="POI_EVIDENCE",scope="PUBLIC",title="Địa điểm tại "+district)] if names else []
            return self._reply(request,session_id,context,criteria,properties=[],citations=citations,research=research,answer=answer,responseKind="AREA_AMENITIES" if names else "INSUFFICIENT_AMENITY_EVIDENCE",extra={"amenityIntent":{"district":district,"categories":list(categories),"mapAvailable":True}},limitations=["Địa điểm theo nguồn bản đồ, chưa xác minh thực địa hoặc giờ hoạt động."]+(["Dịch vụ địa điểm chưa sẵn sàng; vui lòng thử lại."] if provider_errors else []))
        if turn["intent"]=="AREA_AMENITIES":
            context.needs.pop("pending",None)
            decision={"search":False,"question":None,"choices":[]}
        else:
            decision = intake(context, request.question, criteria, turn, explicit_district=explicit_district)
        district = (explicit_district or district) if amenity_only and not decision["search"] else criteria.get("district")
        if decision["question"]:
            return self._reply(request, session_id, context, criteria, properties=[], citations=[], research=research,
                answer=decision["question"], responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"quickReplies": decision["choices"], "clarification": "LIFESTYLE_INTAKE"})
        if decision["search"]:
            # A mixed house+amenity request ranks houses; it is not a POI-only question.
            categories = ()
            amenity_only = False
        # A changed budget/district always re-queries the live API. A stored list is
        # never replayed as a new result set; it only names what to ask about.
        must_search = budget is not None and (decision["search"] or turn["intent"]=="PROPERTY_FOLLOWUP")
        if must_search:
            if budget is None:
                limitations.append("Chưa có ngân sách trong ngữ cảnh; không thể xác định lại danh sách bất động sản.")
            else:
                if context.needs.get("commutePendingLimit") and commute_destination.destination_of(context.needs) and not research:
                    criteria["limit"]=6
                try:
                    response = traced("recommendation", lambda: self.tools.data("recommendation",criteria, research=research, token=token))
                except UpstreamError:
                    if request.requireGeneration:raise
                    return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=research,
                        answer="Chưa truy vấn được nguồn bất động sản. Đây là lỗi kết nối/công cụ, không phải kết luận không có tin phù hợp. Bạn thử lại sau nhé.",
                        responseKind="DATA_SOURCE_ERROR",extra={"queryStatus":"UPSTREAM_ERROR"})
                properties = response["topProperties"]
                pending=context.needs.get("commutePendingLimit")
                destination=commute_destination.destination_of(context.needs)
                if pending and destination and not research:
                    pool=list(properties)
                    properties=self._rank_by_commute(properties,destination,pending.get("minutes"),pending.get("kind") or "SOFT",limitations)
                    if pool and not properties and pending.get("kind")=="HARD" and not any(p.get("commute") for p in pool):
                        return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=research,
                            answer="Chưa có đủ dữ liệu tuyến đường để xác nhận giới hạn đi làm. Không thể kết luận là không có nhà phù hợp; bạn có thể bỏ điều kiện thời gian hoặc thử lại.",
                            responseKind="COMMUTE_DATA_UNAVAILABLE",limitations=limitations,extra={"quickReplies":["Bỏ qua","Tìm theo ngân sách"]})
                    response={**response,"topProperties":properties}
        else:
            limitations.append("Chưa có một ngân sách rõ ràng; hệ thống chưa gọi công cụ lọc bất động sản.")

        # ---- property reference resolution (deterministic, never guessed) ----
        # `result_properties` is the full verified result set of THIS turn and stays the
        # reference universe for the next turn; only the visible selection is narrowed.
        result_properties = list(properties)
        asked_index = turn["ordinal"]
        referenced_id = None
        if asked_index is not None and resumed and context.last_property_ids and not turn["searchChange"]:
            previous_ids=list(context.last_property_ids)
            if not 1<=asked_index<=len(previous_ids):
                return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=research,
                    answer=f"Căn thứ {asked_index} nằm ngoài danh sách đã hiển thị. Không có căn ở vị trí đó.",
                    responseKind="CLARIFICATION_REQUIRED", extra={"clarification": "PROPERTY_INDEX_OUT_OF_RANGE"})
            expected_id=previous_ids[asked_index-1]
            current={p["id"]:p for p in result_properties}
            if expected_id not in current:
                # Absence from this turn's recommendation set says nothing about whether the
                # listing is still public: a follow-up question runs no search. Ask the public
                # detail route, which is the only authority on publication state.
                try:
                    detail=self.backend.property_detail(expected_id.split(":",1)[-1])
                except GroundingError as error:
                    if "PROPERTY_NOT_PUBLIC" in str(error):
                        return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=research,
                            answer="Căn ở thứ tự đó không còn được công khai. Tôi không thay bằng một căn khác và không dùng giá cũ.",responseKind="CLARIFICATION_REQUIRED",result_properties=result_properties)
                    return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=research,
                        answer="Chưa tra cứu được tin ở thứ tự đó nên tôi chưa thể trả lời. Bạn thử lại sau ít phút.",responseKind="CLARIFICATION_REQUIRED",result_properties=result_properties)
                except UpstreamError:
                    return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=research,
                        answer="Chưa tra cứu được tin ở thứ tự đó nên tôi chưa thể trả lời. Bạn thử lại sau ít phút.",responseKind="CLARIFICATION_REQUIRED",result_properties=result_properties)
                # Keep the position the user saw; never slide to a neighbouring card.
                # The detail route already carries the public source record key. A listing
                # fetched this way has no recommendation score, so the card omits it.
                current[expected_id]={**detail,"score":0,"explanations":[],"warnings":[]}
                result_properties=list(current.values())
            ordered=[current[i] for i in previous_ids if i in current]
            result_properties=ordered+[p for p in result_properties if p["id"] not in previous_ids]
            # Resolve by identity even if an earlier result disappeared.
            asked_index=next(i+1 for i,p in enumerate(result_properties) if p["id"]==expected_id)
        if asked_index is not None and result_properties and not turn["searchChange"]:
            if not 1 <= asked_index <= len(result_properties):
                if request.requireGeneration:
                    raise RagUnavailable("AMBIGUOUS_PROPERTY_REFERENCE")
                return self._reply(request, session_id, context, criteria, properties=[], citations=[], research=research,
                    answer=(f"Trong lượt trước chỉ có {len(result_properties)} bất động sản được đề xuất, nên không có "
                            f"bất động sản thứ {asked_index}. Bạn muốn xem lại danh sách hay đổi tiêu chí tìm kiếm?"),
                    responseKind="CLARIFICATION_REQUIRED", limitations=limitations, response=response,
                    extra={"clarification": "PROPERTY_INDEX_OUT_OF_RANGE"})
            properties = [result_properties[asked_index - 1]]
            referenced_id = "recommendation:" + properties[0]["id"]
        elif referral and not turn["searchChange"]:
            # An explicit "căn này" must resolve to the property the user just saw, even
            # though the stored list is the full verified result set of the turn.
            explicit = context.referenced_property_id or prior.get("referencedPropertyId")
            if explicit is not None and result_properties:
                match = [p for p in result_properties
                         if p["id"] == explicit or "recommendation:" + p["id"] == explicit or "property:" + p["id"] == explicit]
                if match:
                    properties = match
                    referenced_id = "recommendation:" + match[0]["id"]
            if referenced_id is None:
                previous = list(prior.get("_propertyIds") or [])
                if len(previous) == 1:
                    properties = [p for p in result_properties if p["id"] == previous[0]] or properties
                    referenced_id = "recommendation:" + previous[0] if properties else None
                elif len(previous) > 1 or len(result_properties) > 1:
                    if request.requireGeneration:
                        raise RagUnavailable("AMBIGUOUS_PROPERTY_REFERENCE")
                    return self._reply(request, session_id, context, criteria, properties=[], citations=[], research=research,
                        answer=("Bạn đang nói tới bất động sản nào? Lượt trước có nhiều lựa chọn. "
                                "Hãy nói rõ thứ tự, ví dụ “căn thứ hai”, hoặc gửi lại mã/tên bất động sản."),
                        responseKind="CLARIFICATION_REQUIRED", limitations=limitations, response=response,
                        extra={"clarification": "AMBIGUOUS_PROPERTY_REFERENCE"})

        if turn.get("domain") and turn["intent"]=="PROPERTY_FOLLOWUP":
            topic="quy hoạch" if turn["domain"]=="PLANNING" else "pháp lý"
            citations=[Citation(sourceId="recommendation:"+p["id"],url=self.backend.settings.backend_url+"/api/v1/recommendations",version="LIVE",contentHash=digest(p),scope="INTERNAL_RESEARCH" if research else "PUBLIC",kind="RECOMMENDATION",title=p["title"]) for p in properties]
            return self._reply(request,session_id,context,criteria,properties=properties,citations=citations,research=research,
                answer="Đã đối chiếu căn đang tham chiếu, nhưng API công khai chưa cung cấp bằng chứng "+topic+" đủ điều kiện. Tôi không coi tin đăng hoặc giá rao là xác nhận pháp lý/quy hoạch và không truy cập giấy tờ riêng tư của chủ tin.",
                responseKind="KNOWLEDGE_SOURCE_UNAVAILABLE",response=response,result_properties=result_properties,reference_id=referenced_id)
        distance_question=bool(re.search(r"(?:bao xa|khoang cach|cach .*truong|gan .*nao)",norm(request.question)))
        if categories and distance_question and len(properties)==1 and (asked_index is not None or referral):
            property=properties[0]
            source=property.get("source") or {}
            groups={"SCHOOL":"education","SUPERMARKET":"shopping","MARKET":"shopping","HOSPITAL":"health","PHARMACY":"health","PARK":"park","PUBLIC_TRANSPORT":"transport"}
            chosen=list(dict.fromkeys(groups[c] for c in categories if c in groups))
            nearby=None
            answer="Chưa có bằng chứng phân biệt trung tâm thương mại trong dữ liệu quanh căn này; tôi không dùng siêu thị hoặc chợ để thay thế." if "MALL" in categories else "Tin này chưa có vị trí căn nhà đủ điều kiện để tính khoảng cách."
            if source.get("kind")=="PROPERTY" and chosen:
                try:
                    nearby=self.backend.property_nearby(source["recordKey"],1000,chosen)
                    location=nearby.get("location") or {}
                    if nearby.get("status")=="LOCATION_UNAVAILABLE":
                        answer="Căn này chưa có tọa độ hợp lệ; chưa thể tính khoảng cách tới tiện ích."
                    elif location.get("accuracy") not in ("EXACT_PROPERTY","BUILDING_ONLY","USER_PROVIDED"):
                        answer="Căn này chỉ có ghim do người đăng cung cấp hoặc vị trí chưa được đối chiếu. Chưa đủ dữ liệu để trả khoảng cách từ căn nhà."
                    else:
                        items=sorted([p for p in nearby["items"] if any(g in chosen for g in p.get("categoryGroups",[]))],key=lambda p:p["distanceMeters"])[:3]
                        origin="tòa nhà (không phải căn hộ cụ thể)" if location["accuracy"]=="BUILDING_ONLY" else "ghim người đăng (chưa xác minh vị trí căn nhà; khoảng cách ước tính)" if location["accuracy"]=="USER_PROVIDED" else "căn nhà"
                        answer=("Khoảng cách đường chim bay từ "+origin+" trong bán kính 1 km: "+"; ".join(p["name"]+": "+(f'{p["distanceMeters"]/1000:.2f} km' if p["distanceMeters"]>=1000 else f'{p["distanceMeters"]:.0f} m') for p in items)+".") if items else "Không tìm thấy tiện ích phù hợp trong bán kính 1 km. Bạn có thể tăng bán kính trên thẻ căn nhà."
                except (UpstreamError,GroundingError):
                    answer="Chưa tải được bằng chứng tiện ích của căn này. Hãy mở mục tiện ích trên thẻ và thử lại."
            if "SCHOOL" in categories:
                answer+=" Nguồn chỉ xác nhận nhóm trường học chung; chưa xác minh trường tiểu học hay cấp học cụ thể."
            citation=Citation(sourceId="recommendation:"+property["id"],url=self.backend.settings.backend_url+"/api/v1/recommendations",version="LIVE",contentHash=digest(property),scope="INTERNAL_RESEARCH" if research else "PUBLIC",kind="RECOMMENDATION",title=property["title"])
            citations=[citation]
            if nearby:
                citations.append(Citation(sourceId="property-nearby:"+source["recordKey"],url=self.backend.settings.backend_url+"/api/v1/properties/"+source["recordKey"]+"/nearby",version=str(nearby.get("fetchedAt") or "LIVE"),contentHash=digest(nearby),scope="INTERNAL_RESEARCH" if research else "PUBLIC",kind="PROPERTY_NEARBY",title="Tiện ích quanh căn nhà"))
            return self._reply(request,session_id,context,criteria,properties=properties,citations=citations,research=research,
                answer=answer,responseKind="PROPERTY_NEARBY_EVIDENCE",limitations=["Khoảng cách đường chim bay, không phải quãng đường hoặc thời gian di chuyển."],
                response=response,result_properties=result_properties,reference_id=referenced_id,
                extra={"propertyNearby":nearby,"referencedPropertyId":property["id"]})

        if not research and response is not None and budget is not None and not properties and (decision["search"] or turn["intent"]=="PROPERTY_FOLLOWUP"):
            # An empty authorized search is useful evidence. Do not replace it with
            # unrelated semantic POIs or claim that a templated answer came from Qwen.
            event("no_match_response", strict=request.requireGeneration, generationRequired=False)
            if request.requireGeneration:
                raise RagUnavailable("FULL_RAG_RUNTIME_UNAVAILABLE")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[], research=research,
                answer=empty_search_answer(criteria, area=describe_area(criteria)), responseKind="NO_MATCHES", limitations=limitations, response=response,
                extra={"quickReplies": ["Tìm bất động sản toàn Đà Nẵng, giữ ngân sách"] if criteria.get("district") else ["Tìm mọi loại bất động sản, giữ ngân sách", "Tìm kỹ hơn"]},
                evidence={"recommendationMethod": response.get("method"),
                    "criteria": criteria, "eligibleCandidateCount": response.get("eligibleCandidateCount"), "topAreas": [],
                    "recommendationSearch": {"performed": True, "resultCount": 0,
                        "sourcePath": "/api/v1/recommendations", "criteriaHash": digest(criteria)},
                    "generation": {"accepted": False, "reason": "NOT_NEEDED_FOR_EMPTY_SEARCH"},
                    "retrievedSourceIds": [], "semanticRetrieval": {"indexVersion": None, "hits": []},
                    "sql": {"status": "NO_PLATFORM_RESULTS", "matchedRows": 0},
                    "gis": gis_evidence([], [], []), "warnings": response.get("warnings", [])})

        # SQL only cross-checks platform IDs obtained from the authorized API, never model text.
        platform = [p for p in properties if p.get("source", {}).get("kind") == "PROPERTY"]
        sql_status, sql_count, rows = "NO_PLATFORM_RESULTS", 0, []
        if platform:
            try:
                rows = traced("sql_crosscheck", lambda: self.repository.lookup([p["source"]["recordKey"] for p in platform]))
                by_id = {r["id"]: r for r in rows}
                for p in platform:
                    row = by_id.get(p["source"]["recordKey"])
                    if row is None or Decimal(str(row["price"])) != Decimal(str(p["priceVnd"])) or Decimal(str(row["area_sqm"])) != Decimal(str(p["areaSqm"])):
                        raise GroundingError("SQL_API_FACT_MISMATCH")
                sql_status, sql_count = "READ_ONLY_MATCHED", len(rows)
            except RagUnavailable as e:
                sql_status = str(e)
                limitations.append("SQL đối chiếu trực tiếp chưa sẵn sàng; giá/diện tích vẫn lấy nguyên từ API Recommendation.")

        retrieval_mode = "E5_FAISS"
        try:
            retrieved = traced("semantic_retrieval", lambda: self.retriever.search(request.question, documents, internal=research, district=district, categories=categories or None, k=3))
        except (RagUnavailable, ImportError):
            retrieval_mode = "TOOL_EVIDENCE_ONLY"
            limitations.append("E5/FAISS chưa sẵn sàng: chỉ dùng bằng chứng API theo khu vực chính xác, không giả lập semantic retrieval.")
            area_ids = [a.get("amenityAreaId") for a in (response or {}).get("topAreas", [])]
            retrieved = [d for d in documents if d["kind"] == "AREA_AMENITY" and d["scope"] == "PUBLIC" and
                         ((d["metadata"].get("district") == district and d["metadata"].get("areaLevel") == "DISTRICT") or
                          d["metadata"]["areaId"] in area_ids)][:3]
            # Exact category routing is an evidence tool, not a replacement embedding model.
            if categories:
                ranked = [d for d in documents if d["kind"] == "POI_EVIDENCE" and d["scope"] == "PUBLIC"
                          and d["metadata"].get("category") in categories
                          and (not district or d["metadata"].get("district") == district)]
                retrieved = ranked[:3]

        if retrieved and any(d.get("retrievalMethod")=="BM25_ONLY_DENSE_UNAVAILABLE" for d in retrieved):
            retrieval_mode="TOOL_EVIDENCE_ONLY"
            limitations.append("Đang tìm bằng từ khóa BM25; E5/FAISS chưa sẵn sàng, không giả lập kết quả vector.")
        if amenity_scope and amenity_scope.get("areaId"):
            # Exact catalog scope only, even if the embedding returns a similarly named district.
            retrieved=[d for d in documents if d["kind"]=="POI_EVIDENCE" and d["scope"]=="PUBLIC"
                       and d["metadata"].get("areaId")==amenity_scope["areaId"] and d["metadata"].get("category") in categories][:3]
            limitations.append("Tiện ích thuộc hồ sơ "+amenity_scope["ward"]+"; chưa có điểm xuất phát để tính khoảng cách từ căn nhà.")
        # Hard guarantee: an explicit POI category may never be answered with another category.
        if categories:
            matched = [d for d in retrieved if d["kind"] == "POI_EVIDENCE" and d["metadata"].get("category") in categories]
            if not matched and not research and district and not amenity_scope:
                # FAISS had no in-category evidence: use the same read-only, VALID-only POI
                # projection that already backs the map card. Never substitute another category.
                from .knowledge import document
                area_url = self.backend.settings.backend_url + "/api/v1/amenities/" + (
                    next((d["metadata"]["areaId"] for d in documents
                          if d["kind"] == "AREA_AMENITY" and d["metadata"].get("areaLevel") == "DISTRICT"
                          and d["metadata"].get("district") == district), "district"))
                for category in categories:
                    try:
                        mapped = traced("amenity_map_fallback", lambda c=category: self.tools.data("places",district,c))
                    except (RagUnavailable, GroundingError, UpstreamError):
                        mapped = None
                        limitations.append("Dịch vụ địa điểm chưa phản hồi hoặc bằng chứng chưa đạt yêu cầu; chưa thể kết luận khu vực không có tiện ích.")
                    items = (mapped or {}).get("items") if isinstance(mapped, dict) else None
                    for item in (items or [])[:3]:
                        metadata = {"areaId": "map:" + item["id"], "district": item["district"],
                                    "name": item["name"], "category": item["category"], "sourceUrl":item.get("sourceUrl"),
                                    "attributionBasis": "GEOAPIFY_PROVIDER_REPORTED" if item.get("sourceName")=="geoapify" else "OPENSTREETMAP_VALID"}
                        retrieved.append(document("poi-map:" + item["id"],
                            f"Bằng chứng tiện ích {item['name']}, loại {item['category']}, tại {item['district']}; "+
                            ("nguồn Geoapify, chưa xác minh thực địa. " if item.get("sourceName")=="geoapify" else "nguồn OpenStreetMap đã kiểm tra nguồn. ")+"Không có khoảng cách tới căn nhà.",
                            area_url, str(item.get("observedAt") or "POI_MAP_V1"), "POI_EVIDENCE", metadata))
            # With an explicit category only in-category POI evidence may reach the model.
            retrieved = [d for d in retrieved
                         if d["kind"] == "POI_EVIDENCE" and d["metadata"].get("category") in categories][:3]
            if not retrieved:
                event("amenity_no_evidence", categories=list(categories), district=district)
                if request.requireGeneration:
                    raise RagUnavailable("NO_MATCHING_AMENITY_EVIDENCE")
                limitations.append("Chưa có bằng chứng tiện ích đúng loại yêu cầu trong kho tri thức công khai; "
                                   "hệ thống không thay bằng loại tiện ích khác và không suy đoán vị trí.")
                return self._reply(request, session_id, context, criteria, properties=[], citations=[], research=research,
                    answer=insufficient_amenity_answer((amenity_scope or {}).get("ward") or district, categories), responseKind="INSUFFICIENT_AMENITY_EVIDENCE",
                    limitations=limitations, response=response, retrieval_mode=retrieval_mode,
                    evidence={"criteria": criteria if budget else None,
                        "amenityIntent": {"district": district, "categories": list(categories), "ward":(amenity_scope or {}).get("ward"), "mapAvailable":not bool(amenity_scope)},
                        "retrievedSourceIds": [], "semanticRetrieval": {"indexVersion": None, "hits": []},
                        "sql": {"status": sql_status, "matchedRows": sql_count},
                        "generation": {"accepted": False, "reason": "NOT_NEEDED_FOR_MISSING_EVIDENCE"},
                        "gis": gis_evidence(rows, properties, []), "warnings": (response or {}).get("warnings", [])})

        facts = {}
        citations = {}
        def add(text, source_id, url, version, kind, scope, metadata, content_hash=None):
            fact_id = "f" + str(len(facts))
            facts[fact_id] = {"text": text, "sourceId": source_id}
            citations[source_id] = Citation(sourceId=source_id, url=url, version=version,
                contentHash=content_hash or digest(metadata), kind=kind, scope=scope, title=source_id)
            return fact_id

        property_facts = []
        route = "/api/v1/recommendations/research" if research else "/api/v1/recommendations"
        for p in properties:
            # All numbers and property IDs originate in the live response. No title/description instructions.
            text = (f"Mã {p['id']}: giá rao {number(p['priceVnd'])} đồng; diện tích {number(p['areaSqm'])} m²; "
                    f"điểm phù hợp {number(p['score'])}/100; khu vực {p.get('district') or 'chưa rõ'}" +
                    (f", {p['ward']}" if p.get("ward") else "") + ".")
            # Full preference explanations remain in the API cards/limitations, not repeated in each generated fact.
            parts = p.get("scoreBreakdown") or {}
            labels = {"budgetFit": "ngân sách", "areaFit": "diện tích", "propertyTypeFit": "loại bất động sản", "amenityFit": "tiện ích"}
            if parts:
                text += " Thành phần điểm: " + "; ".join(f"{labels[k]} {number(v)}" for k, v in parts.items() if k in labels) + "."
            property_facts.append(add(text, "recommendation:" + p["id"], self.backend.settings.backend_url + route,
                "HEURISTIC_V1_1:" + digest({"criteria": criteria, "property": p})[:16], "RECOMMENDATION",
                "INTERNAL_RESEARCH" if research else "PUBLIC", p, digest({"criteria": criteria, "property": p})))
        area_facts = []
        for d in retrieved:
            if not research and d["scope"] != "PUBLIC":
                raise GroundingError("PUBLIC_CORPUS_PERMISSION_VIOLATION")
            area_facts.append(add(d["text"], d["sourceId"], d["url"], d["version"], d["kind"], d["scope"], d["metadata"], d["contentHash"]))
            fact = facts["f" + str(len(facts) - 1)]
            fact["category"] = d["metadata"].get("category")
            fact["district"] = d["metadata"].get("district")
        selected = property_facts + area_facts
        # "Hiển thị chúng trên bản đồ" refers to the previous turn's own evidence.
        # The server never resolves an address or invents a coordinate: it re-emits the
        # same verified evidence and lets the map card render what it already had.
        map_reuse = bool(turn["mapRequest"] and resumed and not categories)
        if map_reuse and not retrieved:
            previous_ids = set(context.evidence_source_ids)
            retrieved = [d for d in documents if d["sourceId"] in previous_ids][:3]
        generation_mode = "EVIDENCE_ONLY"
        generation_evidence = {"accepted": False}
        generated_sentences = None
        try:
            if getattr(self.llm, "output_kind", None) == "grounded_answer":
                generated = traced("ollama_generation", lambda: self.llm.answer(request.question, {k: facts[k] for k in selected}))
                event("generation_metrics", **generated.metrics)
                generated_sentences = traced("answer_validation", lambda: validate_generated_answer(generated.raw, facts, property_facts))
                traced("intent_alignment", lambda: validate_generated_relevance(generated_sentences, facts, categories, district))
                selected = list(dict.fromkeys(property_facts + [s["factId"] for s in generated_sentences]))
                generation_evidence = {**generated.metrics, "accepted": True, "outputSha256": digest(generated.raw),
                                       "sentences": generated_sentences, "style": "GROUNDED_EXTRACTIVE_TEXT"}
                generation_mode = "QWEN_GROUNDED_ANSWER"
            else:
                plan = self.llm.plan(request.question, {k: facts[k] for k in selected})
                chosen = validate_plan(plan, set(selected))
                traced("intent_alignment", lambda: validate_generated_relevance(
                    [{"factId": k} for k in chosen], facts, categories, district))
                # Legacy plan adapter remains available; it never qualifies as an Ollama answer.
                selected = property_facts + [k for k in chosen if k not in property_facts]
                generation_mode = "QWEN_GROUNDED_PLAN"
        except (RagUnavailable, GroundingError) as error:
            generated_sentences = None
            generation_evidence = {"accepted": False, "reason": str(error)}
            event("generation_rejected", reason=reason(error))
            limitations.append("Qwen chưa sẵn sàng hoặc kế hoạch sinh bị validator từ chối; câu trả lời được ghép từ bằng chứng, không phải output Qwen.")
        if request.requireGeneration and (generation_mode not in ("QWEN_GROUNDED_PLAN", "QWEN_GROUNDED_ANSWER") or retrieval_mode != "E5_FAISS"):
            event("strict_rejection", retrievalMode=retrieval_mode, generationMode=generation_mode, reason=generation_evidence.get("reason", "SEMANTIC_RETRIEVAL_UNAVAILABLE"))
            raise RagUnavailable("FULL_RAG_RUNTIME_UNAVAILABLE")
        if research:
            limitations.append("Dữ liệu nghiên cứu chưa xác minh, không được dùng như tin công khai đang bán; không có xác nhận pháp lý hoặc giá giao dịch.")
        used = {facts[k]["sourceId"] for k in selected}
        answer = render_answer(facts, selected, research=research, has_budget=budget is not None, has_properties=bool(properties))
        if generated_sentences is not None:
            # Actual Qwen-generated text survives verbatim validation; only scope labels/citations are appended by server.
            intro = render_answer({}, [], research=research, has_budget=budget is not None, has_properties=bool(properties))
            answer = intro + "\n" + "\n".join(s["text"] + " [" + s["sourceId"] + "]" for s in generated_sentences)
        # Every recommended property retains a citation even when no auxiliary fact is selected.
        return self._reply(request, session_id, context, criteria,
            properties=properties, citations=[c for key, c in citations.items() if key in used], research=research,
            answer=answer, limitations=limitations, response=response,
            result_properties=result_properties, reference_id=referenced_id,
            generation_mode=generation_mode, retrieval_mode=retrieval_mode,
            evidence={"recommendationMethod": (response or {}).get("method"), "criteria": criteria if budget else None,
                      "eligibleCandidateCount": (response or {}).get("eligibleCandidateCount"),
                      "topAreas": (response or {}).get("topAreas", []), "catalogVersion": corpus["summary"]["catalogVersion"],
                      "corpusVersion": corpus["contentHash"], "catalogSummary": corpus["summary"],
                      "retrievedSourceIds": [d["sourceId"] for d in retrieved], "sql": {"status": sql_status, "matchedRows": sql_count},
                      "generation": generation_evidence, "gis": gis_evidence(rows, properties, retrieved),
                      "amenityIntent": {"district": district, "categories": list(categories), "ward":(amenity_scope or {}).get("ward"), "mapAvailable":not bool(amenity_scope)},
                      "semanticRetrieval": {"indexVersion": getattr(self.retriever, "manifest", None).get("version") if isinstance(getattr(self.retriever, "manifest", None), dict) else None,
                                            "hits": [{"sourceId": d["sourceId"], "similarity": d.get("similarity")} for d in retrieved]},
                      "warnings": (response or {}).get("warnings", [])})
