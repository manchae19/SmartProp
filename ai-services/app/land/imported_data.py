"""Runtime adapter for afternoon evidence. No guessed parcel-price joins."""
import json, re
from pathlib import Path
from .budget_rules import fold
from .paths import DATA_ROOT as ROOT
DATA=ROOT/'outputs/afternoon-import-20261125'
def load(name):return json.loads((DATA/name).read_text(encoding='utf-8'))
MANIFEST=load('manifest.json')
RECORDS=load('parcel-records.json')
PROJECT_CANDIDATES=load('project-candidates.json')
ROAD={r['id']:r for r in json.loads((ROOT/'outputs/hoa-xuan-road-prices-20261124/cell-reference-estimates.json').read_text(encoding='utf-8'))}
def money(n):return f'{n/1e9:,.2f}'.replace(',','_').replace('.',',').replace('_','.')+' tỷ'
def ring_area(r):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(r,r[1:])))
def parcel_row(r):
    return dict(r, importedParcel=True, computedAreaSqm=r['areaSqm'], displayName=f"Tờ {r['sheet']} · Thửa {r['parcel']}",
        planningLabel=r['landLabel'],planningCode='QHDVO' if r['purposeGroup']=='housing' else 'QHNN',
        planningCategory='RESIDENTIAL_PLANNING' if r['purposeGroup']=='housing' else 'AGRICULTURAL_PLANNING',
        planningEvidence=[],runtimeEligible=not r['reviewFlags'],demoPriceVnd=None,searchPriceVnd=r.get('priceVnd'),
        priceDescription=('Giá chào theo tin: '+money(r['priceVnd'])) if r.get('priceVnd') else 'Chưa có giá',
        addressEvidence={'location':('Khu vực '+r['road']+', ' if r.get('road') else '')+'Hòa Xuân, Đà Nẵng'},
        recoveryStatus='UNKNOWN',compensationStatus='UNKNOWN',disputeStatus='UNKNOWN',floodEvidence=None,
        geometryClass='SOURCE_REPORTED_PARCEL_NOT_OWNERSHIP_VERIFIED')
SOURCE_ROWS={r['id']:parcel_row(r) for r in RECORDS if r['purposeGroup'] in ('housing','agriculture') and not r['reviewFlags'] and r['areaSqm']>0 and ring_area(r['geometry']['coordinates'][0])>1e-14}
def candidate_row(x):
    return dict(x,unlocatedProjectLot=True,mapPositionAvailable=False,displayName=x['block']+' · Lô '+', '.join(map(str,x['lotNumbers'])),
        computedAreaSqm=x['areaSqm'],referencePriceVnd=x['askingPriceVnd'],searchPriceVnd=x['askingPriceVnd'],demoPriceVnd=None,
        priceDescription=money(x['askingPriceVnd'])+(' (giá chào cũ '+x['sourceDate']+')' if x.get('sourceDate') else ' (giá chào nguồn; chưa rõ ngày)') if x['askingPriceVnd'] else 'Chưa có giá',
        addressEvidence={'location':'Euro Village 2 · Đảo Triệu Phú, Hòa Xuân, Đà Nẵng; chưa định vị riêng từng lô'})
EXTRAS={x['id']:candidate_row(x) for x in PROJECT_CANDIDATES}
def enrich(row):
    out=dict(row); ref=ROAD.get(row['id'])
    if ref:
        out.update(roadPriceEvidence=ref,searchPriceVnd=ref['estimatedReferenceVnd'],
            priceDescription=money(ref['estimatedReferenceVnd'])+' (ước tính theo đường; giá rao tham khảo)',
            effectivePriceClass='PRELIMINARY_NEARBY_ROAD_ESTIMATE')
    elif row.get('demoPriceVnd') is not None:out['searchPriceVnd']=row['demoPriceVnd']
    return out
