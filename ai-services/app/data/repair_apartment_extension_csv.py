"""Recover an unreviewed extension CSV from verified durable log and cache."""
import hashlib
import os
from pathlib import Path
import collect_apartment_extension as collector


def repair(output=collector.OUT,review_root=None):
    output=Path(output)
    if review_root is None:review_root=collector.source.BASE/'processed/apartment_extension_review'
    if (Path(review_root)/'latest.json').exists():raise ValueError('Cohort already locked; do not modify its source CSV')
    lock=output/'collector.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        rows=collector.load_rows(output)
        if not rows or len(rows)!=len({r['record_key'] for r in rows}):raise ValueError('Empty/duplicate durable log')
        for row in rows:
            path=(output/row['detail_file']).resolve()
            if path!=output.resolve()/'detail_cache'/(row['source_listing_id']+'.html'):raise ValueError('Unexpected cache path')
            body=path.read_bytes()
            if hashlib.sha256(body).hexdigest()!=row['response_sha256'] or collector.source.parse_detail(body,row,row['collected_at'])!=row:
                raise ValueError('Cache replay differs')
        collector.source.export_csv(output/'apartment_records.csv',rows)
        print('CSV recovered from verified durable records: '+str(len(rows)))
    finally:lock.unlink()


if __name__=='__main__':repair()
