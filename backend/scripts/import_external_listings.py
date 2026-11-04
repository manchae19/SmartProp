#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
SmartProp: Bước 14 - Import và Data Quality Gate cho External Crawler Listings.
Chạy độc lập trên Windows PowerShell bằng Python của project:
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/import_external_listings.py
"""

import argparse
import csv
import json
import os
from pathlib import Path
import re
import sys
import time
import getpass
import math
import subprocess
from decimal import Decimal
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "ai-services" / "app" / "data" / "processed" / "remaining_diversity_review" / "runs" / "518bbc989587326c" / "eligible.csv"
DEFAULT_MYSQL = Path(r"F:\MySQL\Server8.0\bin\mysql.exe")

TITLE_ERROR_PATTERN = re.compile(r'(404|không tìm thấy|tin đã xóa|page not found|bài viết không tồn tại|lỗi hệ thống|error)', re.IGNORECASE)
MULTI_PROP_PATTERN = re.compile(r'(cặp lô|2 lô|3 lô|4 lô|hai lô|ba lô|nhiều lô|nhiều căn|dãy trọ|dãy phòng|2 căn|3 căn|02 căn|03 căn|hai căn)', re.IGNORECASE)
ADDR_PREFIX_PATTERN = re.compile(r'^(bán\s+(nhà|đất|căn hộ|chung cư|biệt thự|phòng)\s*(riêng|nền)?)\s*', re.IGNORECASE)

GENERIC_ADDRESSES = {
    "đà nẵng",
    "quận cẩm lệ, đà nẵng",
    "quận hải châu, đà nẵng",
    "quận sơn trà, đà nẵng",
    "quận liên chiểu, đà nẵng",
    "quận ngũ hành sơn, đà nẵng",
    "quận thanh khê, đà nẵng",
    "huyện hòa vang, đà nẵng"
}

STOP_WORDS = {
    "bán", "giá", "rẻ", "nhà", "đất", "cần", "chính", "chủ", "tại", "ở", "đẹp",
    "quận", "phường", "đường", "tp", "đà", "nẵng"
}

def clean_address(addr):
    if not addr:
        return ""
    s = ADDR_PREFIX_PATTERN.sub("", addr)
    return s.strip().lower()

def tokenize(text):
    if not text:
        return []
    words = re.findall(r'[\w]+', text.lower())
    return [w for w in words if len(w) > 1 and w not in STOP_WORDS]

def jaccard(l1, l2):
    if not l1 or not l2:
        return 0.0
    s1, s2 = set(l1), set(l2)
    union = s1 | s2
    if not union:
        return 0.0
    return len(s1 & s2) / len(union)

def run_quality_gate(records):
    print(f"[*] Đang chạy Data Quality Gate trên {len(records)} bản ghi...")

    # 1. Single record evaluation
    for r in records:
        issues = []
        title = (r.get("title") or "").strip()
        url = (r.get("detail_url") or "").lower()
        cat = (r.get("category") or "").strip()
        source = (r.get("source") or "").lower()

        # Homedy SALE normalization from /ban-
        if source == "homedy" and "/ban-" in url:
            r["transaction_type"] = "SALE"
            r["transaction_basis"] = "INFERRED_FROM_URL"
        else:
            r["transaction_type"] = "SALE"
            if not r.get("transaction_basis"):
                r["transaction_basis"] = "EXPLICIT_SOURCE_FIELD"

        # Tiêu đề lỗi hoặc 404
        if len(title) < 10 or TITLE_ERROR_PATTERN.search(title):
            issues.append("TITLE_ERROR_OR_404")

        # Tin nhiều BĐS
        if MULTI_PROP_PATTERN.search(title):
            issues.append("MULTI_PROPERTY")

        # Mismatch category và URL
        if ("can-ho" in url or "chung-cu" in url) and cat != "Căn hộ chung cư":
            issues.append("CATEGORY_MISMATCH")
        elif ("ban-dat" in url or "/dat-" in url) and cat != "Đất nền":
            issues.append("CATEGORY_MISMATCH")
        elif ("ban-nha" in url or "/nha-" in url) and cat != "Nhà ở":
            issues.append("CATEGORY_MISMATCH")

        # Missing details
        p_mil = float(r.get("price_million") or 0)
        a_sqm = float(r.get("area_sqm") or 0)
        dist = (r.get("district") or "").strip()

        if p_mil <= 0:
            issues.append("MISSING_PRICE")
        if a_sqm <= 0:
            issues.append("MISSING_AREA")
        if not dist:
            issues.append("MISSING_DISTRICT")

        r["clean_address"] = clean_address(r.get("address_raw"))
        r["title_tokens"] = tokenize(title)
        r["quality_issues"] = issues
        r["verification_status"] = "UNVERIFIED"

    # 2. Duplicate clustering
    n = len(records)
    from collections import defaultdict
    adj = defaultdict(set)

    for i in range(n):
        r1 = records[i]
        addr1 = r1["clean_address"]
        if not addr1 or addr1 in GENERIC_ADDRESSES:
            continue
        p1 = float(r1.get("price_million") or 0)
        a1 = float(r1.get("area_sqm") or 0)
        if p1 <= 0 or a1 <= 0:
            continue

        for j in range(i + 1, n):
            r2 = records[j]
            if addr1 != r2["clean_address"]:
                continue
            if r1.get("category") != r2.get("category"):
                continue

            p2 = float(r2.get("price_million") or 0)
            a2 = float(r2.get("area_sqm") or 0)
            if p2 <= 0 or a2 <= 0:
                continue

            area_diff = abs(a1 - a2) / max(a1, a2)
            if area_diff > 0.03:
                continue

            price_diff = abs(p1 - p2) / max(p1, p2)
            if price_diff > 0.10:
                continue

            jac = jaccard(r1["title_tokens"], r2["title_tokens"])
            if jac >= 0.20 or (area_diff <= 0.01 and price_diff <= 0.05):
                adj[i].add(j)
                adj[j].add(i)

    visited = set()
    duplicate_groups = []
    group_counter = 1

    for i in range(n):
        if i not in visited and i in adj:
            comp = []
            queue = [i]
            visited.add(i)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            if len(comp) > 1:
                gid = f"group_dup_{group_counter:04d}"
                group_counter += 1

                # Check Trường Chinh group
                tc_keys = {"homedy:2615601", "homedy:2346049", "homedy:2247057"}
                comp_keys = {records[idx]["record_key"] for idx in comp}
                if comp_keys.intersection(tc_keys):
                    gid = "group_dup_truong_chinh_cam_le"

                min_price, max_price = None, None
                min_area, max_area = None, None
                first_r = records[comp[0]]
                category = first_r.get("category")
                district = first_r.get("district")
                name = f"Nhóm nghi trùng: {first_r.get('clean_address')}"

                for idx in comp:
                    d = records[idx]
                    d["is_duplicate"] = True
                    d["duplicate_group"] = gid
                    if "NEAR_DUPLICATE" not in d["quality_issues"]:
                        d["quality_issues"].append("NEAR_DUPLICATE")

                    p_vnd = float(d.get("price_million") or 0) * 1_000_000
                    area = float(d.get("area_sqm") or 0)
                    if min_price is None or p_vnd < min_price: min_price = p_vnd
                    if max_price is None or p_vnd > max_price: max_price = p_vnd
                    if min_area is None or area < min_area: min_area = area
                    if max_area is None or area > max_area: max_area = area

                duplicate_groups.append({
                    "group_id": gid,
                    "name": name,
                    "category": category,
                    "district": district,
                    "listing_count": len(comp),
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_area": min_area,
                    "max_area": max_area,
                    "members": list(comp_keys)
                })

    # 3. Finalize quality status
    for r in records:
        issues = r["quality_issues"]
        if "TITLE_ERROR_OR_404" in issues:
            r["quality_status"] = "REJECTED"
        elif issues:
            r["quality_status"] = "NEEDS_REVIEW"
        else:
            r["quality_status"] = "VALID"
        if "is_duplicate" not in r:
            r["is_duplicate"] = False
            r["duplicate_group"] = None

    return duplicate_groups


def escape_sql(value):
    """Hex UTF-8 literals avoid quote/backslash/sql_mode ambiguities."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        if not math.isfinite(value):
            raise ValueError("Nonfinite numeric value in import")
        return str(value)
    return "CONVERT(X'" + str(value).encode("utf8").hex() + "' USING utf8mb4)"

