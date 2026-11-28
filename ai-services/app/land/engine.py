"""Hòa Xuân land demo engine: data loading, lookups and the buyer conversation router.

Ported from the standalone test bot. No HTTP server, no file writes: the SmartProp chat
service owns sessions, and the map/detail routes call the functions at the end of this file.
"""
import pathlib,json,hashlib,re,threading
from decimal import Decimal,ROUND_HALF_UP
from .paths import DATA_ROOT as ROOT
from .budget_rules import budget_band,budget_rank_target,fold
from .project_lookup import lookup as project_lookup
from .lot_pricing import resolve_price
from . import imported_data as imported
from .query_rules import area_filter,requested_location,legal_conditions,ordinal_numbers,fixed_plot_number
from .flood_evidence import evidence as flood_evidence, answer as flood_answer, is_flood_question
from .flood_lookup import lookup as flood_lookup, stats as flood_stats
from .flood_map import map_context as flood_map_context
def points(value):
 if isinstance(value,list) and value and isinstance(value[0],(int,float)):yield value
 elif isinstance(value,list):
  for item in value:yield from points(item)
def bounds(geometry):
 coords=list(points(geometry['coordinates']));return (min(p[0] for p in coords),min(p[1] for p in coords),max(p[0] for p in coords),max(p[1] for p in coords))
DATA=ROOT/'outputs/hoa-xuan-map-rebuild-20261122'
original=json.loads((DATA/'map-grounded-catalog.json').read_text(encoding='utf-8'))
displaylabels=json.loads((ROOT/'outputs/plot-display-labels.json').read_text(encoding='utf-8'))
numbertocell={v['number']:k for k,v in displaylabels.items()}
ENRICHED=ROOT/'outputs/hoa-xuan-enriched-20261122'
validated=json.loads((ENRICHED/'runtime-cells.json').read_text(encoding='utf-8'))
activeids={r['id'] for r in validated}
activeids={rid for rid in activeids if next((r['computedAreaSqm'] for r in original if r['id']==rid),0)>0}
cellinfo={r['id']:r for r in json.loads((ENRICHED/'cells.json').read_text(encoding='utf-8'))}
planinfo={r['id']:r for r in json.loads((ENRICHED/'plans.json').read_text(encoding='utf-8'))}
geometries=[bounds(r['geometry']) for r in original]
byid={r['id']:i for i,r in enumerate(original)}
maplegend=json.loads((DATA/'raw/layer-4-metadata.json').read_text(encoding='utf-8'))['drawingInfo']['renderer']['uniqueValueInfos']
colors={r['value']:r['symbol']['color'][:3] for r in maplegend}
rows=[]
for source in original:
 if source['id'] not in activeids or source['planningCategory']!='RESIDENTIAL_PLANNING' or not 60<=source['computedAreaSqm']<=500:continue
 row=dict(source);unit=10000000+int(hashlib.sha256(row['id'].encode()).hexdigest()[:8],16)%50000001
 row.update(demoUnitPriceVndPerSqm=unit,demoPriceVnd=int((Decimal(str(row['computedAreaSqm']))*unit).quantize(Decimal('1'),rounding=ROUND_HALF_UP)),priceClass='SYNTHETIC_ASSUMPTION_NOT_MARKET',geometryClass='SOURCE_PLANNING_CELL_NOT_CONFIRMED_CADASTRAL_PARCEL')
 rows.append(row)
rows.sort(key=lambda r:(r['demoPriceVnd'],r['id']))
pricedbyid={r['id']:r for r in rows}
pricedbyid={rid:imported.enrich(row) for rid,row in pricedbyid.items()}
def purpose(r):
 code=r['planningCode']
 if r['planningCategory']=='RESIDENTIAL_PLANNING':return 'housing'
 if code=='QHNN':return 'agriculture'
 if code in ['QHDL']:return 'commerce'
 if code.startswith('QHCX'):return 'green'
 if code=='QHMN':return 'water'
 return 'public'
