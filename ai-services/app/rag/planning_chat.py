"""Internal opt-in structured planning answers; no provider calls or generation."""
import re
from .planning_data import PlanningLookup, fold, digest
from .schemas import Citation

LABELS={
 "AUCTION_2026_CATALOG_NOT_AUCTION_OPENING":"Danh mục đấu giá 2026; chưa xác nhận đang mở",
 "PUBLIC_CONSULTATION_NOT_AMENDMENT_APPROVAL":"Hồ sơ lấy ý kiến; chưa xác nhận phê duyệt điều chỉnh",
 "PUBLIC_CONSULTATION_DOCUMENT_READ":"Văn bản lấy ý kiến; không phải quyết định phê duyệt",
 "PLANNING_APPROVAL_DOCUMENT_READ":"Có văn bản phê duyệt quy hoạch đã đọc",
 "LAND_ALLOCATION_DOCUMENT_READ":"Có quyết định giao đất đã đọc",
 "STARTING_PRICE_APPROVAL_REPORTED_NOT_AUCTION_RESULT":"Công bố phê duyệt giá khởi điểm; không phải kết quả đấu giá",
 "PREPARATION_REPORTED_START_DATE_PROJECTED":"Thông tin chuẩn bị và kế hoạch dự kiến; chưa xác nhận khởi công",
 "HISTORICAL_APPLICATION_WINDOW_PUBLISHED":"Đợt tiếp nhận hồ sơ đã công bố trong quá khứ",
 "LISTED_AS_PROJECT_AREA_IN_PROGRESS_AT_PUBLICATION":"Có trong danh mục tại thời điểm công bố",
 "INVESTMENT_POLICY_APPLICATION_INTAKE_NOTICE":"Thông báo tiếp nhận hồ sơ đề nghị chủ trương đầu tư",
 "PLANNING_AMENDMENT_PUBLIC_CONSULTATION":"Lấy ý kiến điều chỉnh quy hoạch",
 "PLANNING_NOTICE_ATTACHMENT_UNVERIFIED":"Thông báo quy hoạch, tệp đính kèm chưa xác minh"}

def classify_planning(question,previous=None):
    q=fold(question);previous=previous or {}
    # Explicit housing/POI requests stay with existing tools, regardless of previous lookup.
    if re.search(r"tim (?:nha|can ho|bat dong san)|ngan sach|benh vien|sieu thi|cong vien|truong hoc|can thu|can do",q):return None
    lot=re.search(r"\b([ab]\d{1,2}[-.]\d{1,2}(?:-\d{1,2})?)\b",q)
    doc=re.search(r'\b(?:qd|quyet dinh|thong bao|tb)\s*(?:so\s*)?(\d{1,5})\b',q)
    phase=re.search(r"giai doan\s+(1a|1b|[0-9]+)\b",q)
    follow=bool(previous and (lot or re.search(r"lo do|du an do|giai doan|con hieu luc|phe duyet chua",q) or (previous.get('operation')=='AUCTION_CATALOG' and re.fullmatch(r'(?:nam )?20[0-9]{2}[?.! ]*',q))))
    explicit=bool(re.search(r"hoa xuan",q))
    follow=follow and not explicit
    if not explicit and not follow:return None
    if (lot or 'ma lo' in q) or follow and previous.get('operation')=='LOT_LOOKUP':op='LOT_LOOKUP'
    elif 'dau gia' in q or follow and previous.get('operation')=='AUCTION_CATALOG':op='AUCTION_CATALOG'
    elif doc or re.search(r"quy hoach|phe duyet|lay y kien|phap ly|giao dat|hieu luc",q):op='PLANNING_STATUS'
    elif 'du an' in q:op='PROJECT_LIST'
    else:return None
    follow=follow and previous.get('operation')==op
    year=re.search(r"\b(20[0-9]{2})\b",q)
    project=None
    if re.search(r"sinh thai|ven song",q):project='sinh thái'
    elif 'aeon' in q:project='AEON'
    return {'operation':op,'document_number':doc[1] if doc else previous.get('document_number') if follow else None,'project':project or (previous.get('project') if follow else None),'phase':phase[1].upper() if phase else previous.get('phase') if follow else None,'lot':lot[1].upper() if lot else previous.get('lot') if follow else None,'year':int(year[1]) if year else previous.get('year') if follow else None}

