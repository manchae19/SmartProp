"""Cached, grounded Vietnamese overview. Ollama chooses vetted wording, never new facts."""
from collections import OrderedDict
from hashlib import sha256
from threading import Lock, Event, BoundedSemaphore
import json,time,re,os,tempfile
from pathlib import Path
import httpx

TEMPLATE_VERSION='LAND_OVERVIEW_V1'
AREA={'COMPUTED_FROM_PLANNING_CELL':'tính từ đường bao ô quy hoạch','SOURCE_PARCEL':'theo nguồn Guland, chưa đối chiếu địa chính','LISTING':'theo tin nguồn'}
PRICE={'SIMULATED_DEMO':'giá giả lập phục vụ trình diễn','ROAD_ASKING_ESTIMATE':'ước tính từ giá rao theo đường','HISTORICAL_ASKING':'giá chào lịch sử','SOURCE_ASKING':'giá chào theo tin nguồn'}

def plain(value):return re.sub(r'\s+',' ',str(value or '')).strip()
def choices(record):
 c=record.get('cadastral') or {};d=record.get('documents') or {};p=record.get('price') or {};f=record.get('flood') or {}
 location=plain(record.get('location')) or 'địa điểm chưa xác định'
 if len(location.split())>13:location=', '.join(location.split(',')[-2:]).strip()
 project=plain(c.get('projectName'))
 project=' Thuộc '+project+'.' if project and len(project.split())<=10 else ''
 area=c.get('areaSqm');area_text=(format(area,'.12g').replace('.',',') if isinstance(area,(int,float)) else str(area).replace('.',','))+' m²' if area is not None else 'chưa có số liệu'
 basis=AREA.get(c.get('areaBasis'),'chưa rõ căn cứ đo đạc')
 land=plain(d.get('landType')) or 'chưa xác định'
 if len(land.split())>12:land='chức năng theo nguồn ở bảng thông tin'
 evidence=p.get('evidence') or [];price=plain(p.get('display')) or 'chưa có dữ liệu'
 nature='; '.join(dict.fromkeys(PRICE.get(x.get('type'),'giá theo nguồn chưa xác minh') for x in evidence)) or 'chưa có căn cứ giá'
 if len(nature.split())>15:nature='giá tham khảo; xem từng căn cứ trong Chi tiết giá'
 kind={'PLANNING_CELL':'Đây là ô quy hoạch, chưa xác nhận thửa địa chính hay lô bán riêng.','GULAND_PARCEL':'Đây là thửa theo nguồn Guland, chưa xác minh địa chính.','PROJECT_LOT':'Đây là lô dự án theo nguồn, chưa xác minh địa chính.','PROJECT_LOT_UNLOCATED':'Lô dự án chưa định vị; không có vị trí chính xác để hiển thị.'}.get(record.get('kind'),'Loại hồ sơ chưa được xác định.')
 flood='Có nguồn tham chiếu ngập cấp tuyến/khu vực, chưa xác nhận ngập riêng lô.' if f.get('records') else 'Chưa có bằng chứng xác minh hiện trạng ngập riêng lô.'
 groups=[
  [f'Vị trí theo hồ sơ: {location}.{project}',f'Hồ sơ đặt tại {location}.{project}'],
  [f'Diện tích {area_text}, {basis}.',f'Diện tích ghi nhận là {area_text}; căn cứ: {basis}.'],
  [f'Loại đất ghi nhận: {land}.',f'Hồ sơ nêu loại đất là {land}.'],
  [f'Giá {price}, thuộc {nature}.',f'Mức giá hiển thị {price}; bản chất là {nature}.'],
  [kind,kind],
  [flood,flood],
  ['Giấy tờ và hiệu lực pháp lý chưa được xác minh độc lập.','Cần kiểm chứng giấy tờ và hiệu lực pháp lý của riêng hồ sơ.'],
 ]
 if d.get('demo') or any(x.get('type')=='SIMULATED_DEMO' for x in evidence) or f.get('isDemoAssumption'):
  groups.append(['Thuộc tính giả lập chỉ dùng trình diễn, không phải xác nhận thực tế.','Một số thuộc tính là giả lập trình diễn, không xác nhận thực tế.'])
 return groups

def render(groups,indices):return ' '.join(group[index] for group,index in zip(groups,indices))
def valid_indices(value,groups):return isinstance(value,list) and len(value)==len(groups) and all(type(i) is int and 0<=i<len(group) for i,group in zip(value,groups))
def fallback(groups):
 text=render(groups,[0]*len(groups))
 if len(text.split())<80:text+=' Các thông tin còn thiếu cần được đối chiếu hồ sơ gốc trước khi sử dụng để ra quyết định.'
 return text

