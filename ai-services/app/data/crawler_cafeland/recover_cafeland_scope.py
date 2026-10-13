"""Fetch missing details for existing Hòa Tiến/Bà Nà cards; no new list crawling."""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from smartprop_geography import norm, resolve, REFERENCE
from crawl_cafeland_danang import Client, FIELDS, parse_detail, save_checkpoint


def historical_location(parts):
    district, basis, _ = resolve(', '.join(parts), source='cafeland')
    return district, 'in_scope' if district else 'review_or_outside_scope'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--max-new', type=int, default=100)
    args = parser.parse_args()
    out = args.input_dir
    target = out / 'cafeland_scope_recovered.csv'
    fields = FIELDS + ['recovery_location_basis', 'recovery_reference']
    seen = set()
    if target.exists():
        with target.open(encoding='utf-8-sig', newline='') as f:
            seen.update(r['source_listing_id'] for r in csv.DictReader(f))
    with (out / 'cafeland_scope_review.csv').open(encoding='utf-8-sig', newline='') as f:
        cards = [r for r in csv.DictReader(f)
                 if norm(r['address_raw'].split(',')[0]) in {'hoa tien', 'ba na'}]
    pending = [r for r in cards if r['source_listing_id'] not in seen]
    if not pending:
        print('All targeted cards already processed.')
        return
    client = Client(3)
    added = 0
    for card in pending:
        row = dict(card)
        district, basis, _ = resolve(row['address_raw'], source='cafeland')
        row.update(district=district, location_status='in_scope')
        body = client.fetch(row['detail_url'])
        try:
            row = parse_detail(body, row, historical_location)
        except Exception:
            (out / 'debug_scope_recovery.html').write_bytes(body)
            raise
        row.update(collected_at=datetime.now(timezone.utc).isoformat(),
                   recovery_location_basis=basis, recovery_reference=REFERENCE)
        new = not target.exists()
        with target.open('a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            if new:
                writer.writeheader()
            writer.writerow(row)
        seen.add(row['source_listing_id'])
        added += 1
        save_checkpoint(out / 'scope_recovery_checkpoint.json', {
            'version': 1, 'saved_count': len(seen), 'target_count': len(cards),
            'last_saved_id': row['source_listing_id'], 'finished': len(seen) == len(cards)})
        print(f'Saved {row["list_id"]}: {added} new, {len(seen)}/{len(cards)} total', flush=True)
        if added >= args.max_new:
            break


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Stopped. Run again to skip saved IDs and resume.', flush=True)
        raise SystemExit(130)
