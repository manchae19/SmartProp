"""Extract identity-checked evidence for the 87 queued train/validation listings."""
import hashlib
import json
from collections import Counter
from audit_all_collected import BASE, read, save_csv
import review_apartment_labels as parser

OUT=BASE/'processed/training_source_review'


def main():
    paths=[BASE/'processed/training_v1/main_dataset.csv',
           BASE/'processed/xgboost_validation_review/train_source_check_queue.csv',
           BASE/'processed/xgboost_validation_review/validation_source_check_queue.csv']
    rows={r['record_key']:r for r in read(paths[0])}
    queue=read(paths[1])+read(paths[2])
    meta=json.loads((OUT/'fetch_manifest.json').read_text(encoding='utf-8'))
    parser.OUT=OUT
    evidence=[]
    for q in queue:
        key=q['record_key'];r=rows[key];m=meta.get(key)
        if m:
            current,flags=parser.detail(r,m)
        else:
            current,flags={'state':'not_fetched'},['not_fetched']
        evidence.append(dict(record_key=key,source=r['source'],split=r['model_split'],category=r['category'],
            title=r['title'],detail_url=r['detail_url'],duplicate_candidate_group=r['duplicate_candidate_group'],
            original_price_million=r['price_million'],original_area_sqm=r['area_sqm'],
            original_review_codes=q['review_codes'],detail_state=current['state'],detail_flags=';'.join(flags),
            detail_price_million=current.get('price_million'),detail_area_sqm=current.get('area_sqm'),
            detail_title=current.get('title',''),description=current.get('description',''),
            detail_sha256=m['sha256'] if m else '',fetched_at_utc=m['fetched_at_utc'] if m else '',
            http_status=m['http_status'] if m else '',response_url=m['response_url'] if m else ''))
    save_csv(OUT/'source_evidence.csv',evidence,list(evidence[0]))
    (OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'evidence_input_hashes.json').write_text(json.dumps({p.relative_to(BASE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2),encoding='utf-8')
    print(json.dumps(dict(total=len(evidence),states=dict(Counter(r['detail_state'] for r in evidence))),ensure_ascii=False))


if __name__=='__main__':main()
