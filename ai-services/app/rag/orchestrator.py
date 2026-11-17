from decimal import Decimal
import re
import time
import unicodedata
from .config import GroundingError, RagUnavailable
from .knowledge import digest
from .schemas import ChatResponse, Citation
from .validator import render_answer, validate_plan, validate_generated_answer, validate_generated_relevance
from urllib.parse import quote
from .gis import gis_evidence
from .diagnostics import traced, event, reason
from .intent import (asks_for_amenities, asks_market_trend, empty_search_answer, poi_categories,
                     CATEGORY_LABELS, insufficient_amenity_answer)
from .followup import (classification, detect_district, budget_from_followup)
from .session import SessionStore, MAX_PROPERTY_IDS
from .personalization import intake, projection, format_vnd


LIMITATIONS = [
    "Giá là giá rao, không phải giá giao dịch hoặc kết quả định giá mới.",
    "Điểm Recommendation là heuristic Hybrid V1.1, không phải AI cá nhân hóa đã huấn luyện hoặc dự báo sinh lời.",
    "Tiện ích là bằng chứng cấp khu vực; không suy ra GPS, khoảng cách hoặc thời gian đi từ từng bất động sản.",
    "RAG không xác minh pháp lý, tình trạng còn bán hoặc mức độ an toàn của bất động sản.",
]

# The advisor renders three property cards, so the search asks for exactly three.
# Storing a longer list would let "căn thứ tư" name a property the user never saw.
SUGGESTION_LIMIT = 3
# When ordering by commute the pool must be wider than the card list, but still small
# enough that one question cannot spend the whole daily Geoapify budget.
RANKING_POOL = 6
# Nearby search: the radius the user sees, and how many candidates the box may return
# before the real distance filter runs.
NEARBY_RADIUS_METERS = 1000
NEARBY_CANDIDATES = 40


