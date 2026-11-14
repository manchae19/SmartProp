"""Seed high-quality, authentic Points of Interest (POIs) across Da Nang districts.
Used by Backend PoiService / PointOfInterestRepository and Frontend HomeGIS / PropertyMap.
"""
import sys
import uuid
from pathlib import Path
import pymysql

# Load credentials from .env
ROOT = Path(__file__).resolve().parents[2]
env_vars = {}
env_file = ROOT / '.env'
if env_file.exists():
    import re
    for line in env_file.read_text(encoding='utf-8-sig').splitlines():
        m = re.match(r'^\s*(?:export\s+)?(DB_USER|DB_PASSWORD)\s*=\s*(.*)$', line)
        if m:
            env_vars[m.group(1)] = m.group(2).strip().strip('"\'')

POIS = [
    # --- SƠN TRÀ ---
    ('Bãi tắm biển Mỹ Khê', 'PARK', 16.0601, 108.2464, 'st-beach-mykhe'),
    ('Bãi tắm Phạm Văn Đồng', 'PARK', 16.0715, 108.2455, 'st-beach-pvd'),
    ('Bãi biển Mân Thái', 'PARK', 16.0885, 108.2475, 'st-beach-manthai'),
    ('Công viên Biển Đông', 'PARK', 16.0705, 108.2460, 'st-park-biendong'),
    ('Bệnh viện 199 - Bộ Công An', 'HOSPITAL', 16.0700, 108.2380, 'st-hosp-199'),
    ('Trung tâm Y tế Quận Sơn Trà', 'HOSPITAL', 16.0872, 108.2325, 'st-hosp-sontra'),
    ('Trạm Y tế Phường Phước Mỹ', 'HOSPITAL', 16.0680, 108.2395, 'st-hosp-phuocmy'),
    ('Trạm Y tế Phường An Hải Bắc', 'HOSPITAL', 16.0785, 108.2390, 'st-hosp-anhaibac'),
    ('Trường THPT Hoàng Hoa Thám', 'SCHOOL', 16.0792, 108.2345, 'st-sch-hoanghoatham'),
    ('Trường THPT Chuyên Lê Quý Đôn', 'SCHOOL', 16.0535, 108.2370, 'st-sch-lequydon'),
    ('Trường THCS Cao Thắng', 'SCHOOL', 16.0855, 108.2378, 'st-sch-caothang'),
    ('Trường Tiểu học Ngô Mây', 'SCHOOL', 16.0880, 108.2420, 'st-sch-ngomay'),
    ('Trường Tiểu học Phước Mỹ', 'SCHOOL', 16.0688, 108.2405, 'st-sch-phuocmy'),
    ('Trường Tiểu học Lê Lai', 'SCHOOL', 16.0830, 108.2340, 'st-sch-lelai'),
    ('Trường THCS Phạm Ngọc Thạch', 'SCHOOL', 16.0760, 108.2350, 'st-sch-phamngocthach'),
    ('Chợ Phước Mỹ', 'SUPERMARKET', 16.0695, 108.2412, 'st-mkt-phuocmy'),
    ('Chợ Mai Sơn Trà', 'SUPERMARKET', 16.0910, 108.2415, 'st-mkt-chomai'),
    ('Chợ Đêm Sơn Trà', 'SUPERMARKET', 16.0620, 108.2310, 'st-mkt-chodem'),
    ('Vincom Plaza Đà Nẵng', 'SUPERMARKET', 16.0717, 108.2291, 'st-mkt-vincom'),
    ('WinMart+ Trần Hưng Đạo', 'SUPERMARKET', 16.0750, 108.2320, 'st-mkt-winmart'),
    ('Cầu Sông Hàn', 'TRANSPORT', 16.0718, 108.2275, 'st-tra-causonghan'),
    ('Cầu Rồng', 'TRANSPORT', 16.0611, 108.2272, 'st-tra-caurong'),
    ('Cầu Thuận Phước', 'TRANSPORT', 16.0965, 108.2225, 'st-tra-cauthuanphuoc'),
    ('Cảng cá & Âu thuyền Thọ Quang', 'TRANSPORT', 16.0980, 108.2390, 'st-tra-cangthoquang'),

    # --- HẢI CHÂU ---
    ('Bệnh viện Đa khoa Đà Nẵng', 'HOSPITAL', 16.0735, 108.2160, 'hc-hosp-danang'),
    ('Bệnh viện C Đà Nẵng', 'HOSPITAL', 16.0740, 108.2175, 'hc-hosp-c'),
    ('Bệnh viện Phụ sản - Nhi (cơ sở 2)', 'HOSPITAL', 16.0755, 108.2185, 'hc-hosp-phusan2'),
    ('Bệnh viện Hoàn Mỹ Đà Nẵng', 'HOSPITAL', 16.0585, 108.2090, 'hc-hosp-hoanmy'),
    ('Bệnh viện Quốc tế Vinmec Đà Nẵng', 'HOSPITAL', 16.0315, 108.2163, 'hc-hosp-vinmec'),
    ('Trường THPT Phan Châu Trinh', 'SCHOOL', 16.0700, 108.2195, 'hc-sch-phanchautrinh'),
    ('Đại học Sư phạm Kỹ thuật Đà Nẵng', 'SCHOOL', 16.0775, 108.2165, 'hc-sch-spkt'),
    ('Đại học Ngoại ngữ Đà Nẵng', 'SCHOOL', 16.0420, 108.2155, 'hc-sch-nn'),
    ('Trường THCS Trưng Vương', 'SCHOOL', 16.0685, 108.2215, 'hc-sch-trungvuong'),
    ('Trường Tiểu học Phù Đổng', 'SCHOOL', 16.0670, 108.2200, 'hc-sch-phudong'),
    ('Chợ Hàn Đà Nẵng', 'SUPERMARKET', 16.0682, 108.2241, 'hc-mkt-chohan'),
    ('Chợ Cồn', 'SUPERMARKET', 16.0685, 108.2140, 'hc-mkt-chocon'),
    ('Chợ Mới Hải Châu', 'SUPERMARKET', 16.0550, 108.2180, 'hc-mkt-chomoi'),
    ('Siêu thị Go! Đà Nẵng (Big C)', 'SUPERMARKET', 16.0665, 108.2135, 'hc-mkt-godanang'),
    ('Siêu thị Lotte Mart Đà Nẵng', 'SUPERMARKET', 16.0350, 108.2270, 'hc-mkt-lotte'),
    ('Công viên APEC Đà Nẵng', 'PARK', 16.0580, 108.2245, 'hc-park-apec'),
    ('Công viên 29 Tháng 3', 'PARK', 16.0610, 108.2030, 'hc-park-29thang3'),
    ('Công viên Châu Á (Asia Park)', 'PARK', 16.0371, 108.2242, 'hc-park-asiapark'),
    ('Sân bay Quốc tế Đà Nẵng', 'TRANSPORT', 16.0538, 108.1994, 'hc-tra-sanbay'),
    ('Ga đường sắt Đà Nẵng', 'TRANSPORT', 16.0705, 108.2105, 'hc-tra-gatau'),
    ('Cầu Trần Thị Lý', 'TRANSPORT', 16.0515, 108.2285, 'hc-tra-cautranthily'),
    ('Cầu Tiên Sơn', 'TRANSPORT', 16.0335, 108.2360, 'hc-tra-cautiensun'),

    # --- THANH KHÊ ---
    ('Trung tâm Y tế Quận Thanh Khê', 'HOSPITAL', 16.0630, 108.1925, 'tk-hosp-thanhkhe'),
    ('Bệnh viện Đa khoa Bình Dân', 'HOSPITAL', 16.0680, 108.2015, 'tk-hosp-binhdan'),
    ('Trường THPT Thái Phiên', 'SCHOOL', 16.0710, 108.2025, 'tk-sch-thaiphien'),
    ('Trường THPT Thanh Khê', 'SCHOOL', 16.0480, 108.1880, 'tk-sch-thanhkhe'),
    ('Đại học Thể dục Thể thao Đà Nẵng', 'SCHOOL', 16.0655, 108.1950, 'tk-sch-tdtt'),
    ('Chợ Siêu thị Đà Nẵng', 'SUPERMARKET', 16.0675, 108.2060, 'tk-mkt-chosieuthi'),
    ('Chợ Thanh Khê', 'SUPERMARKET', 16.0690, 108.1940, 'tk-mkt-chothanhkhe'),
    ('Siêu thị Co.opmart Đà Nẵng', 'SUPERMARKET', 16.0645, 108.1960, 'tk-mkt-coopmart'),
    ('Bãi biển Nguyễn Tất Thành (Vịnh Đà Nẵng)', 'PARK', 16.0750, 108.1950, 'tk-park-nguyentatthanh'),

    # --- NGŨ HÀNH SƠN ---
    ('Bệnh viện Phụ sản - Nhi Đà Nẵng', 'HOSPITAL', 16.0300, 108.2395, 'nhs-hosp-phusannhi'),
    ('Trung tâm Y tế Quận Ngũ Hành Sơn', 'HOSPITAL', 16.0090, 108.2520, 'nhs-hosp-nguhanhson'),
    ('Đại học Kinh tế Đà Nẵng', 'SCHOOL', 16.0504, 108.2361, 'nhs-sch-kinhte'),
    ('Đại học FPT Đà Nẵng', 'SCHOOL', 15.9720, 108.2610, 'nhs-sch-fpt'),
    ('Trường Đại học Y Dược Đà Nẵng', 'SCHOOL', 16.0350, 108.2430, 'nhs-sch-yduoc'),
    ('Trường Quốc tế Singapore (SIS)', 'SCHOOL', 16.0210, 108.2480, 'nhs-sch-sis'),
    ('Chợ Bắc Mỹ An', 'SUPERMARKET', 16.0440, 108.2410, 'nhs-mkt-bacmyan'),
    ('Chợ Non Nước', 'SUPERMARKET', 16.0060, 108.2560, 'nhs-mkt-nonnuoc'),
    ('Khu danh thắng Ngũ Hành Sơn', 'PARK', 16.0050, 108.2630, 'nhs-park-nguhanhson'),
    ('Bãi tắm Bắc Mỹ An', 'PARK', 16.0460, 108.2480, 'nhs-park-bacmyan'),

    # --- CẨM LỆ ---
    ('Trung tâm Y tế Quận Cẩm Lệ', 'HOSPITAL', 16.0220, 108.2070, 'cl-hosp-camle'),
    ('Bệnh viện Phục hồi chức năng', 'HOSPITAL', 16.0290, 108.2110, 'cl-hosp-phuchoichucnang'),
    ('Trường THPT Hòa Vang', 'SCHOOL', 16.0240, 108.2050, 'cl-sch-hoavang'),
    ('Chợ Đầu mối Hòa Cường', 'SUPERMARKET', 16.0310, 108.2185, 'cl-mkt-hoacuong'),
    ('Chợ Cẩm Lệ', 'SUPERMARKET', 16.0210, 108.2040, 'cl-mkt-camle'),
    ('Siêu thị Mega Market Đà Nẵng (Metro)', 'SUPERMARKET', 16.0280, 108.2140, 'cl-mkt-megamarket'),

    # --- LIÊN CHIỂU ---
    ('Trung tâm Y tế Quận Liên Chiểu', 'HOSPITAL', 16.0650, 108.1560, 'lc-hosp-lienchieu'),
    ('Bệnh viện Ung bướu Đà Nẵng', 'HOSPITAL', 16.0560, 108.1630, 'lc-hosp-ungbuou'),
    ('Đại học Bách khoa Đà Nẵng', 'SCHOOL', 16.0740, 108.1500, 'lc-sch-bachkhoa'),
    ('Đại học Sư phạm Đà Nẵng', 'SCHOOL', 16.0610, 108.1590, 'lc-sch-supham'),
    ('Chợ Hòa Khánh', 'SUPERMARKET', 16.0710, 108.1480, 'lc-mkt-hoakhanh'),
    ('Bến xe Trung tâm Đà Nẵng', 'TRANSPORT', 16.0580, 108.1750, 'lc-tra-benxetrungtam'),
    ('Bãi biển Xuân Thiều (Nam Ô)', 'PARK', 16.0950, 108.1380, 'lc-park-xuanthieu'),
]

