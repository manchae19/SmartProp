"""Hòa Xuân land tool for the SmartProp chatbot.

Flow:  question → domain gate → (optional) Ollama rewrite to a canonical command → land engine
       (deterministic filters, prices, record ids, paging) → structured reply for the chat UI.

Ollama only rephrases a question the deterministic router could not read into one canonical
command, and the rewrite is accepted only if it matches the command grammar below and the
engine then understands it. Numbers, record ids, filters and paging always come from the engine.
"""
import json
import re
import unicodedata

import httpx

from .diagnostics import event

UNKNOWN_PREFIX = "Tôi chưa hiểu yêu cầu này"
PUBLIC_ROW_KEYS = ("id", "displayName", "displayNumber", "computedAreaSqm", "priceDescription", "purposeGroup",
                   "planningLabel", "planningCode", "sourceLot", "unlocatedProjectLot", "importedParcel",
                   "pointOnSurface", "demoPriceVnd", "referencePriceVnd", "searchPriceVnd", "effectivePriceClass")


COLLOQUIAL = [
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*tỏi\b", re.I), r"\1 tỷ"),                       # "2 tỏi" = 2 tỷ
    (re.compile(r"\b(?:bị\s+)?nước\s+(?:lên|dâng|ngập)\b|\bngập\s+nước\b|\bbị\s+nước\b", re.I), "ngập"),
    # "mùa mưa" folds to "mua mua" and would read as the verb "mua" (buy); the flood word carries the meaning.
    (re.compile(r"\b(?:vào\s+|khi\s+)?mùa\s+mưa(?:\s+bão)?\b", re.I), ""),
]


def colloquial(question):
    """Deterministic buyer slang → words the land router knows. Never adds a number."""
    english = re.fullmatch(r"(?:find|show(?: me)?) (?:land|plots?)(?: (under|below|over|above) ([0-9]+(?:[.,][0-9]+)?) (billion|million)(?: vnd)?)?[.?! ]*", question.strip(), re.I)
    if english:
        direction = {"under": "dưới", "below": "dưới", "over": "trên", "above": "trên"}
        question = "Tìm đất" + (" " + direction[english[1].lower()] + " " + english[2] + " " + ("tỷ" if english[3].lower() == "billion" else "triệu") if english[1] else "")
    question = re.sub(r"\beuro\s*2\b", "Euro Village 2", question, flags=re.I)
    question = re.sub(r"mắc\s+(?:tiền\s+)?nhất|đắt\s+tiền\s+nhất", "đắt nhất", question, flags=re.I)
    for pattern, repl in COLLOQUIAL:
        question = pattern.sub(repl, question)
    return " ".join(question.split())


def fold(value):
    return " ".join(unicodedata.normalize("NFD", (value or "").lower().replace("đ", "d"))
                    .encode("ascii", "ignore").decode().split())


LAND_WORDS = re.compile(r"\b(dat o|dat nong nghiep|tho cu|lo dat|o dat|o quy hoach|thua|dn-qh-\d|guland|euro(?: village)? 2|euro village|lang chau au|"
                        r"trieu phu|b2[.\- ]?\d+|hoa xuan|mieng dat|manh dat|tim dat|mua dat|xem dat|dat \d|dat khoang|dat tam|"
                        r"dat duoi|dat tren|dat gia|lo \d+ ty|to \d+ thua|danh sach thua|du lieu da nap|thong ke du lieu|"
                        r"lo nay|lo do|lo thu|lo cuoi|dat (?:thuong mai|cong vien|mat nuoc|cong nghiep|cay xanh))\b")
FLOOD_WORDS = re.compile(r"\b(ngap|lut|ngap ung|mua lon)\b")
HOUSE_WORDS = re.compile(r"\b(nha|can ho|chung cu|biet thu|phong ngu|cho thue|thue)\b")
OTHER_DISTRICTS = re.compile(r"\b(hai chau|son tra|thanh khe|ngu hanh son|lien chieu|hoa vang)\b")
FOLLOW_UP = re.compile(r"^(xem them|tiep|con nua|con khong|con lo nao|lo thu|o thu|cai dau|cai thu|can thu|thu nhat|lo cuoi|cai cuoi|"
                       r"re hon|dat hon|re nhat|dat nhat|cao nhat|so sanh|lo nay|o nay|thua nay|lo do|gia lo|"
                       r"bo loc|bo dieu kien|khong loc|doi sang|duoi \d|tren \d|tu \d|khoang \d|tam \d|\d)")
