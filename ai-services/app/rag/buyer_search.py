"""Read-only buyer intake and deterministic cross-source paging. No model-generated facts."""
import re
import base64,zlib
from decimal import Decimal
from urllib.parse import urlencode
from .land_chat import fold
from .tools import UpstreamError, _public_text
from ..land.budget_rules import budget_band
from ..land.query_rules import area_filter,requested_location

TYPES={'dat o':'RESIDENTIAL','dat nong nghiep':'AGRICULTURE','nha':'HOUSE','can ho':'APARTMENT','tat ca':'ALL','dat':'LAND'}
LABELS={'RESIDENTIAL':'Đất ở','AGRICULTURE':'Đất nông nghiệp','HOUSE':'Nhà','APARTMENT':'Căn hộ','ALL':'Tất cả','LAND':'Đất'}
DISTRICTS=['Hải Châu','Sơn Trà','Thanh Khê','Cẩm Lệ','Ngũ Hành Sơn','Liên Chiểu','Hòa Vang']
MORE=re.compile(r'^(?:xem ket qua khac|xem them|tiep|con nua|con khong)[ ?.]*$')

def _price(row):
 try:
  value=Decimal(str(row));return int(value) if value.is_finite() and value>0 and value==int(value) else None
 except Exception:return None

def _public(backend, filters, ceiling):
 """Read every public page within a fixed bound; never label a truncated scan complete."""
 params={'transactionType':'SALE','city':'Đà Nẵng','maxPrice':ceiling,'sort':'priceAsc','size':50}
 if filters['type'] in ('HOUSE','APARTMENT'):params['propertyType']=filters['type']
 elif filters['type'] in ('LAND','RESIDENTIAL','AGRICULTURE'):params['propertyType']='LAND'
 if filters.get('minPrice'):params['minPrice']=filters['minPrice']
 if filters.get('district'):params['district']=filters['district']
 if filters.get('location')=='Hòa Xuân':params['ward']='Hòa Xuân'
 if filters.get('area'):
  params.update({k:v for k,v in [('minArea',filters['area'].get('minArea')),('maxArea',filters['area'].get('maxArea'))] if v is not None})
 result=[]
 for page in range(20):
  body=backend._call('GET','/api/v1/properties?'+urlencode({**params,'page':page}))
  if not isinstance(body,dict) or not isinstance(body.get('items'),list):raise UpstreamError()
  for p in body['items']:
   value=_price(p.get('price'))
   if p.get('status')!='PUBLISHED' or p.get('transactionType')!='SALE' or p.get('priceUnit')!='TOTAL' or p.get('currency')!='VND' or value is None:continue
   if not re.fullmatch(r'[a-fA-F0-9-]{36}',str(p.get('id',''))) or not p.get('title'):continue
   if params.get('propertyType') and p.get('propertyType')!=params['propertyType']:continue
   if filters['type'] in ('RESIDENTIAL','AGRICULTURE') and p.get('landUseType')!=filters['type']:continue
   if filters.get('district') and p.get('district')!=filters['district']:continue
   if filters.get('location')=='Hòa Xuân' and fold(p.get('ward') or '')!='hoa xuan':continue
   area=p.get('areaSqm');bounds=filters.get('area') or {}
   if not _price(area) and not (isinstance(area,(float,Decimal)) and area>0):continue
   if not bounds.get('minArea',0)<=float(area)<=bounds.get('maxArea',float('inf')):continue
   result.append({'key':'PROPERTY:'+p['id'],'source':'SMARTPROP','price':value,'id':p['id'],'title':_public_text(p['title'],300),'area':area,'location':', '.join(x for x in [p.get('ward'),p.get('district')] if x),'priceType':'Giá chào tin đăng','property':{**{k:p[k] for k in ('title','district','ward','propertyType','areaSqm','bedrooms','bathrooms','contentVersion') if k in p},'title':_public_text(p['title'],300),'id':'property:'+p['id'],'priceVnd':value,'score':0,'explanations':[],'warnings':[],'source':{'kind':'PROPERTY','recordKey':p['id'],'name':'SmartProp'},'verificationStatus':'PLATFORM_PUBLISHED','qualityStatus':'PLATFORM_PUBLISHED'}})
  total_pages=body.get('totalPages')
  if isinstance(total_pages,int) and page+1>=total_pages:return result
  if not body['items']:return result
 raise UpstreamError(503)