def run():
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user=env_vars.get('DB_USER', 'root'),
        password=env_vars.get('DB_PASSWORD', ''),
        database='smartprop',
        autocommit=True
    )
    with conn.cursor() as cur:
        # Clean any old test POIs
        cur.execute("DELETE FROM points_of_interest WHERE source_name = 'smartprop-danang-curated' OR id LIKE 'test-poi%';")

        inserted = 0
        for name, cat, lat, lon, ext_id in POIS:
            poi_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'smartprop.danang.poi.{ext_id}'))
            point_wkt = f'POINT({lon:.6f} {lat:.6f})'
            cur.execute("""
                INSERT INTO points_of_interest (id, name, category, location, source_name, external_id, observed_at)
                VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326, 'axis-order=long-lat'), %s, %s, UTC_TIMESTAMP(6))
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    category = VALUES(category),
                    location = VALUES(location),
                    observed_at = VALUES(observed_at);
            """, (poi_id, name, cat, point_wkt, 'smartprop-danang-curated', ext_id))
            inserted += 1

        cur.execute("SELECT count(*) FROM points_of_interest;")
        total = cur.fetchone()[0]
        print(f"SUCCESS: Seeded {inserted} authentic Da Nang POIs. Total POIs in database: {total}")

if __name__ == '__main__':
    run()