def price_text(r):
 if r.get('roadPriceEvidence'):return r['priceDescription']
 if r.get('demoPriceVnd'):return money(r['demoPriceVnd'])+' (giá giả lập demo — không phải giá thị trường)'
 return 'chưa có giá cho ô nhà ở này' if purpose(r)=='housing' else 'không thuộc bộ giá nhà ở'
def enriched_catalog():return ({'version':'MAP-PRICE-ENRICHED-1','priceRule':'area computed EPSG:32649N × deterministic hypothetical unit price 10–60 million VND/m²; no market basis','sourceCatalog':str(ENRICHED/'runtime-cells.json'),'excluded':'non-residential, overlap flagged, code-spatial conflicts, area outside 60–500 sqm','records':rows})
unified_lots={x['id']:x for x in json.loads((ROOT/'outputs/hoa-xuan-projects-20261125/unified-lots.json').read_text(encoding='utf-8'))}
# Conversation state is owned by the caller (SmartProp chat session); see conversation().
sessions={};lock=threading.Lock()
def money(n):return str((Decimal(n)/10**9).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)).replace('.',',')+' tỷ'
def summary(r):
 if r.get('importedParcel') or r.get('unlocatedProjectLot'):return r
 r=imported.enrich(r)
 out={k:v for k,v in r.items() if k!='geometry'};meta=cellinfo[r['id']]
 out.update(displayName=displaylabels[r['id']]['label'],displayNumber=displaylabels[r['id']]['number'],purposeGroup=purpose(r),priceDescription=price_text(r))
 out.update(planningEvidence=[planinfo[i] for i in meta['sourcePlanIds']],codeSpatialConflict=meta['codeSpatialConflict'],runtimeEligible=r['id'] in activeids,recoveryStatus='UNKNOWN',compensationStatus='UNKNOWN',disputeStatus='UNKNOWN',legalStatus='UNKNOWN',effectiveDate='UNKNOWN',dataVersion='HX-ENRICHED-20261122')
 addressfile=ROOT/'outputs/hoa-xuan-road-address-20261122/ui-addresses.json'
 if addressfile.exists():
  global address_cache
  if 'address_cache' not in globals():address_cache=json.loads(addressfile.read_text(encoding='utf-8'))
  out['addressEvidence']=address_cache.get(r['id'])
 referencefile=ROOT/'outputs/chatbot-update-20261123/price-references.json'
 if not r.get('demoPriceVnd') and referencefile.exists():
  global reference_cache
  if 'reference_cache' not in globals():
   refs=json.loads(referencefile.read_text(encoding='utf-8'));reference_cache={c['id']:{'road':c['nearbyRoad'],'status':c['status'],'sourceUrl':refs['baseScheduleRows'][c['referenceRows'][0]]['sourceUrl'],'sourcePages':sorted({refs['baseScheduleRows'][i]['page'] for i in c['referenceRows']}),'applicablePrice':None} for c in refs['unpricedCellRoadCandidates']}
  if r['id'] in reference_cache:out['statePriceReference']=reference_cache[r['id']]
 out['floodEvidence']=flood_evidence(out.get('addressEvidence'),geometry=r.get('geometry'))
 return out
def unified_summary(lot):
 price_evidence=resolve_price(lot)
 lot=dict(lot,priceEvidence=price_evidence)
 parent=original[byid[lot['planningCellId']]]
 lot=dict(lot);lot['priceEvidence']=resolve_price(lot)
 out=summary(parent)
 out.update(id=lot['id'],displayName=lot['block']+' · Lô '+' và '.join(map(str,lot['lotNumbers'])),sourceLot=True,sourceLotEvidence=lot,pointOnSurface=lot['pointOnSurface'],computedAreaSqm=lot.get('areaSqm',lot.get('combinedAreaSqm')),referencePriceVnd=lot['askingPriceVnd'],demoPriceVnd=None,priceDescription=money(lot['askingPriceVnd'])+' (giá chào lịch sử '+lot['sourceDate']+' — không phải giá thị trường hiện tại)',planningCellId=lot['planningCellId'],planningLabel='Đất ở biệt thự',locationEvidence=lot['locationEvidence'])
 out['addressEvidence']={'location':'Euro Village 2, '+lot['block']+', Hòa Xuân, Đà Nẵng; vị trí theo ghim tin nguồn'}
 out['floodEvidence']=None
 return out


