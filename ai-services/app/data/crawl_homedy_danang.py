"""Small, resumable public-HTML Homedy crawler. Dependency: lxml.
No browser impersonation, login, phone-number collection or challenge bypass.
"""
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import argparse
import csv
import json
import re
import time
import unicodedata

from lxml import html

BASE = "https://homedy.com"
USER_AGENT = "SmartPropResearch/0.1"
FIELDS = [
    "list_id", "source", "source_listing_id", "source_url", "title", "category",
    "source_category", "price_raw", "price_million", "area_raw", "area_sqm",
    "address_raw", "district", "ward", "street", "latitude", "longitude",
    "rooms", "toilets", "image_url", "detail_url", "collected_at", "listing_page",
    "detail_fetched", "detail_price_raw", "legal_status", "direction",
    "price_needs_review", "area_needs_review", "region_needs_review",
    "description_mentions_billion", "detail_error",
]


def clean(value):
    return " ".join(str(value or "").split())


def norm(value):
    return "".join(c for c in unicodedata.normalize("NFD", clean(value).lower()) if unicodedata.category(c) != "Mn").replace("đ", "d")


def nodes(element, class_name):
    return element.xpath(f'.//*[contains(concat(" ", normalize-space(@class), " "), " {class_name} ")]')


def node_text(element, class_name):
    found = nodes(element, class_name)
    return clean(found[0].text_content()) if found else ""


def single_number(value):
    value = clean(value).replace("\u00a0", " ")
    # Vietnamese decimal comma; ambiguous thousands/ranges are left missing.
    if not re.fullmatch(r"\d+(?:[.,]\d+)?", value):
        return None
    return float(value.replace(",", "."))


def price_million(raw):
    s = norm(raw)
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(ty|trieu|nghin|ngan|dong|vnd)", s)
    if not match:
        return None
    number = single_number(match.group(1))
    return number * {"ty": 1000, "trieu": 1, "nghin": .001, "ngan": .001, "dong": .000001, "vnd": .000001}[match.group(2)]


def area_sqm(raw):
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*m(?:2|²)", clean(raw))
    return single_number(match.group(1)) if match else None


def category_from_url(url):
    path = urlparse(url).path
    for prefix, label in [("/ban-nha-rieng", "Nhà ở"), ("/ban-nha-mat-pho", "Nhà ở"), ("/ban-biet-thu", "Nhà ở"), ("/ban-can-ho", "Căn hộ chung cư"), ("/ban-dat", "Đất nền"), ("/ban-van-phong", "Mặt bằng / Văn phòng")]:
        if path.startswith(prefix):
            return label
    return "Chưa xác định"


def address_parts(raw):
    district = ward = street = ""
    for part in raw.split(","):
        part = clean(part)
        if re.search(r"\b(Quận|Huyện)\s+", part, re.I):
            district = re.search(r"\b(?:Quận|Huyện)\s+.+", part, re.I).group(0)
        elif re.search(r"\b(Phường|Xã)\s+", part, re.I):
            ward = re.search(r"\b(?:Phường|Xã)\s+.+", part, re.I).group(0)
        elif re.match(r"^Đường\b", part, re.I):
            street = part
    return district, ward, street


def listing_records(page_html, page_url):
    document = html.fromstring(page_html)
    cards = nodes(document, "product-item")
    records = []
    for card in cards:
        anchors = card.xpath('.//a[contains(concat(" ",normalize-space(@class)," ")," title ")]')
        if not anchors:
            continue
        anchor = anchors[0]
        url = urljoin(BASE + "/", anchor.get("href", ""))
        match = re.search(r"-es(\d+)$", urlparse(url).path)
        if urlparse(url).hostname != "homedy.com" or not match:
            continue
        listing_id = match.group(1)
        raw_price, raw_area = node_text(card, "price"), node_text(card, "acreage")
        address = node_text(card, "address")
        district, ward, street = address_parts(address)
        images = card.xpath(".//img")
        image = (images[0].get("data-src") or images[0].get("src")) if images else ""
        record = dict.fromkeys(FIELDS, "")
        record.update(
            list_id=f"homedy:{listing_id}", source="homedy", source_listing_id=listing_id,
            source_url=url, detail_url=url, title=clean(anchor.get("title") or anchor.text_content()),
            category=category_from_url(url), price_raw=raw_price, price_million=price_million(raw_price),
            area_raw=raw_area, area_sqm=area_sqm(raw_area), address_raw=address,
            district=district, ward=ward, street=street, image_url=image,
            collected_at=datetime.now(timezone.utc).isoformat(), listing_page=page_url,
            detail_fetched=False, description_mentions_billion=False,
        )
        records.append(record)
    return records


