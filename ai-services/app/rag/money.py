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
UNIT = "|".join(UNITS)
TOKEN = re.compile(r"(?<![\w.,])("+NUM+r")\s*("+UNIT+r")(?!\w)")
_AMOUNT = rf"{NUM}\s*(?:{UNIT})(?!\w)"
_RANGE_START = rf"(?:(?:{_AMOUNT}|{NUM})\s*(?:den|toi|[-–—])\s*)?"
_SLASH_DATE = (r"(?:0?[1-9]|[12]\d|3[01])\s*/\s*thang\s+(?:0?[1-9]|1[0-2])\b"
               r"(?:\s*[/.-]\s*\d{2,4}\b|\s+nam\s+\d{4}\b|\s*[.!?,;]?\s*$)")
_RECURRING = re.compile(
    rf"(?<![\w.,/])(?:{_RANGE_START}{_AMOUNT}(?:\s*{_AMOUNT})*(?:\s+ruoi)?"
    rf"|(?<!\bngay )(?<!\bthang )(?!{_SLASH_DATE}){_RANGE_START}(?P<bare>{NUM}))"
    r"\s*(?:/\s*|(?:theo|moi|mot|hang)\s+)(?:thang|nam|ngay)\b"
)

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


def _fold(question):
    return "".join(c for c in unicodedata.normalize("NFD", question.lower().replace("đ", "d"))
                   if not unicodedata.combining(c))


def recurring_amounts(question):
    """Return periodic monetary spans in the folded question."""
    return _RECURRING.finditer(_fold(question))


def mask_recurring_amounts(folded_text):
    """Hide periodic amounts while retaining offsets for other text parsers."""
    return _RECURRING.sub(lambda match: " " * len(match[0]), folded_text)


def parse_budget(question):
    # A recurring amount cannot be interpreted as a total purchase price.
    text = mask_recurring_amounts(_fold(question))
    text=text.replace("–","-").replace("—","-")
    # Shared unit in ranges: '2 den 3 ty' -> '2 ty den 3 ty'.
    text=re.sub(r"(?<![\w.,])("+NUM+r")\s*(den|toi|-)\s*("+NUM+r")\s*("+UNIT+r")(?!\w)",
                lambda m:m[1]+" "+m[4]+" "+m[2]+" "+m[3]+" "+m[4],text)
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
    if re.search(r"(?:-|\bam)\s*$",text[:matches[0].start()]):
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
    whole, _, fraction = format(Decimal(str(value)), ",f").partition(".")
    fraction = fraction.rstrip("0")
    return whole.replace(",", ".") + ("," + fraction if fraction else "") + " đồng"