def profile(r):
 if r.get('importedParcel') or r.get('unlocatedProjectLot'):return imported.profile(r)
 r=imported.enrich(r)
 p=summary(r);area=f"{r['computedAreaSqm']:,.3f}".rstrip('0').rstrip('.').replace(',','_').replace('.',',').replace('_','.')
 label='đất ở đô thị / dân cư' if r['planningCategory']=='RESIDENTIAL_PLANNING' else r['planningLabel'].lower()
 return '\n'.join([displaylabels[r['id']]['label']+' · '+r['id'],'Vị trí: '+(p.get('addressEvidence') or {}).get('location','Hòa Xuân, Đà Nẵng'),'Số nhà: chưa xác minh',f"Tọa độ điểm trong ô: {r['pointOnSurface'][1]:.6f}, {r['pointOnSurface'][0]:.6f}",'Loại đất: '+label,'Diện tích: '+area+' m²',('Giá tham khảo: ' if r.get('roadPriceEvidence') else 'Giá mô phỏng: ' if r.get('demoPriceVnd') else 'Giá: ')+price_text(r),'Giấy tờ chính chủ: chưa xác minh','Thu hồi/giải tỏa: chưa xác minh','Tranh chấp/thế chấp: chưa xác minh','Bồi thường: chưa xác minh','Dự án/đồ án: '+('; '.join(x['name'] or 'chưa có tên' for x in p['planningEvidence']) or 'chưa xác minh'),flood_answer(p['floodEvidence'])])