COURTESY = re.compile(r"^(cam on|thank|ok|duoc roi|tot qua)\b")
NEW_SEARCH = re.compile(r"\b(tim|mua|ngan sach|can ho|chung cu|nha|thue|xin chao|chao ban)\b")
FOLLOW_UP_ANY = re.compile(r"\b(lo nay|o nay|thua nay|lo do|lo thu|o thu|so sanh|xem them|re hon|dat hon|co ngap|ngap khong|gia nay|gia do|"
                           r"so do|so hong|giay to|giay chung nhan|thu hoi|tranh chap|the chap|boi thuong|loai dat|du an|chu dau tu|"
                           r"quy hoach|phap ly|huong|mat tien)\b")
LAND_DOMAINS = ("plot", "project", "guland", "flood", "flood_empty", "imported")

# The only commands Ollama may produce. Everything else is rejected.
CANONICAL = re.compile(r"^(Tìm (đất ở|đất nông nghiệp|đất)( (khoảng|dưới|trên|từ) [0-9.,]+( đến [0-9.,]+)? (tỷ|triệu))?"
                       r"( diện tích (khoảng |dưới |trên |từ )?[0-9.,]+( đến [0-9.,]+)? m2)?( rẻ nhất| đắt nhất)?"
                       r"|Xem thêm|Lô thứ [0-9]{1,2}|So sánh lô thứ [0-9]{1,2} và lô thứ [0-9]{1,2}"
                       r"|Lô (này|thứ [0-9]{1,2}) (có ngập không|giá bao nhiêu|có sổ không|loại đất gì|có bị thu hồi không)"
                       r"|Xem lô đất [0-9]{1,4}|Đảo Triệu Phú|Xem thửa Guland|Danh sách vị trí nguy cơ ngập Đà Nẵng"
                       r"|Nguy cơ ngập (phường|quận) [A-Za-zÀ-ỹ ]{2,30})$")
PROMPT = ("Bạn chuyển câu hỏi của người mua đất tại Hòa Xuân, Đà Nẵng thành ĐÚNG MỘT câu lệnh chuẩn. "
          "Chỉ dùng một trong các mẫu: 'Tìm đất ở khoảng N tỷ', 'Tìm đất ở dưới N tỷ', 'Tìm đất ở trên N tỷ', "
          "'Tìm đất ở từ A đến B tỷ', thêm tùy chọn ' diện tích khoảng N m2' hoặc ' diện tích từ A đến B m2', "
          "'Tìm đất nông nghiệp', 'Tìm đất ở rẻ nhất', 'Tìm đất ở đắt nhất', 'Xem thêm', 'Lô thứ N', "
          "'So sánh lô thứ A và lô thứ B', 'Lô này có ngập không', 'Lô này giá bao nhiêu', 'Lô này có sổ không', "
          "'Xem lô đất N', 'Đảo Triệu Phú', 'Xem thửa Guland', 'Danh sách vị trí nguy cơ ngập Đà Nẵng'. "
          "Chỉ trả về đúng câu lệnh trên một dòng, không giải thích, không ngoặc kép. Không tự thêm số, diện tích, giá hay địa danh không có trong câu hỏi; người hỏi không nêu điều kiện nào thì không thêm điều kiện đó. Nếu không chắc, trả dòng trống.")


WORD_NUMBERS = {"mot": "1", "hai": "2", "ba": "3", "bon": "4", "tu": "4", "nam": "5", "sau": "6", "bay": "7", "tam": "8", "chin": "9", "muoi": "10"}


