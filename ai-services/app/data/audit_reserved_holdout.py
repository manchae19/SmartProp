"""Audit reserved IDs via projected metadata; do not inspect targets or score."""
import csv
import hashlib
import json
import re
import uuid
from collections import Counter,defaultdict,deque
from pathlib import Path
import training_v3_common as c

OUT=c.PROCESSED/'reserved_holdout_audit'
FIELDS=['record_key','source','category','model_split','split','pipeline_group','duplicate_candidate_group',
        'current_group','left','right','other_record_key','group_blocking_ids']
GROUP_FIELDS=['pipeline_group','duplicate_candidate_group','current_group']
VN_KEY=re.compile(r'(?:cafeland|nhadat24h|homedy|chotot|alonhadat):\d+')
POLICY=dict(projected_columns=FIELDS,targets_inspected=False,predictions_computed=False,
    direct_exposure='Any saved prediction or train/validation input; prepared inputs excluded conservatively',
    indirect_exposure='Transitive known historical group/duplicate links to an exposed ID',
    candidate_meaning='No model-use evidence found in inventoried local artifacts; not certified new or independently verified assets',
    selection='All reserved representatives without direct or transitive exposure; no price/residual sampling')


def latest(root):return root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']


def projected(path):
    """Read CSV records only through an allowlist, never retaining target columns."""
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        fields=[k for k in FIELDS if k in (reader.fieldnames or [])]
        return fields,[{k:r.get(k,'') for k in fields} for r in reader] if fields else []


def activity(row,name,fit_categories=None):
    if not row.get('record_key'):return ''
    if 'predictions' in name:return 'saved_prediction'
    if name=='train.csv':return 'train_input'
    if name=='validation.csv':return 'validation_input'
    if name=='baseline_inputs.csv' and (fit_categories is None or row.get('category') in fit_categories):
        split=row.get('model_split')
        return 'baseline_train_input' if split=='train' else 'baseline_validation_input' if split=='validation' else ''
    # Test assignment alone does not prove test evaluation.
    return ''


def graph_and_events(catalog):
    graph=defaultdict(dict);events=[]
    def link(left,right,reason,path):
        if left and right and left!=right:
            proof=dict(left=left,right=right,reason=reason,history_file=path)
            graph[left].setdefault(right,proof);graph[right].setdefault(left,proof)
    for item in catalog:
        path=item['path'];groups=defaultdict(set)
        for row in item['rows']:
            key=row.get('record_key','')
            if key:
                for field in GROUP_FIELDS:
                    if row.get(field):groups[(field,row[field])].add(key)
                role=activity(row,Path(path).name,item.get('fit_categories'))
                if role:events.append(dict(record_key=key,role=role,history_file=path))
                link(key,row.get('other_record_key',''),'saved_cross_group_content_candidate',path)
                for other in VN_KEY.findall(row.get('group_blocking_ids','')):link(key,other,'saved_group_blocking_id',path)
            link(row.get('left',''),row.get('right',''),'saved_possible_duplicate_pair',path)
        for (field,value),keys in groups.items():
            keys=sorted(keys)
            for key in keys[1:]:link(keys[0],key,'shared_'+field,path)
    unique={(r['record_key'],r['role'],r['history_file']):r for r in events}
    return graph,list(unique.values())


def components(graph,keys):
    membership={};members={}
    for start in sorted(set(keys)|set(graph)):
        if start in membership:continue
        todo=[start];found=set()
        while todo:
            key=todo.pop()
            if key in found:continue
            found.add(key);todo.extend(set(graph.get(key,{}))-found)
        component=min(found)
        members[component]=found
        for key in found:membership[key]=component
    return membership,members


def evidence_path(graph,start,end):
    queue=deque([start]);before={start:None}
    while queue:
        key=queue.popleft()
        if key==end:break
        for other in sorted(graph.get(key,{})):
            if other not in before:before[other]=key;queue.append(other)
    if end not in before:raise ValueError('Missing claimed exposure path')
    result=[];key=end
    while before[key] is not None:
        parent=before[key];result.append(graph[parent][key]);key=parent
    return list(reversed(result))


