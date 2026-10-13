"""Read-only dataset checks; write a separate audit report, not collection history."""
import csv
import json
from collections import Counter
from pathlib import Path
from collect_chotot_incremental import ROOT, read_existing, now, atomic_json

def main():
    out = ROOT/'data_raw'/'chotot_incremental'
    ids, inventory = read_existing(sorted(ROOT.glob('danang_chotot*.csv')))
    rows = [json.loads(line) for line in (out/'records.jsonl').read_text(encoding='utf-8').splitlines()]
    with (out/'records.csv').open(encoding='utf-8-sig', newline='') as f:
        exported = list(csv.DictReader(f))
    new_ids = [r['source_listing_id'] for r in rows]
    assert len(new_ids) == len(set(new_ids)), 'Duplicate incremental IDs'
    assert new_ids == [r['source_listing_id'] for r in exported], 'CSV/JSONL mismatch'
    overlap = sorted(set(new_ids) & ids)
    assert not overlap, 'Incremental records overlap with legacy IDs'
    report = dict(checked_at=now(), legacy_files=inventory, legacy_unique_ids=len(ids),
                  incremental_rows=len(rows), overlap_ids=overlap, total_unique_source_ids=len(ids|set(new_ids)),
                  quality_counts=dict(Counter(r['quality_status'] for r in rows)),
                  missing_toilets=sum(r['toilets'] is None for r in rows),
                  review_records=[{'id':r['source_listing_id'],'flags':r['review_flags']} for r in rows if r['review_flags']],
                  notes=['Legacy files cover mixed property categories; total is not a house-training sample count.',
                         'Source ID uniqueness does not prove unique physical properties.',
                         'Initial run log predates legacy detail_url ID support; this audit corrects its legacy inventory without rewriting history.'])
    atomic_json(out/'audit_report.json', report)
    print(json.dumps(report,ensure_ascii=True,indent=2))

if __name__=='__main__':
    main()
