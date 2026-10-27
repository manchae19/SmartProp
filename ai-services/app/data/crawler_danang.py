import os
import json
import time
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm

class DanangPropertyCrawler:
    def __init__(self):
        # Base URL cho khu vực Đà Nẵng (Ví dụ cấu trúc phân trang chuẩn)
        self.base_url = "https://batdongsan.com.vn/nha-dat-ban-da-nang/p{page}"
        self.start_page = 1
        self.max_pages = 500       # 500 trang x 20 tin/trang ~ 10.000 records
        self.output_dir = "raw_batches"
        self.state_file = "crawler_checkpoint.json"
        self.batch_size = 10       # Lưu checkpoint sau mỗi 10 trang
        
        os.makedirs(self.output_dir, exist_ok=True)
        self.ua = UserAgent()
        self.session = requests.Session()

    def get_headers(self):
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com.vn/",
            "Connection": "keep-alive"
        }

    def load_checkpoint(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("current_page", self.start_page)
            except Exception:
                return self.start_page
        return self.start_page

    def save_checkpoint(self, next_page):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({"current_page": next_page}, f)

    def parse_card(self, card):
        try:
            # 1. Tiêu đề và Link chi tiết
            title_tag = card.select_one("h3 a, .title a, a.re__card-title")
            title = title_tag.get_text(strip=True) if title_tag else None
            detail_url = title_tag.get("href") if title_tag else None
            if detail_url and not detail_url.startswith("http"):
                detail_url = "https://batdongsan.vn" + detail_url

            # 2. Giá niêm yết (Raw text: "3.2 tỷ", "850 triệu", "Thỏa thuận")
            price_tag = card.select_one(".price, .re__card-config-price, span.pro-price")
            price_raw = price_tag.get_text(strip=True) if price_tag else None

            # 3. Diện tích (Raw text: "85 m²", "100 m2")
            area_tag = card.select_one(".area, .re__card-config-area, span.pro-area")
            area_raw = area_tag.get_text(strip=True) if area_tag else None

            # 4. Địa chỉ / Vị trí hành chính (Quận/Huyện tại Đà Nẵng)
            loc_tag = card.select_one(".location, .re__card-location, span.pro-location")
            location_raw = loc_tag.get_text(strip=True) if loc_tag else "Đà Nẵng"

            # 5. Hình ảnh đại diện (Lưu URL Cloud cho Siamese / YOLOv8 sau này)
            img_tag = card.select_one("img")
            img_url = None
            if img_tag:
                img_url = img_tag.get("data-src") or img_tag.get("data-original") or img_tag.get("src")

            if not title:
                return None

            return {
                "title": title,
                "price_raw": price_raw,
                "area_raw": area_raw,
                "location_raw": location_raw,
                "image_url": img_url,
                "detail_url": detail_url
            }
        except Exception:
            return None

    def execute(self):
        current_page = self.load_checkpoint()
        print(f"[*] Bắt đầu tiến trình cào dữ liệu từ trang {current_page} đến {self.max_pages}...")
        
        batch_records = []
        progress_bar = tqdm(total=self.max_pages, initial=current_page - 1, desc="Thu thập tin")

        while current_page <= self.max_pages:
            url = self.base_url.format(page=current_page)
            
            try:
                response = self.session.get(url, headers=self.get_headers(), timeout=12)
                
                # Kiểm tra phản hồi chống bot
                if response.status_code == 429:
                    tqdm.write(f"[!] Bị giới hạn tốc độ (HTTP 429) ở trang {current_page}. Tạm dừng 90 giây...")
                    time.sleep(90)
                    continue
                elif response.status_code in [403, 503]:
                    tqdm.write(f"[!] Bị chặn IP (HTTP {response.status_code}) ở trang {current_page}. Đổi headers...")
                    time.sleep(30)
                    continue
                elif response.status_code != 200:
                    tqdm.write(f"[!] Bỏ qua trang {current_page} (HTTP Status {response.status_code})")
                    current_page += 1
                    progress_bar.update(1)
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                
                # Lấy tất cả card tin đăng
                cards = soup.select(".product-item, .re__card-full, .item-list")
                if not cards:
                    cards = soup.select(".list-product .item")

                for card in cards:
                    record = self.parse_card(card)
                    if record:
                        batch_records.append(record)

            except requests.exceptions.RequestException as e:
                tqdm.write(f"[x] Lỗi mạng tại trang {current_page}: {str(e)}. Thử lại sau 10s...")
                time.sleep(10)
                continue

            # Xuất batch dữ liệu định kỳ
            if current_page % self.batch_size == 0 or current_page == self.max_pages:
                if batch_records:
                    batch_path = os.path.join(self.output_dir, f"batch_{current_page}.csv")
                    pd.DataFrame(batch_records).to_csv(batch_path, index=False, encoding="utf-8-sig")
                    batch_records = []
                self.save_checkpoint(current_page + 1)

            current_page += 1
            progress_bar.update(1)

            # Jitter delay ngẫu nhiên từ 2.0s đến 4.5s
            time.sleep(random.uniform(2.0, 4.5))

        progress_bar.close()
        print("[+] Thu thập hoàn tất 500 trang dữ liệu!")

if __name__ == "__main__":
    crawler = DanangPropertyCrawler()
    crawler.execute()