def main():
    data=latest(c.PROCESSED/'property_features_v6')
    model=latest(c.PROCESSED/'models_v6_ablation')
    reserved=c.read(data/'reserved_holdout_registry.csv')
    assert len(reserved)==len({r['record_key'] for r in reserved})==684
    assert not {'price_million','area_sqm','title'}&set(reserved[0])
    registry_ids={r['record_key'] for r in reserved}
    original_manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    model_manifest=json.loads((model/'manifest.json').read_text(encoding='utf-8'))
    c.verify(original_manifest['output_sha256'],data);c.verify(model_manifest['output_sha256'],model)
    selection=json.loads((model/'selection.json').read_text(encoding='utf-8'))
    source=c.BASE/json.loads((data/'summary.json').read_text(encoding='utf-8'))['dataset_run']
    protected={}
    for root in [data,model,source]+[latest(c.PROCESSED/f'models_{v}_validation') for v in ['v3','v4','v5']]:
        m=json.loads((root/'manifest.json').read_text(encoding='utf-8'));c.verify(m['output_sha256'],root)
        protected.update({(root/p).relative_to(c.BASE).as_posix():sha for p,sha in m['output_sha256'].items()})
        protected[(root/'manifest.json').relative_to(c.BASE).as_posix()]=c.sha(root/'manifest.json')
    csv_paths=sorted(p for p in c.PROCESSED.rglob('*.csv') if OUT not in p.parents)
    catalog=[];inventory=[]
    inputs={Path(__file__).relative_to(c.BASE).as_posix():c.sha(Path(__file__)),
            Path(c.__file__).relative_to(c.BASE).as_posix():c.sha(Path(c.__file__))}
    for index,path in enumerate(csv_paths,1):
        fields,rows=projected(path);relative=path.relative_to(c.BASE).as_posix()
        inputs[relative]=c.sha(path)
        fit_categories=None
        if path.name=='baseline_inputs.csv' and (path.parent/'baseline_metrics.json').exists():
            metric_path=path.parent/'baseline_metrics.json'
            metrics=json.loads(metric_path.read_text(encoding='utf-8'))
            # Inspect only execution status/input digest, never error values.
            if metrics.get('input_sha256')!=inputs[relative]:raise ValueError('Baseline input snapshot changed')
            fit_categories={category for category,info in metrics['categories'].items() if info.get('status')!='insufficient_data'}
            inputs[metric_path.relative_to(c.BASE).as_posix()]=c.sha(metric_path)
        catalog.append(dict(path=relative,rows=rows,fit_categories=fit_categories))
        inventory.append(dict(path=relative,sha256=inputs[relative],projected_columns=';'.join(fields),metadata_rows=len(rows),
                              activity_file=bool('predictions' in path.name or path.name in ['train.csv','validation.csv','baseline_inputs.csv'])))
        if index%60==0:print(f'History metadata: {index}/{len(csv_paths)} CSV',flush=True)
    for path in [data/'manifest.json',model/'manifest.json',model/'selection.json',c.BASE/'property_text_features_v6.py']:
        inputs[path.relative_to(c.BASE).as_posix()]=c.sha(path)
    graph,events=graph_and_events(catalog)
    membership,members=components(graph,registry_ids|{r['record_key'] for r in events})
    events_bykey=defaultdict(list)
    for event in events:events_bykey[event['record_key']].append(event)
    exposed=defaultdict(set)
    for key in events_bykey:exposed[membership[key]].add(key)
    audit,links=[],[]
    for r in reserved:
        key=r['record_key'];component=membership[key]
        direct=events_bykey.get(key,[])
        related=exposed.get(component,set())
        status='direct_used_or_prepared' if direct else 'historical_group_related' if related else 'no_usage_evidence'
        witness=key if direct else min(related) if related else ''
        audit.append(dict(r,history_component=component,history_component_size=len(members[component]),
            audit_status=status,direct_roles=';'.join(sorted({e['role'] for e in direct})),
            direct_history_files=len({e['history_file'] for e in direct}),exposed_witness_key=witness,
            witness_history_file=events_bykey[witness][0]['history_file'] if witness else '',
            independent_test_certified=False,price_or_error_used_for_selection=False))
        if witness and witness!=key:
            for edge in evidence_path(graph,key,witness):links.append(dict(reserved_record_key=key,exposed_witness_key=witness,**edge))
    candidates=[r for r in audit if r['audit_status']=='no_usage_evidence']
    components_reserved={membership[k] for k in registry_ids}
    relevant_events=[e for e in events if membership[e['record_key']] in components_reserved]
    fingerprint=hashlib.sha256(json.dumps(dict(inputs=inputs,policy=POLICY),sort_keys=True).encode()).hexdigest()[:16]
    target=OUT/'runs'/fingerprint
    if target.exists():
        m=json.loads((target/'manifest.json').read_text(encoding='utf-8'));c.verify(m['output_sha256'],target)
        publish(target);print('Existing audit verified: '+str(target));return
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
    c.write_csv(stage/'reserved_id_audit.csv',audit,list(audit[0]))
    c.write_csv(stage/'candidate_registry.csv',candidates,list(audit[0]))
    c.write_csv(stage/'usage_evidence.csv',relevant_events,['record_key','role','history_file'])
    c.write_csv(stage/'group_exposure_paths.csv',links,['reserved_record_key','exposed_witness_key','left','right','reason','history_file'])
    c.write_csv(stage/'history_inventory.csv',inventory,list(inventory[0]))
    # Save metadata-only protocol before any candidate label inspection/scoring.
    protocol=dict(model_run=model.relative_to(c.BASE).as_posix(),model_manifest_sha256=c.sha(model/'manifest.json'),
        model_selection_sha256=c.sha(model/'selection.json'),selected_arm=selection['best_global_arm'],
        feature_extractor_sha256=c.sha(c.BASE/'property_text_features_v6.py'),
        candidate_registry_sha256=c.sha(stage/'candidate_registry.csv'),candidate_ids=len(candidates),
        intended_kind='archival_holdout_pilot_not_prospective_or_independently_verified_transactions',
        selection_rule=POLICY['selection'],metrics=['MAE_million_VND','MAPE_pct','within_20pct','category_and_price_band_metrics'],
        rules=['Keep frozen model, schemas and text extractor; do not fit vocabularies on candidates.',
               'Check remaining duplicate/source-scope concerns using preset source rules before calling this an independent test.',
               'Evaluate once and retain all included outcomes; do not retune on this pilot.',
               'No automatic pass/fail or application deployment; no fresh-market claim.'],
        labels_inspected_in_audit=False,actually_scored=0,automatic_deployment=False)
    c.write_json(stage/'locked_candidate_protocol.json',protocol)
    summary=dict(reserved_ids=684,classification=dict(Counter(r['audit_status'] for r in audit)),
        candidate_ids=len(candidates),candidate_components=len({r['history_component'] for r in candidates}),
        candidate_by_category=dict(Counter(r['category'] for r in candidates)),candidate_by_source=dict(Counter(r['source'] for r in candidates)),
        csv_files_inventoried=len(inventory),metadata_files_projected=sum(bool(r['projected_columns']) for r in inventory),
        group_exposure_path_edges=len(links),relevant_usage_events=len(relevant_events),
        policy=POLICY,model_run=protocol['model_run'],features_run=data.relative_to(c.BASE).as_posix(),
        independent_test_certified=False,test_evaluated=False,new_network_requests=0,models_modified=False)
    c.write_json(stage/'summary.json',summary)
    (stage/'README.md').write_text('\n'.join([
        '# Kiểm tra lịch sử 684 tin dự phòng','',
        '| Kết quả | Số ID |','|---|---:|',
        *[f'| {k} | {v} |' for k,v in summary['classification'].items()],
        '',f'Có **{len(candidates)} ứng viên**, **{summary["candidate_components"]} nhóm lịch sử riêng biệt**: '
        f'`{summary["candidate_by_category"]}`. Chưa tìm thấy dấu vết dùng trực tiếp hoặc liên kết với ID đã dùng '
        'trong các artifact cục bộ đã kiểm kê. Đây không phải chứng nhận tài sản mới/test độc lập hoặc chưa ai từng xem nhãn.','',
        'Train/validation đầu vào được loại bảo thủ kể cả đầu vào đã chuẩn bị nhưng chưa chứng minh fit. '
        'Một ID chỉ nằm trong test.csv không tự bị coi đã chấm; cần dấu vết dự đoán. Các baseline có trạng thái '
        'insufficient_data không tự tính là đã fit. ID khác trong cùng nhóm/cặp nghi trùng đã lưu cũng bị chặn.','',
        f'Đã kiểm kê {len(inventory)} CSV lịch sử, chỉ giữ các cột metadata allowlist. '
        'Không phân tích giá/diện tích, không tính dự đoán, không gọi mạng, không sửa train/validation/model/reservation. '
        'Hash toàn file dùng để kiểm tra integrity, không dùng nhãn cho lựa chọn.','',
        'Các liên kết nghi trùng là heuristic, không phải xác minh tài sản vật lý. Chưa kiểm tra tất cả trùng ẩn bằng nội dung/địa chỉ '
        'ngoài các liên kết đã lưu; chưa kiểm chứng giao dịch hoặc khả năng dự đoán ở thời điểm tương lai. '
        'Dữ liệu đã qua lọc chất lượng chung trên toàn collection, nên không phải đợt cào mới độc lập.','',
        '## Bước tiếp theo','',
        'Dùng danh sách ứng viên để kiểm tra trùng/loại tài sản theo quy tắc cố định, rồi chấm một lần v6 đã khóa '
        'nếu phù hợp. Không chuyển các tin từng dùng hoặc nhóm liên quan vào test mới. '
        'Nhóm căn hộ chỉ có 8 tin, kết quả sẽ thiếu ổn định; nếu cần kết luận riêng về căn hộ, bổ sung đợt kiểm chứng mới có mục tiêu. '
        'Chưa cần cào đại trà chỉ để tăng train.','',
        '[684 kết luận theo ID](reserved_id_audit.csv), [ứng viên không có dấu vết](candidate_registry.csv), '
        '[bằng chứng sử dụng](usage_evidence.csv), [đường liên kết tới ID đã dùng](group_exposure_paths.csv), '
        '[kiểm kê lịch sử](history_inventory.csv), [giao thức ứng viên khóa với v6](locked_candidate_protocol.json), '
        '[số liệu](summary.json). Tất cả file xuất trong đợt này không chứa giá hoặc dự đoán của ứng viên.','']),encoding='utf-8')
    c.verify(inputs);c.verify(protected)
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=protected,output_sha256=c.outputs(stage)))
    stage.rename(target);publish(target)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True);print(target,flush=True)


def publish(target):
    c.write_json(OUT/'latest.json',dict(run=target.relative_to(OUT).as_posix()))
    (OUT/'README.md').write_text('# Lịch sử dữ liệu dự phòng\n\n'
        f'[Báo cáo hiện tại]({target.relative_to(OUT).as_posix()}/README.md).\n',encoding='utf-8')


if __name__=='__main__':main()