NON_LAND_HOUSE_RE=re.compile(r'\b(nha|can ho|chung cu|biet thu|nha pho|phong tro|mat bang)\b')
LAND_ASSET_RE=re.compile(r'\b(dat|lo dat|o dat|thua)\b')

# Over-budget consent is decided per clause, and every failure mode returns a non-GRANT
# verdict: negative/withdrawal markers are evaluated BEFORE any affirmative verb, and
# questions, quotes, hypotheticals, conditionals, third-party statements, past statements
# and hedges can never produce GRANT. Anything still unclear stays on the hard budget.
_CLAUSE_SPLIT = re.compile(r'[.!?;:,()\[\]"\u201c\u201d]|\b(?:nhung|ma|tuy nhien|song|vi vay|the nhung)\b')
_OVER_MENTION = re.compile(r'\bvuot\b')
_AFFIRMATIVE = ('dong y','chap nhan','cho phep','cho xem','hien thi','xem','lay','them','mo rong','cho toi')
_NEGATION = ('khong','ko','chua','chang','cha','dung','thoi','ngung','huy','bo','cam','chan','tu choi','rut lai','thu hoi','khong he','khong bao gio','chua bao gio','chua tung')
_PAST = ('da tung','tung','truoc day','luc truoc','hoi truoc','ngay xua','ngay truoc')
_HYPOTHETICAL = ('neu','gia su','gia dinh','lieu','co nen','khong chac','chua chac','phan van','dang nghi','hoac','tuy','xem xet','co the','vi du','theo gia dinh','trong truong hop','neu nhu')
_THIRD_PARTY = ('nguoi khac','nguoi ta','moi nguoi','ban ay','ong ay','ba ay','chu nha','chu dau tu','ho ')

def _mentions(clause: str, tokens) -> bool:
 """Whole-word/phrase match so a token can never match inside another word."""
 return any(re.search(r'(?<!\w)' + re.escape(token.strip()) + r'(?!\w)', clause) for token in tokens)

def parse_over_budget_consent(question: str) -> str:
 """Classify over-budget consent into `'GRANT'`, `'DENY'`, `'AMBIGUOUS'`, or `'NONE'`.

 GRANT requires an explicit affirmative clause. Denial, withdrawal, negation and
 contradiction are evaluated first and always win; questions, quotes, hypothetical or
 conditional wording, third-party statements, past-tense recollection and hedges are
 never treated as consent.
 """
 raw = (question or '').strip()
 if not raw:
  return 'NONE'
 text = fold(raw)
 if not text:
  return 'NONE'
 # An explicit "not any more / now no" withdrawal invalidates prior consent regardless of wording.
 if re.search(r'\b(?:bay gio|gio|hien tai|hien gio|hien|thoi|sau nay)\b[^.]{0,40}\b(?:khong|ko)\b', text):
  return 'DENY'
 # A strict-budget affirmation ("tuyệt đối dưới ngân sách") is a refusal to exceed it.
 if re.search(r'\b(?:tuyet doi|nghiem ngat)\b[^.]{0,40}\b(?:duoi|trong|khong qua|toi da)\b[^.]{0,20}\bngan sach\b', text):
  return 'DENY'
 clauses = [clause.strip() for clause in _CLAUSE_SPLIT.split(text) if clause and clause.strip()]
 grant = deny = ambiguous = over_seen = False
 for clause in clauses:
  has_over = bool(_OVER_MENTION.search(clause))
  over_seen = over_seen or has_over
  if not has_over:
   continue
  # A trailing "không" is the Vietnamese yes/no question particle, not a negation of the clause.
  clause_scan = re.sub(r'\bkhong\s*$', '', clause)
  negated = any(re.search(r'\b' + re.escape(token) + r'\b', clause_scan) for token in _NEGATION)
  past = _mentions(clause, _PAST)
  hypothetical = _mentions(clause, _HYPOTHETICAL)
  third_party = _mentions(clause, _THIRD_PARTY)
  affirmative = _mentions(clause, _AFFIRMATIVE)
  first_person = bool(re.search(r'(?<!\w)(?:toi|minh|em|anh|chi)(?!\w)', clause))
  if negated:
   deny = True
  elif past or third_party or hypothetical:
   ambiguous = True
  elif affirmative and (first_person or clause.startswith(('dong y','chap nhan','cho phep','cho xem','hien thi','lay','them','mo rong'))):
   grant = True
  elif affirmative:
   ambiguous = True
  else:
   ambiguous = True
 is_question = '?' in raw or bool(re.search(r'\bkhong\s*$', text))
 if deny and grant:
  # Contradictory instruction: refuse (AMBIGUOUS), never grant.
  return 'AMBIGUOUS'
 if deny:
  return 'DENY'
 if ambiguous:
  return 'AMBIGUOUS'
 if grant:
  return 'AMBIGUOUS' if is_question else 'GRANT'
 return 'NONE' if over_seen else 'NONE'