def accept_rewrite(question, command):
    """A model rewrite is used only if it is one canonical command and invents no number."""
    if not command or not CANONICAL.match(command):
        return False
    folded = fold(question)
    target = fold(command)
    # A paraphrase cannot switch the record family or convert an attribute
    # question to a new catalogue search, even when its numbers are unchanged.
    if "guland" in target and "guland" not in folded:
        return False
    for words in (r"giay to|so do|so hong|phap ly|giay chung nhan", r"thuoc du an|du an nao|chu dau tu", r"dien tich|rong|dai bao nhieu"):
        if re.search(words, folded) and not re.search(words, target):
            return False
    given = set(re.findall(r"\d+", folded)) | {v for k, v in WORD_NUMBERS.items() if re.search(r"\b" + k + r"\b", folded)}
    if not set(re.findall(r"\d+", command)) <= given:
        return False
    # Meaning guards the grammar cannot see: list position vs plot number, and "more" needs a "more" word.
    ordinal = bool(re.search(r"\bthu\b", folded))
    if command.startswith("Xem lô đất") and ordinal:
        return False                      # "lô thứ hai" is position 2 in the list, not plot 2
    if re.match(r"(Lô|So sánh lô) thứ", command) and not ordinal and not re.search(r"\b(?:lo|cai) \d", folded):
        return False
    if command == "Xem thêm" and not re.search(r"\b(?:them|tiep|nua|khac)\b", folded):
        return False
    return True


