from decimal import Decimal
import re
import time
from urllib.parse import quote
from .personalization import AREA_KEYS, matches_area, merge_area
from .config import GroundingError, RagUnavailable
from .schemas import Citation
from .knowledge import digest
from .diagnostics import traced
from .tools import UpstreamError, OutboundRateLimited
from .money import format_vnd
from . import focused_property, address_search, commute_destination, commute_ranking
from .focused_property import focused_intent
from .geo import haversine_meters
from .gis import gis_evidence
from .money import parse_budget
from .locality import (is_listing_location_edit, key as locality_key, listing_location,
                       listing_location_mentions, listing_location_text)
SUGGESTION_LIMIT=3
RANKING_POOL=6
NEARBY_RADIUS_METERS=1000
NEARBY_PENDING = ("nearbyPoints", "nearbyAddress", "nearConsentPending", "pendingNearbyAddress", "nearbySaleVerified")
AREA_RANGE_PROMPT = "Khoảng diện tích chưa hợp lệ. Bạn nhập lại một cận hoặc khoảng, ví dụ từ 70 đến 90 m²."
def norm(text):
    from .orchestrator import norm as normalize
    return normalize(text)
def number(value):
    return format(Decimal(str(value)),"f")


def _matches_listing_filters(item, criteria):
    price = Decimal(str(item["priceVnd"]))
    return (
        (not criteria.get("budgetVnd") or price <= Decimal(str(criteria["budgetVnd"])))
        and (not criteria.get("minPriceVnd") or price >= Decimal(str(criteria["minPriceVnd"])))
        and (criteria.get("propertyType", "ALL") == "ALL" or item.get("propertyType") == criteria["propertyType"])
        and all(not criteria.get(key) or locality_key(criteria[key]) == locality_key(item.get(key))
                for key in ("district", "ward"))
        and matches_area(item.get("areaSqm"), criteria)
    )


