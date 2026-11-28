"""Current asking-price evidence, never transaction prices or inferred trends."""
import re
from decimal import Decimal
from urllib.parse import urlencode
from .intent import fold, purchase_price_question
from .knowledge import digest
from .schemas import Citation

DISTRICTS=("Ngũ Hành Sơn","Thanh Khê","Liên Chiểu","Hải Châu","Sơn Trà","Cẩm Lệ","Hòa Vang")
KINDS={"HOUSE":"nhà phố/nhà riêng","APARTMENT":"căn hộ","LAND":"đất nền","VILLA":"biệt thự","ROOM":"phòng trọ","COMMERCIAL":"mặt bằng"}

def format_money(value):
    whole,_,tail=format(Decimal(str(value)),"f").partition(".")
    tail=tail.rstrip("0")
    return f"{int(whole):,}".replace(",",".")+(","+tail if tail else "")+" đồng"

def market_query(question,previous=None,kind=None,*,price_statistics=True):
    q=fold(question);query=dict(previous or {})
    found=[d for d in DISTRICTS if re.search(r"(?<!\w)"+re.escape(fold(d))+r"(?!\w)",q)]
    if len(found)>1:return None,"Bạn muốn xem thống kê riêng cho khu vực nào trước?"
    if found:query["district"]=found[0]
    if "toan da nang" in q or "toan thanh pho" in q:query.pop("district",None)
    if re.search(r"\b(?:phuong|xa|duong|kiet|hem)\s+",q):return None,"API thống kê hiện hỗ trợ cấp quận/khu vực, chưa có thống kê riêng theo phường hoặc tuyến đường. Bạn muốn chọn quận nào?"
    if kind and kind!="ALL":query["propertyType"]=kind
    elif kind=="ALL":query.pop("propertyType",None)
    if not price_statistics:return query,None
    query.setdefault("transactionType","SALE")
    if query["transactionType"]=="SALE":query.setdefault("priceUnit","TOTAL")
    if purchase_price_question(q):
        query.update(transactionType="SALE", priceUnit="TOTAL")
    elif re.search(r"\b(?:thue|cho thue)\b",q) or query.get("transactionType")=="RENT" and "priceUnit" not in query:
        unit="PER_MONTH" if re.search(r"thang",q) else "PER_YEAR" if re.search(r"nam",q) else "PER_DAY" if re.search(r"ngay",q) else None
        if unit is None:
            query["transactionType"]="RENT";query.pop("priceUnit",None)
            return query,"Bạn muốn xem giá thuê theo tháng, năm hay ngày?"
        query.update(transactionType="RENT",priceUnit=unit)
    elif re.search(r"\b(?:gia mua|gia ban|rao ban)\b",q):query.update(transactionType="SALE",priceUnit="TOTAL")
    return query,None

def market_response(result,query,*,trend=False):
    if result.status in ("SOURCE_UNAVAILABLE","INVALID_EVIDENCE"):
        return {"answer":"Chưa lấy được thống kê giá từ nguồn Backend hoặc bằng chứng chưa hợp lệ. Đây là lỗi nguồn, không phải kết luận khu vực không có bất động sản.","kind":"DATA_SOURCE_ERROR","citations":[],"extra":{"toolResult":result.evidence()},"limitations":[]}
    if result.status=="INSUFFICIENT_DATA":
        return {"answer":"Công cụ thống kê thị trường chưa được cấu hình; chưa đủ dữ liệu để trả lời.","kind":"INSUFFICIENT_MARKET_DATA","citations":[],"extra":{"toolResult":result.evidence()},"limitations":[]}
    body=result.data;amounts=body["overall"];count=amounts["count"]
    where=query.get("district") or "các khu vực có tin trên SmartProp"
    kind=KINDS.get(query.get("propertyType"),"bất động sản")
    suffix={"PER_MONTH":"/tháng","PER_YEAR":"/năm","PER_DAY":"/ngày","TOTAL":""}[body["priceUnit"]]
    limitations=["Thống kê giá chào của tin PUBLISHED còn hiệu lực trên SmartProp; không phải giá giao dịch hay toàn thị trường.","Không có dữ liệu lịch sử để tính xu hướng hoặc dự báo tăng giá."]
    if count<10:limitations.append("Mẫu dưới 10 tin; chưa đủ để coi là đại diện cho thị trường khu vực.")
    if trend:
        answer="Chưa có chuỗi dữ liệu lịch sử phù hợp để kết luận giá tăng/giảm hoặc xu hướng trong kỳ bạn hỏi. API hiện chỉ cung cấp ảnh chụp giá chào hiện tại; tôi không suy diễn xu hướng từ các tin này."
        response_kind="INSUFFICIENT_TREND_DATA"
    elif not count:
        answer=f"Chưa có tin {kind} đủ điều kiện thống kê giá chào tại {where} với bộ lọc này. Đây là thiếu mẫu trong dữ liệu SmartProp, không có nghĩa khu vực không có bất động sản."
        response_kind="INSUFFICIENT_MARKET_DATA"
    else:
        answer=(f"Giá chào {kind} tại {where}, thống kê trên {count} tin công khai còn hiệu lực: "
                +"trung bình "+format_money(amounts["averageAskingPrice"])+suffix
                +"; thấp nhất "+format_money(amounts["minimumAskingPrice"])+suffix
                +"; cao nhất "+format_money(amounts["maximumAskingPrice"])+suffix+".")
        if amounts.get("weightedAskingPricePerSqm") is not None:
            answer+=" Tổng giá chào chia tổng diện tích: "+format_money(amounts["weightedAskingPricePerSqm"])+"/m²"+suffix+"."
        answer+=" Thời điểm thống kê: "+body["asOf"]+". Đây là giá chào trên SmartProp, không phải giá giao dịch."
        if count<10:answer+=" Mẫu ít, chưa đại diện cho thị trường khu vực."
        response_kind="MARKET_PRICE_EVIDENCE"
    source_id="market-summary:"+digest(query)[:16]
    url="/api/v1/properties/market-summary"+("?"+urlencode(query) if query else "")
    citation=Citation(sourceId=source_id,url=url,version=body["asOf"],contentHash=digest(body),scope="PUBLIC",kind="MARKET_SUMMARY",title="Thống kê giá chào công khai SmartProp")
    return {"answer":answer,"kind":response_kind,"citations":[citation],"limitations":limitations,
            "extra":{"toolResult":result.evidence(),"marketSummary":{"sourceId":source_id,"query":query,"asOf":body["asOf"],"source":body["source"],"historyAvailable":False,"amounts":amounts}}}