class LandAdvisor:
    def __init__(self, settings=None, *, enabled=True, engine=None):
        self.settings = settings
        self.enabled = enabled
        self._engine = engine

    @property
    def engine(self):
        if self._engine is None:
            from app.land import engine
            self._engine = engine
        return self._engine

    # ---------------------------------------------------------------- routing
    def wants(self, question, state, *, focused=False):
        n = fold(colloquial(question)).strip(" ?!.")
        if not n:
            return False
        last = (state or {}).get("lastDomain")
        if LAND_WORDS.search(n):
            # A named SmartProp district other than Hòa Xuân is a platform listing search.
            return not (OTHER_DISTRICTS.search(n) and not FLOOD_WORDS.search(n) and "hoa xuan" not in n)
        if FLOOD_WORDS.search(n) and not focused:
            return True
        if last in LAND_DOMAINS and not focused and re.search(r"giay to|phap ly|dien tich|thuoc du an|du an nao|lo dau|cai dau|thue|phi", n):
            return True
        if last in LAND_DOMAINS and not focused and not (HOUSE_WORDS.search(n) and not LAND_WORDS.search(n)):
            return bool(FOLLOW_UP.match(n) or FOLLOW_UP_ANY.search(n) or COURTESY.match(n))
        return False

    # ----------------------------------------------------------------- Ollama
    def rewrite(self, question):
        s = self.settings
        if s is None or getattr(s, "llm_provider", "") != "ollama":
            return None
        # Plain text, one short line. A free-string JSON schema ("format") makes qwen3:4b-instruct on
        # Ollama 0.40 emit only whitespace until num_predict, so the rewrite never arrived in time.
        try:
            with httpx.Client(base_url=s.ollama_url, trust_env=False, timeout=httpx.Timeout(25, connect=2)) as client:
                r = client.post("/api/chat", json={"model": s.ollama_model, "stream": False, "think": False,
                                                   "keep_alive": s.ollama_keep_alive_seconds,
                                                   "options": {"temperature": 0, "seed": 42, "num_predict": 48},
                                                   "messages": [{"role": "system", "content": PROMPT},
                                                                {"role": "user", "content": question[:500]}]})
                r.raise_for_status()
                body = r.json()
                lines = [x for x in str(body["message"]["content"]).strip().splitlines() if x.strip()]
                command = (lines[0] if lines else "").strip().strip('"“”\'`.').strip()
                # The land scope is always Hòa Xuân; a trailing place name adds nothing.
                command = re.sub(r"\s+(?:ở|tại)\s+(?:phường\s+)?Hòa Xuân(?:,?\s*Đà Nẵng)?$", "", command, flags=re.I)
                if body.get("done_reason") != "stop" or len(command) > 120:
                    command = ""
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            event("land_rewrite", outcome="unavailable")
            return None
        if not accept_rewrite(question, command):
            event("land_rewrite", outcome="rejected")
            return None
        event("land_rewrite", outcome="accepted")
        return command

    # ------------------------------------------------------------------- turn
    def reply(self, question, context, *, focused=False):
        if not self.enabled:
            return None
        state = context.needs.get("land")
        question = colloquial(question)
        if not self.wants(question, state, focused=focused):
            if state and NEW_SEARCH.search(fold(question)):
                # The buyer started another kind of search: a later "xem thêm" belongs to that
                # answer, not to the land list shown before it. Filters and selection stay remembered.
                state.update(lastDomain=None, selected=None, seen=[], visibleIds=[])
            return None
        try:
            result, new_state = self.engine.converse(question, state)
            rewritten = None
            if result.get("answer", "").startswith(UNKNOWN_PREFIX):
                command = self.rewrite(question)
                if command:
                    retry, retry_state = self.engine.converse(command, state)
                    if not retry.get("answer", "").startswith(UNKNOWN_PREFIX):
                        result, new_state, rewritten = retry, retry_state, command
        except ValueError as e:
            # Engine validation messages (bad budget, bad area range) are user-facing.
            return self._payload(str(e), {"rows": []}, "LAND_CLARIFICATION", None)
        context.needs["land"] = new_state
        kind = ("FLOOD_CATALOG" if result.get("responseKind") == "FLOOD_CATALOG" else
                "LAND_COMPARISON" if result.get("comparison") else
                "LAND_RECORD" if result.get("selected") or result.get("focusedAnswer") else
                "LAND_SEARCH" if result.get("rows") or result.get("total") is not None else "LAND_INFO")
        return self._payload(result["answer"], result, kind, rewritten)

    def _payload(self, answer, result, kind, rewritten):
        e = self.engine
        rows = []
        for r in (result.get("rows") or [])[:10]:
            demo = r.get("demoPresentation") or {}
            flood = r.get("floodDisplay") or {}
            row = {k: r[k] for k in PUBLIC_ROW_KEYS if r.get(k) is not None}
            row.update(landId=e.land_id(r["id"]), sourceCode=r["id"], kind=("GULAND_PARCEL" if r.get("importedParcel") else
                       "PROJECT_LOT_UNLOCATED" if r.get("unlocatedProjectLot") else "PROJECT_LOT" if r.get("sourceLot") else "PLANNING_CELL"),
                       location=(r.get("addressEvidence") or {}).get("location") or "Hòa Xuân, Đà Nẵng",
                       priceType=("ROAD_ASKING_ESTIMATE" if r.get("roadPriceEvidence") else "HISTORICAL_ASKING" if r.get("sourceLot") or r.get("unlocatedProjectLot")
                                  else "SOURCE_ASKING" if r.get("importedParcel") and r.get("priceVnd") else "SIMULATED_DEMO" if r.get("demoPriceVnd") else "NONE"),
                       located=not r.get("unlocatedProjectLot"),
                       demo={k: demo.get(k) for k in ("landType", "ownershipDocument", "recovery", "dispute", "compensation")} if demo else None,
                       flood={"display": flood.get("display"), "relation": flood.get("relation") or flood.get("basis"),
                              "isDemoAssumption": flood.get("isDemoAssumption", False)} if flood else None)
            rows.append(row)
        flood_records = [{k: x.get(k) for k in ("id", "record_type", "typeLabel", "location_text", "current_unit", "source_district",
                                                "district", "publication_date", "source_page", "source_title", "source_url")}
                         for x in (result.get("floodRecords") or [])[:10]]
        land = {"version": "LAND_V1", "kind": kind, "rows": rows, "start": result.get("start"), "total": result.get("total"),
                "filters": result.get("filters"), "targetPriceVnd": result.get("targetPriceVnd"), "areaFilters": result.get("areaFilters"),
                "unappliedConditions": result.get("unappliedConditions") or [], "selectedId": result.get("selected") if isinstance(result.get("selected"), str) else (rows[0]["sourceCode"] if kind == "LAND_RECORD" and rows else None),
                "floodRecords": flood_records, "floodTotal": result.get("floodTotal"), "floodAllIds": (result.get("floodAllIds") or [])[:200],
                "rewrittenQuestion": rewritten, "dataVersion": "HX-LAND-DEMO-20261126", "demoOnly": True}
        return {"properties": [], "citations": [], "answer": answer, "responseKind": kind,
                "limitations": ["Bản demo Hòa Xuân: giá mô phỏng và các giá trị giấy tờ, thu hồi, ngập theo kịch bản demo được ghi rõ; chưa phải xác minh thực tế."],
                "extra": {"land": land}}
