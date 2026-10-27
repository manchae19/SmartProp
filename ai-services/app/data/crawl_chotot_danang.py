import os
import time
import uuid
import requests
import pandas as pd

DANANG_REGION_ID = 3017
BASE_API = "https://gateway.chotot.com/v1/public/ad-listing"
SESSION_FINGERPRINT = str(uuid.uuid4())

# 1. Tách riêng các danh mục con độc lập để vét tối đa dữ liệu
CATEGORIES = {
    1020: "Nhà ở",
    1030: "Đất nền",
    1010: "Căn hộ chung cư",
    1040: "Mặt bằng / Văn phòng"
}

# 2. Định nghĩa các khoảng giá (đơn vị: VNĐ)
PRICE_RANGES = [
    (0, 1500000000),             # Dưới 1.5 tỷ
    (1500000000, 3000000000),     # 1.5 tỷ - 3 tỷ
    (3000000000, 5000000000),     # 3 tỷ - 5 tỷ
    (5000000000, 10000000000),    # 5 tỷ - 10 tỷ
    (10000000000, 25000000000),   # 10 tỷ - 25 tỷ
    (25000000000, 150000000000)   # Trên 25 tỷ (đến 150 tỷ)
]

def crawl_danang_10k(target_records=10000):
    os.makedirs("data_raw", exist_ok=True)
    all_properties = []
    seen_ids = set()  # Khử trùng tin tức thì theo ID bài đăng
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://nha.chotot.com",
        "Referer": "https://nha.chotot.com/da-nang/mua-ban-bat-dong-san"
    }

    print(f"[*] Bắt đầu tiến trình vét 10.000 tin bằng kỹ thuật Bucketing (Vùng: {DANANG_REGION_ID})...\n")

    for cg_id, cg_name in CATEGORIES.items():
        if len(all_properties) >= target_records:
            break

        for p_min, p_max in PRICE_RANGES:
            if len(all_properties) >= target_records:
                break

            min_ty = p_min / 1_000_000_000
            max_ty = p_max / 1_000_000_000
            print(f"--> Quét mục: [{cg_name}] | Khoảng giá: [{min_ty:.1f} tỷ - {max_ty:.1f} tỷ]")

            offset = 0
            limit = 50

            while len(all_properties) < target_records:
                params = {
                    "region_v2": DANANG_REGION_ID,
                    "cg": cg_id,
                    "st": "s,k",
                    "price": f"{p_min}-{p_max}",  # Truyền tham số khoảng giá vào API
                    "limit": limit,
                    "o": offset,
                    "w": 1,
                    "fingerprint": SESSION_FINGERPRINT,
                    "key_param_included": "true"
                }

                try:
                    res = requests.get(BASE_API, params=params, headers=headers, timeout=10)
                    if res.status_code != 200:
                        break

                    data = res.json()
                    ads = data.get("ads", [])

                    if not ads:
                        # Đã vét hết tin của khoảng giá này, chuyển sang khoảng giá tiếp theo
                        break

                    new_items_count = 0
                    for item in ads:
                        list_id = item.get("list_id")
                        if not list_id or list_id in seen_ids:
                            continue

                        seen_ids.add(list_id)
                        new_items_count += 1

                        price_val = item.get("price")
                        price_mil = float(price_val) / 1_000_000 if price_val else None

                        all_properties.append({
                            "list_id": list_id,
                            "title": item.get("subject"),
                            "category": cg_name,
                            "price_million": price_mil,
                            "area_sqm": item.get("size"),
                            "district": item.get("area_name"),
                            "ward": item.get("ward_name"),
                            "street": item.get("street_name"),
                            "latitude": item.get("latitude"),
                            "longitude": item.get("longitude"),
                            "rooms": item.get("rooms"),
                            "toilets": item.get("toilets"),
                            "image_url": item.get("image"),
                            "detail_url": f"https://nha.chotot.com/{list_id}.htm"
                        })

                    print(f"    + Thu thập thêm: {new_items_count} tin mới | Tổng tích lũy: {len(all_properties)} / {target_records}")
                    offset += limit
                    time.sleep(0.3)

                except Exception as e:
                    print(f"    [x] Lỗi mạng: {e}. Thử lại...")
                    time.sleep(2)
                    continue

    # Xuất ra file CSV
    df = pd.DataFrame(all_properties)
    if not df.empty:
        # Lọc sơ bộ dữ liệu nhiễu
        df = df.dropna(subset=["area_sqm", "price_million"])
        df = df[(df["area_sqm"] >= 10) & (df["price_million"] >= 100)]
        
        output_file = "danang_chotot_10k_raw2.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")

        print("\n========================================")
        print(f"[HOÀN TẤT] Đã thu thập thành công {len(df)} tin tại Đà Nẵng!")
        print(f"File lưu tại: {output_file}")
        print("\nPhân bố dữ liệu theo Quận/Huyện:")
        print(df["district"].value_counts())
        print("========================================")
    else:
        print("[!] Không thu thập được dữ liệu.")

if __name__ == "__main__":
    crawl_danang_10k(target_records=10000)