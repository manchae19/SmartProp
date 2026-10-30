"""Export explicit HTML links so CSV delimiters cannot become part of URLs."""
import argparse
import csv
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlparse


def export(directory):
    sections = []
    total = 0
    for filename, label in [
        ('cafeland_listings.csv', 'Tin đã lấy trang chi tiết'),
        ('cafeland_scope_review.csv', 'Tin cần rà soát địa bàn'),
    ]:
        path = directory / filename
        if not path.exists():
            continue
        with path.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        items = []
        for row in rows:
            url = row['detail_url']
            parsed = urlparse(url)
            if (parsed.scheme != 'https' or parsed.netloc != 'nhadat.cafeland.vn'
                    or not parsed.path.endswith('-' + row['source_listing_id'] + '.html')
                    or parsed.query or parsed.fragment):
                raise ValueError('Unexpected URL for ' + row['source_listing_id'])
            items.append('<li><a target="_blank" rel="noopener noreferrer" href="'
                         + escape(url, quote=True) + '">' + escape(row['title'])
                         + '</a> — ID ' + escape(row['source_listing_id']) + '</li>')
        total += len(items)
        sections.append('<h2>' + label + ' (' + str(len(items)) + ')</h2><ol>'
                        + '\n'.join(items) + '</ol>')
    document = '''<!doctype html>
<html lang="vi"><meta charset="utf-8"><title>Danh sách link CafeLand</title>
<style>body{font:16px/1.6 system-ui;max-width:1000px;margin:32px auto;padding:0 20px}
li{margin:10px 0}a{overflow-wrap:anywhere}</style>
<h1>Danh sách link CafeLand</h1>
<p>Bấm vào tiêu đề để mở URL trong CSV. Danh sách này không kiểm tra tình trạng
còn hiển thị của tin trên CafeLand. Chạy lại script xuất link để cập nhật danh sách.</p>
'''
    document += '<p>Thời điểm xuất (UTC): ' + datetime.now(timezone.utc).isoformat() + '</p>'
    document += '\n'.join(sections) + '</html>'
    output = directory / 'cafeland_links.html'
    output.write_text(document, encoding='utf-8')
    print(f'Exported {total} links: {output.resolve()}')
    return output, total


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    export(args.output_dir)
