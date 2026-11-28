"""Extract supported buyer conditions without inventing missing evidence."""
import re
from .budget_rules import fold,without_money

def area_filter(question):
 n=fold(question).replace('–','-').replace('—','-').replace('²','2')
 num=r'(\d+(?:[.,]\d+)?)'
 convert=lambda v:float(v.replace(',','.'))
 dimensions=re.search(num+r'\s*(?:m\s*)?[x×]\s*'+num+r'\s*m?\b',n) or re.search(r'ngang\s*'+num+r'\s*m?\s*(?:dai|sau)\s*'+num+r'\s*m?\b',n)
 if dimensions:
  area=convert(dimensions[1])*convert(dimensions[2])
  if area<=0:raise ValueError('Kích thước đất phải lớn hơn 0.')
  return {'minArea':area,'maxArea':area}
 constraints=list(re.finditer(r'(duoi|toi da|khong qua|tren|toi thieu|it nhat)\s*'+num+r'\s*(?:m2|met vuong)\b',n))
 if constraints:
  out={}
  for m in constraints:out['maxArea' if m[1] in ('duoi','toi da','khong qua') else 'minArea']=convert(m[2])
  if out.get('minArea',0)<=0 and 'minArea' in out:raise ValueError('Diện tích phải lớn hơn 0.')
  if out.get('minArea',0)>out.get('maxArea',float('inf')):raise ValueError('Khoảng diện tích chưa hợp lệ.')
  return out
 match=re.search(num+r'\s*(?:m2|met vuong)?\s*(?:den|toi|-)\s*'+num+r'\s*(?:m2|met vuong)\b',n)
 if match:
  lo,hi=map(convert,match.groups())
  if lo>hi or lo<=0:raise ValueError('Khoảng diện tích chưa hợp lệ; hãy nêu mốc nhỏ trước mốc lớn.')
  return {'minArea':lo,'maxArea':hi}
 match=re.search(r'(duoi|toi da|khong qua|tren|toi thieu|it nhat)\s*'+num+r'\s*(?:m2|met vuong)\b',n)
 if match:return {('maxArea' if match[1] in ('duoi','toi da','khong qua') else 'minArea'):convert(match[2])}
 match=re.search(r'\bdien tich\s*'+num+r'\s*(?:m2|met vuong)\b',n)
 if match:return {'minArea':convert(match[1]),'maxArea':convert(match[1])}
 match=re.search(r'(?:khoang|tam|xap xi)?\s*'+num+r'\s*(?:m2|met vuong)\b',n)
 if match:
  area=convert(match[1]);delta=area*.1 if re.search(r'\b(khoang|tam|xap xi)\b',match[0]) else 0
  if area<=0:raise ValueError('Diện tích phải lớn hơn 0.')
  return {'minArea':round(area-delta,3),'maxArea':round(area+delta,3)}
 return None

def requested_location(question):
 n=fold(question)
 # Explicit places are checked before a search; unsupported places never become Hòa Xuân results.
 known=['ha noi','sai gon','ho chi minh','hue','hoi an','dien ban','lien chieu','son tra','ngu hanh son','hai chau','hoa vang','hoa tien','hoa lien','quang nam','nha trang','thanh khe','hoa phuoc','hoa quy','hoa hai','quang ngai']
 for name in known:
  if re.search(r'\b'+name+r'\b',n):return name
 match=re.search(r'(?<!hien )\b(?:khu vuc|tai|dia ban)\s+(.+?)(?=\s+(?:gia|duoi|tren|khoang|tam|dien tich)|[;,]|$)',n)
 if match:
  # A known project alias is not an unsupported administrative locality.
  # Resolve from the same source catalogue used by project lookup, never fuzzy-match a new place.
  place=match[1].strip(' .!?')
  if any(x in place for x in ('hoa xuan','da nang','day','nay')):return None
  from .paths import land_enabled
  if not land_enabled():return place
  from .project_lookup import PROJECTS
  if any(place==fold(alias).strip(' .!?') for project in PROJECTS for alias in project['aliases']):return None
  if not any(x in match[1] for x in ('hoa xuan','da nang','day','nay')):return match[1]
 return None

def legal_conditions(question):
 n=fold(question);out=[]
 for pattern,label in [(r'chinh chu','chính chủ'),(r'co so|so do|so hong|giay chung nhan','giấy chứng nhận'),(r'khong (?:co )?tranh chap','không tranh chấp'),(r'khong (?:co )?the chap','không thế chấp'),(r'khong (?:bi |dinh |vuong )?(?:thu hoi|giai toa|quy hoach)','không thu hồi/giải tỏa hoặc vướng quy hoạch')]:
  if re.search(pattern,n):out.append(label)
 return out

def ordinal_numbers(question):
 n=without_money(question);words={'mot':1,'hai':2,'ba':3,'bon':4,'nam':5}
 return [int(m[1]) if m[1].isdigit() else words[m[1]] for m in re.finditer(r'\b(?:lo|o|mieng dat|manh dat)\s+(?:thu\s+)?(\d+|mot|hai|ba|bon|nam)\b(?!\s*(?:ty|ti|trieu|m2))',n)]


def fixed_plot_number(question):
 n=without_money(question)
 match=re.search(r'\b(?:lo|o)(?:\s+dat)?\s+so\s+(\d+)\b|\b(?:lo|o)\s+dat\s+(\d+)\b(?!\s*(?:[.,]\d|m2|m²|met))',n)
 return int(match[1] or match[2]) if match else None
