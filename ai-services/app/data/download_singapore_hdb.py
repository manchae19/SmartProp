"""Download official HDB snapshot and Vietcombank FX; retain provenance."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
import requests

BASE = Path(__file__).resolve().parent / 'data_raw/singapore_hdb'
DATASET = 'd_8b84c4ee58e3cfc0ece0d773c8ca6abc'
API = f'https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET}'
FX = 'https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx'

def main():
    BASE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers['User-Agent'] = 'SmartPropResearch/0.1'
    path = BASE / 'resale_flat_prices.csv'
    if not path.exists():
        response = session.get(API + '/initiate-download', timeout=60)
        response.raise_for_status()
        for _ in range(6):
            time.sleep(15)  # Public API limit: five requests/minute.
            response = session.get(API + '/poll-download', timeout=60)
            response.raise_for_status()
            data = response.json()['data']
            if data.get('url'):
                response = session.get(data['url'], timeout=180)
                response.raise_for_status()
                temporary = path.with_suffix('.part')
                temporary.write_bytes(response.content)
                temporary.replace(path)
                break
        else:
            raise RuntimeError('HDB download was not ready; rerun later.')
    response = session.get(FX, timeout=60)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    rates = next(x.attrib for x in root.iter('Exrate') if x.get('CurrencyCode') == 'SGD')
    buying = float(rates['Transfer'].replace(',', ''))
    selling = float(rates['Sell'].replace(',', ''))
    (BASE / 'vietcombank_fx.xml').write_bytes(response.content)
    metadata = dict(dataset_id=DATASET,
        source=f'https://data.gov.sg/datasets/{DATASET}/view',
        retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
        raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        fx_source=FX, fx_date=root.findtext('DateTime'), fx_rates=rates,
        vnd_per_sgd=(buying + selling)/2,
        fx_method='midpoint of Vietcombank telegraphic buying and selling, snapshot conversion, not historical monthly FX')
    (BASE / 'provenance.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(metadata, indent=2))

if __name__ == '__main__':
    main()