class AdvisorDiscoveryMixin:
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
                        "Geoapify để lấy toạ độ. Địa chỉ sẽ xuất hiện trong hội thoại và lịch sử nếu bạn đăng nhập; không tự ghi vào hồ sơ. Bạn đồng ý chứ?"),
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
        batch_failed = False
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
            batch_failed = True
        by_id = {cell.get("propertyId"): cell for cell in cells if isinstance(cell, dict)}
        # When the batch itself failed there are no cells at all. That is not "no route":
        # nothing was measured, so every listing is unmeasured rather than unroutable.
        batch_failed = batch_failed or not cells
        entries = []
        for property, listing_id in zip(properties, ids):
            cell = by_id.get(listing_id) or {}
            seconds = cell.get("durationSeconds")
            route = None
            if seconds is not None:
                route = {"distanceMeters": cell.get("distanceMeters"), "durationSeconds": seconds,
                         "provider": provider}
            if route:
                property["commute"]={**route,"mode":destination.get("mode","drive"),"estimated":True}
            entries.append({"property": property, "route": route,
                            "status": "NOT_MEASURED" if batch_failed
                            else (cell.get("status") or "NO_ROUTE")})
        ordered = commute_ranking.rank(entries, limit_minutes, kind, SUGGESTION_LIMIT)
        measured = [row for row in entries if row["route"]]
        # A listing the vendor could not route and one the batch never reached are
        # different facts: the first has no route, the second was not measured at all.
        no_route = [row for row in entries if row["status"] == "NO_ROUTE"]
        not_measured = [row for row in entries if row["status"] == "NOT_MEASURED"]
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
                detail = ""
                if no_route:
                    detail += f" {len(no_route)} tin chưa có tuyến."
                if not_measured:
                    detail += f" {len(not_measured)} tin chưa đo được thời gian đi làm trong lượt này."
                limitations.append(
                    f"Trong {len(properties)} tin đã lọc theo ngân sách, chưa tính được tuyến cho tin nào "
                    f"nên chưa xác minh được mốc {limit_minutes} phút.{detail} "
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
            if no_route:
                scope += f" {len(no_route)} tin chưa có tuyến nên không được xếp theo thời gian."
            if not_measured:
                scope += f" {len(not_measured)} tin chưa đo được thời gian đi làm trong lượt này."
            limitations.append(scope)
        return [row["property"] for row in ordered]


    def _address_answer(self, request, session_id, context, criteria, address, *, limitations, research):
        """Listings whose own address carries this house number and street."""
        if not address:
            return None
        try:
            found = traced("search_by_address",
                           lambda: self.backend.search_by_address(address, criteria=criteria))
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
        context.needs["listingAddressScope"] = {"address": address}
        matched = [item for item in found.get("items", [])
                   if address_search.matches(item.get("address") or "", address)]
        properties = [item for item in matched if _matches_listing_filters(item, criteria)][:SUGGESTION_LIMIT]
        complete = found.get("complete", True)
        extra = {"addressQuery": address, "addressSearchComplete": complete}
        if not complete:
            limitations.append(f"Chưa đọc hết danh sách tin theo địa chỉ ({found['pagesRead']} trang).")
        if not properties:
            if not complete:
                answer = f"Chưa thấy tin phù hợp tại {address} trong các trang đã đọc. Vẫn còn trang chưa kiểm tra."
                kind, clarification = "CLARIFICATION_REQUIRED", "ADDRESS_SEARCH_INCOMPLETE"
            elif matched:
                answer = "Không có tin phù hợp với địa chỉ và các bộ lọc bắt buộc hiện tại. Tôi không tự tăng ngân sách."
                kind, clarification = "ADDRESS_NO_RESULTS", "ADDRESS_NO_MATCH"
            else:
                answer = f"Chưa tìm thấy tin nhà tại {address} theo bộ lọc hiện tại."
                kind, clarification = "NO_MATCHES", "ADDRESS_NO_MATCH"
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer=answer, responseKind=kind, limitations=limitations,
                evidence={"recommendationMethod": "ADDRESS_FILTER",
                          "criteria": criteria,
                          "recommendationSearch": {"performed": True, "resultCount": 0,
                              "sourcePath": "/api/v1/properties",
                              "criteriaHash": digest(criteria)},
                          "generation": {"accepted": False, "reason": "NOT_NEEDED_FOR_EMPTY_SEARCH" if complete
                                         else "NOT_NEEDED_FOR_INCOMPLETE_SEARCH"},
                          "retrievedSourceIds": [], "semanticRetrieval": {"indexVersion": None, "hits": []},
                          "sql": {"status": "NO_PLATFORM_RESULTS", "matchedRows": 0},
                          "gis": gis_evidence([], [], [])},
                extra={**extra, "clarification": clarification,
                       "quickReplies": [f"Xem nhà gần {address}", "Tìm theo ngân sách"]})

        coverage = "" if complete else " trong phần đã đọc"
        return self._reply(request, session_id, context, criteria, properties=properties, citations=[],
            research=research,
            answer=(f"Tìm thấy {len(properties)} tin nhà có địa chỉ khớp “{address}”{coverage}. "
                    f"Giá là giá rao công khai của từng tin."),
            responseKind="PROPERTY_LIST", limitations=limitations,
            extra=extra)


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
                origin["latitude"], origin["longitude"], radius, max_price=budget, criteria=criteria))
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
        context.needs["listingAddressScope"] = {"address": address, "origin": origin}
        for item in found.get("items", []):
            if not _matches_listing_filters(item, criteria) or not isinstance(item.get("latitude"), (int, float)) \
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
        extra = {"addressQuery": address, "addressSearchComplete": complete,
                 "nearAddress": True, "radiusMeters": radius}
        if not complete:
            limitations.append(
                f"Chưa đọc hết danh sách tin trong hộp tra cứu ({found['pagesRead']} trang). "
                "Kết quả chỉ tính trên phần đã đọc, chưa phải toàn bộ khu vực.")
        properties = []
        for meters, item in measured[:SUGGESTION_LIMIT]:
            item["distanceMeters"] = round(meters, 1)
            item["distanceType"] = "STRAIGHT_LINE"
            item.setdefault("source", {"kind": "PROPERTY", "recordKey": item["id"],
                                       "name": item.get("title") or "Tin SmartProp"})
            properties.append(item)

        if not properties:
            limitations.append(f"Phạm vi tra cứu là bán kính {radius // 1000} km quanh “{address}”.")
            if complete:
                answer = (f"Chưa tìm thấy tin nhà trong bán kính {radius // 1000} km "
                          f"quanh vị trí đã xác nhận của “{address}” theo bộ lọc hiện tại.")
                kind, clarification = "NO_MATCHES", "ADDRESS_NEARBY_EMPTY"
            else:
                answer = "Chưa thấy tin lân cận phù hợp trong các trang đã đọc. Vẫn còn trang chưa kiểm tra."
                kind, clarification = "CLARIFICATION_REQUIRED", "ADDRESS_SEARCH_INCOMPLETE"
            return self._reply(request, session_id, context, criteria, properties=[], citations=[],
                research=research,
                answer=answer, responseKind=kind, limitations=limitations,
                evidence={"recommendationMethod": "NEARBY_DISTANCE",
                          "criteria": criteria,
                          "recommendationSearch": {"performed": True, "resultCount": 0,
                              "sourcePath": "/api/v1/properties",
                              "criteriaHash": digest(criteria)},
                          "generation": {"accepted": False, "reason": "NOT_NEEDED_FOR_EMPTY_SEARCH" if complete
                                         else "NOT_NEEDED_FOR_INCOMPLETE_SEARCH"},
                          "retrievedSourceIds": [], "semanticRetrieval": {"indexVersion": None, "hits": []},
                          "sql": {"status": "NO_PLATFORM_RESULTS", "matchedRows": 0},
                          "gis": gis_evidence([], [], [])},
                extra={**extra, "clarification": clarification,
                       "quickReplies": ["Tìm theo ngân sách", "Mở rộng bán kính"]})

        limitations.append(
            f"Nhà trong bán kính {radius // 1000} km quanh “{address}”. "
            f"Khoảng cách là đường chim bay từ toạ độ tin đăng tới vị trí đã xác nhận, "
            f"không phải quãng đường đi thực tế.")
        nearest = "gần nhất" if complete else "gần nhất trong phần đã đọc"
        return self._reply(request, session_id, context, criteria, properties=properties, citations=[],
            research=research,
            answer=(f"Nhà trong bán kính {radius // 1000} km quanh “{address}”: "
                    f"{len(properties)} tin, {nearest} {properties[0]['distanceMeters'] / 1000:.2f} km."),
            responseKind="PROPERTY_LIST", limitations=limitations,
            extra={**extra, "nearOrigin": origin})

    def dispatch_discovery(self, request, session_id, context, turn, address_query, *,
                           districts=(), research=False, token=None, account=None, continuing=False):
        if research:return None
        state=context.needs
        address, outside_address, mode = address_query
        previous_search = state.get("listingAddressScope")
        location_edit = bool(previous_search and not address and is_listing_location_edit(request.question)
                             and not turn["categories"] and not turn["domain"])
        prior = context.criteria()
        pending_nearby = state.get("nearConsentPending") or state.get("nearbyPoints")
        control = norm(request.question).strip().rstrip(".!?")
        reply_to_nearby = (control == "dong y tim vi tri"
                           or commute_destination.is_plain_consent(request.question)
                           or commute_destination.candidate_index(request.question, 5))
        if pending_nearby and reply_to_nearby and not mode and not state.get("nearbySaleVerified"):
            # Checkpoints from before the transaction guard may have recorded a rental as LIVING.
            for key in NEARBY_PENDING:
                state.pop(key, None)
            return self._reply(request, session_id, context, prior, properties=[], citations=[], research=False,
                answer="Bạn nhập lại địa chỉ cần tìm tin mua để xác nhận vị trí cho lượt tìm này nhé.",
                responseKind="CLARIFICATION_REQUIRED", extra={"clarification": "NEAR_ADDRESS_RESTART"})
        minutes,fresh_kind=commute_ranking.limit_from(request.question)
        explicit_commute=minutes is not None or commute_ranking.wants_work_proximity(request.question) or focused_intent(request.question)=='COMMUTE'
        if turn['intent'] in ('MARKET_PRICE','MARKET_TREND','MARKET_ANALYSIS','LEGAL_QA','PLANNING_QA','KNOWLEDGE','AREA_AMENITIES') and not explicit_commute:
            return None
        if turn["intent"] == "UPDATE_CRITERIA" and not (mode or location_edit or explicit_commute):
            return None
        if turn.get('searchChange') and not (continuing or explicit_commute or mode or location_edit):
            for key in ('commuteStage','commutePoints','commutePendingAddress','commutePendingLimit'):
                state.pop(key,None)
            state.pop("listingAddressScope", None)
        criteria={k:v for k,v in prior.items() if not k.startswith('_')}
        criteria.setdefault('purpose','LIVING');criteria.setdefault('propertyType','ALL')
        prior_area = {key: criteria.pop(key) for key in AREA_KEYS if key in criteria}
        criteria.update(request.model_dump(include=set(AREA_KEYS), exclude_none=True))
        filter_text = outside_address if mode else request.question
        if not merge_area(criteria, prior_area, filter_text if mode or location_edit or turn["searchChange"] else "",
                          allow_bare=state.get("pending") == "min_area"):
            for key in NEARBY_PENDING:
                state.pop(key, None)
            return self._reply(request, session_id, context, prior, properties=[], citations=[], research=False,
                answer=AREA_RANGE_PROMPT, responseKind="CLARIFICATION_REQUIRED",
                extra={"clarification": "AREA_RANGE_INVALID"})
        location = {"district": request.district, "ward": request.ward}
        if mode or location_edit:
            place_text = listing_location_text(outside_address) if mode else outside_address
            mentions = listing_location_mentions(place_text)
            if mentions:
                try:
                    areas = self.backend.amenity_areas() if any(m["level"] in ("phuong", "xa") for m in mentions) else []
                    resolved = listing_location(place_text, districts, areas if isinstance(areas, list) else [])
                except (GroundingError, UpstreamError):
                    resolved = None
                if resolved is None or any(location[key] and locality_key(location[key]) != locality_key(label)
                                           for key, label in resolved.items()):
                    return self._reply(request, session_id, context, prior, properties=[], citations=[], research=False,
                        answer="Bạn xác nhận một quận hoặc một phường cần lọc nhé. Tôi chưa tìm khi địa bàn chưa rõ hoặc mâu thuẫn.",
                        responseKind="CLARIFICATION_REQUIRED", extra={"clarification": "LISTING_LOCALITY_UNRESOLVED"})
                location.update(resolved)
        if location["district"]:
            if locality_key(criteria.get("district")) != locality_key(location["district"]):
                criteria.pop("ward", None)
            criteria["district"] = location["district"]
        if location["ward"]:
            criteria["ward"] = location["ward"]
        parsed=parse_budget(filter_text)
        if parsed.status == 'AMBIGUOUS' and (mode or location_edit):
            return self._reply(request, session_id, context, prior, properties=[], citations=[], research=False,
                answer="Tôi chưa xác định rõ ngân sách. Bạn nhập mức tối đa hoặc một khoảng bằng đồng nhé.",
                responseKind="CLARIFICATION_REQUIRED", extra={"clarification": "BUDGET_AMBIGUOUS"})
        if parsed.status=='AMBIGUOUS' and turn.get('budgetMentioned'):return None
        if parsed.status=='VALID':
            criteria['budgetVnd']=str(parsed.maximum)
            if parsed.minimum is not None:criteria['minPriceVnd']=str(parsed.minimum)
            else:criteria.pop('minPriceVnd',None)
        if request.budgetVnd is not None:criteria['budgetVnd']=str(request.budgetVnd)
        if request.minPriceVnd is not None:criteria['minPriceVnd']=str(request.minPriceVnd)
        if 'propertyType' in request.model_fields_set:criteria['propertyType']=request.propertyType
        if turn.get('propertyType'):criteria['propertyType']=turn['propertyType']
        if turn.get('purpose'):criteria['purpose']=turn['purpose']
        limits=[]
        if location_edit:
            if previous_search.get("origin"):
                return self._nearby_from(request, session_id, context, criteria, previous_search["address"],
                                         previous_search["origin"], limitations=limits, research=False)
            return self._address_answer(request, session_id, context, criteria, previous_search["address"],
                                        limitations=limits, research=False)
        if mode:
            for key in ("listingAddressScope", *NEARBY_PENDING):
                state.pop(key, None)
        if mode=='AT_ADDRESS':
            return self._address_answer(request,session_id,context,criteria,address,limitations=limits,research=False)
        if mode=='NEAR_ADDRESS':
            state['pendingNearbyAddress']=address
            state['nearConsentPending']=True
            state["nearbySaleVerified"] = True
            self.sessions.record(context,criteria=criteria,property_ids=None,area_ids=None,evidence_ids=[],question=request.question)
            return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=False,
                answer='Để tìm nhà trong 1 km, bạn có đồng ý gửi địa chỉ này tới Geoapify không? Tôi chỉ dùng điểm trong phiên này.',
                responseKind='CLARIFICATION_REQUIRED',extra={'clarification':'NEAR_ADDRESS_CONSENT','quickReplies':['Đồng ý tìm vị trí','Bỏ qua']})
        if pending_nearby and control in ("bo qua", "huy"):
            for key in NEARBY_PENDING:
                state.pop(key, None)
            return self._reply(request, session_id, context, criteria, properties=[], citations=[], research=False,
                answer="Đã bỏ qua tìm vị trí.", responseKind="CRITERIA_UPDATED")
        if state.get('nearConsentPending'):
            if control == "dong y tim vi tri":
                state.pop('nearConsentPending',None)
                address=state.pop('pendingNearbyAddress')
                try:
                    points=self.backend.geocode_workplace(address)
                except (UpstreamError,GroundingError):
                    state.pop("nearbySaleVerified", None)
                    return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=False,
                        answer="Dịch vụ tìm vị trí chưa sẵn sàng hoặc đã chạm hạn mức. Tôi chưa thể xác định vị trí để tìm trong 1 km; đây không phải kết luận là không có nhà. Bạn có thể thử lại sau hoặc tìm theo ngân sách.",
                        responseKind="DATA_SOURCE_ERROR",extra={"queryStatus":"GEOCODING_UNAVAILABLE","quickReplies":["Tìm theo ngân sách"]})
                if not points:
                    state.pop("nearbySaleVerified", None)
                    return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=False,answer='Chưa tìm được vị trí cho địa chỉ này. Bạn có thể nhập địa chỉ rõ hơn.',responseKind='CLARIFICATION_REQUIRED')
                state['nearbyPoints']=points[:5];state['nearbyAddress']=address
                return self._reply(request,session_id,context,criteria,properties=[],citations=[],research=False,
                    answer='Bạn chọn và xác nhận đúng điểm để tìm nhà trong 1 km. Đây là vị trí đề xuất, chưa xác minh số nhà.',responseKind='CLARIFICATION_REQUIRED',
                    extra={'clarification':'NEAR_ADDRESS_PICK','quickReplies':[str(i+1)+'. '+str(p.get('label',''))[:60] for i,p in enumerate(points[:5])]})
        if state.get('nearbyPoints'):
            points=state['nearbyPoints'];index=commute_destination.candidate_index(request.question,len(points))
            if index:
                origin = points[index - 1]
                state.pop("nearbyPoints")
                address = state.pop("nearbyAddress")
                state.pop("nearbySaleVerified", None)
                return self._nearby_from(request,session_id,context,criteria,address,origin,limitations=limits,research=False)
        minutes,kind=commute_ranking.limit_from(request.question)
        if minutes is not None or commute_ranking.wants_work_proximity(request.question):
            state['commutePendingLimit']={'minutes':minutes,'kind':kind or 'SOFT'}
        focus=request.propertyId or state.get('focusedPropertyId')
        focused_kind=focused_intent(request.question) if focus else None
        if focus and (focused_kind in ('COMMUTE','AMENITY') or commute_destination.stage_of(state)):
            state['focusedPropertyId']=focus
            return self._focused_answer(request,session_id,context,criteria,self.backend.property_detail(focus),focused_kind or 'COMMUTE',limitations=limits,research=False,token=token)
        pending=commute_destination.stage_of(state)
        wants=commute_destination.wants_new(request.question) or commute_destination.wants_saved(request.question)
        if pending or wants or state.get('commutePendingLimit') and not commute_destination.destination_of(state):
            if account and account.get('enabled'):state['active']=True
            reply=self._commute_destination(request,session_id,context,criteria,limitations=limits,research=False,token=token)
            if reply is not None:return reply
            if not commute_destination.destination_of(state):
                return self._commute_source_prompt(request,session_id,context,criteria,limitations=limits,research=False)
            state['commuteResumeSearch']=True
            self.sessions.record(context,criteria=criteria,property_ids=None,area_ids=None,evidence_ids=[],question=request.question)
        return None
