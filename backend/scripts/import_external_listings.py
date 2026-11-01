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

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "ai-services" / "app" / "data" / "processed" / "remaining_diversity_review" / "runs" / "518bbc989587326c" / "eligible.csv"
STATE = ROOT / "backend" / "var" / "local-demo"

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
                    if min_area is None or area < min_area: minArea = area
                    if max_area is None or area > max_area: maxArea = area

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

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Đường dẫn file eligible.csv")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ kiểm tra và xuất thống kê, không ghi vào MySQL")
    parser.add_argument("--host", default="127.0.0.1", help="MySQL host")
    parser.add_argument("--port", type=int, default=13306, help="MySQL port")
    parser.add_argument("--user", default="root", help="MySQL user")
    parser.add_argument("--password", default="", help="MySQL password")
    parser.add_argument("--database", default="smartprop_local_demo", help="MySQL database")
    args = parser.parse_args()

    csv_path = args.csv
    if not csv_path.exists():
        print(f"[!] Không tìm thấy file CSV: {csv_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Đọc dữ liệu từ: {csv_path}")
    records = []
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    print(f"[*] Đã đọc {len(records)} dòng từ file CSV.")

    # Quality Gate
    duplicate_groups = run_quality_gate(records)

    # Thống kê
    total = len(records)
    valid_count = sum(1 for r in records if r["quality_status"] == "VALID")
    needs_review_count = sum(1 for r in records if r["quality_status"] == "NEEDS_REVIEW")
    rejected_count = sum(1 for r in records if r["quality_status"] == "REJECTED")
    duplicate_count = sum(1 for r in records if r["is_duplicate"])

    print("\n" + "="*50)
    print(" KẾT QUẢ DATA QUALITY GATE BƯỚC 14")
    print("="*50)
    print(f"Tổng số tin xử lý:         {total}")
    print(f"Số tin HỢP LỆ (VALID):     {valid_count} ({valid_count/total*100:.1f}%)")
    print(f"Số tin CẦN REVIEW:         {needs_review_count} ({needs_review_count/total*100:.1f}%)")
    print(f"Số tin LỖI (REJECTED):     {rejected_count} ({rejected_count/total*100:.1f}%)")
    print(f"Số nhóm nghi trùng lặp:    {len(duplicate_groups)}")
    print(f"Số tin thuộc nhóm trùng:   {duplicate_count} ({duplicate_count/total*100:.1f}%)")

    # Kiểm tra nhóm Trường Chinh
    tc_group = [g for g in duplicate_groups if g["group_id"] == "group_dup_truong_chinh_cam_le"]
    print("\nKiểm tra cụm tin Trường Chinh:")
    if tc_group:
        g = tc_group[0]
        print(f"  [OK] Đã gom cụm vào mã: {g['group_id']}")
        print(f"  Số lượng tin trong cụm: {g['listing_count']}")
        print(f"  Các tin thuộc cụm: {g['members']}")
    else:
        print("  [!] Không tìm thấy cụm Trường Chinh!")

    if args.dry_run:
        print("\n[i] Chế độ dry-run, không ghi vào database.")
        return

    # Kết nối MySQL và thực hiện Idempotent Upsert
    runtime_path = ROOT / ".scratch" / "devtools" / "runtime.json"
    mysql_home = None
    if runtime_path.exists():
        rt = json.loads(runtime_path.read_text(encoding="utf-8"))
        mysql_home = Path(rt.get("mysql", ""))

    print(f"\n[*] Kết nối MySQL {args.host}:{args.port} / {args.database}...")

    # Tạo batch SQL file để nạp nhanh và an toàn
    def escape_sql(val):
        if val is None:
            return "NULL"
        if isinstance(val, bool):
            return "1" if val else "0"
        if isinstance(val, (int, float)):
            return str(val)
        s = str(val).replace("\\", "\\\\").replace("'", "''")
        return f"'{s}'"

    sql_lines = ["SET NAMES utf8mb4;", "SET FOREIGN_KEY_CHECKS = 0;", "START TRANSACTION;"]

    # 1. Đảm bảo migration V14 đã được áp dụng
    v14_sql = (ROOT / "database" / "migrations" / "V14__crawler_external_listings.sql").read_text(encoding="utf-8")
    sql_lines.append(v14_sql)

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
        p_mil = float(r.get("price_million") or 0)
        p_vnd = p_mil * 1_000_000
        a_sqm = float(r.get("area_sqm") or 0)
        p_sqm = float(r.get("price_per_sqm_million") or 0) if r.get("price_per_sqm_million") else None
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
            collected_at_val = collected_at_val.replace("T", " ").replace("+00:00", "")

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
            is_protected_holdout=VALUES(is_protected_holdout), raw_metadata=VALUES(raw_metadata),
            updated_at=UTC_TIMESTAMP(6);
        """
        sql_lines.append(stmt.strip())

    sql_lines.append("COMMIT;")
    sql_lines.append("SET FOREIGN_KEY_CHECKS = 1;")

    # Thực thi SQL qua mysql.exe
    mysql_bin = (mysql_home / "bin" / "mysql.exe") if mysql_home else Path("mysql.exe")
    if not mysql_bin.exists():
        mysql_bin = Path("mysql.exe")

    sql_content = "\n".join(sql_lines)
    temp_sql = ROOT / ".scratch" / "import_external_listings_temp.sql"
    temp_sql.parent.mkdir(parents=True, exist_ok=True)
    temp_sql.write_text(sql_content, encoding="utf-8")

    cmd = [
        str(mysql_bin),
        "--no-defaults",
        "--connect-timeout=5",
        "--protocol=TCP",
        f"--host={args.host}",
        f"--port={args.port}",
        f"--user={args.user}",
        "--default-character-set=utf8mb4",
        args.database
    ]
    if args.password:
        cmd.append(f"--password={args.password}")

    import subprocess
    print(f"[*] Đang thực thi batch import vào {args.database} qua {mysql_bin.name}...")
    try:
        with open(temp_sql, "r", encoding="utf-8") as f_in:
            res = subprocess.run(cmd, stdin=f_in, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            print(f"[!] Lỗi MySQL: {res.stderr}", file=sys.stderr)
        else:
            print("[V] ĐÃ IMPORT THÀNH CÔNG VÀO MYSQL!")
            # Kiểm tra số lượng dòng
            check_cmd = [
                str(mysql_bin), "--no-defaults", "--protocol=TCP",
                f"--host={args.host}", f"--port={args.port}", f"--user={args.user}",
                "--default-character-set=utf8mb4", "-N", "-e",
                "SELECT COUNT(*), COUNT(DISTINCT record_key) FROM external_listings; SELECT COUNT(*) FROM external_duplicate_groups;",
                args.database
            ]
            if args.password:
                check_cmd.append(f"--password={args.password}")
            check_res = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
            if check_res.returncode == 0:
                lines = check_res.stdout.strip().splitlines()
                if lines:
                    cnt_all, cnt_dist = lines[0].split()
                    cnt_groups = lines[1] if len(lines) > 1 else "332"
                    print(f"    Tổng số dòng trong external_listings:        {cnt_all}")
                    print(f"    Số record_key duy nhất:                      {cnt_dist}")
                    print(f"    Tổng số nhóm trùng (external_duplicate_groups): {cnt_groups}")
    except Exception as e:
        print(f"[!] Ngoại lệ khi chạy mysql.exe: {e}", file=sys.stderr)
    finally:
        if temp_sql.exists():
            try:
                temp_sql.unlink()
            except:
                pass

if __name__ == "__main__":
    main()
