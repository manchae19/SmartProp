"""User-approved inclusive budget bands; no changes to dataset prices."""
import re, unicodedata, importlib.util, sys, pathlib
from decimal import Decimal
def fold(s):return ''.join(c for c in unicodedata.normalize('NFD',s.lower().replace('đ','d')) if not unicodedata.combining(c))
spec=importlib.util.spec_from_file_location('review_money',pathlib.Path(__file__).with_name('money_parser.py'))
money=importlib.util.module_from_spec(spec);sys.modules[spec.name]=money;spec.loader.exec_module(money)

def normalize_price(question):
    n=fold(re.sub(r'(?iu)\btầm\b','khoảng',question)).replace('–','-').replace('—','-')
    n=re.sub(r'(?<=\d)(ty|ti|trieu|tr)(?=\d)',r'\1 ',n)
    n=n.replace('<=',' toi da ').replace('>=',' toi thieu ').replace('<',' duoi ').replace('>',' tren ')
    # Common compact billion notation: 7t5, 7ty5, 7 tỷ 500, 7 tỷ rưỡi.
    n=re.sub(r'(?<![\w.,])(\d+)\s*(?:ty|ti|t)\s*(\d{1,3})(?![\w.,])(?!\s*(?:trieu|tr|nghin|ngan|dong|vnd|m2|m²|met))',
             lambda m:str(Decimal(m[1])+(Decimal(m[2])/10 if len(m[2])==1 else Decimal(m[2])/1000))+' ty',n)
    n=re.sub(r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*t\b',r'\1 ty',n)
    digits={'khong':0,'mot':1,'hai':2,'ba':3,'bon':4,'tu':4,'nam':5,'lam':5,'sau':6,'bay':7,'tam':8,'chin':9}
    def words_number(match):
        words=match[1].split();value=0;pending=None
        for word in words:
            if word in digits:pending=digits[word]
            elif word=='tram':value+=(pending if pending is not None else 1)*100;pending=None
            elif word in ('muoi','chuc'):value+=(pending if pending is not None else 1)*10;pending=None
        return str(value+(pending or 0))+' '+match[2]
    words=r'(?:khong|mot|hai|ba|bon|tu|nam|lam|sau|bay|tam|chin|muoi|tram|linh|le|chuc)'
    start_words=r'(?:khong|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi|tram)'
    n=re.sub(r'\b('+start_words+r'(?:\s+'+words+r')*)\s+(ty|ti|trieu|tr)\b',words_number,n)
    # A full grouped VND amount is usable without requiring a trailing unit.
    n=re.sub(r'(?<![\w.,-])(\d{1,3}(?:[.,]\d{3}){2,}|\d{7,15})(?![\w.,])(?!\s*(?:ty|ti|trieu|tr|dong|vnd|m2|m²))',r'\1 vnd',n)
    # Expand shared units before distinguishing prices from plot numbers.
    n=re.sub(r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(den|toi|-)\s*(\d+(?:[.,]\d+)?)\s*(ty|ti|trieu|tr)\b',r'\1 \4 \2 \3 \4',n)
    return n


def budget_band(question):
    n=normalize_price(question)
    # Explicit ranges always take priority over inferred bands.
    explicit=bool(re.search(r'\d[\d.,]*\s*(?:ty|ti|trieu)?\s*(?:den|toi|-)\s*\d',n))
    tokens=list(money.TOKEN.finditer(n))
    if not tokens:return None
    prefix=n[:tokens[0].start()]
    above=bool(re.search(r'\b(tren|hon|tu|toi thieu|it nhat)\s*$',prefix))
    below=bool(re.search(r'\b(duoi|toi da|khong qua|khong vuot|tro xuong)\s*$',prefix)) or bool(re.search(r'\b(tro xuong|do lai)\b',n))
    above=above or bool(re.search(r'\b(tro len|do len)\b',n))
    clean=re.sub(r'\b(tren|hon|toi thieu|it nhat|tam|khoang|quanh|xap xi)\b','',n)
    parsed=money.parse_budget(clean)
    if parsed.status!='VALID':raise ValueError('Mức giá chưa rõ; hãy nêu một mốc có đơn vị hoặc khoảng từ … đến … tỷ.')
    amount=int(parsed.maximum)
    if explicit and parsed.minimum is not None:return {'minPrice':int(parsed.minimum),'maxPrice':amount}
    if above and below:raise ValueError('Bạn muốn giá từ mốc này trở lên hay trở xuống?')
    if above:return {'minPrice':amount}
    if below:return {'maxPrice':amount}
    if re.search(r'\bdung\b',n):return {'minPrice':amount,'maxPrice':amount}
    if not re.search(r'\b(khoang|tam|quanh|xap xi)\b',n):return {'maxPrice':amount}
    delta=500000000 if amount>5000000000 else 300000000
    return {'minPrice':max(0,amount-delta),'maxPrice':amount+delta}


def budget_rank_target(question,band):
    if band is None:return None
    n=normalize_price(question)
    explicit=bool(re.search(r'\d[\d.,]*\s*(?:ty|ti|trieu|tr)?\s*(?:den|toi|-)\s*\d',n))
    if explicit and 'minPrice' in band and 'maxPrice' in band:return (band['minPrice']+band['maxPrice'])//2
    clean=re.sub(r'\b(tren|hon|toi thieu|it nhat|tam|khoang|quanh|xap xi)\b','',n)
    parsed=money.parse_budget(clean)
    return int(parsed.maximum) if parsed.status=='VALID' else None

def without_money(question):
    # Let the existing parser handle area/type/place without overriding bands.
    n=normalize_price(question)
    return money.TOKEN.sub('',n)