def norm(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d")) if not unicodedata.combining(c))


def number(value):
    return format(Decimal(str(value)), "f").rstrip("0").rstrip(".") if "." in format(Decimal(str(value)), "f") else format(Decimal(str(value)), "f")


def budget_from_question(question):
    # Exact single amount only. Multiple amounts / shorthand are not guessed.
    if len(re.findall(r"tỷ|\bty\b|triệu|\btrieu\b", question.lower())) != 1:
        return None
    values = re.findall(r"(?<![\w.,])([0-9]+(?:[.,][0-9]+)?)\s*(tỷ|ty|triệu|trieu)\b(?!\s*\d)", question.lower())
    if len(values) != 1:
        return None
    value, unit = values[0]
    amount = Decimal(value.replace(",", ".")) * (10**9 if unit in ("tỷ", "ty") else 10**6)
    return amount if 1 <= amount <= 999999999999999 else None


from .account_preferences import fingerprint, seed
from .tools import UpstreamError, OutboundRateLimited
from . import focused_property
from .focused_property import focused_intent
from . import address_search, commute_destination, commute_ranking
from .geo import haversine_meters

class ChatOrchestrator:
    def __init__(self, backend, repository, knowledge, retriever, llm, sessions=None):
        self.backend, self.repository, self.knowledge = backend, repository, knowledge
        self.retriever, self.llm = retriever, llm
        # Bounded in-memory conversation memory. Never persisted, never authoritative.
        self.sessions = sessions or SessionStore()

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
            if not callable(poi_fn):
                continue
            try:
                items = poi_fn(property_id)
                if isinstance(items, list):
                    p["nearbyPois"] = items
                    p["nearbyPoisStatus"] = "AVAILABLE" if items else "NO_POIS_IN_RADIUS"
                else:
                    p["nearbyPoisStatus"] = "UNAVAILABLE"
            except UpstreamError as error:
                p["nearbyPoisStatus"] = "PROPERTY_NOT_PUBLIC" if error.status == 404 else "UNAVAILABLE"
            except Exception:
                p["nearbyPoisStatus"] = "UNAVAILABLE"

    # ------------------------------------------------------------------
    def _reply(self, request, session_id, context, criteria, *, properties, citations, research,
               answer, responseKind=None, limitations=None, response=None, extra=None,
               evidence=None, generation_mode="EVIDENCE_ONLY", retrieval_mode="TOOL_EVIDENCE_ONLY",
               result_properties=None, reference_id=None):
        """Single exit point: every reply records bounded state and returns the session id.

        `properties` is what the user sees; `result_properties` is the full verified
        result set of this turn, which is what the next turn must be able to reference.
        """
        if properties:
            self._enrich(properties)
        full = list(result_properties if result_properties is not None else properties)
        property_ids = [p["id"] for p in full][:MAX_PROPERTY_IDS]
        if context.needs.get("ordinalTurn"):
            # An ordinal turn only narrows the view; the list the user refers to is the
            # one already on screen, not the fresh query result behind it.
            property_ids = list(context.needs.get("lastPropertyIds") or property_ids)
        elif not property_ids:
            # A reply that shows no listing must not erase the list the user is still
            # referring to; only a real new result set replaces it.
            property_ids = list(context.needs.get("lastPropertyIds") or [])
        else:
            context.needs["lastPropertyIds"] = property_ids
        self.sessions.record(context,
            criteria={**{k: v for k, v in (criteria or {}).items() if k not in ("sessionTurn", "_propertyIds")},
                      "_propertyIds": property_ids,
                      "lastSearchEmpty": bool(context.needs.get("lastSearchEmpty"))} if criteria else None,
            property_ids=property_ids,
            area_ids=[a.get("amenityAreaId") for a in (response or {}).get("topAreas", []) if a.get("amenityAreaId")],
            evidence_ids=[c.sourceId for c in citations],
            referenced_property_id=reference_id,
            question=request.question)
        payload = dict(evidence or {})
        if responseKind:
            payload["responseKind"] = responseKind
        payload["session"] = {"id": session_id, "turn": context.turns, "context": context.public()}
        if extra:
            payload.update(extra)
        if context.needs.get("active"):
            needs = projection(context, criteria or {})
            payload["needs"] = needs
            if not payload.get("quickReplies"):
                payload["quickReplies"] = ["Tìm kỹ hơn"] if properties else []
            limitations = list(dict.fromkeys(list(limitations or []) + needs["limitations"]))
        return ChatResponse(answer=answer, mode="INTERNAL_RESEARCH" if research else "SAFE",
            generationMode=generation_mode, retrievalMode=retrieval_mode, citations=list(citations),
            recommendedProperties=list(properties), evidence=payload, dataLimitations=list(limitations or []))

    def _focused_answer(self, request, session_id, context, criteria, focused, intent, *, limitations, research, token=None):
        """Answer a question about the one listing the user opened, from public data only."""
        # The listing itself is the evidence: one PUBLIC citation pointing at its own
        # public API path, so the client can verify the answer is grounded.
        citations = [Citation(sourceId="property:" + focused["id"], url="/api/v1/properties/" + focused["id"],
                              version=str(focused.get("contentVersion") or "1"), kind="PROPERTY_DETAIL", scope="PUBLIC",
                              title=focused["title"] or "Tin đang xem",
                              contentHash=digest({"id": focused["id"], "priceVnd": focused["priceVnd"],
                                                  "areaSqm": focused.get("areaSqm")}))]
        extra = {"focusedProperty": {"id": focused["id"], "title": focused["title"],
                                     "priceVnd": str(focused["priceVnd"]), "intent": intent}}
        if intent == "PRICE":
            answer = focused_property.price_answer(focused)
        elif intent == "AREA":
            answer = focused_property.area_answer(focused)
        elif intent == "AMENITY":
            category = focused_property.amenity_category(request.question)
            try:
                pois = traced("focused_pois", lambda: self.backend.nearby_pois(focused["id"], radius=2000, limit=20))
            except (GroundingError, UpstreamError):
                pois = []
                limitations.append("Chưa tải được dữ liệu tiện ích của tin này.")
            answer = focused_property.amenity_answer(focused, pois, category)
            extra["amenityCategory"] = category
        elif intent == "COMMUTE":
            destination = commute_destination.destination_of(context.needs)
            if not isinstance(destination, dict):
                # No confirmed destination yet: ask where work is, then resolve it.
                picked = self._commute_destination(request, session_id, context, criteria,
                                                   limitations=limitations, research=research, token=token)
                if picked is not None:
                    return picked
                destination = commute_destination.destination_of(context.needs)
            if not isinstance(destination, dict):
                return self._commute_source_prompt(request, session_id, context, criteria,
                                                   limitations=limitations, research=research)
            mode = commute_destination.mode_for(request.question, destination.get("mode") or "drive")
            destination["mode"] = mode
            context.needs["commuteDestination"] = destination
            try:
                commute = traced("focused_commute", lambda: self.backend.commute(
                    focused["id"], destination["latitude"], destination["longitude"],
                    destination.get("label") or "", mode))
            except (GroundingError, UpstreamError):
                answer = "Chưa tính được thời gian đi làm cho tin này."
                limitations.append("Tuyến đường chưa sẵn sàng; không suy ra thời gian từ khoảng cách đường chim bay.")
                extra["commute"] = None
            else:
                threshold = focused_property.commute_threshold(request.question)
                answer = focused_property.commute_answer(focused, commute, mode, threshold)
                extra["commute"] = {"distanceMeters": commute["distanceMeters"],
                                    "durationSeconds": commute["durationSeconds"], "mode": mode,
                                    "provider": commute.get("provider") or "",
                                    "thresholdMinutes": threshold}
        else:
            answer = "Tôi chưa có dữ liệu cho câu hỏi này về tin đang xem."
        return self._reply(request, session_id, context, criteria, properties=[], citations=citations,
            research=research, answer=answer, responseKind="FOCUSED_PROPERTY", limitations=limitations,
            extra=extra)

    def _commute_source_prompt(self, request, session_id, context, criteria, *, limitations, research):
        """The one question both surfaces ask before any routing can happen."""
        context.needs["commuteStage"] = commute_destination.ASK_SOURCE
        return self._reply(request, session_id, context, criteria, properties=[], citations=[],
            research=research,
            answer=("Để tính thời gian đi làm, tôi cần một địa điểm cụ thể. "
                    "Bạn muốn dùng nơi làm việc đã lưu hay nhập địa điểm khác?"),
            responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
            extra={"clarification": "COMMUTE_DESTINATION_REQUIRED",
                   "quickReplies": ["Dùng nơi làm việc đã lưu", "Nhập địa điểm khác", "Bỏ qua"]})

    def _commute_destination(self, request, session_id, context, criteria, *, limitations, research, token=None):
        """Resolve where the user works, or return a reply asking them to choose.

        Returns None when the caller should fall through to the plain "saved / new /
        skip" question. Anything that reaches the map provider needs an explicit yes
        in this same conversation; nothing is written to the profile.
        """
        state = context.needs
        stage = commute_destination.stage_of(state)
        question = request.question

        if commute_destination.wants_skip(question):
            for key in ("commuteStage", "commutePendingAddress", "commutePoints", "commutePendingLimit"):
                state.pop(key, None)
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer=("Được, tôi bỏ qua phần thời gian đi làm. Bạn vẫn có thể hỏi giá hoặc tiện ích của căn này."),
                responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"clarification": "COMMUTE_SKIPPED"})

        if stage == commute_destination.PICK_CANDIDATE:
            points = state.get("commutePoints") or []
            index = commute_destination.candidate_index(question, len(points))
            if index is None:
                return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                    research=research,
                    answer=("Bạn chọn địa điểm nào? Trả lời số thứ tự trong danh sách, hoặc nói “bỏ qua”."),
                    responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                    extra={"clarification": "COMMUTE_PICK_CANDIDATE",
                           "commuteCandidates": [{"index": i + 1, "label": p["label"],
                                                  "approximate": p.get("approximate", False)}
                                                 for i, p in enumerate(points)]})
            chosen = points[index - 1]
            state["commuteDestination"] = {"latitude": chosen["latitude"], "longitude": chosen["longitude"],
                                           "label": chosen["label"], "mode": commute_destination.mode_for(question)}
            for key in ("commuteStage", "commutePendingAddress", "commutePoints"):
                state.pop(key, None)
            return None

        if stage == commute_destination.AWAIT_ADDRESS:
            address = commute_destination.address_from(question)
            if address is None:
                return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                    research=research,
                    answer=("Bạn nhập địa điểm làm việc giúp tôi, ví dụ “123 Nguyễn Văn Linh”. "
                            "Tôi chỉ gửi địa chỉ này tới dịch vụ bản đồ khi bạn gửi."),
                    responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                    extra={"clarification": "COMMUTE_ADDRESS_REQUIRED",
                           "quickReplies": ["Bỏ qua"]})
            # Typing the address after being told it goes to the map provider is the consent.
            state["commutePendingAddress"] = address
            try:
                points = traced("geocode_workplace", lambda: self.backend.geocode_workplace(address))
            except (GroundingError, UpstreamError) as geocode_error:
                state.pop("commutePendingAddress", None)
                state.pop("commuteStage", None)
                if "GEOCODING_RATE_LIMITED" in str(geocode_error):
                    # The shared map budget is spent: say so rather than blame the address.
                    return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                        research=research,
                        answer=("Dịch vụ bản đồ đang hết hạn mức truy cập nên tôi chưa tra được vị trí. "
                                "Bạn thử lại sau ít phút, hoặc nói “bỏ qua” để xem thông tin khác của căn này."),
                        responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                        extra={"clarification": "COMMUTE_GEOCODING_BUSY", "quickReplies": ["Bỏ qua"]})
                limitations.append("Chưa tìm được vị trí cho địa chỉ đã nhập; không suy ra toạ độ.")
                return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                    research=research,
                    answer=("Chưa tìm được vị trí cho địa chỉ bạn nhập. Bạn thử địa chỉ cụ thể hơn, "
                            "hoặc nói “bỏ qua” để xem thông tin khác của căn này."),
                    responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                    extra={"clarification": "COMMUTE_GEOCODE_FAILED", "quickReplies": ["Bỏ qua"]})
            state.pop("commutePendingAddress", None)
            return self._accept_points(request, session_id, context, criteria, points,
                                       limitations=limitations, research=research)

        if commute_destination.wants_saved(question):
            if not token or not context.needs.get("active"):
                return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                    research=research,
                    answer=("Tôi chưa có nơi làm việc đã lưu cho phiên này vì bạn đang dùng chế độ khách "
                            "hoặc chưa bật tư vấn cá nhân. Bạn nhập địa điểm cụ thể, hoặc nói “bỏ qua”."),
                    responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                    extra={"clarification": "COMMUTE_NO_SAVED_WORKPLACE",
                           "quickReplies": ["Nhập địa điểm khác", "Bỏ qua"]})
            try:
                result = traced("saved_workplace", lambda: self.backend.saved_workplace(token))
            except (GroundingError, UpstreamError):
                result = {"available": False, "reason": "NOT_RESOLVED", "points": []}
            if not result.get("available"):
                return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                    research=research,
                    answer=("Nơi làm việc đã lưu chưa đủ cụ thể để tìm vị trí, nên tôi chưa tính được thời gian đi làm. "
                            "Bạn nhập một địa điểm cụ thể, hoặc nói “bỏ qua”."),
                    responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                    extra={"clarification": "COMMUTE_SAVED_WORKPLACE_UNRESOLVED",
                           "quickReplies": ["Nhập địa điểm khác", "Bỏ qua"]})
            return self._accept_points(request, session_id, context, criteria, result["points"],
                                       limitations=limitations, research=research)

        if commute_destination.wants_new(question):
            state["commuteStage"] = commute_destination.AWAIT_ADDRESS
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer=("Bạn nhập địa điểm làm việc. Địa chỉ bạn gửi sẽ được chuyển tới dịch vụ bản đồ "
                        "Geoapify để lấy toạ độ; tôi không lưu lại và không ghi vào hồ sơ. Bạn đồng ý chứ?"),
                responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"clarification": "COMMUTE_ADDRESS_CONSENT",
                       "quickReplies": ["Bỏ qua"]})
        # Nothing chosen yet: remember that a commute answer is pending so the next turn
        # ("saved", "new address", "skip") is routed back here even without a keyword.
        state["commuteStage"] = commute_destination.ASK_SOURCE
        return None

    def _accept_points(self, request, session_id, context, criteria, points, *, limitations, research):
        """One candidate is unambiguous; several must be confirmed by the user."""
        usable = [p for p in points if isinstance(p, dict)]
        if not usable:
            return None
        if len(usable) == 1:
            only = usable[0]
            context.needs["commuteDestination"] = {
                "latitude": only["latitude"], "longitude": only["longitude"],
                "label": only.get("label") or "", "mode": commute_destination.mode_for(request.question)}
            for key in ("commuteStage", "commutePoints"):
                context.needs.pop(key, None)
            return None
        context.needs["commuteStage"] = commute_destination.PICK_CANDIDATE
        context.needs["commutePoints"] = usable[:5]
        return self._reply(request, session_id, context, criteria, properties=[], citations=[],
            research=research,
            answer=("Tôi tìm được vài vị trí khớp với địa điểm đó. Bạn chọn đúng chỗ làm giúp tôi, "
                    "hoặc nhập địa chỉ cụ thể hơn."),
            responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
            extra={"clarification": "COMMUTE_PICK_CANDIDATE",
                   "commuteCandidates": [{"index": i + 1, "label": p.get("label", ""),
                                          "approximate": p.get("approximate", False)}
                                         for i, p in enumerate(usable[:5])],
                   "quickReplies": [str(i + 1) + ". " + (p.get("label") or "")[:60]
                                    for i, p in enumerate(usable[:5])] + ["Bỏ qua"]})

    def _rank_by_commute(self, properties, destination, limit_minutes, kind, limitations):
        """Measure the trip to work for every candidate in one vendor call, then order.

        Only listings that already passed the budget and hard criteria reach here, and the
        pool is bounded so one question cannot drain the routing budget.
        """
        ids = [str(property.get("id", "")).split(":", 1)[-1] for property in properties]
        provider = ""
        try:
            result = traced("commute_matrix", lambda: self.backend.commute_matrix(
                ids, destination["latitude"], destination["longitude"],
                destination.get("label") or "", destination.get("mode") or "drive"))
            provider = result.get("provider") or ""
            cells = result.get("cells") or []
        except OutboundRateLimited as limited:
            limitations.append(
                f"SmartProp đã chạm hạn mức gọi dịch vụ tính tuyến nên chưa xếp hạng được theo "
                f"thời gian đi làm. Thử lại sau khoảng {limited.retry_after} giây.")
            cells = []
        except GroundingError as error:
            if "ROUTE_NOT_CONFIGURED" in str(error):
                limitations.append("Dịch vụ tính tuyến chưa được cấu hình nên danh sách giữ nguyên thứ tự mặc định.")
            else:
                limitations.append("Chưa xác minh được thời gian đi làm cho các tin này; "
                                   "không suy ra từ khoảng cách đường chim bay.")
            cells = []
        except UpstreamError:
            limitations.append("Chưa xác minh được thời gian đi làm cho các tin này; "
                               "không suy ra từ khoảng cách đường chim bay.")
            cells = []
        by_id = {cell.get("propertyId"): cell for cell in cells if isinstance(cell, dict)}
        entries = []
        for property, listing_id in zip(properties, ids):
            cell = by_id.get(listing_id) or {}
            seconds = cell.get("durationSeconds")
            route = None
            if seconds is not None:
                route = {"distanceMeters": cell.get("distanceMeters"), "durationSeconds": seconds,
                         "provider": provider}
            entries.append({"property": property, "route": route,
                            "status": cell.get("status") or "NO_ROUTE"})
        ordered = commute_ranking.rank(entries, limit_minutes, kind, SUGGESTION_LIMIT)
        measured = [row for row in entries if row["route"]]
        vendor = focused_property.VENDOR_LABELS.get(provider, "dịch vụ tính tuyến")
        if kind == "HARD" and not ordered:
            if measured:
                # Every route was measured and every one failed the cap: say that plainly.
                fastest = min(row["route"]["durationSeconds"] for row in measured)
                limitations.append(
                    f"Trong {len(properties)} tin đã lọc theo ngân sách, {len(measured)} tin có tuyến "
                    f"nhưng đều vượt mốc {limit_minutes} phút (nhanh nhất {fastest / 60:.0f} phút). "
                    f"Đây là phạm vi đã kiểm tra, không phải kết luận về toàn thị trường.")
            else:
                limitations.append(
                    f"Trong {len(properties)} tin đã lọc theo ngân sách, chưa tính được tuyến cho tin nào "
                    f"nên chưa xác minh được mốc {limit_minutes} phút. "
                    f"Đây là phạm vi đã kiểm tra, không phải kết luận về toàn thị trường.")
        elif measured:
            # Describe the listings actually kept, not every route that was measured.
            kept = [row for row in ordered if row["route"]]
            fastest = min(row["route"]["durationSeconds"] for row in kept)
            slowest = max(row["route"]["durationSeconds"] for row in kept)
            scope = (f"Xếp hạng theo thời gian di chuyển ước tính theo {vendor} cho {len(kept)}/"
                     f"{len(properties)} tin trong ngân sách, tuyến {fastest / 60:.0f}–{slowest / 60:.0f} phút.")
            if len(kept) < len(measured):
                scope += (f" {len(measured) - len(kept)} tin có tuyến nhưng vượt mốc "
                          f"{limit_minutes} phút nên bị loại.")
            if len(measured) < len(properties):
                scope += f" {len(properties) - len(measured)} tin chưa có tuyến nên không được xếp theo thời gian."
            limitations.append(scope)
        return [row["property"] for row in ordered]

    @staticmethod
    def _district_of(point):
        """The district named by a geocoded point, when the provider returned one."""
        label = str(point.get("label") or "")
        for name in ("Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn", "Liên Chiểu",
                     "Cẩm Lệ", "Hòa Vang", "Hoàng Sa"):
            if name.lower() in label.lower():
                return name
        return None

    def _address_answer(self, request, session_id, context, criteria, address, *, limitations, research):
        """Listings whose own address carries this house number and street."""
        if not address:
            return None
        try:
            found = traced("search_by_address",
                           lambda: self.backend.search_by_address(address, limit=SUGGESTION_LIMIT))
        except OutboundRateLimited as limited:
            limitations.append(f"SmartProp đã chạm hạn mức tra cứu. Thử lại sau khoảng "
                               f"{limited.retry_after} giây.")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer="Chưa tra cứu được theo địa chỉ này vì hệ thống đang chạm hạn mức tra cứu.",
                responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"clarification": "ADDRESS_SEARCH_RATE_LIMITED"})
        except (GroundingError, UpstreamError):
            limitations.append("Chưa tra cứu được theo địa chỉ này do lỗi dịch vụ; không suy ra kết quả.")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer=("Chưa tra cứu được tin nhà theo địa chỉ này do lỗi dịch vụ. "
                        "Bạn thử lại giúp tôi sau ít phút."),
                responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"clarification": "ADDRESS_SEARCH_UNAVAILABLE"})

        # The backend filter is a substring match; the house number must be exact.
        matched = [item for item in found.get("items", [])
                   if address_search.matches(item.get("address") or "", address)]
        if not matched:
            # This search completed with nothing; a later ordinal must not reach back
            # into the list from before it.
            context.needs["lastSearchEmpty"] = True
            limitations.append(
                f"Đã tra {found.get('total', 0)} tin có địa chỉ chứa chuỗi tìm kiếm; "
                f"không tin nào đúng số nhà và tên đường của “{address}”.")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer=f"Chưa tìm thấy tin nhà tại {address}.",
                responseKind="NO_MATCHES", limitations=limitations,
                evidence={"recommendationMethod": "ADDRESS_FILTER",
                          "criteria": criteria,
                          "recommendationSearch": {"performed": True, "resultCount": 0,
                              "sourcePath": "/api/v1/recommendations",
                              "criteriaHash": digest(criteria)},
                          "generation": {"accepted": False, "reason": "NOT_NEEDED_FOR_EMPTY_SEARCH"},
                          "retrievedSourceIds": [], "semanticRetrieval": {"indexVersion": None, "hits": []},
                          "sql": {"status": "NO_PLATFORM_RESULTS", "matchedRows": 0},
                          "gis": gis_evidence([], [], [])},
                extra={"clarification": "ADDRESS_NO_MATCH",
                       "addressQuery": address,
                       "quickReplies": [f"Xem nhà gần {address}", "Tìm theo ngân sách"]})

        properties = matched[:SUGGESTION_LIMIT]
        context.needs["addressQuery"] = address
        context.needs["lastSearchEmpty"] = False
        return self._reply(request, session_id, context, criteria, properties=properties, citations=[],
            research=research,
            answer=(f"Tìm thấy {len(properties)} tin nhà có địa chỉ khớp “{address}”. "
                    f"Giá là giá rao công khai của từng tin."),
            responseKind="PROPERTY_LIST", limitations=limitations,
            extra={"addressQuery": address})

    def _near_address_answer(self, request, session_id, context, criteria, address, *, limitations, research):
        """Listings near an address. Coordinates only locate; they never prove a house number."""
        if not address:
            return None
        try:
            points = traced("geocode_address", lambda: self.backend.geocode_workplace(address))
        except OutboundRateLimited as limited:
            limitations.append(f"Dịch vụ bản đồ đang chạm hạn mức; thử lại sau khoảng "
                               f"{limited.retry_after} giây.")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer="Chưa định vị được địa chỉ này vì dịch vụ bản đồ đang chạm hạn mức tra cứu.",
                responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"clarification": "ADDRESS_GEOCODING_BUSY"})
        except (GroundingError, UpstreamError):
            limitations.append("Chưa định vị được địa chỉ này; không suy ra tin lân cận.")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer=("Chưa định vị được địa chỉ này nên tôi chưa tìm được nhà lân cận. "
                        "Bạn thử địa chỉ cụ thể hơn."),
                responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"clarification": "ADDRESS_GEOCODING_UNAVAILABLE"})
        if not points:
            limitations.append("Không tìm được toạ độ cho địa chỉ này.")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer=f"Chưa định vị được “{address}” nên tôi chưa tìm được nhà lân cận.",
                responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"clarification": "ADDRESS_GEOCODING_UNAVAILABLE"})

        point = points[0]
        origin = {"latitude": float(point["latitude"]), "longitude": float(point["longitude"]),
                  "label": str(point.get("label") or address)}
        context.needs["nearOrigin"] = origin
        return self._nearby_from(request, session_id, context, criteria, address, origin,
                                 limitations=limitations, research=research)

    def _nearby_from(self, request, session_id, context, criteria, address, origin, *, limitations, research):
        """Listings within the radius of a confirmed point, nearest first.

        The bounding box only narrows the candidate set; every candidate is measured and
        anything beyond the radius is dropped, so a district's three best listings can
        never stand in for a real nearby result.
        """
        radius = NEARBY_RADIUS_METERS
        budget = criteria.get("budgetVnd")
        try:
            found = traced("search_nearby", lambda: self.backend.search_nearby(
                origin["latitude"], origin["longitude"], radius, limit=NEARBY_CANDIDATES,
                max_price=budget))
        except OutboundRateLimited as limited:
            limitations.append(f"SmartProp đã chạm hạn mức tra cứu. Thử lại sau khoảng "
                               f"{limited.retry_after} giây.")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer="Chưa tra cứu được tin nhà lân cận vì hệ thống đang chạm hạn mức tra cứu.",
                responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"clarification": "ADDRESS_SEARCH_RATE_LIMITED"})
        except (GroundingError, UpstreamError):
            limitations.append("Chưa tra cứu được tin nhà lân cận do lỗi dịch vụ; không suy ra kết quả.")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer="Chưa tra cứu được tin nhà lân cận do lỗi dịch vụ. Bạn thử lại giúp tôi sau ít phút.",
                responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                extra={"clarification": "ADDRESS_SEARCH_UNAVAILABLE"})

        measured = []
        for item in found.get("items", []):
            if not isinstance(item.get("latitude"), (int, float)) \
                    or not isinstance(item.get("longitude"), (int, float)):
                continue
            meters = haversine_meters(origin["latitude"], origin["longitude"],
                                      item["latitude"], item["longitude"])
            # A listing exactly on the boundary counts as inside; the tolerance absorbs
            # floating-point noise from the coordinate round-trip.
            if meters <= radius + 0.5:
                measured.append((meters, item))
        # Ties are broken by id so the same data always yields the same order.
        measured.sort(key=lambda pair: (round(pair[0], 3), pair[1]["id"]))
        complete = bool(found.get("complete", True))
        properties = []
        for meters, item in measured[:SUGGESTION_LIMIT]:
            item["distanceMeters"] = round(meters, 1)
            item["distanceType"] = "STRAIGHT_LINE"
            # The card contract expects the same shape the recommendation path returns.
            item.setdefault("source", {"kind": "PROPERTY", "recordKey": item["id"],
                                       "name": item.get("title") or "Tin SmartProp"})
            item.setdefault("qualityStatus", "PLATFORM_PUBLISHED")
            item.setdefault("verificationStatus", "PLATFORM_PUBLISHED")
            item.setdefault("score", 0)
            item.setdefault("explanations", [])
            item.setdefault("warnings", [])
            properties.append(item)

        if not properties:
            limitations.append(
                f"Đã đo {len(found.get('items', []))} tin trong hộp tra cứu quanh “{address}”; "
                f"không tin nào nằm trong bán kính {radius // 1000} km. Đây là phạm vi đã kiểm tra.")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer=(f"Chưa tìm thấy tin nhà trong bán kính {radius // 1000} km "
                        f"quanh vị trí đã xác nhận của “{address}”."),
                responseKind="NO_MATCHES", limitations=limitations,
                evidence={"recommendationMethod": "NEARBY_DISTANCE",
                          "criteria": criteria,
                          "recommendationSearch": {"performed": True, "resultCount": 0,
                              "sourcePath": "/api/v1/recommendations",
                              "criteriaHash": digest(criteria)},
                          "generation": {"accepted": False, "reason": "NOT_NEEDED_FOR_EMPTY_SEARCH"},
                          "retrievedSourceIds": [], "semanticRetrieval": {"indexVersion": None, "hits": []},
                          "sql": {"status": "NO_PLATFORM_RESULTS", "matchedRows": 0},
                          "gis": gis_evidence([], [], [])},
                extra={"clarification": "ADDRESS_NEARBY_EMPTY", "addressQuery": address,
                       "nearAddress": True, "radiusMeters": radius,
                       "quickReplies": ["Tìm theo ngân sách", "Mở rộng bán kính"]})

        limitations.append(
            f"Nhà trong bán kính {radius // 1000} km quanh “{address}”. "
            f"Khoảng cách là đường chim bay từ toạ độ tin đăng tới vị trí đã xác nhận, "
            f"không phải quãng đường đi thực tế.")
        if not complete:
            # The page walk stopped early, so this is not provably the nearest set.
            limitations.append(
                f"Chưa đọc hết danh sách tin trong hộp tra cứu ({found.get('pagesRead', 0)} trang), "
                f"nên đây là các tin gần nhất trong phần đã đọc, chưa phải toàn bộ khu vực.")
        # Each card needs its own PUBLIC citation, exactly like the recommendation path,
        # so the client can verify the listing is grounded in a public record.
        citations = [Citation(sourceId="recommendation:" + p["id"],
                              url="/api/v1/recommendations",
                              version=str(p.get("contentVersion") or "1"),
                              kind="RECOMMENDATION", scope="PUBLIC",
                              title=p.get("title") or "Tin SmartProp",
                              contentHash=digest({"id": p["id"], "priceVnd": p["priceVnd"],
                                                  "areaSqm": p.get("areaSqm"),
                                                  "distanceMeters": p.get("distanceMeters")}))
                     for p in properties]
        return self._reply(request, session_id, context, criteria, properties=properties, citations=citations,
            research=research,
            answer=(f"Nhà trong bán kính {radius // 1000} km quanh “{address}”: "
                    f"{len(properties)} tin, gần nhất {properties[0]['distanceMeters'] / 1000:.2f} km."),
            responseKind="PROPERTY_LIST", limitations=limitations,
            extra={"addressQuery": address, "nearAddress": True, "radiusMeters": radius,
                   "nearOrigin": origin})

    def _market_answer(self, request, session_id, context, research, district):
        """Answer market-trend questions from aggregate MySQL statistics, not property intake."""
        try:
            data = self.backend.market_analytics(district)
        except (RagUnavailable, GroundingError, UpstreamError):
            return self._reply(request, session_id, context, {}, properties=[], citations=[], research=research,
                answer="Chưa tải được dữ liệu thống kê thị trường từ SmartProp. Không có số liệu thay thế được tạo.",
                responseKind="MARKET_ANALYTICS_UNAVAILABLE",
                limitations=["Không dùng dữ liệu giả hoặc số liệu ngoài database khi nguồn thống kê chưa sẵn sàng."],
                evidence={"market": {"status": "UNAVAILABLE", "district": district},
                          "generation": {"accepted": False, "reason": "MARKET_DATA_UNAVAILABLE"},
                          "retrievedSourceIds": [], "semanticRetrieval": {"hits": []}})
        stat = data.get("overall") or {}
        if district:
            stat = next((item for item in data.get("byDistrict") or [] if item.get("key") == district), stat)
        meta = data.get("meta") or {}
        count = int(stat.get("count") or 0)
        minimum = int(meta.get("minSample") or 30)
        place = district or "Đà Nẵng"
        if stat.get("dataStatus") != "OK" or count < minimum or stat.get("medianAskingPriceVnd") is None:
            answer = (f"Chưa đủ mẫu giá rao để kết luận xu hướng tại {place}: "
                      f"{count} tin, dưới ngưỡng tối thiểu {minimum} tin. Không tạo xu hướng từ mẫu nhỏ.")
        else:
            total = format_vnd(stat["medianAskingPriceVnd"])
            per_sqm = Decimal(str(stat.get("medianPricePerSqm"))) / Decimal("1000000") if stat.get("medianPricePerSqm") is not None else None
            per_sqm_text = (str(per_sqm.quantize(Decimal("0.1"))).replace(".", ",") + " triệu/m²"
                            if per_sqm is not None else "chưa đủ dữ liệu giá/m²")
            answer = (f"Ảnh chụp giá rao tại {place}: trung vị {total}/căn, "
                      f"trung vị {per_sqm_text}, "
                      f"trên {count} tin đủ điều kiện. Đây là giá rao, không phải giá giao dịch; "
                      "hệ thống không dự báo tăng/giảm.")
            if meta.get("temporalStatus") != "AVAILABLE":
                answer += " Dữ liệu hiện tại chưa có chuỗi thời gian đủ để kết luận xu hướng."
        limitations = [
            "Số liệu là giá rao từ các nguồn công khai trong SmartProp, không phải giá giao dịch đã công chứng.",
            "Không dự báo giá, tỷ lệ tăng giá hoặc xu hướng tương lai.",
            f"Ngưỡng mẫu tối thiểu cho thống kê: {minimum} tin.",
        ]
        answer += " Xem thêm trang Phân tích thị trường để đối chiếu bảng và khoảng giá."
        return self._reply(request, session_id, context, {}, properties=[], citations=[], research=research,
            answer=answer, responseKind="MARKET_ANALYTICS", limitations=limitations,
            evidence={"market": {"status": "OK", "district": district, "overall": stat,
                                  "generatedAt": meta.get("generatedAt"),
                                  "temporalStatus": meta.get("temporalStatus"),
                                  "sourceCounts": data.get("bySource", [])},
                      "generation": {"accepted": False, "reason": "DETERMINISTIC_MARKET_AGGREGATE"},
                      "retrievedSourceIds": [], "semanticRetrieval": {"hits": []}})

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
        turn = classification(request.question, context if resumed else None)
        event("session_turn", resumed=resumed, turn=context.turns,
              followup=bool(turn["searchChange"] or turn["ordinal"] or turn["mapRequest"] or turn["analytic"]))
        limitations = list(LIMITATIONS)
        corpus = traced("corpus_load", self.knowledge.load)
        if traced("amenity_summary", self.backend.amenity_summary)["catalogVersion"] != corpus["summary"]["catalogVersion"]:
            raise GroundingError("PUBLIC_CORPUS_VERSION_DRIFT")
        documents = corpus["documents"]
        names = sorted({d["metadata"].get("district", "") for d in documents}, key=len, reverse=True)
        if account and not resumed:
            seed(context,account,names)
        explicit_district = request.district or detect_district(request.question, names)
        if asks_market_trend(request.question):
            return self._market_answer(request, session_id, context, research, explicit_district)
        # A follow-up that only refines one criterion keeps every other stored criterion.
        prior = context.criteria()
        district = explicit_district or prior.get("district")
        # Explicit POI categories are a routing rule, never a similarity guess.
        categories = poi_categories(request.question)
        asked_budget = budget_from_question(request.question)
        if asked_budget is None and request.budgetVnd is None:
            asked_budget = budget_from_followup(request.question)
        budget = request.budgetVnd if request.budgetVnd is not None else (asked_budget if asked_budget is not None else (
            Decimal(str(prior["budgetVnd"])) if prior.get("budgetVnd") is not None else None))
        criteria = request.model_dump(exclude={"question", "requireGeneration", "sessionId"}, exclude_none=True)
        # Defaults are not client intent: carry the stored value unless the caller overrides it.
        if criteria.get("purpose") == "LIVING" and prior.get("purpose"):
            criteria["purpose"] = prior["purpose"]
        if criteria.get("propertyType") == "ALL" and prior.get("propertyType"):
            criteria["propertyType"] = prior["propertyType"]
        for area_key in ("minAreaSqm", "maxAreaSqm", "minAreaExclusive", "maxAreaExclusive"):
            if area_key not in criteria and prior.get(area_key) is not None:
                criteria[area_key] = prior[area_key]
        if turn["purpose"]:
            criteria["purpose"] = turn["purpose"]
        if turn["propertyType"]:
            criteria["propertyType"] = turn["propertyType"]
        if not request.ward and prior.get("ward") and not explicit_district:
            criteria["ward"] = prior["ward"]
        if district is not None:
            criteria["district"] = district
        if prior.get("amenityPriorities"):
            criteria["amenityPriorities"] = list(prior["amenityPriorities"])
        response = None
        properties = []
        # An amenity-only follow-up must not spend a Recommendation call.
        amenity_only = bool(categories) and not turn["searchChange"] and turn["ordinal"] is None
        referral = turn["needsPropertyReference"]
        if budget is not None:
            criteria["budgetVnd"] = str(budget)
            if "minAreaSqm" in criteria:
                criteria["minAreaSqm"] = str(criteria["minAreaSqm"])
        # A listing the user opened travels as an opaque id. The server re-reads it through
        # the public API, so a draft or private listing is rejected here, not in the browser.
        focused = None
        if request.propertyId is not None:
            try:
                focused = traced("property_focus", lambda: self.backend.property_detail(request.propertyId))
            except GroundingError:
                if request.requireGeneration:
                    raise RagUnavailable("PROPERTY_NOT_PUBLIC")
                return self._reply(request, session_id, context, criteria, properties=[], citations=[], research=research,
                    answer=("Tin bạn đang xem không còn công khai hoặc không tồn tại, nên tôi không thể trả lời về căn đó. "
                            "Bạn có thể mở một tin khác hoặc hỏi lại theo ngân sách."),
                    responseKind="CLARIFICATION_REQUIRED", limitations=limitations,
                    extra={"clarification": "PROPERTY_NOT_PUBLIC"})
            context.needs["focusedPropertyId"] = focused["id"]
        elif context.needs.get("focusedPropertyId"):
            # The user left the listing page: drop the property context but keep budget and
            # the confirmed workplace, which belong to the session rather than to a listing.
            context.needs.pop("focusedPropertyId", None)
        # A question about the listing on screen, or a pending commute step, is answered
        # here so the lifestyle intake never hijacks it.
        if focused is not None:
            intent = focused_intent(request.question)
            # A pending commute step ("which workplace?", "pick a candidate") must be
            # answered even though its wording is not a commute question on its own.
            if intent is None and commute_destination.stage_of(context.needs):
                intent = "COMMUTE"
            if intent is not None:
                return self._focused_answer(request, session_id, context, criteria, focused, intent,
                                            limitations=limitations, research=research, token=token)
        # Record a commute-ranking request before any intake question can intercept it,
        # otherwise "tối đa 25 phút" is lost while the user answers "which district?".
        fresh_minutes, fresh_kind = commute_ranking.limit_from(request.question)
        if (fresh_minutes is not None
                or commute_ranking.wants_work_proximity(request.question)):
            context.needs["commutePendingLimit"] = {"minutes": fresh_minutes, "kind": fresh_kind}
        elif (not commute_destination.stage_of(context.needs)
                and commute_destination.destination_of(context.needs)):
            # A plain search after the workplace is settled drops the earlier commute ask;
            # while the workplace is still unknown the ask must survive the intake turns.
            context.needs.pop("commutePendingLimit", None)

        # Changing the workplace is its own request: it must work even on a turn that is
        # not a property search and not focused on a listing.
        if (not research and focused is None
                and (commute_destination.wants_new(request.question)
                     or commute_destination.wants_saved(request.question))):
            picked = self._commute_destination(request, session_id, context, criteria,
                                               limitations=limitations, research=research, token=token)
            if picked is not None:
                return picked

        # A street address is its own request: it must not be read as a budget, reduced
        # to a district, or overridden by the listing the user happens to have open.
        address_intent = None if research else address_search.intent(request.question)
        if address_intent == "AT_ADDRESS":
            return self._address_answer(request, session_id, context, criteria,
                                        address_search.address_in(request.question),
                                        limitations=limitations, research=research)
        if address_intent == "NEAR_ADDRESS":
            return self._near_address_answer(request, session_id, context, criteria,
                                             address_search.address_in(request.question),
                                             limitations=limitations, research=research)

        decision = intake(context, request.question, criteria, turn, explicit_district=explicit_district)
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
        must_search = (budget is not None and not amenity_only) or (referral and bool(prior))
        if must_search:
            if budget is None:
                limitations.append("Chưa có ngân sách trong ngữ cảnh; không thể xác định lại danh sách bất động sản.")
            else:
                # A commute ranking needs a wider pool than the three cards it shows,
                # otherwise the fastest route among three is not the fastest found.
                commute_dest = commute_destination.destination_of(context.needs)
                pending = context.needs.get("commutePendingLimit") or {}
                if (not research and (pending or commute_destination.stage_of(context.needs))
                        and not isinstance(commute_dest, dict)):
                    picked = self._commute_destination(request, session_id, context, criteria,
                                                       limitations=limitations, research=research, token=token)
                    if picked is not None:
                        return picked
                    commute_dest = commute_destination.destination_of(context.needs)
                    if not isinstance(commute_dest, dict):
                        return self._commute_source_prompt(request, session_id, context, criteria,
                                                           limitations=limitations, research=research)
                limit_minutes = pending.get("minutes")
                limit_kind = pending.get("kind")
                by_commute = bool(commute_dest) and not research and bool(pending)
                if not research:
                    criteria["limit"] = RANKING_POOL if by_commute else SUGGESTION_LIMIT
                response = traced("recommendation", lambda: self.backend.recommend(criteria, research=research, token=token))
                pool = response["topProperties"]
                if not research:
                    if by_commute and len(pool) > 1:
                        pool = self._rank_by_commute(pool, commute_dest, limit_minutes,
                                                     limit_kind or "SOFT", limitations)
                        if limit_minutes:
                            criteria["commuteLimitMinutes"] = limit_minutes
                            criteria["commuteLimitKind"] = limit_kind
                        if not pool and limit_kind == "HARD" and limit_minutes:
                            # Nothing survived the cap; let the user widen it in one tap.
                            context.needs["commuteSuggestWiden"] = limit_minutes
                    properties = pool[:SUGGESTION_LIMIT]
                else:
                    properties = pool
        else:
            if not categories:
                limitations.append("Chưa có một ngân sách rõ ràng; hệ thống chưa gọi công cụ lọc bất động sản.")

        # ---- property reference resolution (deterministic, never guessed) ----
        # `result_properties` is the full verified result set of THIS turn and stays the
        # reference universe for the next turn; only the visible selection is narrowed.
        result_properties = list(properties)
        asked_index = turn["ordinal"]
        context.needs["ordinalTurn"] = asked_index is not None
        # A completed search with no result clears the reference list for later ordinals.
        # Only the search paths that actually ran may set this; an address lookup already
        # recorded its own outcome before returning. A hard commute cap that emptied the
        # list is still a search that ran, so it counts too.
        if asked_index is None and decision.get("search") and not context.needs.get("addressQuery") \
                and not decision.get("question"):
            # Only a search that actually ran counts; an intake question did not search.
            # A later turn that does return cards clears the flag again.
            context.needs["lastSearchEmpty"] = not result_properties
        elif result_properties and asked_index is None:
            context.needs["lastSearchEmpty"] = False
        if result_properties and asked_index is None:
            # Remember the list the user is looking at. An ordinal turn only narrows the
            # view, and a reply that shows nothing must not erase the list either.
            context.needs["lastPropertyIds"] = [p["id"] for p in result_properties][:MAX_PROPERTY_IDS]
        referenced_id = None
        referenced_universe = None
        target = None
        if asked_index is not None:
            # "căn thứ ba" counts the cards the previous turn offered. When the user
            # changed nothing, the saved order wins even if the new query reorders or
            # drops one of the listings.
            saved = list(prior.get("_propertyIds") or [])
            # A search that completed with zero results replaces the list: an ordinal must
            # not silently reach back into the list from before that search.
            if context.needs.get("lastSearchEmpty") or prior.get("lastSearchEmpty") \
                    or (context.last_criteria or {}).get("lastSearchEmpty"):
                # The last search finished with nothing, so there is no card at any
                # position. Say that instead of reaching into an older list.
                context.needs["lastSearchEmpty"] = False
                if request.requireGeneration:
                    raise RagUnavailable("AMBIGUOUS_PROPERTY_REFERENCE")
                return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                    research=research,
                    answer=("Lượt tìm gần nhất không có bất động sản nào, nên không có "
                            f"bất động sản thứ {asked_index}. Bạn muốn tìm lại hay đổi tiêu chí?"),
                    responseKind="CLARIFICATION_REQUIRED", limitations=limitations, response=response,
                    extra={"clarification": "PROPERTY_INDEX_OUT_OF_RANGE"})
            if not turn["searchChange"] and not explicit_district and saved:
                by_id = {p["id"]: p for p in result_properties}
                restored = [by_id[pid] for pid in saved if pid in by_id]
                if restored:
                    result_properties = restored
                    referenced_universe = list(restored)
            if saved and not turn["searchChange"] and not explicit_district:
                if not 1 <= asked_index <= len(saved):
                    if request.requireGeneration:
                        raise RagUnavailable("AMBIGUOUS_PROPERTY_REFERENCE")
                    return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                        research=research,
                        answer=(f"Trong lượt trước chỉ có {len(saved)} bất động sản được đề xuất, nên không có "
                                f"bất động sản thứ {asked_index}. Bạn muốn xem lại danh sách hay đổi tiêu chí tìm kiếm?"),
                        responseKind="CLARIFICATION_REQUIRED", limitations=limitations, response=response,
                        result_properties=referenced_universe or result_properties,
                        extra={"clarification": "PROPERTY_INDEX_OUT_OF_RANGE"})
                target = saved[asked_index - 1]
        if asked_index is not None and target is not None:
            # The saved position names an id; the listing itself is re-read through the
            # public detail route, so a missing row in a fresh Recommendation result is
            # not evidence that the listing was removed.
            properties = [p for p in result_properties if p["id"] == target][:1]
            if not properties:
                try:
                    detail = traced("property_focus", lambda: self.backend.property_detail(target))
                except GroundingError:
                    return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                        research=research,
                        answer=(f"Bất động sản thứ {asked_index} trong danh sách trước "
                                "không còn công khai hoặc đã bị gỡ, nên tôi không trả thông tin cho căn đó. "
                                "Bạn muốn xem lại danh sách hiện có?"),
                        responseKind="CLARIFICATION_REQUIRED", limitations=limitations, response=response,
                        result_properties=referenced_universe or result_properties,
                        extra={"clarification": "PROPERTY_NOT_PUBLIC"})
                except UpstreamError:
                    limitations.append("Chưa tra cứu được tin này do lỗi dịch vụ; danh sách tham chiếu được giữ nguyên.")
                    return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                        research=research,
                        answer=("Chưa tra cứu được tin bạn hỏi do lỗi dịch vụ. "
                                "Bạn thử lại giúp tôi, danh sách trước vẫn còn đó."),
                        responseKind="CLARIFICATION_REQUIRED", limitations=limitations, response=response,
                        result_properties=referenced_universe or result_properties,
                        extra={"clarification": "PROPERTY_LOOKUP_UNAVAILABLE"})
                properties = [detail]
            referenced_id = "recommendation:" + properties[0]["id"] if properties else None
        elif asked_index is not None and result_properties:
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
        elif referral:
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

        # ---- answers about the single listing the user opened ----
        # Handled before the search path so "căn này giá bao nhiêu" never spends a
        # Recommendation call and never mixes in a different listing's facts.

        if not research and budget is not None and not properties and (decision["search"] or not asks_for_amenities(request.question)):
            # An empty authorized search is useful evidence. Do not replace it with
            # unrelated semantic POIs or claim that a templated answer came from Qwen.
            event("no_match_response", strict=request.requireGeneration, generationRequired=False)
            if request.requireGeneration:
                raise RagUnavailable("FULL_RAG_RUNTIME_UNAVAILABLE")
            widen = context.needs.pop("commuteSuggestWiden", None)
            no_match_extra = {}
            if widen:
                # A hard cap emptied the list: offer the next step instead of a dead end.
                no_match_extra = {"clarification": "COMMUTE_LIMIT_EXCEEDED",
                                  "quickReplies": [f"Nới mốc {int(widen * 2)} phút",
                                                   f"Chỉ cần tối đa {int(widen * 1.5)} phút",
                                                   "Bỏ mốc thời gian"]}
            return self._reply(request, session_id, context, criteria, properties=[], citations=[], research=research,
                answer=empty_search_answer(criteria), responseKind="NO_MATCHES", limitations=limitations, response=response,
                extra=no_match_extra,
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
                    # Enrich only after the ID/price/area cross-check passes. These are
                    # fixed public projections, never fields chosen or written by the LLM.
                    p["listingCode"] = row.get("listing_code")
                    p["description"] = row.get("description")
                    p["address"] = row.get("address")
                    p["propertyType"] = row.get("property_type")
                    p["bedrooms"] = row.get("bedrooms")
                    p["bathrooms"] = row.get("bathrooms")
                    p["floor"] = row.get("floor")
                    p["direction"] = row.get("direction")
                    p["amenities"] = row.get("declared_amenities") or []
                    p["project"] = row.get("project")
                    p["images"] = row.get("images") or []
                    p["legal"] = row.get("legal")
                    if row.get("imageUrl"):
                        p["imageUrl"] = row["imageUrl"]
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

        # Hard guarantee: an explicit POI category may never be answered with another category.
        if categories:
            matched = [d for d in retrieved if d["kind"] == "POI_EVIDENCE" and d["metadata"].get("category") in categories]
            if not matched and not research and district:
                # FAISS had no in-category evidence: use the same read-only, VALID-only POI
                # projection that already backs the map card. Never substitute another category.
                from .knowledge import document
                area_url = self.backend.settings.backend_url + "/api/v1/amenities/" + (
                    next((d["metadata"]["areaId"] for d in documents
                          if d["kind"] == "AREA_AMENITY" and d["metadata"].get("areaLevel") == "DISTRICT"
                          and d["metadata"].get("district") == district), "district"))
                for category in categories:
                    try:
                        mapped = traced("amenity_map_fallback", lambda c=category: self.backend.amenity_map(district, c))
                    except (RagUnavailable, GroundingError):
                        mapped = None
                    items = (mapped or {}).get("items") if isinstance(mapped, dict) else None
                    for item in (items or [])[:3]:
                        metadata = {"areaId": "map:" + item["id"], "district": item["district"],
                                    "name": item["name"], "category": item["category"],
                                    "attributionBasis": "OPENSTREETMAP_VALID"}
                        retrieved.append(document("poi-map:" + item["id"],
                            f"Bằng chứng tiện ích {item['name']}, loại {item['category']}, tại {item['district']}; "
                            "nguồn OpenStreetMap đã kiểm tra nguồn. Không có khoảng cách tới căn nhà.",
                            area_url, item.get("observedAt", "POI_MAP_V1"), "POI_EVIDENCE", metadata))
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
                    answer=insufficient_amenity_answer(district, categories), responseKind="INSUFFICIENT_AMENITY_EVIDENCE",
                    limitations=limitations, response=response, retrieval_mode=retrieval_mode,
                    evidence={"criteria": criteria if budget else None,
                        "amenityIntent": {"district": district, "categories": list(categories)},
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
            # Listing code is intentionally omitted from the conversational answer;
            # the validated property ID/link remains available in the card/citation.
            legal = p.get("legal") or {}
            text += (f" Hồ sơ pháp lý công khai: {int(legal.get('verified') or 0)} đã duyệt, "
                     f"{int(legal.get('pending') or 0)} chờ duyệt; không công khai tệp pháp lý riêng tư.")
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
        answer = render_answer(facts, selected, research=research, has_budget=budget is not None,
                               has_properties=bool(properties), requires_budget=not bool(categories))
        if generated_sentences is not None:
            # Actual Qwen-generated text survives verbatim validation; only scope labels/citations are appended by server.
            intro = render_answer({}, [], research=research, has_budget=budget is not None,
                                  has_properties=bool(properties), requires_budget=not bool(categories))
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
                      "amenityIntent": {"district": district, "categories": list(categories)},
                      "semanticRetrieval": {"indexVersion": getattr(self.retriever, "manifest", None).get("version") if isinstance(getattr(self.retriever, "manifest", None), dict) else None,
                                            "hits": [{"sourceId": d["sourceId"], "similarity": d.get("similarity")} for d in retrieved]},
                      "warnings": (response or {}).get("warnings", [])})