def build_import_sql(records, duplicate_groups):
    sql_lines = ["SET NAMES utf8mb4;", "SET SESSION sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION';", "START TRANSACTION;"]

    # 2. Upsert duplicate groups
    for g in duplicate_groups:
        stmt = f"""
        INSERT INTO external_duplicate_groups
            (group_id, name, category, district, listing_count, min_price, max_price, min_area, max_area)
        VALUES ({escape_sql(g['group_id'])}, {escape_sql(g['name'])}, {escape_sql(g['category'])}, {escape_sql(g['district'])},
                {g['listing_count']}, {escape_sql(g['min_price'])}, {escape_sql(g['max_price'])}, {escape_sql(g['min_area'])}, {escape_sql(g['max_area'])})
        ON DUPLICATE KEY UPDATE
            name=VALUES(name), category=VALUES(category), district=VALUES(district),
            listing_count=VALUES(listing_count), min_price=VALUES(min_price), max_price=VALUES(max_price),
            min_area=VALUES(min_area), max_area=VALUES(max_area);
        """
        sql_lines.append(stmt.strip())

    # 3. Upsert external_listings in batches
    for r in records:
        p_mil = Decimal(r.get("price_million") or "0")
        p_vnd = p_mil * 1_000_000
        a_sqm = Decimal(r.get("area_sqm") or "0")
        p_sqm = Decimal(r.get("price_per_sqm_million") or "0") if r.get("price_per_sqm_million") else None
        if any(not v.is_finite() for v in [p_mil,a_sqm]+([] if p_sqm is None else [p_sqm])):
            raise ValueError("Nonfinite numeric value in import")
        holdout = r.get("protected_holdout", "").lower() == "true"

        raw_meta = {
            "assigned_split": r.get("assigned_split"),
            "training_allowed": r.get("training_allowed"),
            "original_price_million": r.get("original_price_million"),
            "original_area_sqm": r.get("original_area_sqm"),
            "original_category": r.get("original_category"),
            "review_codes": r.get("review_codes"),
            "displayed_date": r.get("displayed_date"),
            "age_days": r.get("age_days"),
            "transaction_raw": r.get("transaction_raw"),
            "status_crawler": r.get("status"),
            "duplicate_candidate_group_crawler": r.get("duplicate_candidate_group")
        }

        collected_at_val = r.get("collected_at")
        if collected_at_val:
            observed = datetime.fromisoformat(collected_at_val.replace("Z", "+00:00"))
            if observed.tzinfo is None:
                raise ValueError("collected_at must include a timezone")
            collected_at_val = observed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

        stmt = f"""
        INSERT INTO external_listings
            (record_key, source, source_listing_id, title, detail_url, category, transaction_type,
             transaction_basis, price, price_million, area_sqm, price_per_sqm_million, district,
             address_raw, quality_status, quality_issues, verification_status, duplicate_group,
             is_duplicate, is_protected_holdout, collected_at, raw_metadata)
        VALUES
            ({escape_sql(r['record_key'])}, {escape_sql(r['source'])}, {escape_sql(r.get('source_listing_id'))},
             {escape_sql(r['title'])}, {escape_sql(r['detail_url'])}, {escape_sql(r['category'])},
             {escape_sql(r['transaction_type'])}, {escape_sql(r['transaction_basis'])},
             {p_vnd}, {p_mil}, {a_sqm}, {escape_sql(p_sqm)}, {escape_sql(r.get('district'))},
             {escape_sql(r.get('address_raw'))}, {escape_sql(r['quality_status'])},
             {escape_sql(json.dumps(r['quality_issues']))}, {escape_sql(r['verification_status'])},
             {escape_sql(r['duplicate_group'])}, {1 if r['is_duplicate'] else 0},
             {1 if holdout else 0}, {escape_sql(collected_at_val)}, {escape_sql(json.dumps(raw_meta))})
        ON DUPLICATE KEY UPDATE
            title=VALUES(title), detail_url=VALUES(detail_url), category=VALUES(category),
            transaction_type=VALUES(transaction_type), transaction_basis=VALUES(transaction_basis),
            price=VALUES(price), price_million=VALUES(price_million), area_sqm=VALUES(area_sqm),
            price_per_sqm_million=VALUES(price_per_sqm_million), district=VALUES(district),
            address_raw=VALUES(address_raw), quality_status=VALUES(quality_status),
            quality_issues=VALUES(quality_issues), verification_status=VALUES(verification_status),
            duplicate_group=VALUES(duplicate_group), is_duplicate=VALUES(is_duplicate),
            is_protected_holdout=(is_protected_holdout OR VALUES(is_protected_holdout)), raw_metadata=VALUES(raw_metadata),
            updated_at=UTC_TIMESTAMP(6);
        """
        sql_lines.append(stmt.strip())

    sql_lines.append("COMMIT;")

    return "\n".join(sql_lines)


