"""Deterministic Vietnamese purchase budgets. Never silently reuse an unreadable amount."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
import unicodedata

LIMIT = Decimal("999999999999999")
UNITS = {"ty": Decimal(10**9), "ti": Decimal(10**9), "trieu": Decimal(10**6), "tr": Decimal(10**6),
         "nghin": Decimal(1000), "ngan": Decimal(1000), "k": Decimal(1000),
         "dong": Decimal(1), "vnd": Decimal(1), "d": Decimal(1)}
NUM = r"[0-9]+(?:[.,][0-9]+|[ ][0-9]{3})*"
UNIT = r"ty|ti|trieu|tr|nghin|ngan|dong|vnd|k|d"
TOKEN = re.compile(r"(?<![\w.,])("+NUM+r")\s*("+UNIT+r")(?!\w)")

@dataclass(frozen=True)
class Budget:
    status: str
    maximum: Decimal | None = None
    minimum: Decimal | None = None
    reason: str | None = None


def _number(raw):
    raw=raw.replace(" ", "")
    if re.fullmatch(r"[0-9]{1,3}(?:[.,][0-9]{3})+",raw):
        raw=raw.replace(".", "").replace(",", "")
    elif "." in raw and "," in raw:
        raise InvalidOperation()
    elif raw.count(".")+raw.count(",")>1:
        raise InvalidOperation()
    return Decimal(raw.replace(",", "."))


def parse_budget(question):
    text="".join(c for c in unicodedata.normalize("NFD",question.lower().replace("đ","d")) if not unicodedata.combining(c))
    text=text.replace("–","-").replace("—","-")
    # Shared unit in ranges: '2 den 3 ty' -> '2 ty den 3 ty'.
    text=re.sub(r"(?<![\w.,])("+NUM+r")\s*(den|toi|-)\s*("+NUM+r")\s*("+UNIT+r")(?!\w)",
                lambda m:m[1]+" "+m[4]+" "+m[2]+" "+m[3]+" "+m[4],text)
    # A price per square metre is not a purchase ceiling: "30 triệu/m2" must never become
    # a 30 000 000 VND total budget.
    if re.search(r"(?<![\w.,])"+NUM+r"\s*(?:"+UNIT+r")\s*(?:/|tren|moi|mot|1)\s*(?:m2|m²|met vuong|m vuong)(?!\w)",text):
        return Budget("AMBIGUOUS",reason="UNIT_PRICE_NOT_TOTAL")
    # Area figures are not money: "nhà 2 tỷ 100m2" is a 2 tỷ budget and a 100 m² area,
    # not an unreadable "2 tỷ 100".
    text=re.sub(r"(?<![\w.,])"+NUM+r"\s*(?:m2|m²|met vuong|m vuong)(?!\w)"," ; ",text)
    if re.search(r"\b(?:tang|giam|them|bot)\b.{0,25}\b(?:them|bot)\b|\b(?:them|bot)\s+\d",text):
        return Budget("AMBIGUOUS",reason="RELATIVE_CHANGE_REQUIRES_CONFIRMATION")
    text=text.replace("nho hon", "duoi")
    matches=list(TOKEN.finditer(text))
    if not matches:
        bare=text.strip()
        stated=re.search(r"\b(?:ngan sach|toi co|minh co|tai chinh)\s+(?:toi da\s+)?("+NUM+r")(?![\w.,])",text)
        if stated: bare=stated[1]
        if re.fullmatch(NUM,bare):
            try:
                amount=_number(bare)
                return Budget("VALID",amount) if 1000000<=amount<=LIMIT else Budget("AMBIGUOUS",reason="MISSING_UNIT")
            except InvalidOperation:
                return Budget("AMBIGUOUS",reason="INVALID_NUMBER")
        mentioned=bool(re.search(r"\d[^;!?]{0,15}\b(?:ty|ti|trieu|vnd|dong)\b",text))
        return Budget("AMBIGUOUS" if mentioned else "NOT_MENTIONED",reason="UNREADABLE_AMOUNT" if mentioned else None)
    # "âm 2 tỷ" / "-2 tỷ" are negative; "tầm 2 tỷ", "năm nay 2 tỷ" or "làm 2 tỷ" are not.
    if re.search(r"(?:-|(?<!\w)am)\s*$",text[:matches[0].start()]):
        return Budget("AMBIGUOUS",reason="NEGATIVE_AMOUNT")
    amounts=[]
    end=0
    previous_unit=None
    try:
        for match in matches:
            value=_number(match[1]);unit=UNITS[match[2]]
            gap=text[end:match.start()]
            if amounts and re.fullmatch(r"\s*(?:va\s*)?",gap):
                if unit>=previous_unit or value!=int(value) or (unit!=1 and value*unit>=previous_unit):
                    return Budget("AMBIGUOUS",reason="AMBIGUOUS_COMPOSITE")
                amounts[-1]+=value*unit
            else:
                amounts.append(value*unit)
            previous_unit=unit;end=match.end()
        suffix=text[end:]
        if re.match(r"\s*ruoi\b",suffix):
            if len(amounts)!=1 or len(matches)!=1:return Budget("AMBIGUOUS",reason="AMBIGUOUS_COMPOSITE")
            amounts[0]+=previous_unit/2
            suffix=re.sub(r"^\s*ruoi\b","",suffix)
        if re.match(r"\s*\d",suffix):return Budget("AMBIGUOUS",reason="MISSING_UNIT")
        if any(not a.is_finite() or a<1 or a>LIMIT or a!=a.to_integral_value() for a in amounts):
            return Budget("AMBIGUOUS",reason="AMOUNT_OUT_OF_RANGE")
        if len(amounts)==2 and re.search(r"\b(?:den|toi)\b|\s-\s|\d\s*-\s*\d",text) and not re.search(r"\b(?:hoac|hay)\b",text):
            low,high=amounts
            return Budget("VALID",high,low) if low<=high else Budget("AMBIGUOUS",reason="REVERSED_RANGE")
        if len(amounts)!=1:return Budget("AMBIGUOUS",reason="MULTIPLE_AMOUNTS")
        if re.search(r"\b(?:tren|hon|it nhat|toi thieu)\s*$",text[:matches[0].start()]):
            return Budget("AMBIGUOUS",reason="MISSING_MAXIMUM")
        return Budget("VALID",amounts[0])
    except (InvalidOperation,ValueError,OverflowError):
        return Budget("AMBIGUOUS",reason="INVALID_NUMBER")


def format_vnd(value):
    """Vietnamese grouping without rounding: a non-zero fraction is kept, never dropped."""
    amount=Decimal(str(value))
    whole,_,fraction=format(amount,"f").partition(".")
    sign="-" if whole.startswith("-") else ""
    grouped=f"{int(whole.lstrip('-') or 0):,}".replace(",", ".")
    fraction=fraction.rstrip("0")
    return sign+grouped+(","+fraction if fraction else "")+" đồng"