def enrich(record, page_html):
    document = html.fromstring(page_html)
    headings = document.xpath("//h1")
    if not headings:
        raise ValueError("Detail page missing h1")
    container = headings[0].getparent()
    record["title"] = clean(headings[0].text_content())
    addresses = container.xpath('./div[contains(concat(" ",normalize-space(@class)," ")," address ")]')
    if addresses:
        raw_address = clean(addresses[0].text_content())
        record["address_raw"] = raw_address
        record["district"], record["ward"], _ = address_parts(raw_address)
        street_nodes = addresses[0].xpath('.//*[@itemprop="streetAddress"]')
        if street_nodes:
            street = clean(street_nodes[0].text_content())
            match = re.search(r"Đường\s+.+", street)
            record["street"] = match.group(0) if match else ""
    for attribute in nodes(document, "product-attributes--item"):
        spans = attribute.xpath("./span")
        if len(spans) < 2:
            continue
        label, value = clean(spans[0].text_content()), clean(spans[1].text_content())
        key = {"Loại hình": "source_category", "Tình trạng pháp lý": "legal_status", "Hướng nhà": "direction", "Số phòng ngủ": "rooms", "Phòng ngủ": "rooms", "Số phòng tắm": "toilets", "Số toilet": "toilets"}.get(label)
        if key:
            record[key] = single_number(value) if key in {"rooms", "toilets"} else value
    prices = document.xpath('//li[label[normalize-space(.)="Giá"]]/strong')
    if prices:
        record["detail_price_raw"] = clean(prices[0].text_content())
    description = node_text(document, "description")
    record["description_mentions_billion"] = bool(re.search(r"\bty\b", norm(description)))
    record["detail_fetched"] = True
    return record


def quality_flags(record):
    price, area = record.get("price_million"), record.get("area_sqm")
    record["price_needs_review"] = price is None or price <= 0 or price < 100
    if price is not None and area and not 2 <= price / area <= 300:
        record["price_needs_review"] = True
    detail_price = price_million(record.get("detail_price_raw", ""))
    if detail_price is not None and price is not None and abs(detail_price - price) > .01:
        record["price_needs_review"] = True
    if record.get("description_mentions_billion") and price is not None and price < 100:
        record["price_needs_review"] = True
    record["area_needs_review"] = area is None or not 20 <= area <= 1000
    record["region_needs_review"] = "da nang" not in norm(record.get("address_raw"))


class Client:
    def __init__(self, delay):
        self.delay, self.last_request, self.robot = delay, 0, None

    def get(self, url, check_robots=True):
        if urlparse(url).hostname != "homedy.com":
            raise RuntimeError("Refusing off-site request")
        if check_robots and not self.robot.can_fetch(USER_AGENT, url):
            raise RuntimeError(f"robots.txt disallows {url}")
        for attempt in range(2):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=20) as response:
                    if urlparse(response.url).hostname != "homedy.com":
                        raise RuntimeError("Unexpected off-site redirect")
                    body = response.read().decode("utf-8", errors="replace")
                    if "Just a moment" in body or "cf-chl-" in body:
                        raise RuntimeError("Challenge page; stopping")
                    return body
            except HTTPError as exc:
                if exc.code in {401, 403, 429}:
                    raise RuntimeError(f"HTTP {exc.code}; stop. Retry-After={exc.headers.get('Retry-After')}") from exc
                if exc.code < 500 or attempt == 1:
                    raise
            except (URLError, TimeoutError):
                if attempt == 1:
                    raise
        raise RuntimeError("Request failed")

    def load_robots(self):
        raw = self.get(BASE + "/robots.txt", check_robots=False)
        # Some deployments serve literal escaped CRLF separators.
        raw = raw.replace("\\r\\n", "\n")
        self.robot = RobotFileParser(BASE + "/robots.txt")
        self.robot.parse(raw.splitlines())
        crawl_delay = self.robot.crawl_delay(USER_AGENT)
        if crawl_delay:
            self.delay = max(self.delay, crawl_delay)


