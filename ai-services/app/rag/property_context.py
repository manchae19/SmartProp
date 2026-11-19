"""Property-scoped answers use only the existing public detail endpoint."""
from datetime import datetime, timezone
from decimal import Decimal
import re
import unicodedata
from .knowledge import digest
from .schemas import Citation
from .money import format_vnd
from .tools import UpstreamError
from .config import GroundingError

def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFD",str(value).lower().replace("đ","d")) if not unicodedata.combining(c))


def monthly_income_claim(p):
    """Only explicit income/rent claims, never a bare monthly price or an invented estimate."""
    claims=[]
    for field in ("title","description"):
        original=str(p.get(field) or "")[:20000]
        text=normalized(original)
        for match in re.finditer(r"(?:dong tien|doanh thu|thu nhap|cho thue|tien thue)[^.!?;\n]{0,65}?([0-9]{1,3}(?:[.,][0-9]{1,2})?)\s*(?:trieu|tr)\s*(?:dong|vnd)?\s*(?:/\s*(?:1\s*)?thang|moi thang|mot thang)",text):
            prefix=text[max(0,match.start()-24):match.start()]
            fragment=match.group(0)
            if re.search(r"khong|chua|khong phai",prefix) or re.search(r"khong|chua|du kien|uoc tinh|co the|toi da|len den|khoang|tu |den |[–—-]|loi nhuan|rong",fragment):
                return None,"UNCERTAIN"
            value=Decimal(match.group(1).replace(",","."))*1000000
            if value>0:claims.append((value,field,fragment))
    if not claims:return None,"MISSING"
    if len({c[0] for c in claims})!=1:return None,"CONFLICT"
    return claims[0],"CLAIMED"


def listing_analysis(p, question, price, area):
    price,area=Decimal(str(price)),Decimal(str(area))
    q=normalized(question)
    investment=any(word in q for word in ("dau tu","loi suat","dong tien","sinh loi","hoan von","cho thue","phan tich","danh gia","nen mua"))
    if not investment:return None
    sale=p.get("priceUnit")=="TOTAL" and p.get("transactionType")=="SALE"
    lines=["Phân tích sơ bộ từ nội dung tin đăng — chưa xác minh độc lập.",
           "Giá chào: "+format_vnd(price)+("" if p.get("priceUnit")=="TOTAL" else {"PER_MONTH":"/tháng","PER_YEAR":"/năm","PER_DAY":"/ngày"}.get(p.get("priceUnit"),""))+"; diện tích kê khai: "+str(area)+" m²."]
    metrics={"basis":"PUBLIC_LISTING_CLAIMS","askingPriceVnd":str(price),"areaSqm":str(area),"independentlyVerified":False}
    if sale:
        sqm=(price/area).quantize(Decimal("1"))
        lines.append("Giá chào trên diện tích kê khai: khoảng "+format_vnd(sqm)+"/m². Chưa rõ loại diện tích và chưa có giá đối chiếu để nhận xét đắt/rẻ.")
        metrics["askingPricePerDeclaredSqmVnd"]=str(sqm)
    rooms=p.get("bedrooms")
    if isinstance(rooms,int) and not isinstance(rooms,bool) and rooms>0:
        lines.append("Tin khai báo "+str(rooms)+" phòng ngủ; số phòng không chứng minh số phòng cho thuê, công suất hoặc doanh thu.")
    claim,status=monthly_income_claim(p)
    metrics["rentalClaimStatus"]=status
    if sale and claim:
        monthly,field,excerpt=claim
        annual=monthly*12
        percent=(annual/price*100).quantize(Decimal("0.01"))
        lines.append("Người đăng nêu: “"+excerpt+"” ("+("tiêu đề" if field=="title" else "mô tả")+"). Nếu con số này là doanh thu thuê hằng tháng và duy trì đủ 12 tháng, doanh thu giả định là "+format_vnd(annual)+"/năm, tương đương khoảng "+str(percent).replace(".",",")+"% giá chào/năm. Đây là tỷ lệ doanh thu/giá mua giả định, chưa phải lợi suất ròng; chưa trừ thời gian trống, thuế, vận hành, sửa chữa và lãi vay. Cụm “dòng tiền” chưa cho biết là doanh thu hay thu nhập ròng.")
        metrics.update(monthlyRentalClaimVnd=str(monthly),annualRevenueScenarioVnd=str(annual),grossRevenueToAskingPricePercent=str(percent),claimField=field,claimExcerpt=excerpt)
    elif status=="CONFLICT":
        lines.append("Các mức thu nhập thuê trong tin không thống nhất; chưa tính tỷ lệ doanh thu. Cần người đăng giải thích và cung cấp chứng từ.")
    elif sale:
        lines.append("Chưa có một mức doanh thu thuê hằng tháng rõ ràng, nhất quán để tính tỷ lệ doanh thu. Không tự ước lượng tiền thuê.")
    else:
        lines.append("Đây không phải tin bán có tổng giá mua; không dùng giá thuê làm giá mua để tính lợi suất đầu tư.")
    lines.extend(["Điểm cần làm rõ: loại diện tích, hợp đồng thuê và chứng từ thu tiền (nếu khai thác cho thuê), tỷ lệ trống, chi phí, tình trạng công trình, hồ sơ pháp lý và quy hoạch.",
                  "Kết luận theo dữ liệu hiện có: có thể dùng các thông số trên để sàng lọc và đặt câu hỏi cho người đăng; chưa đủ cơ sở kết luận nên đầu tư, định giá thị trường hay cam kết sinh lời."])
    return "\n\n".join(lines),metrics


