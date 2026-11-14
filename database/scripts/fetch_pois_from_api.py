"""Fetch live Points of Interest (POIs) across Da Nang from Geoapify Places API.
Inserts into MySQL table points_of_interest with SRID 4326.
"""
import re
import sys
import time
import uuid
from pathlib import Path
import pymysql
import requests

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[2]
env_vars = {}
env_file = ROOT / '.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8-sig').splitlines():
        m = re.match(r'^\s*(?:export\s+)?([A-Za-z0-9_]+)\s*=\s*(.*)$', line)
        if m:
            env_vars[m.group(1)] = m.group(2).strip().strip('"\'')

api_key = env_vars.get('GEOAPIFY_API_KEY')
if not api_key:
    print("ERROR: GEOAPIFY_API_KEY not found in .env")
    sys.exit(1)

# District centers across Da Nang
CENTERS = [
    ('Sơn Trà', 16.0820, 108.2440),
    ('Hải Châu', 16.0600, 108.2200),
    ('Thanh Khê', 16.0650, 108.1950),
    ('Ngũ Hành Sơn', 16.0350, 108.2430),
    ('Cẩm Lệ', 16.0250, 108.2100),
    ('Liên Chiểu', 16.0650, 108.1550),
]

CATEGORY_MAPPING = {
    'education': 'SCHOOL',
    'healthcare': 'HOSPITAL',
    'leisure.park': 'PARK',
    'commercial.supermarket': 'SUPERMARKET',
    'commercial.shopping_mall': 'SUPERMARKET',
    'public_transport': 'TRANSPORT',
}

def run():
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user=env_vars.get('DB_USER', 'root'),
        password=env_vars.get('DB_PASSWORD', ''),
        database='smartprop',
        autocommit=True
    )

    total_added = 0
    total_skipped = 0

    print("Connecting to Geoapify Places API to fetch live Da Nang POIs...")

    with conn.cursor() as cur:
        for center_name, lat, lon in CENTERS:
            print(f"\n--- Scanning area: {center_name} ({lat:.4f}, {lon:.4f}) ---")
            for api_cat, db_cat in CATEGORY_MAPPING.items():
                url = (
                    f"https://api.geoapify.com/v2/places"
                    f"?categories={api_cat}"
                    f"&filter=circle:{lon:.5f},{lat:.5f},4500"
                    f"&limit=40"
                    f"&apiKey={api_key}"
                )
                try:
                    res = requests.get(url, timeout=12)
                    if res.status_code != 200:
                        print(f"  Warning: {api_cat} returned HTTP {res.status_code}")
                        continue

                    data = res.json()
                    features = data.get('features', [])
                    cat_added = 0

                    for f in features:
                        props = f.get('properties', {})
                        name = props.get('name')
                        if not name or len(name.strip()) < 2:
                            total_skipped += 1
                            continue

                        name = name.strip()[:250]
                        p_lat = props.get('lat')
                        p_lon = props.get('lon')
                        place_id = props.get('place_id') or str(uuid.uuid4())

                        if not (p_lat and p_lon):
                            continue

                        poi_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"geoapify.place.{place_id}"))
                        point_wkt = f"POINT({p_lon:.6f} {p_lat:.6f})"

                        cur.execute("""
                            INSERT INTO points_of_interest (
                                id, name, category, location, source_name, external_id, source_url, observed_at
                            ) VALUES (
                                %s, %s, %s, ST_GeomFromText(%s, 4326, 'axis-order=long-lat'), %s, %s, %s, UTC_TIMESTAMP(6)
                            )
                            ON DUPLICATE KEY UPDATE
                                name = VALUES(name),
                                category = VALUES(category),
                                location = VALUES(location),
                                observed_at = VALUES(observed_at);
                        """, (
                            poi_id,
                            name,
                            db_cat,
                            point_wkt,
                            'geoapify_places_api',
                            place_id[:250],
                            f"https://www.geoapify.com/place/{place_id[:100]}"
                        ))
                        cat_added += 1

                    total_added += cat_added
                    print(f"  [{db_cat}] Fetched {cat_added} places from API")
                    time.sleep(0.15) # avoid rate limit

                except Exception as e:
                    print(f"  Error fetching {api_cat}: {e}")

        cur.execute("SELECT count(*) FROM points_of_interest WHERE source_name = 'geoapify_places_api';")
        api_pois = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM points_of_interest;")
        total_pois = cur.fetchone()[0]

        print("\n==========================================")
        print(f"SUCCESS: Synced live POIs from Geoapify API!")
        print(f"Total API POIs in database: {api_pois}")
        print(f"Total combined POIs in database: {total_pois}")
        print("==========================================")

if __name__ == '__main__':
    run()
