"""A prompt alone cannot prevent the hallucinations demonstrated in notebook cells 9/10."""
import json
import re
from .config import GroundingError


def validate_plan(raw, allowed):
    if not isinstance(raw, str) or len(raw) > 12000 or re.search(r"[\u3400-\u9fff]", raw):
        raise GroundingError("INVALID_MODEL_PLAN")
    try:
        plan = json.loads(raw)
    except (ValueError, TypeError) as e:
        raise GroundingError("INVALID_MODEL_PLAN") from e
    if not isinstance(plan, dict) or set(plan) != {"factIds"}:
        raise GroundingError("INVALID_MODEL_PLAN")
    ids = plan["factIds"]
    if not isinstance(ids, list) or len(ids) > 20 or not all(isinstance(i, str) and i in allowed for i in ids) or len(set(ids)) != len(ids):
        raise GroundingError("UNSUPPORTED_MODEL_FACT")
    return ids


def validate_generated_answer(raw, facts, property_facts):
    if not isinstance(raw, str) or len(raw) > 20000 or re.search(r"[\u3400-\u9fff]", raw):
        raise GroundingError("INVALID_GENERATED_ANSWER")
    try:
        result = json.loads(raw)
    except (ValueError, TypeError) as e:
        raise GroundingError("INVALID_GENERATED_ANSWER") from e
    if not isinstance(result, dict) or set(result) != {"sentences"} or not isinstance(result["sentences"], list) or not 1 <= len(result["sentences"]) <= 3:
        raise GroundingError("INVALID_GENERATED_ANSWER")
    seen, sentences = set(), []
    for item in result["sentences"]:
        if not isinstance(item, dict) or set(item) != {"factId", "text"}:
            raise GroundingError("INVALID_GENERATED_SENTENCE")
        fid = item["factId"]
        if not isinstance(fid, str) or fid not in facts or fid in seen or item["text"] != facts[fid]["text"]:
            raise GroundingError("UNSUPPORTED_GENERATED_CLAIM")
        seen.add(fid)
        sentences.append({"factId": fid, "text": item["text"], "sourceId": facts[fid]["sourceId"]})
    if property_facts:
        selected = [s["factId"] for s in sentences if s["factId"] in property_facts]
        if not selected or selected[0] != property_facts[0] or selected != sorted(selected, key=property_facts.index):
            raise GroundingError("GENERATED_RANKING_DRIFT")
    return sentences


def render_answer(facts, selected, *, research, has_budget, has_properties, requires_budget=True):
    intro = "Kết quả tham khảo từ dữ liệu SmartProp hiện có."
    if research:
        intro = "CHỈ NGHIÊN CỨU NỘI BỘ — dữ liệu chưa xác minh, không phải tin đang bán đã được công nhận công khai."
    if requires_budget and not has_budget:
        intro += " Bạn cần cung cấp ngân sách để hệ thống lọc bất động sản."
    elif requires_budget and has_budget and not has_properties:
        intro += " Không có bất động sản đủ điều kiện trong phạm vi tìm kiếm; không mở dữ liệu nghiên cứu để thay thế kết quả rỗng."
    return "\n".join([intro] + [facts[i]["text"] + f" [{facts[i]['sourceId']}]" for i in selected])


def validate_generated_relevance(sentences, facts, categories, district):
    """The answer must cite evidence of the requested category and geography.

    A semantically close but differently categorised sentence can never back an
    explicit POI category question. This runs on the already-validated sentences.
    """
    if not categories:
        return sentences
    for sentence in sentences:
        fact = facts.get(sentence["factId"])
        if fact is None:
            raise GroundingError("UNSUPPORTED_GENERATED_CLAIM")
        category = fact.get("category")
        if category is not None and category not in categories:
            raise GroundingError("AMENITY_SCOPE_MISMATCH")
        if district and category is not None and fact.get("district") not in (None, district):
            raise GroundingError("AMENITY_SCOPE_MISMATCH")
    return sentences