def _consent_scope(state: dict) -> dict:
 return {k: state.get(k) for k in ('type', 'location', 'district', 'ward', 'maxPrice', 'minPrice', 'mode', 'area')}

def _revoke_consent(state: dict) -> None:
 state['allowOverBudget'] = False
 state['consentScope'] = None
 state['pendingOverBudgetScope'] = None

def respond(bot,request,context,turn,*,allow_demo=False):
 n=fold(request.question).strip(' ?!.');existing=context.needs.get('buyerSearch');more=bool(MORE.fullmatch(n))
 if turn['intent']=='PROPERTY_FOLLOWUP':
  ordinal=turn.get('ordinal')
  visible=(existing or {}).get('visible',[])
  if isinstance(ordinal,int) and 1<=ordinal<=len(visible):
   selected=visible[ordinal-1]
   land_state=context.needs.get('land',{})
   if selected['source']=='SMARTPROP':
    turn['ordinal']=sum(x['source']=='SMARTPROP' for x in visible[:ordinal])
    land_state['lastDomain']=None
   else:land_state['lastDomain']='plot'
  return None
 # Questions about evidence or an already-selected asset stay in their existing tools.
 if turn['intent'] in ('AREA_AMENITIES','MARKET_ANALYSIS','MARKET_PRICE','MARKET_TREND','PLANNING_QA','LEGAL_QA') or re.search(r'ngap|\blut\b|giay to|phap ly|thuoc du an|lo thu|can thu|lo dau|dien tich bao nhieu|so do|so hong|the chap',n):
  if isinstance(existing,dict):existing.update(pagingActive=False,pending=None)
  return None
 # Switching from a land/buyer search to a non-land house/apartment search exits to SmartProp Recommendation.
 if NON_LAND_HOUSE_RE.search(n) and not LAND_ASSET_RE.search(n) and (existing or {}).get('pending')!='type':
  if isinstance(existing,dict):
   existing.update(active=False,pending=None,pagingActive=False,visible=[],order=None,offset=0,seen=[])
   _revoke_consent(existing)
  land_state=context.needs.get('land')
  if isinstance(land_state,dict):land_state.update(lastDomain=None,selected=None,seen=[],visibleIds=[],projectRows=[])
  if context.needs.get('listOwner') in ('BUYER','LAND'):context.needs['listOwner']='PROPERTY'
  return None
 consent_decision=parse_over_budget_consent(request.question)
 try:band=budget_band(request.question)
 except ValueError as error:
  context.needs.setdefault('buyerSearch',dict(existing or {}))
  return {'answer':str(error),'properties':[],'citations':[],'responseKind':'BUYER_SEARCH','extra':{'buyerSearch':{'rows':[],'summary':[]}}}
 chosen=next((value for text,value in sorted(TYPES.items(),key=lambda x:-len(x[0])) if re.search(r'\b'+text+r'\b',n)),None)
 search=bool(re.search(r'\b(tim|mua|toi co|ngan sach|xem dat|bat dong san|tin dang)\b',n))
 pending_stage=(existing or {}).get('pending')
 active_session=bool((existing or {}).get('active'))
 if request.propertyId or (context.needs.get('focusedPropertyId') and not search):return None
 if more and existing and context.needs.get('land',{}).get('lastDomain') in ('flood','flood_empty'):return None
 if more and existing and not existing.get('pagingActive'):
  return {'answer':'Danh sách tìm kiếm trước đã tạm dừng. Hãy nêu lại yêu cầu tìm tài sản để bắt đầu; tôi không lấy lại trang cũ sau câu hỏi tiện ích hoặc pháp lý.','properties':[],'citations':[],'responseKind':'BUYER_SEARCH','extra':{'buyerSearch':{'rows':[],'summary':[]}}}
 if more and not existing:return None
 if existing and not active_session and not pending_stage and not search:return None
 if not (more or search or (pending_stage and (chosen or band or 'hoa xuan' in n or any(fold(x) in n for x in DISTRICTS) or 'da nang' in n)) or (active_session and (band or chosen or consent_decision in ('GRANT','DENY','AMBIGUOUS')))):return None
 if re.search(r'euro|trieu phu|b2[.\-]|guland',n):
  if isinstance(existing,dict):existing['pagingActive']=False
  return None
 if re.search(r'\b(gan|di lam|noi lam|ban kinh|thoi gian)\b',n):return None
 state=dict(existing or {});state.setdefault('type',None)
 if not state.get('location'):
  if context.district:state.update(location=context.district,district=context.district)
  elif context.ward and fold(context.ward)=='hoa xuan':state['location']='Hòa Xuân'
 is_exact=bool(re.search(r'(?iu)\bđúng\b',request.question) or (re.search(r'\bdung\b',n) and not re.search(r'\bdung\s+vuot\b',n)))
 if band:
  state['maxPrice']=band.get('maxPrice');state['minPrice']=band.get('minPrice')
  state['mode']='EXACT' if is_exact else 'APPROXIMATE' if re.search(r'\b(khoang|tam|quanh|xap xi)\b',n) else 'MAXIMUM'
  if state['maxPrice'] is not None:context.budget_vnd=str(state['maxPrice'])
 if chosen:state['type']=chosen
 elif re.search(r'\b(lo dat|tim dat|mua dat|dat duoi|dat khoang)\b',n):state['type']='LAND'
 elif not state.get('type'):
  if re.search(r'\b(lo dat|tim dat|mua dat|dat duoi|dat khoang)\b',n):state['type']='LAND'
  elif context.property_type in ('HOUSE','APARTMENT'):state['type']=context.property_type
 if 'hoa xuan' in n:state.update(location='Hòa Xuân',district=None)
 else:
  district=next((x for x in DISTRICTS if fold(x) in n),None)
  if district:state.update(location=district,district=district)
  elif 'da nang' in n:state.update(location='Đà Nẵng',district=None)
 if request.district and not state.get('location'):state.update(location=request.district,district=request.district)
 if request.budgetVnd is not None:
  req_ceiling=int(request.budgetVnd)
  state['maxPrice']=min(state['maxPrice'],req_ceiling) if state.get('maxPrice') else req_ceiling
 area=area_filter(request.question)
 if area:state['area']=area
 current_scope=_consent_scope(state)
 pending_scope=state.get('pendingOverBudgetScope')
 if consent_decision=='GRANT' and pending_scope is not None and pending_scope!=current_scope:
  # A confirmation surfaced for earlier criteria cannot grant consent for new criteria.
  consent_decision='AMBIGUOUS'
 if consent_decision=='GRANT':
  state['allowOverBudget']=True
  state['consentScope']=current_scope
  state['pendingOverBudgetScope']=None
 elif consent_decision in ('DENY','AMBIGUOUS'):
  _revoke_consent(state)
 elif not state.get('allowOverBudget') or state.get('consentScope')!=current_scope:
  # Any change to search criteria invalidates prior over-budget consent (fail-closed).
  _revoke_consent(state)
 previous={k:v for k,v in (existing or {}).items() if k in ('type','location','district','maxPrice','minPrice','mode','area','allowOverBudget')}
 current={k:v for k,v in state.items() if k in ('type','location','district','maxPrice','minPrice','mode','area','allowOverBudget')}
 if previous!=current or not more:state.update(seen=[],offset=0,order=None)
 def packet(answer,rows=None,**extra):
  context.needs['buyerSearch']=state
  summary=[LABELS.get(state.get('type'),'Chưa chọn loại tài sản'),state.get('location') or 'Chưa chọn khu vực']
  if state.get('maxPrice') is not None:summary.append(('Ngân sách tối đa: ' if state.get('mode')=='MAXIMUM' else 'Giá đang lọc đến: ')+f"{state['maxPrice']:,}".replace(',','.')+' đồng')
  return {'answer':answer,'properties':[],'citations':[],'responseKind':'BUYER_SEARCH','extra':{'quickReplies':extra.pop('quickReplies',[]),'buyerSearch':{'rows':rows or [],'summary':summary,**extra}}}
 if not state.get('type'):
  state.update(active=True,pending='type',pagingActive=False)
  return packet('Bạn muốn tìm loại tài sản nào?',quickReplies=['Đất ở','Đất nông nghiệp','Nhà','Căn hộ','Tất cả'])
 outside=requested_location(request.question)
 if outside and outside not in [fold(x) for x in DISTRICTS] and outside not in ('hoa xuan','cam le'):
  state.update(active=True,pending='location',pagingActive=False)
  return packet('Chưa có nguồn tìm kiếm được hỗ trợ cho địa bàn bạn vừa nêu. Tôi không thay thế bằng kết quả Đà Nẵng.')
 if not state.get('location'):
  state.update(active=True,pending='location',pagingActive=False)
  return packet('Bạn muốn tìm ở khu vực nào?',quickReplies=['Hòa Xuân','Đà Nẵng',*DISTRICTS[:6]])
 if not state.get('maxPrice'):
  state.update(active=True,pending='budget',pagingActive=False)
  return packet('Ngân sách tối đa của bạn là bao nhiêu?')
 state.update(active=True,pending=None,pagingActive=True)
 ceiling=state['maxPrice']
 reference_ceiling=ceiling*115//100 if (state.get('mode','MAXIMUM')=='MAXIMUM' and state.get('allowOverBudget') is True and state.get('consentScope')==_consent_scope(state)) else ceiling
 pool=[];warnings=[]
 if allow_demo and getattr(bot.land_advisor,"enabled",False) and state['type'] in ('LAND','RESIDENTIAL','AGRICULTURE','ALL') and state['location'] in ('Hòa Xuân','Đà Nẵng','Cẩm Lệ'):
  e=bot.land_advisor.engine;group='agriculture' if state['type']=='AGRICULTURE' else 'housing'
  candidates=[dict(e.imported.enrich(e.pricedbyid.get(r['id'],r)),purposeGroup=e.purpose(r)) for r in e.original if r['id'] in e.activeids]
  candidates+=list(e.imported.SOURCE_ROWS.values())+[e.unified_summary(r) for r in e.unified_lots.values()]+list(e.imported.EXTRAS.values())
  for r in candidates:
   value=e.imported.value(r);purpose=r.get('purposeGroup') or (e.purpose(r) if r.get('planningCode') and r.get('planningCategory') else None)
   if purpose not in ('housing','agriculture'):continue
   if state['type'] not in ('LAND','ALL') and purpose!=group:continue
   bounds=state.get('area') or {};size=r.get('computedAreaSqm')
   if size is None or not bounds.get('minArea',0)<=size<=bounds.get('maxArea',float('inf')):continue
   if value is None or not (state.get('minPrice') or 0)<=value<=reference_ceiling:continue
   raw=e.summary(r) if r['id'] in e.byid else r
   payload=bot.land_advisor._payload('',{'rows':[raw]},'LAND_SEARCH',None)['extra']['land']['rows'][0]
   pool.append({'key':'LAND:'+r['id'],'source':'LAND_DATA','price':int(value),'id':payload['landId'],'title':payload['displayName'],'area':size,'location':payload['location'],'priceType':payload['priceType'],'land':payload})
 if state['type'] in ('HOUSE','APARTMENT','LAND','RESIDENTIAL','AGRICULTURE','ALL'):
  try:pool+=_public(bot.backend,state,reference_ceiling)
  except UpstreamError:
   warnings.append('Chưa tải được tin đăng SmartProp; không coi lỗi nguồn là không có tin phù hợp.')
 # Only source identities are deduplicated; coincident geometry does not prove a duplicate parcel.
 unique={x['key']:x for x in pool if state.get('minPrice',0) is None or x['price']>=state.get('minPrice',0)}
 pool=[x for x in unique.values() if x['price']<=reference_ceiling]
 pool.sort(key=lambda x:(x['price']>ceiling,x['price'],x['key']))
 if state.get('order') is None:
  state['order']=base64.b64encode(zlib.compress('\n'.join(x['key'] for x in pool).encode(),6)).decode()
 keys=zlib.decompress(base64.b64decode(state['order'])).decode().splitlines()
 by_key={x['key']:x for x in pool};cursor=state.get('offset',0);page=[]
 while cursor<len(keys) and len(page)<5:
  row=by_key.get(keys[cursor]);cursor+=1
  if row is not None:page.append(row)
 for x in page:
  x['overBudgetVnd']=max(0,x['price']-ceiling);x['overBudgetPercent']=round(x['overBudgetVnd']*100/ceiling,2)
 # Remember which criteria produced an over-budget confirmation; a later click for other criteria must re-confirm.
 state['pendingOverBudgetScope']=_consent_scope(state) if any(x['overBudgetVnd'] for x in page) else None
 state['offset']=cursor
 remaining=any(key in by_key for key in keys[cursor:])
 state['visible']=[{'source':x['source'],'id':x['id']} for x in page]
 land_ids=[x['land']['sourceCode'] if x.get('land') else None for x in page]
 context.needs['land']={**context.needs.get('land',{}),'visibleIds':land_ids,'seen':land_ids,'selected':next((x for x in land_ids if x),None),'lastDomain':'plot' if land_ids else None,'band':{'maxPrice':ceiling}}
 context.needs['listOwner']='BUYER'
 answer=('Hiển thị '+str(len(page))+' kết quả, giá tăng dần. Kết quả trong ngân sách được hiển thị trước; giá và nguồn được ghi trên từng thẻ.' if page else 'Đã hết kết quả theo bộ lọc hiện tại.' if more else 'Không có kết quả phù hợp với bộ lọc hiện tại.')
 if any(x['overBudgetVnd'] for x in page):answer+=' Nhóm tham khảo vượt ngân sách tối đa 15%; ngân sách đã lưu không thay đổi.'
 if warnings and not page:answer='Nguồn tin đăng hiện không truy cập được; chưa thể kết luận có hay không có tin phù hợp.'
 result=packet(answer+(' '+ ' '.join(warnings) if warnings else ''),page,total=len(pool),quickReplies=(['Xem kết quả khác'] if remaining else [])+(['Tìm lại theo bộ lọc'] if warnings else []))
 properties=[x['property'] for x in page if x.get('property')]
 result['result_properties']=properties
 result['response']={'topProperties':properties,'topAreas':[]}
 from .schemas import Citation
 from .knowledge import digest
 result['citations']=[Citation(sourceId=p['id'],url='/api/v1/properties/'+p['source']['recordKey'],version=str(p.get('contentVersion') or 1),contentHash=digest(p),scope='PUBLIC',kind='PROPERTY_DETAIL',title=p['title']) for p in properties]
 return result