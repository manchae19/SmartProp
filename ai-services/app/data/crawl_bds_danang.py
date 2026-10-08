import os
import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://batdongsan.com.vn/nha-dat-ban-da-nang/p{page}"

def scrape_danang(max_pages=3):
    os.makedirs("data_raw", exist_ok=True)
    all_properties = []
    
    # Khởi tạo session giả lập trình duyệt Chrome mới nhất
    session = requests.Session(impersonate="chrome124")

    print(f"[*] Bắt đầu thu thập dữ liệu từ trang 1 đến trang {max_pages}...")

    for page in range(1, max_pages + 1):
        url = BASE_URL.format(page=page)
        print(f"--> Đang quét trang {page}/{max_pages}: {url}")
        
        headers = {
            "authority": "batdongsan.com.vn",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "referer": "https://www.google.com.vn/",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        try:
            # Gửi request với TLS Fingerprint của Chrome thật
            response = session.get(url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                print(f"[x] Lỗi HTTP {response.status_code} tại trang {page}.")
                time.sleep(5)
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Selector trích xuất các card tin đăng của batdongsan.com.vn
            cards = soup.select(".js__card, .re__card-full")
            
            if not cards:
                print(f"[!] Không bóc tách được card ở trang {page}. Có thể cấu trúc trang thay đổi.")
                continue

            for card in cards:
                link_tag = card.select_one("a.js__product-link-for-varnish, h3 a, a.re__card-title")
                title = link_tag.get("title") or link_tag.get_text(strip=True) if link_tag else None
                
                href = link_tag.get("href") if link_tag else ""
                detail_url = "https://batdongsan.com.vn" + href if href.startswith("/") else href

                price_tag = card.select_one(".re__card-config-price, span.price")
                area_tag = card.select_one(".re__card-config-area, span.area")
                location_tag = card.select_one(".re__card-location, .location")
                img_tag = card.select_one("img")

                price_raw = price_tag.get_text(strip=True) if price_tag else None
                area_raw = area_tag.get_text(strip=True) if area_tag else None
                location_raw = location_tag.get_text(strip=True) if location_tag else "Đà Nẵng"
                img_url = img_tag.get("data-src") or img_tag.get("src") if img_tag else None

                if title and price_raw:
                    all_properties.append({
                        "title": title,
                        "price_raw": price_raw,
                        "area_raw": area_raw,
                        "location_raw": location_raw,
                        "image_url": img_url,
                        "detail_url": detail_url
                    })

            print(f"    + Đã lấy thành công {len(cards)} tin (Tổng: {len(all_properties)} tin)")

        except Exception as e:
            print(f"[x] Gặp sự cố tại trang {page}: {e}")
            time.sleep(5)
            continue

        # Nghỉ ngẫu nhiên từ 3 đến 5 giây để Cloudflare không kích hoạt kiểm tra lại
        time.sleep(random.uniform(3.0, 5.0))

    if all_properties:
        df = pd.DataFrame(all_properties)
        df.to_csv("danang_bds_10k_raw.csv", index=False, encoding="utf-8-sig")
        print(f"\n[Hoàn tất] Đã lưu {len(df)} tin đăng vào danang_bds_10k_raw.csv")
    else:
        print("\n[!] Không thu thập được dữ liệu nào.")

if __name__ == "__main__":
    scrape_danang(max_pages=3)