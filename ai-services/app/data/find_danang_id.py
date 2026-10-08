import requests

print("[*] Đang truy vấn từ điển vùng của Chợ Tốt...")

# 1. Gọi trực tiếp API metadata vùng
try:
    res = requests.get("https://gateway.chotot.com/v1/public/regions", timeout=5).json()
    regions = res.get("regions", res if isinstance(res, list) else [])
    for r in regions:
        name = r.get("name", "") or r.get("region_name", "")
        if "đà nẵng" in name.lower() or "da nang" in name.lower():
            print(f"\n[+] TÌM THẤY TỪ METADATA: {r}")
except Exception as e:
    print(f"[-] Không đọc được endpoint /regions: {e}")

# 2. Quét mở rộng dải region_v2 từ 15000 đến 70000
print("\n[*] Đang quét mở rộng dải region_v2...")
for r in range(15000, 75000, 1000):
    try:
        url = f"https://gateway.chotot.com/v1/public/ad-listing?region_v2={r}&limit=1"
        res = requests.get(url, timeout=3).json()
        ads = res.get("ads", [])
        if ads:
            loc = f"{ads[0].get('area_name', '')} - {ads[0].get('region_name', '')}"
            print(f"-> region_v2 = {r}: {loc}")
            if "đà nẵng" in loc.lower():
                print(f"\n===> CHÍNH XÁC: region_v2 của Đà Nẵng là {r} <===")
                break
    except Exception:
        pass