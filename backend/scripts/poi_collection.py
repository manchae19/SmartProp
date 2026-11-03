"""Step 19.4.1B - Da Nang POI collection (OSM Overpass + bounded Geoapify cross-check).

Commands:
  audit    read-only audit of the existing points_of_interest rows + legacy taxonomy proposal
  collect  fetch (cached) Overpass data for a scope: --scope hoavang|danang
  process  normalize/validate/dedupe cached raw data -> candidates (no DB writes)
  load     create enrichment schema (additive) and insert VALID new POIs + legacy enrichment
  verify   MySQL Spatial tests

Safety: never UPDATE/DELETE points_of_interest. New rows use INSERT ... ON DUPLICATE KEY UPDATE id=id.
No property->POI distances are computed here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
import time
import unicodedata
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pymysql
import requests

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
OUT = ROOT / ".scratch" / "tinix-integration" / "step19-4-1b"
RAW = OUT / "raw"
SCOPES = ROOT / "backend/src/main/resources/geocoding/danang-search-scopes.geojson"
MIGRATION = ROOT / "database/research-migrations/V20__poi_taxonomy_enrichment.sql"

TAXONOMY_VERSION = "POI_TAXONOMY_V1_1"
OSM_SOURCE = "openstreetmap_overpass"
OSM_LICENSE = "ODbL 1.0 (OpenStreetMap contributors)"
OSM_ATTRIBUTION = "© OpenStreetMap contributors (ODbL) via Overpass API"
UA = "SmartProp-Research/1.0 (local academic project; contact: project owner)"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DANANG_DISTRICTS = ["Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn", "Cẩm Lệ", "Liên Chiểu", "Hòa Vang"]

# Overpass selectors per taxonomy category (nwr = node/way/relation). Names are mandatory later.
SELECTORS = {
    "SCHOOL": ['nwr["amenity"~"^(school|kindergarten|college|university)$"]'],
    "HOSPITAL": ['nwr["amenity"~"^(hospital|clinic)$"]', 'nwr["healthcare"~"^(hospital|clinic|centre)$"]'],
    "PHARMACY": ['nwr["amenity"="pharmacy"]'],
    "MARKET": ['nwr["amenity"="marketplace"]'],
    "SUPERMARKET": ['nwr["shop"~"^(supermarket|mall|department_store)$"]'],
    "PARK": ['nwr["leisure"~"^(park|garden)$"]'],
    "BEACH": ['nwr["natural"="beach"]'],
    "PUBLIC_TRANSPORT": [
        'node["highway"="bus_stop"]',
        'nwr["amenity"="bus_station"]',
        'nwr["railway"~"^(station|halt)$"]',
        'nwr["aeroway"~"^(aerodrome|terminal)$"]',
    ],
}


# ---------------------------------------------------------------- text/geo helpers
def nfc(s: str | None) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "")).strip()


def fold(s: str | None) -> str:
    n = unicodedata.normalize("NFD", s or "")
    n = "".join(c for c in n if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", n)).strip()


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0  # MySQL ST_Distance_Sphere default radius
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _ring_contains(ring, x, y) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


class DistrictLocator:
    """Point-in-polygon over the 7 Da Nang ADM2 polygons shipped with SmartProp (holes honoured)."""

    def __init__(self):
        data = json.loads(SCOPES.read_text(encoding="utf-8"))
        self.polys: list[tuple[str, list, tuple]] = []
        for f in data["features"]:
            if f["properties"]["name"] not in DANANG_DISTRICTS:
                continue
            g = f["geometry"]
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for rings in polys:
                xs = [p[0] for p in rings[0]]
                ys = [p[1] for p in rings[0]]
                self.polys.append((f["properties"]["name"], rings, (min(xs), min(ys), max(xs), max(ys))))
        self.bbox = (
            min(p[2][0] for p in self.polys), min(p[2][1] for p in self.polys),
            max(p[2][2] for p in self.polys), max(p[2][3] for p in self.polys),
        )

    def district_bbox(self, name):
        bs = [p[2] for p in self.polys if p[0] == name]
        return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))

    def locate(self, lat, lon) -> str | None:
        for name, rings, bb in self.polys:
            if not (bb[0] <= lon <= bb[2] and bb[1] <= lat <= bb[3]):
                continue
            if _ring_contains(rings[0], lon, lat) and not any(_ring_contains(h, lon, lat) for h in rings[1:]):
                return name
        # Coastal boundary tolerance fallback (up to 120m) for coastal beaches and shoreline features
        best_name, best_dist = None, 120.0
        for name, rings, bb in self.polys:
            if not (bb[0] - 0.003 <= lon <= bb[2] + 0.003 and bb[1] - 0.003 <= lat <= bb[3] + 0.003):
                continue
            d = min(haversine_m(lat, lon, p[1], p[0]) for p in rings[0])
            if d < best_dist:
                best_dist = d
                best_name = name
        return best_name


# ---------------------------------------------------------------- DB
def connect(readonly=False):
    spec = importlib.util.spec_from_file_location("rec", SCRIPT_DIR / "run-recommendation-local.py")
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    priv = rec.private_environment()
    conn = pymysql.connect(host="127.0.0.1", port=3306, user=priv["DB_USER"], password=priv["DB_PASSWORD"],
                           database="smartprop", charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)
    for k in ("DB_USER", "DB_PASSWORD", "JWT_SECRET"):
        priv.pop(k, None)
    if readonly:
        with conn.cursor() as cur:
            cur.execute("SET SESSION TRANSACTION READ ONLY")
    return conn


def load_legacy(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id,name,category,source_name,external_id,ST_Latitude(location) lat,ST_Longitude(location) lon "
                    "FROM points_of_interest WHERE source_name <> %s OR source_name IS NULL", (OSM_SOURCE,))
        return cur.fetchall()


# ---------------------------------------------------------------- legacy taxonomy proposal (metadata only)
def legacy_taxonomy(row):
    """Return (taxonomy_category, status, reasons). Never changes the stored legacy category."""
    name, cat = row["name"] or "", row["category"]
    f = fold(name)
    if cat == "PARK":
        if re.search(r"\b(bai tam|bai bien|beach)\b", f) and "pool" not in f:
            return "BEACH", "LEGACY_RECLASSIFIED", ["BEACH_WAS_STORED_AS_PARK"]
        if re.search(r"\b(pool|spa|bambus|van hoa|the thao|danh thang|playground)\b", f) or f == "cong vien":
            return "PARK", "NEEDS_REVIEW", ["LEGACY_PARK_NOT_CLEARLY_A_PUBLIC_PARK"]
        return "PARK", "LEGACY_UNVERIFIED", []
    if cat in ("SUPERMARKET", "TRANSPORT") and re.match(r"^cho\b", f):
        return "MARKET", "LEGACY_RECLASSIFIED", [f"MARKET_WAS_STORED_AS_{cat}"]
    if cat == "SUPERMARKET":
        return "SUPERMARKET", "LEGACY_UNVERIFIED", []
    if cat == "HOSPITAL":
        if re.search(r"\b(nha thuoc|pharmacy|hieu thuoc|quay thuoc)\b", f):
            return "PHARMACY", "LEGACY_RECLASSIFIED", ["PHARMACY_WAS_STORED_AS_HOSPITAL"]
        return "HOSPITAL", "LEGACY_UNVERIFIED", []
    if cat == "SCHOOL":
        return "SCHOOL", "LEGACY_UNVERIFIED", []
    if cat == "TRANSPORT":
        if re.search(r"\b(ga |ga$|ben xe|san bay|tram xe buyt|bus|airport|station|xe buyt)\b", f + " "):
            return "PUBLIC_TRANSPORT", "LEGACY_RECLASSIFIED", ["TRANSPORT_NAMED_PUBLIC_TRANSIT"]
        return "TRANSPORT_UNCLASSIFIED", "NEEDS_REVIEW", ["LEGACY_TRANSPORT_NAME_IS_ADDRESS_OR_NON_TRANSIT"]
    return cat, "NEEDS_REVIEW", ["UNKNOWN_LEGACY_CATEGORY"]


# ---------------------------------------------------------------- Overpass
def overpass_query(category, bbox):
    w, s, e, n = bbox
    box = f"{s:.5f},{w:.5f},{n:.5f},{e:.5f}"
    parts = "".join(f"{sel}({box});" for sel in SELECTORS[category])
    return f"[out:json][timeout:180];({parts});out center tags;"


def fetch_overpass(scope, category, bbox, log, sleep_s=12):
    RAW.mkdir(parents=True, exist_ok=True)
    cache = RAW / f"overpass_{scope}_{category}.json"
    if cache.exists():
        log.append({"provider": "overpass", "scope": scope, "category": category, "cache_hit": True, "http": None})
        return json.loads(cache.read_text(encoding="utf-8"))
    q = overpass_query(category, bbox)
    for attempt in range(1, 5):
        t0 = time.time()
        r = requests.post(OVERPASS_URL, data={"data": q}, headers={"User-Agent": UA}, timeout=240)
        log.append({"provider": "overpass", "scope": scope, "category": category, "cache_hit": False,
                    "attempt": attempt, "http": r.status_code, "seconds": round(time.time() - t0, 1),
                    "requested_at": datetime.now(timezone.utc).isoformat()})
        if r.status_code == 200:
            data = r.json()
            data["_meta"] = {"query": q, "fetched_at": datetime.now(timezone.utc).isoformat(),
                             "osm_base": data.get("osm3s", {}).get("timestamp_osm_base")}
            cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            time.sleep(sleep_s)
            return data
        time.sleep(sleep_s * attempt * 2)
    raise RuntimeError(f"Overpass failed for {scope}/{category}")


def cmd_collect(scope):
    loc = DistrictLocator()
    OUT.mkdir(parents=True, exist_ok=True)
    bbox = loc.district_bbox("Hòa Vang") if scope == "hoavang" else loc.bbox
    log_path = OUT / "api_request_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    for cat in SELECTORS:
        d = fetch_overpass(scope, cat, bbox, log)
        print(f"[collect] {scope}/{cat}: {len(d.get('elements', []))} elements", flush=True)
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- normalize / validate
def element_point(el):
    if el["type"] == "node":
        return el.get("lat"), el.get("lon"), "OSM_NODE"
    c = el.get("center") or {}
    return c.get("lat"), c.get("lon"), f"OSM_{el['type'].upper()}_CENTER"


def subcategory(cat, tags, name):
    f = fold(name)
    if cat == "SCHOOL":
        a = tags.get("amenity")
        if a == "kindergarten":
            return "PRESCHOOL"
        if a in ("college", "university"):
            return "HIGHER_EDUCATION"
        if re.search(r"tieu hoc", f):
            return "PRIMARY"
        if re.search(r"\bthcs\b|trung hoc co so", f):
            return "LOWER_SECONDARY"
        if re.search(r"\bthpt\b|trung hoc pho thong", f):
            return "UPPER_SECONDARY"
        return "SCHOOL_GENERAL"
    if cat == "HOSPITAL":
        if re.search(r"tram y te|y te phuong|y te xa", f):
            return "COMMUNE_HEALTH_STATION"
        return "HOSPITAL" if (tags.get("amenity") == "hospital" or tags.get("healthcare") == "hospital") else "CLINIC"
    if cat == "SUPERMARKET":
        return {"supermarket": "SUPERMARKET", "mall": "SHOPPING_MALL", "department_store": "DEPARTMENT_STORE"}.get(tags.get("shop"), None)
    if cat == "PARK":
        return tags.get("leisure", "park").upper()
    if cat == "PUBLIC_TRANSPORT":
        if tags.get("highway") == "bus_stop":
            return "BUS_STOP"
        if tags.get("amenity") == "bus_station":
            return "BUS_STATION"
        if tags.get("railway"):
            return "RAIL_STATION"
        if tags.get("aeroway"):
            return "AIRPORT"
    return None


def name_category_conflict(cat, name):
    f = fold(name)
    if cat == "MARKET" and re.search(r"\b(sieu thi|mart|bach hoa|supermarket|coop)\b", f):
        return "MARKET_TAG_BUT_SUPERMARKET_NAME"
    if cat == "SUPERMARKET" and re.match(r"^cho\b", f):
        return "SUPERMARKET_TAG_BUT_MARKET_NAME"
    if cat == "PARK" and re.search(r"\b(bai tam|bai bien|beach)\b", f):
        return "PARK_TAG_BUT_BEACH_NAME"
    return None


def confidence(el, tags, basis):
    s = 0.40 + 0.20  # OSM object + required name
    if tags.get("name:vi") or tags.get("wikidata") or tags.get("brand"):
        s += 0.10
    if any(tags.get(k) for k in ("operator", "addr:street", "addr:housenumber", "website", "opening_hours", "phone")):
        s += 0.05
    s += {"OSM_NODE": 0.15, "OSM_WAY_CENTER": 0.08}.get(basis, 0.03)  # centroid of polygons is an approximation
    return min(round(s, 2), 0.95)


def build_candidates(loc, legacy, geoapify_idx=None):
    cands = []
    for p in sorted(RAW.glob("overpass_*_*.json")):
        _, scope, cat = p.stem.split("_", 2)
        if scope == "hoavang" and (RAW / f"overpass_danang_{cat}.json").exists():
            continue  # full-scope file supersedes the pilot file
        data = json.loads(p.read_text(encoding="utf-8"))
        fetched = data["_meta"]["fetched_at"]
        for el in data["elements"]:
            tags = el.get("tags", {})
            lat, lon, basis = element_point(el)
            name = nfc(tags.get("name:vi") or tags.get("name"))
            c = {"osm_type": el["type"], "osm_id": el["id"], "ref": f"{el['type']}/{el['id']}", "category": cat,
                 "name": name, "lat": lat, "lon": lon, "basis": basis, "tags": {k: tags[k] for k in tags if k in (
                     "amenity", "shop", "leisure", "natural", "highway", "railway", "aeroway", "healthcare", "access", "name:vi")},
                 "fetched_at": fetched, "reasons": [], "status": "VALID"}
            c["subcategory"] = subcategory(cat, tags, name)
            cands.append((c, tags))
    return cands


def process(geo_path=None):
    loc = DistrictLocator()
    conn = connect(readonly=True)
    legacy = load_legacy(conn)
    conn.close()
    leg = []
    for r in legacy:
        t, st, _ = legacy_taxonomy(r)
        leg.append({"id": r["id"], "name": r["name"], "fold": fold(r["name"]), "cat": t, "status": st,
                    "lat": r["lat"], "lon": r["lon"]})
    cands = build_candidates(loc, legacy)
    geo = json.loads(Path(geo_path).read_text(encoding="utf-8")) if geo_path and Path(geo_path).exists() else None

    seen_ref, out = set(), []
    for c, tags in cands:
        if c["ref"] in seen_ref:
            continue
        seen_ref.add(c["ref"])
        reasons = c["reasons"]
        lat, lon = c["lat"], c["lon"]
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            c["status"] = "REJECTED"; reasons.append("INVALID_COORDINATES")
            out.append(c); continue
        c["district"] = loc.locate(lat, lon)
        if c["district"] is None:
            c["status"] = "REJECTED"; reasons.append("OUTSIDE_DANANG_POLYGONS")
        elif len(c["name"]) < 2 or re.fullmatch(r"[\d\W]+", c["name"]):
            c["status"] = "REVIEW"; reasons.append("UNNAMED_OR_INVALID_NAME")
        elif tags.get("access") in ("private", "no"):
            c["status"] = "REVIEW"; reasons.append("ACCESS_NOT_PUBLIC")
        elif tags.get("leisure") == "garden" and tags.get("garden:type") in ("private", "residential"):
            c["status"] = "REVIEW"; reasons.append("PRIVATE_GARDEN")
        else:
            conf = name_category_conflict(c["category"], c["name"])
            if conf:
                c["status"] = "REVIEW"; reasons.append(conf)
        c["confidence"] = confidence({}, tags, c["basis"])
        out.append(c)

    # ---- duplicate detection: batch (same category) then legacy
    grid = defaultdict(list)
    def cell(lat, lon): return (round(lat / 0.0015), round(lon / 0.0015))
    ordered = sorted([c for c in out if c["status"] == "VALID"], key=lambda c: (-c["confidence"], c["ref"]))
    kept = []
    for c in ordered:
        f = fold(c["name"])
        dup_of = None
        cx, cy = cell(c["lat"], c["lon"])
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for k in grid[(cx + dx, cy + dy)]:
                    if k["category"] != c["category"]:
                        continue
                    d = haversine_m(c["lat"], c["lon"], k["lat"], k["lon"])
                    kf = fold(k["name"])
                    same = f == kf or (min(len(f), len(kf)) >= 6 and (f in kf or kf in f))
                    lim = 15 if c["category"] == "PUBLIC_TRANSPORT" else 120
                    if (same and d <= lim) or d <= 8:
                        dup_of = k["ref"]; break
                if dup_of: break
            if dup_of: break
        if dup_of:
            c["status"] = "DUPLICATE_BATCH"; c["reasons"].append(f"DUPLICATE_OF_{dup_of}")
        else:
            kept.append(c); grid[(cx, cy)].append(c)

    lgrid = defaultdict(list)
    for r in leg:
        lgrid[cell(r["lat"], r["lon"])].append(r)
    legacy_corroboration = defaultdict(list)
    for c in kept:
        f = fold(c["name"]); cx, cy = cell(c["lat"], c["lon"])
        hit = conflict = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for r in lgrid[(cx + dx, cy + dy)]:
                    d = haversine_m(c["lat"], c["lon"], r["lat"], r["lon"])
                    same = f == r["fold"] or (min(len(f), len(r["fold"])) >= 6 and (f in r["fold"] or r["fold"] in f))
                    if same and d <= 200 and r["cat"] == c["category"]:
                        hit = r
                    elif f == r["fold"] and d <= 100 and r["cat"] != c["category"] and c["category"] != "PUBLIC_TRANSPORT":
                        conflict = conflict or r
        if hit:
            c["status"] = "DUPLICATE_LEGACY"; c["reasons"].append(f"DUPLICATE_OF_LEGACY_{hit['id']}")
            legacy_corroboration[hit["id"]].append(c["ref"])
        elif conflict:
            c["status"] = "REVIEW"; c["reasons"].append(f"CATEGORY_CONFLICT_WITH_LEGACY_{conflict['id']}")

    # ---- optional Geoapify cross-check (Hòa Vang pilot; Geoapify is OSM-derived, so NOT independent)
    if geo:
        for c in out:
            c["geoapify_match"] = False
        gp = geo["points"]
        for c in out:
            if c["status"] != "VALID":
                continue
            f = fold(c["name"])
            for g in gp:
                if g["category"] == c["category"] and haversine_m(c["lat"], c["lon"], g["lat"], g["lon"]) <= 150:
                    gf = fold(g["name"])
                    if f == gf or (min(len(f), len(gf)) >= 6 and (f in gf or gf in f)):
                        c["geoapify_match"] = True; break
    for c in out:
        if c["status"] == "VALID" and c["confidence"] < 0.60:
            c["status"] = "REVIEW"; c["reasons"].append("LOW_CONFIDENCE")
    (OUT / "poi_candidates.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in out), encoding="utf-8")
    (OUT / "legacy_corroboration.json").write_text(json.dumps(legacy_corroboration, ensure_ascii=False), encoding="utf-8")
    print("[process]", dict(Counter(c["status"] for c in out)), f"total={len(out)}")
    return out, leg


# ---------------------------------------------------------------- geoapify pilot cross-check (bounded)
GEO_MAP = {
    "SCHOOL": "education.school,education.kindergarten", "HOSPITAL": "healthcare.hospital,healthcare.clinic_or_praxis",
    "PHARMACY": "healthcare.pharmacy", "MARKET": "commercial.marketplace", "SUPERMARKET": "commercial.supermarket",
    "PARK": "leisure.park", "BEACH": "beach", "PUBLIC_TRANSPORT": "public_transport",
}
GEO_CALL_CAP = 12


def cmd_geoapify_pilot():
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z0-9_]+)\s*=\s*(.*)$", line)
        if m:
            env[m.group(1)] = m.group(2).strip().strip("\"'")
    key = env.get("GEOAPIFY_API_KEY")
    if not key:
        print("BLOCKED: no GEOAPIFY_API_KEY"); return
    cache = RAW / "geoapify_hoavang_pilot.json"
    if cache.exists():
        print("[geoapify] cache hit; 0 new requests"); return
    loc = DistrictLocator()
    w, s, e, n = loc.district_bbox("Hòa Vang")
    log_path = OUT / "api_request_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    points, calls = [], 0
    for cat, api_cat in GEO_MAP.items():
        if calls >= GEO_CALL_CAP:
            break
        r = requests.get("https://api.geoapify.com/v2/places", params={
            "categories": api_cat, "filter": f"rect:{w:.5f},{n:.5f},{e:.5f},{s:.5f}", "limit": 60, "apiKey": key}, timeout=30)
        calls += 1
        log.append({"provider": "geoapify_places", "scope": "hoavang_pilot", "category": cat, "http": r.status_code,
                    "limit": 60, "requested_at": datetime.now(timezone.utc).isoformat()})
        if r.status_code == 200:
            for f in r.json().get("features", []):
                p = f["properties"]
                if p.get("name") and p.get("lat") and p.get("lon"):
                    points.append({"category": cat, "name": nfc(p["name"]), "lat": p["lat"], "lon": p["lon"]})
        time.sleep(1.0)  # well under the free-tier 5 req/s limit
    cache.write_text(json.dumps({"points": points, "calls": calls}, ensure_ascii=False), encoding="utf-8")
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[geoapify] {calls} requests, {len(points)} named points (cross-check only, not stored)")


# ---------------------------------------------------------------- load
def poi_uuid(ref):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://www.openstreetmap.org/{ref}"))


def cmd_load(apply):
    out, leg = process(RAW / "geoapify_hoavang_pilot.json")
    corro = json.loads((OUT / "legacy_corroboration.json").read_text(encoding="utf-8"))
    conn = connect()
    conn.autocommit(False)
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) c FROM points_of_interest"); before = cur.fetchone()["c"]
        if not apply:
            print(f"[load] DRY RUN. before={before}"); conn.rollback(); return
        for stmt in [s.strip() for s in re.split(r";\s*\n", MIGRATION.read_text(encoding="utf-8")) if s.strip()]:
            cur.execute(stmt)  # idempotent: IF NOT EXISTS / CREATE OR REPLACE VIEW
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        ins_new = 0
        for c in out:
            if c["status"] != "VALID":
                continue
            pid = poi_uuid(c["ref"])
            cur.execute(
                "INSERT INTO points_of_interest (id,name,category,location,source_name,external_id,source_url,observed_at) "
                "VALUES (%s,%s,%s,ST_GeomFromText(%s,4326,'axis-order=long-lat'),%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE id=id",
                (pid, c["name"][:255], c["category"], f"POINT({c['lon']:.7f} {c['lat']:.7f})", OSM_SOURCE, c["ref"],
                 f"https://www.openstreetmap.org/{c['ref']}", datetime.fromisoformat(c["fetched_at"]).replace(tzinfo=None)))
            ins_new += cur.rowcount == 1
            cur.execute(
                "INSERT INTO poi_taxonomy_enrichment (poi_id,taxonomy_version,taxonomy_category,taxonomy_subcategory,legacy_category,"
                "district_historical,location_basis,location_confidence,review_status,review_reasons,source_license,attribution,"
                "source_object_ref,collected_at) VALUES (%s,%s,%s,%s,NULL,%s,%s,%s,'VALID',%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE poi_id=poi_id",
                (pid, TAXONOMY_VERSION, c["category"], c["subcategory"], c["district"], c["basis"], c["confidence"],
                 json.dumps(c["reasons"]), OSM_LICENSE, OSM_ATTRIBUTION, c["ref"], now))
        # legacy rows: metadata only, original category untouched
        loc = DistrictLocator()
        leg_new = 0
        cur.execute("SELECT id,name,category,source_name,external_id,ST_Latitude(location) a,ST_Longitude(location) b "
                    "FROM points_of_interest WHERE source_name <> %s OR source_name IS NULL", (OSM_SOURCE,))
        for r in cur.fetchall():
            t, st, reasons = legacy_taxonomy(r)
            if r["id"] in corro:
                reasons = reasons + [f"CORROBORATED_BY_OSM:{','.join(corro[r['id']][:3])}"]
            is_geo = r["source_name"] == "geoapify_places_api"
            cur.execute(
                "INSERT INTO poi_taxonomy_enrichment (poi_id,taxonomy_version,taxonomy_category,taxonomy_subcategory,legacy_category,"
                "district_historical,location_basis,location_confidence,review_status,review_reasons,source_license,attribution,"
                "source_object_ref,collected_at) VALUES (%s,%s,%s,NULL,%s,%s,'LEGACY_POINT',NULL,%s,%s,%s,%s,%s,NULL) ON DUPLICATE KEY UPDATE poi_id=poi_id",
                (r["id"], TAXONOMY_VERSION, t, r["category"], loc.locate(r["a"], r["b"]), st, json.dumps(reasons),
                 "ODbL 1.0 (OpenStreetMap contributors) via Geoapify Places" if is_geo else "SmartProp curated seed (unverified)",
                 "© OpenStreetMap contributors (ODbL), Geoapify" if is_geo else "SmartProp curated seed",
                 (r["external_id"] or "")[:80]))
            leg_new += cur.rowcount == 1
        conn.commit()
        cur.execute("SELECT COUNT(*) c FROM points_of_interest"); after = cur.fetchone()["c"]
        print(f"[load] before={before} after={after} new_poi_rows={ins_new} legacy_enrichment_rows={leg_new}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect").add_argument("--scope", choices=["hoavang", "danang"], required=True)
    sub.add_parser("geoapify-pilot")
    sub.add_parser("process")
    sub.add_parser("load").add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.cmd == "collect":
        cmd_collect(a.scope)
    elif a.cmd == "geoapify-pilot":
        cmd_geoapify_pilot()
    elif a.cmd == "process":
        process(RAW / "geoapify_hoavang_pilot.json")
    elif a.cmd == "load":
        cmd_load(a.apply)


if __name__ == "__main__":
    main()