def chat(q,sid):
 if not isinstance(q,str) or not q.strip() or len(q)>2000:raise ValueError('Hãy nhập câu hỏi từ 1–2000 ký tự.')
 if sid not in sessions:
  if len(sessions)>2000:sessions.pop(next(iter(sessions)))
  sid=secrets.token_hex(16);sessions[sid]={'band':None,'area':None,'legal':[],'offset':0,'seen':[],'group':'housing'}
 state=sessions[sid];n=fold(q);band=budget_band(q);area=area_filter(q)
 source_selection=imported.selection(q,state)
 if source_selection is not None:return {'sessionId':sid,**source_selection}
 if 'du lieu da nap' in n or 'thong ke du lieu' in n:
  return {'sessionId':sid,'answer':'Đã nạp '+str(len(activeids))+' ô quy hoạch đủ điều kiện, '+str(len(imported.ROAD))+' ước tính theo đường, '+str(len(imported.SOURCE_ROWS))+' hồ sơ thửa nguồn đủ điều kiện. Hồ sơ nguồn và ô quy hoạch là các cấp dữ liệu khác nhau, không cộng thành tổng lô thực tế.','rows':[],'importStats':imported.stats()}
 flood_result=flood_lookup(q,state)
 if flood_result is not None:return {'sessionId':sid,**flood_result}
 state['lastDomain']='plot'
 outside=requested_location(q)
 if outside:return {'sessionId':sid,'answer':'Hiện chưa có dữ liệu cho địa bàn bạn hỏi ('+outside+'). Bản test chỉ hỗ trợ Hòa Xuân, Đà Nẵng; không trả lô Hòa Xuân thay thế.','rows':[]}
 project_result=project_lookup(q,state,has_filters=band is not None or area is not None)
 if project_result is not None:
  candidates=[unified_summary(x) for x in project_result['sourceLots']]
  candidates.extend(imported.candidate_row(x) for x in imported.PROJECT_CANDIDATES if (not re.search(r'\bb2[.\- ]?(\d+)\b',n) or fold(x['block'])==re.sub(r'\bb2[.\- ]?(\d+)\b',r'b2.\1',re.search(r'\bb2[.\- ]?(\d+)\b',n)[0])))
  if re.search(r'\blo\s+(\d+)(?!\d)(?!\s*(?:ty|ti|trieu))',n) and re.search(r'\bb2[.\- ]?\d+\b',n):
   wanted=int(re.search(r'\blo\s+(\d+)',n)[1]);candidates=[x for x in candidates if wanted in (x.get('lotNumbers') or x.get('sourceLotEvidence',{}).get('lotNumbers',[]))]
  if band is not None:candidates=[x for x in candidates if imported.value(x) is not None and band.get('minPrice',0)<=imported.value(x)<=band.get('maxPrice',10**16)]
  if area is not None:candidates=[x for x in candidates if area.get('minArea',0)<=x['computedAreaSqm']<=area.get('maxArea',float('inf'))]
  project_result.update(rows=candidates,sourceLots=[],clearPlotSelection=not bool(candidates))
  project_result['answer']='Euro Village 2 · Làng Châu Âu 2 · Đảo Triệu Phú\n'+str(len(candidates))+' hồ sơ phù hợp; '+str(sum(bool(x.get('sourceLot')) for x in candidates))+' hồ sơ có ghim nguồn, còn lại chưa định vị. Giá chào lịch sử hoặc chưa rõ ngày không phải giá thị trường hiện tại hay giá giao dịch; chưa xác nhận đang bán. Cặp 14–15 giữ chung diện tích và giá.\nGiấy chứng nhận từng lô: chưa xác minh pháp lý thực tế (chỉ có thông tin giới thiệu từ nguồn tin cũ, không xác nhận đã cấp sổ).'
  state['seen']=[r['id'] for r in candidates];state['selected']=state['seen'][0] if state['seen'] else None
  return {'sessionId':sid,**project_result}
 if state.get('selected') in unified_lots and re.search(r'\b(lo|o|dat)\s*(nay|do)\b',n):
  item=unified_summary(unified_lots[state['selected']])
  return {'sessionId':sid,'answer':item['displayName']+' · '+item['priceDescription'],'rows':[item],'selected':True}
 requested_legal=legal_conditions(q)
 def legal_note():return ('Các điều kiện chưa xác minh: '+', '.join(state.get('legal',[]))+'. Các kết quả dưới đây chưa được lọc theo những điều kiện này.\n') if state.get('legal') else ''
 if requested_legal:state['legal']=requested_legal
 if re.search(r'\b(bo|khong can)\s+(?:dieu kien\s+)?phap ly\b',n):state['legal']=[]
 ordinals=ordinal_numbers(q)
 source_selection=imported.selection(q,state,ordinals)
 if source_selection is not None:return {'sessionId':sid,**source_selection}
 if 'so sanh' in n:
  ids=list(dict.fromkeys(re.findall(r'\bdn-qh-\d+-\d+\b',n)))
  ids=[i.upper() for i in ids]
  if not ids and len(ordinals)>=2:
   if any(i<1 or i>len(state['seen']) for i in ordinals):return {'sessionId':sid,'answer':'Hãy tìm danh sách trước và chọn hai thứ tự có trong danh sách đã xem.','rows':[]}
   ids=[state['seen'][i-1] for i in ordinals]
  if len(ids)!=2 or any(i not in activeids or purpose(original[byid[i]]) not in ('housing','agriculture') for i in ids):return {'sessionId':sid,'answer':'Hãy nêu hai lô hợp lệ để so sánh, ví dụ “so sánh lô thứ 1 và lô thứ 2”.','rows':[]}
  compared=[pricedbyid.get(i,original[byid[i]]) for i in ids]
  return {'sessionId':sid,'answer':legal_note()+'So sánh hai lô:\n\n'+'\n\n'.join(profile(r) for r in compared),'rows':[summary(r) for r in compared],'start':1,'comparison':True}
 fixed=fixed_plot_number(q)
 if fixed is not None:
  rid=numbertocell.get(fixed)
  if rid is None:return {'sessionId':sid,'answer':'Hãy chọn tên từ Lô đất 1 đến Lô đất 8000.','rows':[]}
  target=next(r for r in original if r['id']==rid)
 else:target=None
 source_id=re.search(r'\bdn-qh-\d+-\d+\b',n)
 if not target and source_id:
  rid=source_id[0].upper()
  if rid not in byid:return {'sessionId':sid,'answer':'Không tìm thấy mã lô này trong danh mục.','rows':[]}
  target=original[byid[rid]]
 if not target and ordinals:
  number=ordinals[0]
  if number>len(state['seen']) or number<1:return {'sessionId':sid,'answer':'Chưa có ô ở thứ tự này. Hãy tìm trước hoặc dùng mã DN-QH.','rows':[]}
  target=next(r for r in original if r['id']==state['seen'][number-1])
 if not target and re.search(r'\b(lo|o|dat)\s*(nay|do)\b',n):
  selected=state.get('selected');target=next((r for r in original if r['id']==selected),None)
  if not target:return {'sessionId':sid,'answer':'Bạn đang hỏi ô nào? Hãy nêu số thứ tự hoặc mã DN-QH.','rows':[]}
 if not target and is_flood_question(q):
  selected=state.get('selected');target=next((r for r in original if r['id']==selected),None)
  if not target:return {'sessionId':sid,'answer':'Bạn muốn kiểm tra ngập cho lô nào? Hãy chọn một lô trên bản đồ hoặc nêu mã DN-QH.','rows':[]}
 if target:
  if purpose(target) not in ('housing','agriculture'):
   return {'sessionId':sid,'answer':'Ô này không thuộc hai nhóm đang hỗ trợ: đất ở và đất nông nghiệp. Bạn muốn tìm nhóm nào?','rows':[]}
  if target['id'] not in activeids:return {'sessionId':sid,'answer':'Lô này đang chờ rà soát dữ liệu, chưa đưa vào bộ kết quả tìm kiếm.','rows':[]}
  target=next((r for r in rows if r['id']==target['id']),target);state['selected']=target['id']
  note='Chưa có giá thị trường khớp lô này. Giá bên dưới là giá mô phỏng dùng kiểm thử.\n' if re.search(r'thi truong|dinh gia',n) else 'Chưa tính khoảng cách hoặc tuyến đường đến tiện ích này.\n' if re.search(r'bao nhieu km|cach .*bao xa|benh vien',n) else ''
  ref=summary(target).get('statePriceReference')
  if ref:note+='Đã tìm được bảng giá nhà nước có tên '+ref['road']+' ở gần lô; chưa xác định đúng đoạn đường và vị trí áp dụng, nên chưa gán giá cho lô này.\n'
  return {'sessionId':sid,'answer':note+legal_note()+profile(target),'rows':[summary(target)],'start':1,'selected':target['id']}
 if re.search(r'\banh\b|hinh anh',n):return {'sessionId':sid,'answer':'Bản test chưa hỗ trợ tải và phân tích ảnh tin đăng.','rows':[]}
 if re.search(r'thi truong|dinh gia',n):return {'sessionId':sid,'answer':'Chưa có giá thị trường khớp từng lô. Bạn có thể tìm theo giá mô phỏng hoặc chọn một lô để xem thông tin.','rows':[]}
 requested=None
 for pattern,group in [(r'\b(nong nghiep|hoa mau|trong cay)\b','agriculture'),(r'\b(thuong mai|dich vu|du lich)\b','commerce'),(r'\b(cong vien|cay xanh)\b','green'),(r'\b(mat nuoc|song ho)\b','water'),(r'\b(cong cong|truong hoc|y te)\b','public'),(r'\b(dat o|tho cu|nha o|dat mua|mua dat)\b','housing')]:
  if re.search(pattern,n):requested=group;break
 # A fresh generic priced search defaults to the priced housing catalogue,
 # rather than inheriting agriculture from an unrelated earlier search.
 if requested is None and band is not None:requested='housing'
 if requested not in (None,'housing','agriculture'):
  return {'sessionId':sid,'answer':'Hiện chỉ tìm kiếm hai nhóm: đất ở và đất nông nghiệp.','rows':[]}
 if requested is not None:
  if requested!=state.get('group') and band is None:state['band']=None
  state.update(group=requested,offset=0,seen=[])
 if re.search(r'bo (?:loc |dieu kien )?dien tich|khong gioi han dien tich',n):state.update(area=None,offset=0,seen=[])
 if area is not None:state.update(area=area,offset=0,seen=[])
 if band is not None:state.update(band=band,priceTarget=budget_rank_target(q,band),offset=0,seen=[])
 elif re.search(r'\b(them|tiep|khac|con)\b',n) and state['seen'] and requested is None and area is None and not requested_legal:state['offset']+=5
 elif area is not None or requested_legal:state.update(offset=0,seen=[])
 elif state['band'] is None and requested is None:return {'sessionId':sid,'answer':'Bạn muốn tìm đất ở hay đất nông nghiệp? Ví dụ: “Tìm đất ở khoảng 2 tỷ”, “Xem đất nông nghiệp”.','rows':[]}
 else:
  if requested is None and not re.search(r'\b(them|tiep|khac|con)\b',n):return {'sessionId':sid,'answer':'Bạn có thể tìm theo giá, nói “xem thêm”, hoặc hỏi mã ô DN-QH để xem vị trí.','rows':[]}
 f=state['band'];pool=[pricedbyid.get(r['id'],r) for r in original if r['id'] in activeids and purpose(r)==state.get('group','housing')]
 pool.extend(r for r in imported.SOURCE_ROWS.values() if r['purposeGroup']==state.get('group','housing'))
 a=state.get('area')
 if a:pool=[r for r in pool if a.get('minArea',0)<=r['computedAreaSqm']<=a.get('maxArea',float('inf'))]
 if f is not None and state.get('group')!='housing' and not any(imported.value(r) is not None for r in pool):
  state.update(selected=None,seen=[])
  return {'sessionId':sid,'answer':'Nhóm đất này chưa có bộ giá. Bạn có thể hỏi “Xem đất nông nghiệp” để xem vị trí hoặc “Tìm đất ở khoảng 2 tỷ”.','rows':[],'clearPlotSelection':True}
 matches=[r for r in pool if imported.value(r) is not None and f.get('minPrice',0)<=imported.value(r)<=f.get('maxPrice',10**15)] if f is not None else pool
 target_price=state.get('priceTarget') if f else None
 matches.sort(key=lambda r:((abs((imported.value(r) if imported.value(r) is not None else 10**16)-target_price) if target_price is not None else (imported.value(r) if imported.value(r) is not None else 10**16)),r['id']))
 offset=state['offset'];page=matches[offset:offset+5];state['seen']=[r['id'] for r in matches[:offset+len(page)]]
 state['selected']=page[0]['id'] if page else None
 interval=((money(f['minPrice'])+' đến '+money(f['maxPrice'])) if 'minPrice' in f and 'maxPrice' in f else 'từ '+money(f['minPrice'])+' trở lên' if 'minPrice' in f else 'tối đa '+money(f['maxPrice'])) if f else None
 names={'housing':'nhà ở','agriculture':'nông nghiệp','commerce':'dịch vụ/du lịch','green':'cây xanh/công viên','water':'mặt nước','public':'công cộng và nhóm khác'}
 text=legal_note()+f"Tìm thấy {len(matches)} hồ sơ thuộc nhóm {names[state.get('group','housing')]}"+(f' có giá {interval}. Loại giá và nguồn được ghi riêng từng hồ sơ: giá chào, ước tính theo đường hoặc mô phỏng.' if interval else '. Gồm ô quy hoạch và thửa nguồn; chưa xác nhận đang bán.')
 if target_price is not None:text+=' Ưu tiên các lô có giá gần '+money(target_price)+' nhất.'
 if a:text+=' Diện tích áp dụng: '+str(a.get('minArea',0))+'–'+str(a.get('maxArea','không giới hạn'))+' m².'
 text+=f' Đang hiển thị số {offset+1}–{offset+len(page)}.' if page else ' Không còn kết quả để hiển thị.'
 return {'sessionId':sid,'answer':text,'rows':[summary(r) for r in page],'start':offset+1,'total':len(matches),'filters':f,'targetPriceVnd':target_price,'priceSort':'CLOSEST_TO_TARGET' if target_price is not None else 'ASCENDING','areaFilters':a,'unverifiedConditions':state.get('legal',[]),'clearPlotSelection':not bool(page)}