def save(records, output):
    temporary = output.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    # Windows may temporarily lock the CSV (Excel, preview or antivirus).
    # Retry replacement without rewriting the completed temporary file.
    for attempt in range(1, 11):
        try:
            temporary.replace(output)
            return
        except PermissionError as exc:
            if attempt == 10:
                raise PermissionError(
                    f"Khong the thay the {output}. "
                    "Hay dong Excel hoac ung dung dang mo CSV. "
                    f"Du lieu moi van nam tai {temporary}."
                ) from exc
            print(
                f"[Luu CSV] File dang bi khoa. "
                f"Thu lai {attempt}/10 sau 3 giay...",
                flush=True,
            )
            time.sleep(3)


def crawl(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "homedy_records.csv"
    state_path = args.output_dir / "homedy_checkpoint.json"
    existing = []
    if output.exists():
        with output.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS:
                raise ValueError("Existing output has a different schema; use another output directory")
            existing = list(reader)
    seen = {r["list_id"] for r in existing}
    if len(seen) != len(existing):
        raise ValueError("Duplicate IDs in existing output")
    checkpoint = json.loads(state_path.read_text()) if state_path.exists() else {}
    start = args.start_page or (checkpoint.get("next_page", 1) if checkpoint.get("listing") == args.listing else 1)
    client = Client(args.delay)
    client.load_robots()
    page_signatures, new_count = set(), 0
    try:
        for page in range(start, start + args.pages):
            url = BASE + args.listing + (f"/p{page}" if page > 1 else "")
            records = listing_records(client.get(url), url)
            if not records:
                print(f"Page {page}: no parsed cards; stop and check selector/end of listings", flush=True)
                break
            signature = frozenset(r["list_id"] for r in records)
            if signature in page_signatures:
                print("Repeated page IDs; stop", flush=True)
                break
            page_signatures.add(signature)
            added, fully_processed = 0, True
            for record in records:
                if record["list_id"] in seen:
                    continue
                if new_count >= args.max_new:
                    fully_processed = False
                    break
                if args.details:
                    try:
                        enrich(record, client.get(record["detail_url"]))
                    except RuntimeError:
                        raise
                    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                        record["detail_error"] = f"{type(exc).__name__}: {exc}"
                quality_flags(record)
                existing.append(record)
                seen.add(record["list_id"])
                added += 1
                new_count += 1
                save(existing, output)
            checkpoint = {"listing": args.listing, "next_page": page + 1 if fully_processed else page}
            state_path.write_text(json.dumps(checkpoint), encoding="utf-8")
            print(f"Page {page}: cards={len(records)}, new={added}, run_new={new_count}, total={len(existing)}", flush=True)
            if new_count >= args.max_new:
                break
    finally:
        if existing:
            save(existing, output)
        print(f"Saved total={len(existing)}; new_this_run={new_count}; CSV={output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect a small Homedy Da Nang sample")
    parser.add_argument("--listing", default="/ban-nha-rieng-da-nang")
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--max-new", type=int, default=10)
    parser.add_argument("--start-page", type=int)
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--delay", type=float, default=2)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "data_raw" / "homedy")
    args = parser.parse_args()
    if not re.fullmatch(r"/ban-[a-z0-9-]*da-nang", args.listing):
        parser.error("Use a Homedy sale-listing path ending in da-nang")
    if args.pages <= 0 or args.max_new <= 0 or args.delay < 1 or (args.start_page is not None and args.start_page <= 0):
        parser.error("pages/max-new/start-page must be positive; delay must be >= 1")
    try:
        crawl(args)
    except KeyboardInterrupt:
        print("Stopped by user; completed records were retained")
    except Exception as exc:
        parser.exit(1, f"Stopped: {exc}\n")
