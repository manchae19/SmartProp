"""Audit saved CafeLand CSVs without network requests."""
import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DISTRICTS = {'Hải Châu', 'Thanh Khê', 'Sơn Trà', 'Ngũ Hành Sơn',
             'Liên Chiểu', 'Cẩm Lệ', 'Hòa Vang'}


def audit(directory):
    def read(name):
        path = directory / name
        if not path.exists():
            return []
        with path.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError(f'Malformed CSV: {path}')
        return rows

    accepted = read('cafeland_listings.csv')
    review = read('cafeland_scope_review.csv')
    ids = Counter(row['source_listing_id'] for row in accepted + review)
    errors = []
    for row in accepted:
        ident = row['source_listing_id']
        if (not ident.isdigit() or row['list_id'] != 'cafeland:' + ident
                or not row['detail_url'].endswith('-' + ident + '.html')
                or row['source'] != 'cafeland'
                or row['district'] not in DISTRICTS
                or row['transaction_type'] != 'Bán'
                or row['detail_fetched'] != 'True'
                or row['location_status'] != 'in_scope'):
            errors.append(ident)
    report = {
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'accepted_count': len(accepted),
        'scope_review_count': len(review),
        'duplicate_ids': [ident for ident, count in ids.items() if count > 1],
        'invalid_accepted_ids': errors,
        'districts': dict(Counter(row['district'] for row in accepted)),
        'needs_review_count': sum(any(row[k] == 'True' for k in
            ['category_needs_review', 'price_needs_review', 'area_needs_review'])
            or bool(row['review_reason']) for row in accepted),
        'checkpoint': json.loads((directory / 'checkpoint.json').read_text(encoding='utf-8')),
    }
    (directory / 'quality_summary.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.output_dir)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(1 if result['duplicate_ids'] or result['invalid_accepted_ids'] else 0)