from .demo_documents import annotate as annotate_demo_document
summary_source=summary
def summary(r):return annotate_demo_document(summary_source(r))
unified_summary_source=unified_summary
def unified_summary(r):return annotate_demo_document(unified_summary_source(r))
profile_source=profile
def profile(r):
 p=summary(r) if r['id'] in byid else annotate_demo_document(r)
 demo=p.get('demoPresentation')
 if not demo:return profile_source(r)
 record_nature='Ô quy hoạch tham khảo (không phải thửa địa chính chính thức)' if p['id'] in byid and not p.get('sourceLot') and not p.get('importedParcel') else 'Hồ sơ nguồn tham khảo (chưa xác minh địa chính)'
 return '\n'.join([p.get('displayName',p['id']),'Bản chất hồ sơ: '+record_nature,'Vị trí: '+(p.get('addressEvidence') or {}).get('location','Hòa Xuân, Đà Nẵng'),
  'Loại đất: '+demo['landType'],'Diện tích: '+str(p['computedAreaSqm'])+' m²',
  ('Giá tham khảo: ' if p.get('roadPriceEvidence') else 'Giá giả lập demo: ' if p.get('demoPriceVnd') else 'Giá: ')+p.get('priceDescription','Chưa có giá'),
  'Giấy tờ chính chủ: '+demo['ownershipDocument'],'Thu hồi/giải tỏa: '+demo['recovery'],
  'Tranh chấp/thế chấp: '+demo['dispute'],'Bồi thường: '+demo['compensation'],'Ngập lụt: '+p.get('floodDisplay',{}).get('display','Chưa xác minh')])
