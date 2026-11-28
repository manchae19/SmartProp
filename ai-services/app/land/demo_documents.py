"""User-approved demo presentation; source evidence and legal status stay unchanged."""
import json,re
from pathlib import Path
from .paths import DATA_ROOT
ROOT=DATA_ROOT/'outputs/hoa-xuan-enriched-20261122'
PLANS={p['id']:p for p in json.loads((ROOT/'plans.json').read_text(encoding='utf-8'))}
CELL_PLANS={c['id']:c['sourcePlanIds'] for c in json.loads((ROOT/'cells.json').read_text(encoding='utf-8'))}
def project_name(row):
    if row.get('sourceLot') or row.get('unlocatedProjectLot'):return 'Euro Village 2'
    names=[p.get('name','') for p in row.get('planningEvidence',[])]
    for cid in row.get('planningCandidates',[]):
        names.extend(PLANS.get(pid,{}).get('name','') for pid in CELL_PLANS.get(cid,[]))
    return next((name for name in names if re.search(r'khu đô thị|khu biệt thự|đảo vip|\bkdc\b|khu [a-e](?:\d|\s|\b)',name,re.I)),None)
def annotate(row):
    r=dict(row)
    flood_geometry=r.get('geometry') or ({'type':'Point','coordinates':r['pointOnSurface']} if r.get('sourceLot') and r.get('pointOnSurface') else None)
    if flood_geometry and not (r.get('floodEvidence') or {}).get('items'):
        from .flood_evidence import evidence
        r['floodEvidence']=evidence(r.get('addressEvidence'),geometry=flood_geometry)
    flood=r.get('floodEvidence') or {}
    items=flood.get('items',[])
    if items:
        relation=items[0].get('relation','ILLUSTRATIVE_CORRIDOR')
        display={'DIRECT_SOURCE_MATCH':'Có nguồn nguy cơ ngập trùng tên đường và địa bàn',
                 'SOURCE_TEXT_MENTION':'Có nguồn nguy cơ ngập nhắc tới tuyến đường gần lô',
                 'ILLUSTRATIVE_CORRIDOR':'Liên quan tuyến tham chiếu nguy cơ ngập (dải minh họa 80 m)'}[relation]
        r['floodDisplay']={'display':display,'basis':'SOURCE_ROAD_CONTEXT','relation':relation,'detail':flood.get('message'),
                           'recordIds':[i['id'] for i in items],'isDemoAssumption':False,'verifiedForThisParcel':False,'physicalFloodStatus':'UNKNOWN'}
    elif r.get('unlocatedProjectLot'):
        r['floodDisplay']={'display':'Chưa xác định vị trí để đối chiếu','basis':'UNLOCATED','isDemoAssumption':False,'verifiedForThisParcel':False,'physicalFloodStatus':'UNKNOWN'}
    else:
        r['floodDisplay']={'display':'Chưa có bản ghi ngập trùng tuyến đường nguồn (giả định kịch bản demo — không xác nhận an toàn ngập)','basis':'USER_APPROVED_DEMO_SCENARIO','isDemoAssumption':True,'verifiedForThisParcel':False,'physicalFloodStatus':'UNKNOWN'}
    housing=r.get('purposeGroup')=='housing' or r.get('planningCategory')=='RESIDENTIAL_PLANNING' or r.get('sourceLot') or r.get('unlocatedProjectLot')
    agriculture=r.get('purposeGroup')=='agriculture' or r.get('planningCategory')=='AGRICULTURAL_PLANNING'
    if not housing and not agriculture:return r
    project=project_name(r) if housing else None
    document='Sổ hồng' if project else 'Sổ đỏ'
    evidence={'document':document,'display':'Giả định kịch bản demo ('+document.lower()+') — chưa có giấy chứng nhận thực tế được xác minh','basis':'USER_APPROVED_DEMO_SCENARIO',
              'verifiedForThisParcel':False,'isDemoAssumption':True}
    land_type_base=('Nhóm quy hoạch tham khảo: đất ở dự án '+project) if project else 'Nhóm quy hoạch tham khảo: đất ở' if housing else 'Nhóm quy hoạch tham khảo: đất nông nghiệp'
    r['demoPresentation']={'version':'BUYER-DEMO-RULES-20261128','isDemoScenario':True,
        'projectName':project,'landType':land_type_base+' (giả định demo, chưa xác minh địa chính)',
        'ownershipDocument':evidence['display'],
        'recovery':'Chưa xác minh quy hoạch thu hồi/giải tỏa (giả định kịch bản demo — không xác nhận không vướng quy hoạch)' if housing and not project else 'Chưa xác minh',
        'dispute':'Chưa xác minh','mortgage':'Chưa xác minh','compensation':'Chưa xác minh'}
    r['certificateDisplay']=evidence
    return r