def focused_reply(backend, property_id, question):
    try:
        p=backend.public_property(property_id)
    except UpstreamError as error:
        if error.status != 404: raise
        return dict(answer="Tin này không còn được công khai hoặc đã hết hạn. Bạn hãy chọn tin khác.", properties=[], citations=[], responseKind="PROPERTY_UNAVAILABLE", extra={"clearPropertyContext":True})
    expires=p.get("expiresAt")
    if expires and datetime.fromisoformat(expires.replace("Z","+00:00")) <= datetime.now(timezone.utc):
        return dict(answer="Tin đã hết hạn, không thể dùng làm căn cứ tư vấn hiện tại.", properties=[],citations=[],responseKind="PROPERTY_UNAVAILABLE",extra={"clearPropertyContext":True})
    price=Decimal(str(p.get("price")));area=Decimal(str(p.get("areaSqm")))
    if not price.is_finite() or price<=0 or not area.is_finite() or area<=0 or p.get("currency")!="VND": raise GroundingError("INVALID_PROPERTY_FACTS")
    title=p.get("title")
    if not isinstance(title,str) or not title.strip(): raise GroundingError("MISSING_PROPERTY_TITLE")
    unit={"TOTAL":"", "PER_MONTH":"/tháng", "PER_YEAR":"/năm", "PER_DAY":"/ngày"}.get(p.get("priceUnit"))
    if unit is None: raise GroundingError("INVALID_PROPERTY_PRICE_UNIT")
    answer=title+". Giá chào: "+format_vnd(price)+unit+". Diện tích do người đăng cung cấp: "+str(area)+" m². Địa chỉ: "+str(p.get("address") or "chưa được cung cấp")+". "
    answer+="Tin đang công khai; trạng thái này không xác minh tài sản còn bán/cho thuê. Chưa có bằng chứng pháp lý hoặc xác minh thực địa trong dữ liệu công khai. Ghim nếu có là do người đăng cung cấp, chưa được xác minh độc lập."
    analysis=listing_analysis(p,question,price,area)
    if analysis:answer=analysis[0]
    stamp=datetime.now(timezone.utc).isoformat()
    citation=Citation(sourceId="property:"+property_id,url="/api/v1/properties/"+property_id,version=stamp,contentHash=digest(p),scope="PUBLIC",kind="PROPERTY_DETAIL",title=title)
    return dict(answer=answer,properties=[],citations=[citation],responseKind="FOCUSED_PROPERTY_EVIDENCE",extra={"focusedProperty":{"id":property_id,"title":title},"listingAnalysis":analysis[1] if analysis else None,"quickReplies":["Phân tích đầu tư căn này","Pháp lý căn này đã xác minh chưa?","Tìm nhà khác"]},limitations=["Thông tin do người đăng cung cấp; cần đối chiếu hồ sơ và vị trí thực tế."])