chat_core=chat
from .conversation_router import route as route_buyer_question
def chat(q,sid):
 result=route_buyer_question(q,sid,globals())
 result['rows']=[annotate_demo_document(r) for r in result.get('rows',[])]
 return result


# ---------------------------------------------------------------------------------------
# SmartProp integration API. Chat, detail page and map all go through these functions so
# that the three views always show the same relation, price and demo status for a record.
# ---------------------------------------------------------------------------------------
import copy as _copy
from .flood_evidence import CATALOG as FLOOD_CATALOG

def resolve(rid):
 """Any record id the tool can show: planning cell, Guland parcel, project lot (located or not)."""
 if not isinstance(rid,str):return None
 if rid in imported.SOURCE_ROWS:return annotate_demo_document(imported.SOURCE_ROWS[rid])
 if rid in imported.EXTRAS:return annotate_demo_document(imported.EXTRAS[rid])
 if rid in unified_lots:return unified_summary(unified_lots[rid])
 if rid in byid:
  r=original[byid[rid]];return summary(pricedbyid.get(rid,r))
 return None

def converse(question,state=None):
 """One buyer turn. `state` is the caller-owned conversation state (None starts a new one).
 Returns (result, new_state). The engine keeps no conversation between calls."""
 with lock:
  sessions.clear()
  sid='smartprop-session'
  if state is not None:sessions[sid]=_copy.deepcopy(state)
  try:
   result=chat(question,sid if state is not None else None)
   new_state=sessions.get(result.get('sessionId'))
  finally:
   sessions.clear()
 result.pop('sessionId',None)
 return result,new_state