class OverviewService:
 def __init__(self,generator=None,clock=time.monotonic,max_entries=128,cache_dir=None,wall_clock=time.time):
  self.cache_dir=Path(cache_dir) if cache_dir is not None else None;self.wall_clock=wall_clock
  self.generator=generator or self.ollama;self.clock=clock;self.max_entries=max_entries
  self.cache=OrderedDict();self.pending={};self.lock=Lock();self.capacity=BoundedSemaphore(2)
 def ollama(self,groups):
  from app.rag.config import Settings
  settings=Settings.from_env()
  if settings.llm_provider!='ollama':return None
  # Output is indices into approved equivalent sentences: no model prose is trusted.
  with httpx.Client(base_url=settings.ollama_url,trust_env=False,timeout=httpx.Timeout(8,connect=1),follow_redirects=False) as client:
   response=client.post('/api/chat',json={'model':settings.ollama_model,'stream':False,'think':False,'format':{'type':'object','properties':{'choices':{'type':'array','items':{'type':'integer','minimum':0,'maximum':1}}},'required':['choices'],'additionalProperties':False},'options':{'temperature':0,'num_predict':100},'messages':[{'role':'system','content':'Biên tập tổng quan tiếng Việt trung tính. Mỗi nhóm có hai cách diễn đạt cùng dữ kiện. Chọn một chỉ số 0 hoặc 1 cho từng nhóm theo đúng thứ tự để nối thành đoạn văn 80–120 từ. Chỉ trả JSON choices. Không tạo câu hoặc dữ kiện mới.'},{'role':'user','content':json.dumps(groups,ensure_ascii=False)}]})
   response.raise_for_status();body=response.json()
   if body.get('done_reason') not in (None,'stop'):return None
   return json.loads(body['message']['content']).get('choices')
 def disk_path(self,key):
  return self.cache_dir/(sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest()+'.json')
 def read_disk(self,key,record):
  if self.cache_dir is None:return None
  try:
   path=self.disk_path(key)
   if path.stat().st_size>65536:return None
   stored=json.loads(path.read_text(encoding='utf-8'));result=stored['result']
   if stored['key']!=list(key):return None
   if result['generationMode']=='TEMPLATE' and self.wall_clock()-stored['savedAt']>300:return None
   if result['generationMode'] not in ('TEMPLATE','OLLAMA_GROUNDED_CHOICES'):return None
   expected=(record['landId'],key[0],key[1],key[2],key[3])
   if tuple(result.get(k) for k in ('landId','sourceCode','dataVersion','templateVersion','contentHash'))!=expected:return None
   text=result['text'];groups=choices(record);remaining=text
   if text!=fallback(groups):
    for group in groups:
     matched=next((x for x in group if remaining.startswith(x)),None)
     if matched is None:return None
     remaining=remaining[len(matched):].lstrip()
    if remaining or not 80<=len(text.split())<=120:return None
   if result['wordCount']!=len(text.split()):return None
   ttl=3600 if result['generationMode']!='TEMPLATE' else max(0,300-(self.wall_clock()-stored['savedAt']))
   return result,ttl
  except (OSError,ValueError,TypeError,KeyError):return None
 def write_disk(self,key,result):
  if self.cache_dir is None:return
  temporary=None
  try:
   self.cache_dir.mkdir(parents=True,exist_ok=True)
   with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.cache_dir,prefix='.overview-',suffix='.tmp',delete=False) as handle:
    temporary=Path(handle.name)
    json.dump({'key':list(key),'savedAt':self.wall_clock(),'result':result},handle,ensure_ascii=False)
   os.replace(temporary,self.disk_path(key))
  except OSError:pass # Read-only disk must not prevent the page from loading.
  finally:
   try:
    if temporary is not None:temporary.unlink(missing_ok=True)
   except OSError:pass
 def get(self,record):
  canonical=json.dumps(record,sort_keys=True,ensure_ascii=False,separators=(',',':'))
  digest=sha256(canonical.encode()).hexdigest()
  key=(record['sourceCode'],record['dataVersion'],TEMPLATE_VERSION,digest)
  with self.lock:
   cached=self.cache.get(key)
   if cached and cached[0]>self.clock():self.cache.move_to_end(key);return {**cached[1],'cached':True}
   disk=self.read_disk(key,record)
   if disk:
    result,ttl=disk
    self.cache[key]=(self.clock()+ttl,result)
    while len(self.cache)>self.max_entries:self.cache.popitem(last=False)
    return {**result,'cached':True}
   event=self.pending.get(key);owner=event is None
   if owner:event=Event();self.pending[key]=event
  if not owner:
   event.wait(10)
   with self.lock:
    cached=self.cache.get(key)
    if cached:return {**cached[1],'cached':True}
   return self.result(record,digest,fallback(choices(record)),'TEMPLATE')
  try:
   groups=choices(record);text=fallback(groups);mode='TEMPLATE';acquired=self.capacity.acquire(blocking=False)
   if acquired:
    try:
     indices=self.generator(groups)
     if valid_indices(indices,groups):
      candidate=render(groups,indices)
      if 80<=len(candidate.split())<=120:text=candidate;mode='OLLAMA_GROUNDED_CHOICES'
    except (httpx.HTTPError,ValueError,KeyError,TypeError):pass
    finally:self.capacity.release()
   result=self.result(record,digest,text,mode)
   self.write_disk(key,result)
   with self.lock:
    self.cache[key]=(self.clock()+(3600 if mode!='TEMPLATE' else 300),result);self.cache.move_to_end(key)
    while len(self.cache)>self.max_entries:self.cache.popitem(last=False)
   return result
  finally:
   with self.lock:self.pending.pop(key,None);event.set()
 def result(self,record,digest,text,mode):
  return {'landId':record['landId'],'sourceCode':record['sourceCode'],'dataVersion':record['dataVersion'],'templateVersion':TEMPLATE_VERSION,'contentHash':digest,'text':text,'wordCount':len(text.split()),'generationMode':mode,'cached':False}

service=OverviewService(cache_dir=Path(os.environ.get('SMARTPROP_OVERVIEW_CACHE_DIR') or Path(__file__).resolve().parents[3]/'.local-run'/'cache'/'land-overviews'))