"""Import Da Nang points of interest from the Geoapify Places API into `points_of_interest`.

The chatbot's property cards and the listing map read nearby amenities from this table
(`/api/v1/properties/{id}/points-of-interest`). It is data, not schema, so a fresh clone or
a restored backup has it empty until this script is run against that database.

Safety rules:
* The target database is explicit (--host/--port/--database). Port 3306 (the real
  schema) is refused unless --allow-production is given.
* Only loopback hosts are accepted.
* The API key is never printed, logged or written to the cache.
* Every row keeps its provenance: source_name `geoapify_places_api`, the Geoapify
  place_id as external_id, and, when Geoapify reports it, the real OpenStreetMap object
  URL as source_url. No URL is invented.

Usage (copy database):
    python database/scripts/fetch_pois_from_api.py --port 13425 --database smartprop_copy \
        --credentials-json path/to/runtime.local.json
    python database/scripts/fetch_pois_from_api.py ... --dry-run      # fetch and count only
    python database/scripts/fetch_pois_from_api.py ... --from-cache   # reuse saved responses
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = ROOT / ".scratch" / "poi-geoapify"
SOURCE_NAME = "geoapify_places_api"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}

# Urban Da Nang (Hai Chau, Thanh Khe, Son Tra, Ngu Hanh Son, Cam Le, Lien Chieu), split
# into tiles so a dense tile does not hit the per-request limit and hide places.
BBOX = (108.120, 15.960, 108.300, 16.130)  # lon_min, lat_min, lon_max, lat_max
GRID = 4
PAGE_LIMIT = 200
MAX_PAGES = 5

# Geoapify category -> stored category. Stored values are the ones the UI and the
# nearby service already understand. Pharmacies are not hospitals; markets are not
# supermarkets.
CATEGORIES = {
    "education.school": "SCHOOL",
    "education.college": "SCHOOL",
    "education.university": "SCHOOL",
    "childcare.kindergarten": "SCHOOL",
    "healthcare.hospital": "HOSPITAL",
    "healthcare.clinic_or_praxis": "HOSPITAL",
    "healthcare.pharmacy": "PHARMACY",
    "commercial.supermarket": "SUPERMARKET",
    "commercial.marketplace": "MARKET",
    "commercial.shopping_mall": "MALL",
    "leisure.park": "PARK",
    "beach": "BEACH",
}
OSM_TYPES = {"n": "node", "w": "way", "r": "relation", "node": "node", "way": "way", "relation": "relation"}


def read_env_file(path):
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"^\s*(?:export\s+)?([A-Za-z0-9_]+)\s*=\s*(.*)$", line)
            if m:
                values[m.group(1)] = m.group(2).strip().strip("\"'")
    return values


def check_target(host, port, database, allow_production):
    """Refuse anything but a loopback MySQL; the real 3306 schema needs an explicit flag."""
    if host not in LOOPBACK:
        raise SystemExit("Refusing non-local database host.")
    if not 1 <= port <= 65535:
        raise SystemExit("Invalid port.")
    if port == 3306 and not allow_production:
        raise SystemExit("Port 3306 is the real database; pass --allow-production to write there.")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", database or ""):
        raise SystemExit("Invalid database name.")


def tiles(bbox=BBOX, grid=GRID):
    lon0, lat0, lon1, lat1 = bbox
    dx, dy = (lon1 - lon0) / grid, (lat1 - lat0) / grid
    for i in range(grid):
        for j in range(grid):
            yield (round(lon0 + i * dx, 5), round(lat0 + j * dy, 5),
                   round(lon0 + (i + 1) * dx, 5), round(lat0 + (j + 1) * dy, 5))


def osm_url(props):
    """Real OpenStreetMap object URL when Geoapify reports the OSM identity, else None."""
    raw = (props.get("datasource") or {}).get("raw") or {}
    osm_type = OSM_TYPES.get(str(raw.get("osm_type", "")).lower())
    osm_id = raw.get("osm_id")
    if osm_type and isinstance(osm_id, int) and osm_id > 0:
        return f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
    return None


def to_row(feature, category):
    """Map one Geoapify feature to a table row, or None when it lacks a usable name or point."""
    props = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    name = str(props.get("name") or "").strip()
    place_id = str(props.get("place_id") or "").strip()
    coords = geometry.get("coordinates") if geometry.get("type") == "Point" else None
    if len(name) < 2 or not place_id or len(place_id) > 255 or not coords or len(coords) < 2:
        return None
    lon, lat = coords[0], coords[1]
    if not all(isinstance(v, (int, float)) for v in (lon, lat)) or not (-90 <= lat <= 90 and -180 < lon <= 180):
        return None
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"geoapify:{place_id}")),
        "name": name[:255],
        "category": category,
        "wkt": f"POINT({lon:.7f} {lat:.7f})",
        "external_id": place_id,
        "source_url": osm_url(props),
    }


def fetch(api_key, cache_dir, from_cache):
    import requests
    rows = {}
    calls = 0
    cache_dir.mkdir(parents=True, exist_ok=True)
    for geo_category, category in CATEGORIES.items():
        for rect in tiles():
            for page in range(MAX_PAGES):
                key = hashlib.sha256(f"{geo_category}|{rect}|{page}".encode()).hexdigest()[:24]
                cached = cache_dir / f"{key}.json"
                if cached.exists():
                    body = json.loads(cached.read_text(encoding="utf-8"))
                elif from_cache:
                    break
                else:
                    params = {"categories": geo_category, "filter": "rect:" + ",".join(map(str, rect)),
                              "limit": PAGE_LIMIT, "offset": page * PAGE_LIMIT, "lang": "vi", "apiKey": api_key}
                    try:
                        response = requests.get("https://api.geoapify.com/v2/places", params=params, timeout=20)
                    except requests.RequestException as error:
                        # The exception text carries the request URL, which contains the key.
                        raise SystemExit(f"Geoapify request failed ({type(error).__name__}).") from None
                    calls += 1
                    if response.status_code != 200:
                        raise SystemExit(f"Geoapify returned HTTP {response.status_code} for {geo_category}.")
                    body = response.json()
                    cached.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
                    time.sleep(0.2)
                features = body.get("features") or []
                for feature in features:
                    row = to_row(feature, category)
                    # A place listed under several categories keeps the first, most specific one.
                    if row and row["external_id"] not in rows:
                        rows[row["external_id"]] = row
                if len(features) < PAGE_LIMIT:
                    break
    return list(rows.values()), calls


def write(rows, host, port, database, user, password):
    import pymysql
    connection = pymysql.connect(host=host, port=port, user=user, password=password,
                                 database=database, charset="utf8mb4", autocommit=False)
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT DATABASE()")
            if cur.fetchone()[0] != database:
                raise SystemExit("Connected to an unexpected schema.")
            cur.executemany(
                """INSERT INTO points_of_interest (id, name, category, location, source_name, external_id, source_url, observed_at)
                   VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326, 'axis-order=long-lat'), %s, %s, %s, UTC_TIMESTAMP(6))
                   ON DUPLICATE KEY UPDATE name = VALUES(name), category = VALUES(category), location = VALUES(location),
                       source_url = VALUES(source_url), observed_at = VALUES(observed_at), updated_at = UTC_TIMESTAMP(6)""",
                [(r["id"], r["name"], r["category"], r["wkt"], SOURCE_NAME, r["external_id"], r["source_url"]) for r in rows])
            connection.commit()
            cur.execute("SELECT category, COUNT(*) FROM points_of_interest WHERE source_name = %s GROUP BY category ORDER BY category",
                        (SOURCE_NAME,))
            return cur.fetchall()
    finally:
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--allow-production", action="store_true")
    parser.add_argument("--credentials-json", type=Path, help="JSON file with DB_USER and DB_PASSWORD")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env", help="source of GEOAPIFY_API_KEY")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--from-cache", action="store_true", help="use saved responses only, no API calls")
    parser.add_argument("--dry-run", action="store_true", help="fetch and count, do not write")
    args = parser.parse_args(argv)
    check_target(args.host, args.port, args.database, args.allow_production)

    env = read_env_file(args.env_file)
    api_key = os.environ.get("GEOAPIFY_API_KEY") or env.get("GEOAPIFY_API_KEY")
    if not api_key and not args.from_cache:
        raise SystemExit("GEOAPIFY_API_KEY is not set.")
    rows, calls = fetch(api_key, args.cache_dir, args.from_cache)
    counts = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    with_osm = sum(1 for r in rows if r["source_url"])
    print(f"Geoapify calls: {calls}; places: {len(rows)} ({with_osm} with an OpenStreetMap URL)")
    print("By category: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if args.dry_run:
        return 0

    if args.credentials_json:
        creds = json.loads(args.credentials_json.read_text(encoding="utf-8-sig"))
        user, password = creds.get("DB_USER"), creds.get("DB_PASSWORD")
    else:
        user = os.environ.get("DB_USER") or env.get("DB_USER")
        password = os.environ.get("DB_PASSWORD") or env.get("DB_PASSWORD")
    if not user or password is None:
        raise SystemExit("Database credentials are missing.")
    stored = write(rows, args.host, args.port, args.database, user, password)
    print(f"Stored in {args.database}: " + ", ".join(f"{c}={n}" for c, n in stored))
    return 0


if __name__ == "__main__":
    sys.exit(main())