class PlanningAdvisor:
    def __init__(self,path=None,*,enabled=False):self.lookup=PlanningLookup(path,enabled=enabled)
    def reply(self,question,context):
        if not self.lookup.enabled:return None
        query=classify_planning(question,context.needs.get('lastLookup'))
        if query is None:return None
        try:result=self.lookup.query(query['operation'],**{k:v for k,v in query.items() if k!='operation'})
        except (ValueError,OSError,KeyError,TypeError):result={'status':'SOURCE_UNAVAILABLE','items':[]}
        status=result['status'];rows=result['items'];citations={};details=[];items=[]
        if query['operation']=='AUCTION_CATALOG' and query['year'] is None:
            status='NEEDS_CLARIFICATION';rows=[]
        if status=='DISABLED':answer='Tra cứu hồ sơ Hòa Xuân chưa được bật. Chưa sử dụng dữ liệu nghiên cứu chưa duyệt để trả lời.'
        elif status=='SOURCE_UNAVAILABLE':answer='Nguồn hồ sơ đã duyệt chưa sẵn sàng hoặc quá hạn rà soát. Chưa thể trả lời bằng dữ liệu này.'
        elif status=='OUTSIDE_COVERAGE':answer='Bộ danh mục hiện chỉ bao phủ Hòa Xuân năm 2026; chưa có dữ liệu đã duyệt cho năm bạn hỏi.'
        elif status=='NEEDS_CLARIFICATION' and query['operation']=='AUCTION_CATALOG':answer='Bạn muốn tra cứu danh mục đấu giá năm nào? Bộ dữ liệu hiện chỉ có phạm vi năm 2026.'
        elif status=='NEEDS_CLARIFICATION':answer='Có nhiều lô trùng mã hoặc chưa đủ phạm vi. Bạn cho biết tên dự án và giai đoạn để đối chiếu đúng lô.'
        elif status=='NO_MATCHES':answer='Không tìm thấy hồ sơ phù hợp trong phần dữ liệu đã duyệt; điều này không có nghĩa khu vực không có dự án hoặc khu đất.'
        else:answer='Các hồ sơ trong phạm vi dữ liệu đã duyệt tại Hòa Xuân:'
        for r in rows:
            def v(k):return r['facts'].get(k,{}).get('value')
            label=LABELS.get(v('legal_event_status'),'Chưa xác minh trạng thái')
            text=v('name')+(' · '+v('lot_code') if v('lot_code') else '')+(' · Giai đoạn '+v('phase') if v('phase') else '')+' — '+label
            if v('area_sqm') is not None:text+='; diện tích theo nguồn: '+str(v('area_sqm'))+' m²'
            text+='; chưa xác nhận hiệu lực hiện hành.'
            refs=[]
            for source in r['sources']:
                sid='planning:'+digest({'url':source['url'],'sha':source['sha256']})[:24]
                refs.append(sid)
                if sid not in citations:
                    citations[sid]=Citation(sourceId=sid,url=source['url'],version=source['sha256'][:16],contentHash=source['sha256'],scope='PUBLIC',kind='PLANNING_SOURCE',title=source['title'])
                    details.append({'sourceId':sid,'url':source['url'],'title':source['title'],'documentDate':source['document_date'],'publicationDate':source['publication_date'],'checkedAt':source['checked_at'],'verification':'SOURCE_CHECKED','legalStatus':label})
            items.append({'id':r['id'],'name':v('name'),'lotCode':v('lot_code'),'phase':v('phase'),'legalStatus':label,'sourceIds':refs})
            answer+='\n• '+text
        if status in {'OK','NEEDS_CLARIFICATION'}:
            context.needs['lastLookup']={**query,'recordIds':[r['id'] for r in rows],'snapshotVersion':result.get('snapshot_hash')}
        return {'answer':answer,'citations':list(citations.values()),'properties':[],'responseKind':'PLANNING_LOOKUP','limitations':['Thông tin sự kiện theo văn bản, không xác nhận quyền sở hữu, khả năng giao dịch hoặc hiệu lực pháp lý hiện hành.'],'extra':{'planningLookup':{'version':'V1','status':status,'operation':query['operation'],'sources':details,'items':items,'total':result.get('total',0),'truncated':result.get('truncated',False)}}}