def neighbors(rid):
 if rid in imported.SOURCE_ROWS:
  row=annotate_demo_document(imported.SOURCE_ROWS[rid])
  features=[{'type':'Feature','geometry':row['geometry'],'properties':{**{k:v for k,v in row.items() if k!='geometry'},'selected':True}}]
  for parent_id in row.get('planningCandidates',[]):
   if parent_id in byid:
    parent=original[byid[parent_id]];props=summary(pricedbyid.get(parent_id,parent));props.update(color=colors.get(parent['planningCode'],[150,160,170]))
    features.append({'type':'Feature','geometry':parent['geometry'],'properties':props})
  return {'type':'FeatureCollection','selectedId':rid,'totalNearby':len(features),'truncated':False,'features':features}
 if rid in unified_lots:
  lot=unified_lots[rid];parent=original[byid[lot['planningCellId']]]
  props=summary(parent);props.update(color=colors.get(parent['planningCode'],[150,160,170]))
  return {'type':'FeatureCollection','selectedId':rid,'totalNearby':2,'truncated':False,'features':[{'type':'Feature','geometry':lot['geometry'],'properties':{**unified_summary(lot),'selected':True}},{'type':'Feature','geometry':parent['geometry'],'properties':props}]}
 if rid not in byid:return None
 i=byid[rid];b=geometries[i];window=(b[0]-.0018,b[1]-.0018,b[2]+.0018,b[3]+.0018)
 indices=sorted([j for j,g in enumerate(geometries) if g[0]<=window[2] and g[2]>=window[0] and g[1]<=window[3] and g[3]>=window[1]],key=lambda j:(0 if j==i else 1,(original[j]['pointOnSurface'][0]-original[i]['pointOnSurface'][0])**2+(original[j]['pointOnSurface'][1]-original[i]['pointOnSurface'][1])**2,original[j]['id']))
 features=[];priced={r['id']:r for r in rows}
 for j in indices[:600]:
  r=original[j];p=summary(priced.get(r['id'],r)) if j==i else {k:r[k] for k in ('id','planningCode','planningCategory','planningLabel')}
  p.update(selected=j==i,color=colors.get(r['planningCode'],[150,160,170]),hasDemoPrice=r['id'] in priced,displayName=displaylabels.get(r['id'],{}).get('label',r['id']))
  features.append({'type':'Feature','geometry':r['geometry'],'properties':p})
 return {'type':'FeatureCollection','features':features,'selectedId':rid,'totalNearby':len(indices),'truncated':len(indices)>600}