def value(row):return row.get('searchPriceVnd',row.get('referencePriceVnd',row.get('demoPriceVnd')))
def profile(row):
    lines=[row['displayName'],'Vị trí: '+row['addressEvidence']['location'],f"Diện tích: {row['computedAreaSqm']:g} m²",'Giá: '+row['priceDescription']]
    if row.get('importedParcel'):
        lines+=['Loại đất: '+row['landLabel'],'Sổ hồng theo tin: '+row.get('bookTypeSourceReported','chưa có thông tin'),
            'Giấy tờ chính chủ, tranh chấp, thu hồi/giải tỏa: chưa xác minh',
            'Quy hoạch theo nguồn: '+(row.get('planningText') or 'Chưa có thông tin áp dụng cho thửa này'),
            'Ô quy hoạch tham chiếu: '+(', '.join(row.get('planningCandidates',[])) or 'chưa nối được'),
            'Nguồn: '+row['sourceUrl']]
    else:lines+=['Chưa khớp tọa độ/đường bao; không gán vào ô gần đó.','Ngày giá và tình trạng đang bán: chưa xác minh.','Nguồn: '+row['sourceUrl']]
    return '\n'.join(lines)
def selection(q,state,ordinals=None):
    n=fold(q);selected=None
    follow=state.get('lastDomain')=='imported' and bool(re.fullmatch(r'(?:xem |con |lo |thua |nao |hay |khong |nua |khac |tiep|them|\?)+',n))
    if ('guland' in n or 'danh sach thua' in n or follow) and not re.search(r'\b(to|thua)\s+\d+',n) and not re.search(r'\b(ty|trieu)\b',n):
        offset=state.get('importOffset',0)+5 if follow else 0
        rows=list(SOURCE_ROWS.values());page=rows[offset:offset+5]
        state.update(lastDomain='imported',importOffset=offset,seen=[r['id'] for r in rows[:offset+len(page)]],selected=page[0]['id'] if page else None)
        return {'answer':f'Tìm thấy {len(rows)} hồ sơ thửa đủ điều kiện từ nguồn Guland. Hiển thị {offset+1}–{offset+len(page)}. Chưa xác nhận đang bán; diện tích theo nguồn.', 'rows':page,'start':offset+1,'total':len(rows)}
    for rid in [*SOURCE_ROWS,*EXTRAS]:
        if rid.lower() in n:selected=rid;break
    if not selected and ordinals and 'so sanh' not in n:
        i=ordinals[0]
        if 1<=i<=len(state.get('seen',[])):selected=state['seen'][i-1]
    if not selected and re.search(r'\b(lo|o|thua)(?: dat)?\s+(nay|do)\b',n):selected=state.get('selected')
    row=SOURCE_ROWS.get(selected) or EXTRAS.get(selected)
    if row:
        state['selected']=selected
        return {'answer':profile(row),'rows':[row],'selected':True,'start':1}
    # Exact sheet/parcel lookup remains separate from ordinal lot numbering.
    sheet=re.search(r'\bto\s+(\d+)\b',n);parcel=re.search(r'\bthua\s+(\d+)\b',n)
    if sheet and parcel:
        results=[r for r in SOURCE_ROWS.values() if r['sheet']==int(sheet[1]) and r['parcel']==int(parcel[1])]
        state.update(seen=[r['id'] for r in results],selected=results[0]['id'] if results else None)
        return {'answer':profile(results[0]) if results else 'Chưa có hồ sơ đủ điều kiện cho tờ/thửa này. Bản ghi mâu thuẫn được giữ trong mục chờ đối chiếu.','rows':results,'start':1}
    return None
def stats():
    return {**MANIFEST,'searchableSourceParcels':len(SOURCE_ROWS),'searchableSourceAskingPrices':sum(value(r) is not None for r in SOURCE_ROWS.values()),
        'projectCandidatesLocated':0,'roadPriceMeaning':'ESTIMATE_FROM_NEARBY_ROAD_NOT_VERIFIED_FRONTAGE'}