def mysql_command(mysql_bin, host, port, database, user):
    if (host, port, database) != ("127.0.0.1", 3306, "smartprop"):
        raise ValueError("Only MySQL Local 127.0.0.1:3306/smartprop is authorized")
    return [str(mysql_bin), "--no-defaults", "--connect-timeout=5", "--protocol=TCP",
        "--host=" + host, "--port=" + str(port), "--database=" + database,
        "--user=" + user, "--default-character-set=utf8mb4", "--batch", "--raw", "--skip-column-names"]

def import_to_mysql(records, duplicate_groups, *, mysql_bin=DEFAULT_MYSQL,
                    host="127.0.0.1", port=3306, database="smartprop", user="root", password):
    cmd=mysql_command(mysql_bin, host, port, database, user)
    sql=build_import_sql(records, duplicate_groups)  # validate before any connection/write
    env=os.environ.copy()
    env["MYSQL_PWD"]=password
    # Avoid stored login-path/defaults; do not read or modify that configuration.
    env["MYSQL_TEST_LOGIN_FILE"]=str(ROOT/".scratch"/"disabled_importer_login_file")
    def execute(statement):
        result=subprocess.run(cmd, input=statement, env=env, capture_output=True,
            text=True, encoding="utf8", errors="replace", timeout=180)
        if result.returncode:
            message=result.stderr or "MySQL command failed"
            raise RuntimeError(message.replace(password,"[REDACTED]") if password else message)
        return result.stdout
    try:
        identity=json.loads(execute("SELECT JSON_OBJECT('version',VERSION(),'port',@@port,'database',DATABASE());").strip())
        if identity != {"version":"8.0.46", "port":3306, "database":"smartprop"}:
            raise RuntimeError("Unexpected MySQL identity; no import performed")
        history=[json.loads(line) for line in execute("SELECT JSON_OBJECT('version',version,'type',type,'success',success,'checksum',checksum) FROM smartprop.flyway_schema_history ORDER BY installed_rank;").splitlines() if line.strip()]
        if history != [{"version":"13","type":"BASELINE","success":1,"checksum":None},
                       {"version":"14","type":"SQL","success":1,"checksum":-1382804267}]:
            raise RuntimeError("Baseline13/V14 history differs; no import performed")
        unverified=execute("SELECT COUNT(*) FROM smartprop.external_listings WHERE verification_status<>'UNVERIFIED';").strip()
        if unverified != "0":
            raise RuntimeError("Verified/other external records exist; do not overwrite them")
        execute(sql)  # transaction with DML only; client exits on first error
        return {"rows":int(execute("SELECT COUNT(*) FROM smartprop.external_listings;").strip()),
                "unique_keys":int(execute("SELECT COUNT(DISTINCT record_key) FROM smartprop.external_listings;").strip()),
                "groups":int(execute("SELECT COUNT(*) FROM smartprop.external_duplicate_groups;").strip())}
    finally:
        env.pop("MYSQL_PWD",None)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv",type=Path,default=DEFAULT_CSV)
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=3306)
    parser.add_argument("--database",default="smartprop")
    parser.add_argument("--user",default=os.environ.get("DB_USER","root"))
    parser.add_argument("--mysql-bin",type=Path,default=DEFAULT_MYSQL)
    args=parser.parse_args()
    mysql_command(args.mysql_bin,args.host,args.port,args.database,args.user)
    with args.csv.open(encoding="utf-8-sig",newline="") as handle:
        records=list(csv.DictReader(handle))
    if not records or len({r["record_key"] for r in records}) != len(records):
        raise ValueError("CSV empty or record_key duplicated")
    groups=run_quality_gate(records)
    stats={"total":len(records),
        "VALID":sum(r["quality_status"]=="VALID" for r in records),
        "NEEDS_REVIEW":sum(r["quality_status"]=="NEEDS_REVIEW" for r in records),
        "REJECTED":sum(r["quality_status"]=="REJECTED" for r in records),
        "duplicate_groups":len(groups),"suspected_duplicates":sum(r["is_duplicate"] for r in records)}
    print(json.dumps(stats,ensure_ascii=False))
    if args.dry_run:
        build_import_sql(records,groups)
        print("DRY RUN: no database connection or writes")
        return
    password=os.environ.get("DB_PASSWORD")
    if not password:
        if not sys.stdin.isatty():raise RuntimeError("Enter credentials locally; never use password arguments")
        password=getpass.getpass("MySQL Local password (hidden): ")
    if not password:raise RuntimeError("Missing private credentials")
    result=import_to_mysql(records,groups,mysql_bin=args.mysql_bin,
        host=args.host,port=args.port,database=args.database,user=args.user,password=password)
    print(json.dumps({"import_result":result}))

if __name__=="__main__":
    try:main()
    except Exception as exc:
        secret=os.environ.get("DB_PASSWORD","")
        error=str(exc).replace(secret,"[REDACTED]") if secret else str(exc)
        print("STOP: "+error,file=sys.stderr)
        sys.exit(1)
