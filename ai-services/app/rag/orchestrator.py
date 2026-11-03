from decimal import Decimal
import re
import unicodedata
from .config import GroundingError, RagUnavailable
from .knowledge import digest
from .schemas import ChatResponse, Citation
from .validator import render_answer, validate_plan, validate_generated_answer
from .gis import gis_evidence
from .diagnostics import traced, event, reason
from .intent import asks_for_amenities, empty_search_answer


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
    def __init__(self, backend, repository, knowledge, retriever, llm):
        self.backend, self.repository, self.knowledge = backend, repository, knowledge
        self.retriever, self.llm = retriever, llm

    def chat(self, request, *, research=False, token=None):
        # Authorization happens BEFORE corpus retrieval or backend/sql tools.
        if research:
            traced("research_authorization", lambda: self.backend.authorize_research(token))
        limitations = list(LIMITATIONS)
        corpus = traced("corpus_load", self.knowledge.load)
        if traced("amenity_summary", self.backend.amenity_summary)["catalogVersion"] != corpus["summary"]["catalogVersion"]:
            raise GroundingError("PUBLIC_CORPUS_VERSION_DRIFT")
        documents = corpus["documents"]
        district = request.district
        if not district:
            names = sorted({d["metadata"].get("district", "") for d in documents}, key=len, reverse=True)
            district = next((d for d in names if d and re.search(r"(?<!\w)" + re.escape(norm(d)) + r"(?!\w)", norm(request.question))), None)
        budget = request.budgetVnd if request.budgetVnd is not None else budget_from_question(request.question)
        criteria = request.model_dump(exclude={"question", "requireGeneration"}, exclude_none=True)
        criteria["district"] = district
        response = None
        properties = []
        if budget is not None:
            criteria["budgetVnd"] = str(budget)
            if "minAreaSqm" in criteria:
                criteria["minAreaSqm"] = str(criteria["minAreaSqm"])
            response = traced("recommendation", lambda: self.backend.recommend(criteria, research=research, token=token))
            properties = response["topProperties"]
        else:
            limitations.append("Chưa có một ngân sách rõ ràng; hệ thống chưa gọi công cụ lọc bất động sản.")

        if not research and budget is not None and not properties and not asks_for_amenities(request.question):
            # An empty authorized search is useful evidence. Do not replace it with
            # unrelated semantic POIs or claim that a templated answer came from Qwen.
            event("no_match_response", strict=request.requireGeneration, generationRequired=False)
            if request.requireGeneration:
                raise RagUnavailable("FULL_RAG_RUNTIME_UNAVAILABLE")
            return ChatResponse(answer=empty_search_answer(criteria), mode="SAFE",
                generationMode="EVIDENCE_ONLY", retrievalMode="TOOL_EVIDENCE_ONLY", citations=[], recommendedProperties=[],
                evidence={"responseKind": "NO_MATCHES", "recommendationMethod": response.get("method"),
                    "criteria": criteria, "eligibleCandidateCount": response.get("eligibleCandidateCount"), "topAreas": [],
                    "recommendationSearch": {"performed": True, "resultCount": 0,
                        "sourcePath": "/api/v1/recommendations", "criteriaHash": digest(criteria)},
                    "generation": {"accepted": False, "reason": "NOT_NEEDED_FOR_EMPTY_SEARCH"},
                    "retrievedSourceIds": [], "semanticRetrieval": {"indexVersion": None, "hits": []},
                    "sql": {"status": "NO_PLATFORM_RESULTS", "matchedRows": 0},
                    "gis": gis_evidence([], [], []), "warnings": response.get("warnings", [])}, dataLimitations=limitations)

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
            retrieved = traced("semantic_retrieval", lambda: self.retriever.search(request.question, documents, internal=research, district=district, k=3))
        except (RagUnavailable, ImportError):
            retrieval_mode = "TOOL_EVIDENCE_ONLY"
            limitations.append("E5/FAISS chưa sẵn sàng: chỉ dùng bằng chứng API theo khu vực chính xác, không giả lập semantic retrieval.")
            area_ids = [a.get("amenityAreaId") for a in (response or {}).get("topAreas", [])]
            retrieved = [d for d in documents if d["kind"] == "AREA_AMENITY" and d["scope"] == "PUBLIC" and
                         ((d["metadata"].get("district") == district and d["metadata"].get("areaLevel") == "DISTRICT") or
                          d["metadata"]["areaId"] in area_ids)][:3]
            # Exact category routing is an evidence tool, not a replacement embedding model.
            categories = {"HOSPITAL": ["benh vien", "y te"], "SCHOOL": ["truong", "giao duc"],
                          "MARKET": ["cho"], "SUPERMARKET": ["sieu thi"], "PARK": ["cong vien"], "BEACH": ["bai bien"]}
            requested = {c for c, terms in categories.items() if any(re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", norm(request.question)) for t in terms)}
            if district and requested:
                retrieved = retrieved[:1] + [d for d in documents if d["kind"] == "POI_EVIDENCE" and d["scope"] == "PUBLIC"
                    and d["metadata"].get("district") == district and d["metadata"].get("category") in requested][:2]
            # Exact category routing is an evidence tool, not a replacement embedding model.
            categories = {"HOSPITAL": ["benh vien", "y te"], "SCHOOL": ["truong", "giao duc"],
                          "MARKET": ["cho"], "SUPERMARKET": ["sieu thi"], "PARK": ["cong vien"], "BEACH": ["bai bien"]}
            requested = {c for c, terms in categories.items() if any(re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", norm(request.question)) for t in terms)}
            if district and requested:
                retrieved = retrieved[:1] + [d for d in documents if d["kind"] == "POI_EVIDENCE" and d["scope"] == "PUBLIC"
                    and d["metadata"].get("district") == district and d["metadata"].get("category") in requested][:2]

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
        selected = property_facts + area_facts
        generation_mode = "EVIDENCE_ONLY"
        generation_evidence = {"accepted": False}
        generated_sentences = None
        try:
            if getattr(self.llm, "output_kind", None) == "grounded_answer":
                generated = traced("ollama_generation", lambda: self.llm.answer(request.question, {k: facts[k] for k in selected}))
                event("generation_metrics", **generated.metrics)
                generated_sentences = traced("answer_validation", lambda: validate_generated_answer(generated.raw, facts, property_facts))
                selected = list(dict.fromkeys(property_facts + [s["factId"] for s in generated_sentences]))
                generation_evidence = {**generated.metrics, "accepted": True, "outputSha256": digest(generated.raw),
                                       "sentences": generated_sentences, "style": "GROUNDED_EXTRACTIVE_TEXT"}
                generation_mode = "QWEN_GROUNDED_ANSWER"
            else:
                plan = self.llm.plan(request.question, {k: facts[k] for k in selected})
                chosen = validate_plan(plan, set(selected))
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
        return ChatResponse(answer=answer,
            mode="INTERNAL_RESEARCH" if research else "SAFE", generationMode=generation_mode, retrievalMode=retrieval_mode,
            citations=[c for key, c in citations.items() if key in used], recommendedProperties=properties,
            evidence={"recommendationMethod": (response or {}).get("method"), "criteria": criteria if budget else None,
                      "eligibleCandidateCount": (response or {}).get("eligibleCandidateCount"),
                      "topAreas": (response or {}).get("topAreas", []), "catalogVersion": corpus["summary"]["catalogVersion"],
                      "corpusVersion": corpus["contentHash"], "catalogSummary": corpus["summary"],
                      "retrievedSourceIds": [d["sourceId"] for d in retrieved], "sql": {"status": sql_status, "matchedRows": sql_count},
                      "generation": generation_evidence, "gis": gis_evidence(rows, properties, retrieved),
                      "semanticRetrieval": {"indexVersion": getattr(self.retriever, "manifest", None).get("version") if isinstance(getattr(self.retriever, "manifest", None), dict) else None,
                                            "hits": [{"sourceId": d["sourceId"], "similarity": d.get("similarity")} for d in retrieved]},
                      "warnings": (response or {}).get("warnings", [])}, dataLimitations=limitations)
