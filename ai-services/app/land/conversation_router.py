"""Buyer intent routing with explicit unsupported filters and shared entity selection."""
import re,secrets
from .demo_documents import annotate
from .budget_rules import fold,budget_band,budget_rank_target
from .query_rules import area_filter,requested_location,legal_conditions

def route(q,sid,g):
 if not isinstance(q,str) or not q.strip() or len(q)>2000:raise ValueError('Hãy nhập câu hỏi từ 1–2000 ký tự.')
 q=re.sub(r'\beuro\s*2\b','Euro Village 2',q,flags=re.I)
 q=re.sub(r'mắc\s+(?:tiền\s+)?nhất|đắt\s+tiền\s+nhất','đắt nhất',q,flags=re.I)
 n=fold(q).strip(' ?!.');sessions=g['sessions'];imp=g['imported']
 if sid not in sessions:
  sid=secrets.token_hex(16);sessions[sid]={'band':None,'area':None,'legal':[],'offset':0,'seen':[],'group':'housing'}
 s=sessions[sid];s.setdefault('scope','plots')
 def reply(text,rows=None,**kw):return dict(sessionId=sid,answer=text,rows=rows or [],**kw)
 def resolve(rid):
  if rid in imp.SOURCE_ROWS:return imp.SOURCE_ROWS[rid]
  if rid in imp.EXTRAS:return imp.EXTRAS[rid]
  if rid in g['unified_lots']:return g['unified_summary'](g['unified_lots'][rid])
  if rid in g['byid']:
   r=g['original'][g['byid'][rid]];return g['summary'](g['pricedbyid'].get(rid,r))
  return None
 def refs():
  visible=s.get('visibleIds',s.get('seen',[]))
  ids=re.findall(r'\b(?:dn-qh-\d+-\d+|ev2-[a-z0-9-]+|gl-(?:parcel|listing)-\d+)\b',n);out=[]
  for rid in ids:
   row=resolve(rid.upper())
   if row:out.append(row)
  for m in re.finditer(r'\b(?:lo|o|mieng|manh)\s+dat\s+(?:so\s+)?(\d+)\b(?!\s*(?:ty|ti|trieu|m2))',n):
   rid=g['numbertocell'].get(int(m[1]));row=resolve(rid)
   if row:out.append(row)
  ords=[]
  for m in re.finditer(r'\b(?:lo|o|can|cai)\s+(?:thu\s+)?(\d+|nhat|mot|hai|ba|bon|nam|dau tien)\b(?!\s*(?:ty|ti|trieu|m2))',n):
   word=m[1];ords.append(int(word) if word.isdigit() else {'nhat':1,'mot':1,'hai':2,'ba':3,'bon':4,'nam':5,'dau tien':1}[word])
  if re.search(r'\b(?:lo|o|cai|thua) dau(?: tien)?\b',n):ords=[1]
  if re.search(r'hai lo dau',n):ords=[1,2]
  if re.search(r'(?:lo|cai) cuoi(?: cung)?',n):ords=[len(visible)]
  if re.search(r'\bthu (nhat|hai|ba)\b',n) and not ords:ords=[{'nhat':1,'hai':2,'ba':3}[re.search(r'\bthu (nhat|hai|ba)\b',n)[1]]]
  for i in ords:
   if 1<=i<=len(visible):
    row=resolve(visible[i-1])
    if row:out.append(row)
  if not out and (re.search(r'\b(lo|o|thua|gia|khu vuc|cho)(?: dat)? (nay|do)\b',n) or re.search(r'giay to|phap ly|dien tich bao nhieu|dien tich the nao|thuoc du an|du an nao',n)):
   row=resolve(s.get('selected'))
   if row:out.append(row)
  return list({r['id']:r for r in out}.values())
 if 'thong ke du lieu' in n or 'du lieu da nap' in n:return g['chat_core'](q,sid)
 if re.search(r'^dat (?:thuong mai|cong vien|mat nuoc|cong nghiep)',n):return reply('Hiện chỉ hỗ trợ tìm hai nhóm: đất ở và đất nông nghiệp.')
 if re.fullmatch(r'(xin chao|chao(?: ban)?|hello|hi)[!. ]*',n):return reply('Chào bạn! Bạn muốn tìm đất theo ngân sách, xem một lô đất hay tra nguy cơ ngập?')
 if re.search(r'ban (?:lam duoc gi|co the lam gi)|huong dan|chuc nang',n):return reply('Tôi hỗ trợ tìm đất ở và đất nông nghiệp tại Hòa Xuân, xem hồ sơ và vị trí, so sánh giá/diện tích, tra nguồn nguy cơ ngập Đà Nẵng. Ví dụ: “Tìm đất khoảng 7 tỷ, 100 m²”.')
 if re.search(r'cam on|thank',n):return reply('Rất vui được hỗ trợ bạn. Bạn có thể hỏi tiếp về lô đang xem.')
 if re.search(r'nhan vien|gap .*tu van',n):return reply('Bản thử chưa kết nối nhân viên tư vấn. Bạn có thể lưu mã lô và các thông tin muốn hỏi thêm.')
 if re.search(r'\b(find land|english)\b',n):return reply('Hiện tôi hỗ trợ tiếng Việt. Bạn thử: “Tìm đất khoảng 2 tỷ”.')
 if re.search(r'thu tuc|sang ten|dat coc|thue mua|thue ban|vay ngan hang|nam sau|du bao|(?<!chu )dau tu|ban dat giup|dang ban|dang tin|sunland|dao vip\b',n):
  return reply('Chưa có chức năng tư vấn thủ tục, thuế, vay, dự báo giá hoặc đăng bán trong bản thử. Tôi có thể tra hồ sơ đất Hòa Xuân và nguồn nguy cơ ngập. Chưa có danh mục riêng cho dự án khác bạn nêu.')
 if re.search(r'(?:tho cu|nong nghiep).*(?:la gi|xay nha)',n):return reply('Tôi có thể hiển thị loại đất theo nguồn. Chưa có bộ tài liệu pháp luật được đối chiếu để giải đáp câu hỏi này; cần kiểm tra mục đích sử dụng và hồ sơ cụ thể tại cơ quan có thẩm quyền.')
 if re.search(r'gia .*con dung|gia nay .*hien tai|gia .*cap nhat',n):return reply('Chưa xác nhận giá còn đúng hiện tại. Hồ sơ dự án có giá chào lịch sử năm 2021; giá theo đường là ước tính từ nguồn rao. Hãy xem ngày và nguồn giá của từng hồ sơ.')
 if re.search(r'thoi tiet|1\s*\+\s*1',n):return reply('Câu hỏi này nằm ngoài phạm vi tra cứu bất động sản của bản thử.')
 if re.search(r'thuế|phí|lệ phí',q,re.I):
  return reply('Chưa đủ hồ sơ và căn cứ pháp luật đã kiểm chứng để tính thuế/phí cho lô này. Cần biết loại giao dịch, thời điểm, giá tính thuế, loại đất và trường hợp miễn giảm. Tôi không coi câu hỏi thuế là yêu cầu thuê đất.')
 if re.search(r'\bthue\b',n) and not re.search(r'cho thue|thue dat|thue lo',n):
  return reply('Bạn đang hỏi thuế/phí hay thuê đất? Hãy nêu rõ để tôi không nhầm hai nhu cầu. Chưa có căn cứ tính thuế cho riêng lô này.')
 if re.search(r'can ho|chung cu|phong ngu|\bthue\b|nha (?:[1-9]|cho)',n):return reply('Hiện chỉ có hồ sơ đất ở và đất nông nghiệp; chưa hỗ trợ căn hộ, nhà xây sẵn hoặc cho thuê.')
 if re.search(r'trieu\s*(?:/\s*m|mot met|moi met)|trieu\s*/\s*m2',n):return reply('Bạn đang nêu đơn giá trên m². Hiện bộ lọc dùng tổng giá lô; hãy cho biết tổng ngân sách hoặc diện tích để quy đổi.')
 amenity=bool(re.search(r'gan (?:truong|cong vien|song|cho|benh vien|sieu thi)|benh vien|truong hoc|sieu thi',n))
 search=bool(re.search(r'\b(tim|mua|xem dat|xem thua|danh sach thua|dat o|dat nong nghiep|ngan sach|re nhat|dat nhat|cao nhat)\b',n))
 plotrefs=refs()
 # After a flood catalogue, "lô thứ 1" refers to that list, which holds flood locations, not plots.
 if s.get('lastDomain')=='flood' and not plotrefs and re.search(r'\b(?:lo|o|cai) (?:thu|dau)',n):
  return reply('Danh sách vừa xem là vị trí nguy cơ ngập, không phải lô đất. Hãy chọn “Xem trên bản đồ” ở vị trí cần tra, hoặc tìm lô đất theo giá.')
 # "Tìm đất 2" carries no unit: it may be 2 tỷ, 2 triệu/m² or lô số 2. Ask instead of listing everything.
 # "Xem lô đất 7" stays a fixed plot number; only a search verb with a bare number is ambiguous.
 bare=re.fullmatch(r'(?:tim|mua) (?:mieng |manh )?dat(?: o)? (\d+(?:[.,]\d+)?)',n)
 if bare:return reply('Bạn muốn tìm đất giá khoảng '+bare[1]+' tỷ, hay xem Lô đất số '+bare[1]+'? Hãy nêu kèm đơn vị, ví dụ “Tìm đất khoảng '+bare[1]+' tỷ”.')
 if not plotrefs and re.search(r'\b(?:lo|o|thua|cho)(?: dat)? (?:nay|do)\b',n) and not s.get('selected'):
  return reply('Bạn đang hỏi lô nào? Hãy tìm danh sách trước, chọn số thứ tự trong danh sách hoặc nêu mã lô (ví dụ “Lô đất số 7”).')
 # "lô đất 100m2" is an area, not plot number 100.
 if not plotrefs and re.search(r'\b(?:dn-qh-|lo (?:dat (?:so )?\d+(?![\d.,]*\s*(?:m2|m²|met|m\b))|thu (?:\d+|nhat)|so \d+|nay))',n) and not re.search(r'\bty\b|\btrieu\b|\bb2[.\- ]',n) and 'so sanh' not in n:
  return reply('Chưa xác định được hồ sơ này. Hãy chọn số thứ tự có trong danh sách vừa xem hoặc mã lô hợp lệ từ Lô đất 1 đến Lô đất 8000.')
 if re.search(r'\bto\s+\d+\b',n) and re.search(r'\bthua\s+\d+\b',n):
  found=imp.selection(q,s)
  if found is not None:return {'sessionId':sid,**found}
 if 'so sanh' in n:
  if not 2<=len(plotrefs)<=3:return reply('Hãy chọn 2–3 hồ sơ trong danh sách vừa xem, ví dụ “So sánh lô thứ 1 và lô thứ 2”.')
  return reply('So sánh '+str(len(plotrefs))+' hồ sơ:\n\n'+'\n\n'.join(r.get('displayName',r['id'])+'\nDiện tích: '+str(r['computedAreaSqm'])+' m²\nGiá: '+r.get('priceDescription','chưa có giá') for r in plotrefs),plotrefs,comparison=True,start=1)
 if plotrefs and not search:
  r=annotate(plotrefs[0]);s['selected']=r['id'];s['lastDomain']='project' if s.get('scope')=='project' else 'plot'
  if re.search(r'ngap|\blut\b',n):
   flood=r['floodDisplay'];text='Ngập lụt: '+flood['display']+'.'
   text+=' '+flood['detail'] if flood.get('detail') else ' Hiện chưa xác nhận hiện trạng ngập của riêng lô này.'
  elif re.search(r'chu dau tu',n):text='Chủ đầu tư Euro Village 2: Sun Group — theo nguồn giới thiệu dự án.' if r.get('sourceLot') or r.get('unlocatedProjectLot') else 'Chưa có thông tin chủ đầu tư được xác nhận cho hồ sơ này.'
  elif re.search(r'(?:cho xem|xem|anh|ban).*so (?:do|hong)|\banh\b|hinh anh',n):text='Chưa có ảnh lô đất hoặc bản chụp giấy chứng nhận trong hồ sơ này.'
  elif re.search(r'chu .*la ai|so dien thoai|lien he chu',n):text='Chưa có thông tin chủ đất hoặc số điện thoại chủ đất được xác minh cho lô này.'
  elif re.search(r'huong|mat tien|ngang|duong .*m5',n):text='Chưa có dữ liệu hướng, mặt tiền hoặc chiều rộng đường được xác minh cho riêng lô này.'
  elif amenity:text='Chưa kết nối dữ liệu tiện ích và khoảng cách cho riêng lô này; chưa xác định được trường học/bệnh viện gần nhất.'
  elif re.search(r'so do|so hong|giay to|giay chung nhan|chinh chu',n):
   document=r.get('certificateDisplay');text='Giấy tờ chính chủ: '+(document['display'] if document else 'Chưa xác minh')+'.'
  elif re.search(r'thu hoi|giai toa',n):text='Thu hồi/giải tỏa: '+r.get('demoPresentation',{}).get('recovery','Chưa xác minh')+'.'
  elif re.search(r'dien tich',n):text='Diện tích: '+str(r.get('computedAreaSqm','chưa xác minh'))+' m² theo nguồn; chưa xác minh đo đạc thực tế.'
  elif re.search(r'boi thuong|the chap|tranh chap|phap ly',n):text='Tranh chấp/thế chấp và bồi thường: chưa xác minh.'
  elif re.search(r'loai dat|dat gi',n):text='Loại đất: '+r.get('demoPresentation',{}).get('landType',r.get('planningLabel','Chưa xác định'))+'.'
  elif re.search(r'quy hoach|du an',n):text='Dự án/đồ án theo nguồn: '+('; '.join(x.get('name') or 'chưa có tên' for x in r.get('planningEvidence',[])) or 'chưa xác minh')+'. Chưa đối chiếu đủ văn bản gốc và hiệu lực để kết luận vướng quy hoạch.'
  elif re.search(r'\bgia\b',n):
   text='Giá: '+r.get('priceDescription','chưa có giá')+'. Chưa xác nhận giá giao dịch thị trường hiện tại.'
   asked=budget_band(q) if re.search(r'\d\s*(?:ty|ti|trieu)',n) else None
   if asked and g['imported'].value(r) is None:text+=' Hồ sơ này chưa có giá nên chưa so được với mức bạn nêu.'
   elif asked and not asked.get('minPrice',0)<=g['imported'].value(r)<=asked.get('maxPrice',10**18):text+=' Giá này nằm ngoài mức bạn nêu.'
  else:text=g['profile'](r)
  # Keep the short, field-specific answer visible; name the record so the answer stands alone.
  name=r.get('displayName') or r['id']
  if not text.startswith(name):text=name+' — '+text
  return reply(text,[r],focusedAnswer=True,selected=r['id'],start=1)
 if re.search(r'chu dau tu',n) and re.search(r'euro|trieu phu|chau au',n):return reply('Chủ đầu tư Euro Village 2: Sun Group — theo nguồn giới thiệu dự án.')
 if re.search(r'ngap|\blut\b',n) and not search:
  if re.search(r'sau bao nhieu|do sau|nam 20\d\d|hay ngap nhat',n):return reply('Chưa có số liệu độ sâu ngập theo năm hoặc cơ sở xếp hạng khu vực ngập nhiều nhất. Có thể tra danh mục vị trí nguy cơ theo nguồn.')
  if re.fullmatch(r'canh bao ngap[? ]*',n):q='Cảnh báo ngập Đà Nẵng'
  if re.search(r'lien chieu',n) and not re.search(r'quan|phuong|cu',n):return reply('Bạn muốn tra phường Liên Chiểu hiện tại hay quận Liên Chiểu cũ? Hai phạm vi có số bản ghi khác nhau.')
  if re.search(r'hai chau',n) and not re.search(r'phuong|quan|cu',n):q+=' quận Hải Châu cũ'
  result=g['chat_core'](q,sid)
  if result.get('responseKind')!='FLOOD_CATALOG':s['lastDomain']='flood_empty'
  return result
 if s.get('lastDomain')=='flood' and re.fullmatch(r'(xem them|tiep|con nua|con khong)',n):return g['chat_core'](q,sid)
 if s.get('lastDomain')=='flood_empty' and re.fullmatch(r'(xem them|tiep|con nua|con khong)',n):return reply('Chưa có danh sách ngập phù hợp để xem tiếp. Hãy chọn địa bàn hoặc tuyến đường khác.')
 if s.get('lastDomain')=='flood' and re.search(r'lo thu|cai dau',n):return reply('Danh sách vừa xem là vị trí nguy cơ ngập, không phải lô đất. Hãy chọn “Xem trên bản đồ” ở vị trí cần tra.')
 outside=requested_location(q)
 if outside:return reply('Chưa có dữ liệu đất cho '+outside+'. Phạm vi tra đất hiện chỉ có Hòa Xuân, Đà Nẵng; không trả lô ở nơi khác thay thế.')
 if amenity and not search:return reply('Chưa kết nối dữ liệu tiện ích trong bản thử. Chưa thể xác định tên, khoảng cách hoặc tuyến đường đến tiện ích bạn hỏi.')
 if re.search(r'gia dat nha nuoc|dinh gia',n):return reply('Chưa hỗ trợ định giá hoặc áp bảng giá nhà nước cho đúng đoạn đường/vị trí thửa. Có thể xem giá chào hoặc ước tính tham khảo khi hồ sơ có nguồn.')
 if re.search(r'gia dinh',n):return reply('Bạn muốn mua đất để ở hay đầu tư? Hãy cho biết diện tích, khu vực và tiện ích cần ưu tiên; hiện chưa có bộ lọc tiện ích cho gia đình.')
 more=bool(n.split()) and set(n.split())<=set('xem con lo dat nao hay khong khac nua tiep them'.split()) and bool(set(n.split())&{'con','them','tiep','khac'})
 project=bool(re.search(r'euro|trieu phu|chau au|\bb2[.\- ]?\d+',n))
 if project:
  result=g['chat_core'](q,sid);s.update(scope='project',projectRows=result.get('rows',[]),visibleIds=[r['id'] for r in result.get('rows',[])],lastDomain='project')
  return result
 if more and s.get('scope')=='project':return reply('Đã hiển thị hết '+str(len(s.get('projectRows',[])))+' hồ sơ của dự án theo điều kiện vừa tìm. Chưa có hồ sơ tiếp theo.',[],clearPlotSelection=False)
 if re.search(r'bo (?:loc |dieu kien )?dien tich|khong loc dien tich',n):
  s['area']=None;s['offset']=0;q='Tìm đất';search=True
 if re.search(r'bo (?:loc |dieu kien )?gia|khong loc gia',n):s.update(band=None,priceTarget=None,offset=0);q='Tìm đất';search=True
 band=budget_band(q);area=area_filter(q)
 if not (search or band or area or more or re.search(r're hon|dat hon|thap nhat|cao nhat',n)):
  return reply('Tôi chưa hiểu yêu cầu này. Bạn có thể tìm theo giá/diện tích, hỏi một lô đang xem hoặc tra nguy cơ ngập.')
 # Price and source scope are maintained explicitly instead of falling back to all planning cells.
 if 'guland' in n or 'danh sach thua' in n:s['scope']='guland'
 elif search and not more:s['scope']='plots'
 if band is not None:s.update(band=band,priceTarget=budget_rank_target(q,band),offset=0)
 if area is not None:s.update(area=area,offset=0)
 if re.search(r'\b(nong nghiep|hoa mau)\b',n):
  if s.get('group')!='agriculture' and band is None:s['band']=None
  s['group']='agriculture'
 elif band is not None or re.search(r'\b(dat o|tho cu)\b',n):s['group']='housing'
 s['lastDomain']='plot';notes=[]
 if amenity:notes.append('Chưa lọc được theo tiện ích, gần sông/chợ/trường học.')
 if re.search(r'ngap|\blut\b',n):notes.append('Chưa lọc được điều kiện không ngập cho từng lô.')
 if re.search(r'\bduong\b',n):notes.append('Chưa lọc theo đúng tuyến đường hoặc chiều rộng đường bạn nêu.')
 if re.search(r'gan |mat tien',n) and not notes:notes.append('Chưa lọc được điều kiện vị trí/mặt tiền bạn nêu.')
 legal=legal_conditions(q)
 if legal:notes.append('Chưa lọc được các điều kiện pháp lý: '+', '.join(legal)+'.')
 if re.search(r'cam le|da nang',n):notes.append('Phạm vi kết quả đất: Hòa Xuân, Đà Nẵng.')
 if s['scope']=='guland':pool=list(imp.SOURCE_ROWS.values())
 else:pool=[dict(imp.enrich(g['pricedbyid'].get(r['id'],r)),purposeGroup=g['purpose'](r)) for r in g['original'] if r['id'] in g['activeids']]
 # Do not add source parcel counts to planning-cell counts in an undifferentiated list.
 group=s.get('group','housing')
 # "Xem thửa Guland" lists every eligible parcel; a group only narrows it when the buyer names one.
 if not (s['scope']=='guland' and not re.search(r'\b(dat o|tho cu|nong nghiep|hoa mau)\b',n) and band is None and s.get('band') is None):
  pool=[r for r in pool if r.get('purposeGroup')==group]
 a=s.get('area')
 if a:pool=[r for r in pool if a.get('minArea',0)<=r['computedAreaSqm']<=a.get('maxArea',float('inf'))]
 f=s.get('band')
 if re.search(r're hon|dat hon',n):
  previous=resolve(s.get('selected'));pivot=imp.value(previous) if previous else s.get('priceTarget')
  if pivot is None:return reply('Bạn muốn rẻ hơn mức giá nào? Hãy chọn một hồ sơ có giá hoặc nêu ngân sách.')
  f={'maxPrice':pivot-1} if 're hon' in n else {'minPrice':pivot+1};s.update(band=f,priceTarget=None,offset=0)
 if f:pool=[r for r in pool if imp.value(r) is not None and f.get('minPrice',0)<=imp.value(r)<=f.get('maxPrice',10**18)]
 descending=bool(re.search(r'dat nhat|cao nhat',n));ascending=bool(re.search(r're nhat|thap nhat|re hon',n))
 if descending or ascending:s['sort']='desc' if descending else 'asc';s['priceTarget']=None;pool=[r for r in pool if imp.value(r) is not None]
 elif band is not None:s['sort']='target'
 target=s.get('priceTarget');mode=s.get('sort','target')
 pool.sort(key=lambda r:((-(imp.value(r) or 0) if mode=='desc' else (imp.value(r) if imp.value(r) is not None else 10**18) if mode=='asc' or target is None else abs((imp.value(r) if imp.value(r) is not None else 10**18)-target)),r['id']))
 if more:s['offset']=s.get('offset',0)+5
 elif not re.search(r're hon',n):s['offset']=0
 start=s.get('offset',0);page=pool[start:start+5]
 s.update(seen=[r['id'] for r in pool[:start+len(page)]],visibleIds=[r['id'] for r in page],selected=page[0]['id'] if page else None,legal=[])
 if f and f.get('minPrice')==5000000000 and re.search(r'\bduoi\b',n):notes.append('Theo khung giá đã chọn, đang lọc từ 5 tỷ đến '+g['money'](f['maxPrice'])+'.')
 scope='thửa nguồn Guland (chưa xác minh địa chính)' if s['scope']=='guland' else 'ô quy hoạch tham khảo (không phải thửa địa chính chính thức)'
 text=f'Tìm thấy {len(pool)} {scope} phù hợp.'
 if a:text+=' Diện tích: '+str(a.get('minArea',0))+'–'+str(a.get('maxArea','không giới hạn'))+' m².'
 text+=f' Hiển thị {start+1}–{start+len(page)}.' if page else ' Chưa có kết quả; không tự mở rộng điều kiện.'
 if page and any(r.get('demoPriceVnd') and not r.get('roadPriceEvidence') for r in page):notes.append('Một số kết quả dùng giá giả lập demo (không phải giá thị trường hay giá giao dịch), được ghi rõ trên thẻ.')
 page=[g['summary'](r) if r['id'] in g['byid'] else r for r in page]
 return reply(text+('\n'+'\n'.join(notes) if notes else ''),page,start=start+1,total=len(pool),filters=f,targetPriceVnd=s.get('priceTarget'),areaFilters=a,unappliedConditions=notes,clearPlotSelection=not bool(page))