def planning_cells():
 return {'type':'FeatureCollection','features':[{'type':'Feature','geometry':r['geometry'],'properties':{'id':r['id'],'planningCode':r['planningCode'],'planningCategory':r['planningCategory'],'color':colors.get(r['planningCode'],[150,160,170])}} for r in original]}

def flood_map(ids=None):return flood_map_context(ids)
def flood_catalog():return {'stats':flood_stats(),'records':FLOOD_CATALOG['records']}
def project_boundaries():
 data=json.loads((ROOT/'outputs/hoa-xuan-projects-20261125/overview.geojson').read_text(encoding='utf-8'))
 return {**data,'features':[f for f in data['features'] if f['properties']['kind']=='Giai đoạn']}
def import_status():return imported.stats()
def health():return {'status':'DEMO_ONLY','planningCells':len(original),'runtimeCells':len(activeids),'pricedCells':len(rows),'gulandParcels':len(imported.SOURCE_ROWS),'projectLots':len(unified_lots)+len(imported.EXTRAS),'flood':flood_stats()}

# Stable internal ids. Source codes (DN-QH-…, GL-PARCEL-…, EV2-…) stay the source key; the
# SmartProp-side id is a UUIDv5 of the source code, so it never collides with listing UUIDs and
# the mapping is reproducible (exported to processed/<version>/relations/id-map.json).
import uuid as _uuid
LAND_NAMESPACE=_uuid.uuid5(_uuid.NAMESPACE_URL,'https://smartprop.local/land-demo/hoa-xuan')
def land_id(code):return str(_uuid.uuid5(LAND_NAMESPACE,code))
def all_codes():return list(byid)+list(imported.SOURCE_ROWS)+list(unified_lots)+list(imported.EXTRAS)
_by_land_id=None
def code_for(value):
 """Accept a source code or its land UUID; return the source code or None."""
 global _by_land_id
 if not isinstance(value,str) or len(value)>80:return None
 if resolve(value) is not None:return value
 if _by_land_id is None:_by_land_id={land_id(c):c for c in all_codes()}
 return _by_land_id.get(value.lower())
