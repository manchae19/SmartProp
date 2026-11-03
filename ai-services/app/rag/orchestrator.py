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
    # Exact single amount only. Multiple amounts / shorthand are not guessed.
    if len(re.findall(r"tỷ|\bty\b|triệu|\btrieu\b", question.lower())) != 1:
        return None
    values = re.findall(r"(?<![\w.,])([0-9]+(?:[.,][0-9]+)?)\s*(tỷ|ty|triệu|trieu)\b(?!\s*\d)", question.lower())
    if len(values) != 1:
        return None
    value, unit = values[0]
    amount = Decimal(value.replace(",", ".")) * (10**9 if unit in ("tỷ", "ty") else 10**6)
    return amount if 1 <= amount <= 999999999999999 else None


class ChatOrchestrator:
    def __init__(self, backend, repository, knowledge, retriever, llm, sessions=None):
        self.backend, self.repository, self.knowledge = backend, repository, knowledge
        self.retriever, self.llm = retriever, llm
        # Bounded in-memory conversation memory. Never persisted, never authoritative.
        self.sessions = sessions or SessionStore()

    # ------------------------------------------------------------------
    def _reply(self, request, session_id, context, criteria, *, properties, citations, research,
               answer, responseKind=None, limitations=None, response=None, extra=None,
               evidence=None, generation_mode="EVIDENCE_ONLY", retrieval_mode="TOOL_EVIDENCE_ONLY",
               result_properties=None, reference_id=None):
        """Single exit point: every reply records bounded state and returns the session id.

        `properties` is what the user sees; `result_properties` is the full verified
        result set of this turn, which is what the next turn must be able to reference.
        """
        full = list(result_properties if result_properties is not None else properties)
        property_ids = [p["id"] for p in full][:MAX_PROPERTY_IDS]
        self.sessions.record(context,
            criteria={**{k: v for k, v in (criteria or {}).items() if k not in ("sessionTurn", "_propertyIds")},
                      "_propertyIds": property_ids} if criteria and (criteria.get("budgetVnd") or criteria.get("district")) else None,
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
        return ChatResponse(answer=answer, mode="INTERNAL_RESEARCH" if research else "SAFE",
            generationMode=generation_mode, retrievalMode=retrieval_mode, citations=list(citations),
            recommendedProperties=list(properties), evidence=payload, dataLimitations=list(limitations or []))

    def chat(self, request, *, research=False, token=None):
        # Authorization happens BEFORE corpus retrieval or backend/sql tools.
        if research:
            traced("research_authorization", lambda: self.backend.authorize_research(token))
        # Session scope comes from the authenticated route, never from the client payload,
        # so a public caller cannot address (or read) a research context.
        scope = "INTERNAL_RESEARCH" if research else "PUBLIC"
        context, session_id, resumed = traced("session_begin",
            lambda: self.sessions.begin(request.sessionId, scope=scope))
        turn = classification(request.question, context if resumed else None)
        event("session_turn", resumed=resumed, turn=context.turns,
              followup=bool(turn["searchChange"] or turn["ordinal"] or turn["mapRequest"] or turn["analytic"]))
        limitations = list(LIMITATIONS)
        corpus = traced("corpus_load", self.knowledge.load)
        if traced("amenity_summary", self.backend.amenity_summary)["catalogVersion"] != corpus["summary"]["catalogVersion"]:
            raise GroundingError("PUBLIC_CORPUS_VERSION_DRIFT")
        documents = corpus["documents"]
        names = sorted({d["metadata"].get("district", "") for d in documents}, key=len, reverse=True)
        explicit_district = request.district or detect_district(request.question, names)
        # A follow-up that only refines one criterion keeps every other stored criterion.
        prior = context.criteria() if resumed else {}
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
        if "minAreaSqm" not in criteria and prior.get("minAreaSqm") is not None:
            criteria["minAreaSqm"] = prior["minAreaSqm"]
        if turn["purpose"]:
            criteria["purpose"] = turn["purpose"]
        if turn["propertyType"]:
            criteria["propertyType"] = turn["propertyType"]
        if not request.ward and prior.get("ward") and not explicit_district:
            criteria["ward"] = prior["ward"]
        if district is not None:
            criteria["district"] = district
        response = None
        properties = []
        # An amenity-only follow-up must not spend a Recommendation call.
        amenity_only = bool(categories) and not turn["searchChange"] and turn["ordinal"] is None
        referral = turn["needsPropertyReference"]
        if budget is not None:
            criteria["budgetVnd"] = str(budget)
            if "minAreaSqm" in criteria:
                criteria["minAreaSqm"] = str(criteria["minAreaSqm"])
        # A changed budget/district always re-queries the live API. A stored list is
        # never replayed as a new result set; it only names what to ask about.
        must_search = (budget is not None and not amenity_only) or (referral and bool(prior))
        if must_search:
            if budget is None:
                limitations.append("Chưa có ngân sách trong ngữ cảnh; không thể xác định lại danh sách bất động sản.")
            else:
                response = traced("recommendation", lambda: self.backend.recommend(criteria, research=research, token=token))
                properties = response["topProperties"]
        else:
            limitations.append("Chưa có một ngân sách rõ ràng; hệ thống chưa gọi công cụ lọc bất động sản.")

        # ---- property reference resolution (deterministic, never guessed) ----
        # `result_properties` is the full verified result set of THIS turn and stays the
        # reference universe for the next turn; only the visible selection is narrowed.
        result_properties = list(properties)
        asked_index = turn["ordinal"]
        referenced_id = None
        if asked_index is not None and result_properties:
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

        if not research and budget is not None and not properties and not asks_for_amenities(request.question):
            # An empty authorized search is useful evidence. Do not replace it with
            # unrelated semantic POIs or claim that a templated answer came from Qwen.
            event("no_match_response", strict=request.requireGeneration, generationRequired=False)
            if request.requireGeneration:
                raise RagUnavailable("FULL_RAG_RUNTIME_UNAVAILABLE")
            return self._reply(request, session_id, context, criteria, properties=[], citations=[], research=research,
                answer=empty_search_answer(criteria), responseKind="NO_MATCHES", limitations=limitations, response=response,
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
                      "amenityIntent": {"district": district, "categories": list(categories)},
                      "semanticRetrieval": {"indexVersion": getattr(self.retriever, "manifest", None).get("version") if isinstance(getattr(self.retriever, "manifest", None), dict) else None,
                                            "hits": [{"sourceId": d["sourceId"], "similarity": d.get("similarity")} for d in retrieved]},
                      "warnings": (response or {}).get("warnings", [])})
