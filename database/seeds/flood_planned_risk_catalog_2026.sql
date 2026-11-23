-- Danh muc vi tri co nguy co ngap ung khi mua lon tren dia ban thanh pho Da Nang.
--
-- Nguon: Phu luc VIII kem Quyet dinh 2322/QD-UBND ngay 26/05/2026, trang 33-35.
--   https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf
--
-- Chay lai duoc: moi dong co id co dinh PL8-<nhom>-<stt> va dung
-- INSERT ... ON DUPLICATE KEY UPDATE, nen chay bao nhieu lan cung chi co mot ban ghi
-- cho moi vi tri. Khong xoa cac ban ghi ngap da nhap truoc do.
--
-- Cot current_unit la phuong/xa hien tai sau sap xep 2025, doi chieu qua
-- backend/scripts/danang_admin_mapping_v1.json (NQ 1659/NQ-UBTVQH15).
-- Dong chua doi chieu duoc dia ban co current_unit NULL va area_basis
-- 'NO_AREA_IN_SOURCE': van nam trong danh muc, hien thi "Chua doi chieu dia ban".
--
-- area_basis = 'OSM_ADDRESS': dia ban xac dinh bang dia chi duong/to dan pho tren
-- OpenStreetMap Nominatim (addressdetails), doi chieu cheo voi trang gioi thieu
-- phuong An Hai (https://anhai.danang.gov.vn/gioi-thieu/gioi-thieu-chung).
-- Nam dong duoc doi chieu o nhom IV (Son Tra cu):
--   PL8-IV-01  Bung binh Pham Van Dong - Ngo Quyen  -> Phuong An Hai
--              Moi diem doc Pham Van Dong va quanh giao lo voi Ngo Quyen deu
--              thuoc to dan pho cua An Hai (An My 2, An Trung 1, An Don 2).
--   PL8-IV-04  Tran Hung Dao giao Tran Quang Dieu / Ha Thi Than / Trieu Viet Vuong
--              -> Phuong An Hai. Ca ba duong giao deu thuoc An Hai.
--   PL8-IV-07  Le Tan Trung (Phan Ba Phien -> Ho Ngoc Lam) -> Phuong Son Tra
--   PL8-IV-08  Ngo Quyen - An Trung Dong 6 -> Phuong An Hai
--   PL8-IV-09  Le Tan Trung (Dinh Cong Tru -> Nguyen Thi Hong) -> Phuong Son Tra
-- Nguon nguy co ngap van la Phu luc VIII; OSM chi dung de xac dinh phuong.
--
-- Nhom II (Thanh Khe cu) — 41 dong ra soat, 40 dong xac dinh duoc phuong.
--
-- Hai dot sap xep don vi hanh chinh, can doc dung thu tu:
--   NQ 1251/NQ-UBTVQH15 (hieu luc 01/01/2025) — cap xa trong quan Thanh Khe:
--     Tan Chinh nhap vao Chinh Gian, Tam Thuan nhap vao Xuan Ha,
--     Vinh Trung nhap vao Thac Gian, Hoa Khe nhap vao Thanh Khe Dong.
--   NQ 1659/NQ-UBTVQH15 (hieu luc 01/07/2025) — mo hinh 2 cap:
--     Xuan Ha, Chinh Gian, Thac Gian, Thanh Khe Tay va Thanh Khe Dong
--     hop thanh Phuong Thanh Khe hien tai.
--     An Khe, Hoa An, Hoa Phat hop thanh Phuong An Khe hien tai.
-- Vi vay to dan pho cu (Tan Chinh, Tam Thuan, Vinh Trung, Hoa Khe) van xuat hien
-- trong ket qua tra cuu, nhung deu da nam trong Phuong Thanh Khe.
--
-- Moi dong duoi day tra dung so nha / so kiet / giao lo / hai dau doan ma nguon neu:
--   Phuong Thanh Khe (32 dong):
--     II-01 Nguyen Van Linh (to 28 Thac Gian)   II-02 Le Duan (to 14 Tan Chinh)
--     II-03 Huynh Ngoc Hue (to 63 Hoa Khe)      II-06 Tran Cao Van (to 65 Thanh Khe Tay)
--     II-07 Kiet 814 Tran Cao Van (to 50 Thanh Khe Dong)
--     II-08 Ha Huy Tap 88 (to 53 Thanh Khe Dong)
--     II-09 Tran Xuan Le (to 58 Hoa Khe)        II-10 Ky Dong (to 39 Xuan Ha)
--     II-11 Kiet 96 Dien Bien Phu (to 44 Chinh Gian)
--     II-12 Kiet 246 Tran Cao Van (to 32 Xuan Ha)
--     II-13 Thai Thi Boi (to 45 Chinh Gian)     II-14 Kiet 402 Le Duan (to 14 Tan Chinh)
--     II-15 Kiet 384 Dien Bien Phu (to 53 Thanh Khe Dong)
--     II-16 Mai Xuan Thuong (to 54 Hoa Khe)     II-17 Kiet 5 Cu Chinh Lan (to 55 Hoa Khe)
--     II-18 Kiet 112 Tran Cao Van (to 04 Tam Thuan)
--     II-19 Kiet 196 Tran Cao Van (to 05 Tam Thuan)
--     II-20 Tran Cao Van (to 36 Xuan Ha)        II-21 Tran Cao Van (to 34 Xuan Ha)
--     II-22 Kiet 272 Tran Cao Van (to 07 Tam Thuan)
--     II-23 Ton That Dam (to 32 Xuan Ha)        II-24 390 Le Duan (to 14 Tan Chinh)
--     II-25 Thai Thi Boi (to 45 Chinh Gian)     II-26 Phan Thanh (to 26 Thac Gian)
--     II-27 Pham Van Nghi (to 29 Thac Gian)     II-28 Bau Hac 1 (to 17 Vinh Trung)
--     II-29 Do Quang (to 21 Vinh Trung)         II-30 Tran Tong (to 29 Thac Gian)
--     II-31 Cau vuot Nga ba Hue (to 65 Thanh Khe Tay)
--     II-32 Bau Trang 6 (to 65 Thanh Khe Tay)   II-33 Me Nhu (to 66/67 Thanh Khe Tay)
--     II-41 Ham chui Dien Bien Phu (to 28 Thac Gian / 42 Chinh Gian)
--   Phuong An Khe (8 dong):
--     II-04 Nguyen Dinh Tuu (to Dong Xuan 3)    II-05 Truong Chinh (to Phuoc Truong 7)
--     II-34 Kiet 317 Nguyen Phuoc Nguyen (to Thuan An 2)
--     II-35 Kiet 325 Nguyen Phuoc Nguyen (to Thuan An 2)
--     II-36 Nguyen Phuoc Nguyen (to Dong Xuan 2/3)
--     II-37 Tan Hoa 1 (to Tan Hoa 1 / Tan An 2)
--     II-38 Pham Ngoc Mau (to Tan An 1/2)
--     II-39 Can Giuoc + Nguyen Gian Thanh + Phan Lang 1 (to Phan Lang 1/2)
--   Con cho (1 dong):
--     II-40 Khu vuc Khe Can — nguon chi neu ten kenh, khong co so nha / kiet /
--           giao lo. Kenh chay qua nhieu phuong nen khong du can cu gan mot phuong.
--           Giu current_unit NULL, area_basis 'NO_AREA_IN_SOURCE'.
--
-- Duong chay qua nhieu phuong da duoc kiem o cap vi tri, khong dung ten duong chung:
--   Tran Cao Van  chay qua Phuong Thanh Khe va Phuong Hai Chau. Cac so nha
--                 112-272 va kiet 814 deu nam trong doan Phuong Thanh Khe
--                 (quet doc truc duong, reverse-check tung diem).
--   Cu Chinh Lan  chay qua Phuong Thanh Khe (to 62, 64 Hoa Khe) va Phuong An Khe
--                 (to Dong Xuan 4, An Xuan). Kiet 5 nam o to 55 Hoa Khe
--                 -> Phuong Thanh Khe.
--   Le Duan       kiet 402 nam o to 14 Tan Chinh -> Phuong Thanh Khe.
--   Phan Lang 9   thuoc Phuong Thanh Khe, nhung nguon chi neu Phan Lang 1
--                 (to Phan Lang 1, Phuong An Khe) nen khong anh huong ket luan.
--
-- Nhom VI (Cam Le cu) — 13 dong chua anh xa, da ra soat toan bo.
-- Theo NQ 1659/NQ-UBTVQH15, dia ban Cam Le cu nay thuoc ba don vi:
--   Phuong Cam Le   <- Khue Trung, Hoa Tho Dong, Hoa Tho Tay
--   Phuong An Khe   <- Hoa An, Hoa Phat
--   Phuong Hoa Xuan <- Hoa Xuan
-- Bon dong xac dinh duoc phuong hien tai (area_basis 'OSM_ADDRESS'):
--   VI-04  Ton Dan (Vu Lang -> lang mo Thai Thi Boi, to 22, 25, 27)
--          -> Phuong An Khe. Ca hai dau doan deu thuoc Phuong An Khe
--          (Ton Dan to Hoa Binh 1, Vu Lang to Nghi An 1/2).
--   VI-12  Nga ba Hue -> Phuong An Khe. Dia danh cu the, to Binh Thuan 4
--          nay thuoc Phuong An Khe.
--   VI-15  Khe Can - to 25-34, 43, 44 phuong Hoa An -> Phuong An Khe.
--          Nguon neu ro phuong cu Hoa An, theo NQ 1659 thuoc Phuong An Khe.
--   VI-18  Nguyen Thi Sau, Thanh Luong 20, Thai Van Lung -> Phuong Hoa Xuan.
--          Thanh Luong 20 (to Thanh Luong 3) va Thai Van Lung (to Trung Luong 8)
--          deu thuoc Phuong Hoa Xuan; tuyen thu ba khong tra duoc nhung cung khu vuc.
-- Chin dong con lai giu current_unit NULL:
--   VI-01  Cau vuot Hoa Cam — nut giao tren ranh gioi Phuong Cam Le / Phuong Hoa Cuong.
--   VI-02  Truong Son (QL1AB, Km21+200) — duong dai qua nhieu xa/phuong.
--   VI-03  Kenh Yen The - Bac Son — cong trinh kenh/cong, khong phai cap duong.
--   VI-05  Bau Sen - to 3, 4 phuong Hoa Tho Dong — khong tra duoc vi tri to.
--   VI-10  Tuyen Son - Tuy Loan — doan dai qua nhieu don vi.
--   VI-11  Nguyen Nhan — chi tra duoc co so y te ten gan dung.
--   VI-13  Cong Khe Can GD2 — doan dai tu cho Chieu den Phuoc Tuong.
--   VI-14  Nut giao Nguyen Hien Le - Phan Triem — khong tra duoc toa do nut giao.
--   VI-17  Nut giao Pham Xuan An - 29/3 — khong dinh vi duoc ca hai duong.
-- Luu y: xac dinh phuong cua vi tri nguy co ngap KHONG phai chung minh mot lo dat
-- cu the nam trong vung ngap. Ket qua chi cho biet vi tri nguon thuoc phuong nao.


INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-01', 'PLANNED_RISK', 'Khu vực đường Đống Đa',
  'Đống Đa', NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-02', 'PLANNED_RISK', 'Khu vực đường Trần Phú, nút Hoàng Văn Thụ - Trần Phú',
  'Trần Phú', NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-03', 'PLANNED_RISK', 'Nguyễn Văn Linh (Đầu mương C3 - Nguyễn Hoàng)',
  NULL, NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-04', 'PLANNED_RISK', 'Nút Núi Thành - Tiểu La',
  NULL, NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-05', 'PLANNED_RISK', 'Khu vực trước SN 420 Núi Thành (gần Công ty Môi trường đô thị)',
  NULL, NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-06', 'PLANNED_RISK', 'Khu vực đường Lê Thanh Nghị',
  'Lê Thanh Nghị', NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-07', 'PLANNED_RISK', 'Khu vực đường 2/9, Tống Phước Phổ',
  NULL, NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-08', 'PLANNED_RISK', 'Khu vực K383 Núi Thành',
  NULL, NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-09', 'PLANNED_RISK', 'Khu vực Hải Hồ và vùng lân cận',
  NULL, NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-10', 'PLANNED_RISK', 'Thăng Long (KDC trước Trạm bơm chống ngập Trương Chí Cương)',
  NULL, NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-11', 'PLANNED_RISK', 'Tổ 27 phường Hòa Thuận Tây',
  NULL, 'Phường Hòa Cường', 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', 'Phường Hòa Cường', 'HISTORICAL_WARD_MAPPED',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-I-12', 'PLANNED_RISK', 'Khu vực đường Quang Trung',
  'Quang Trung', NULL, 'Hải Châu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hải Châu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-01', 'PLANNED_RISK', 'Khu vực đường Nguyễn Văn Linh - Hàm Nghi',
  'Nguyễn Văn Linh', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-02', 'PLANNED_RISK', 'Khu vực đường Lê Duẩn (Ông Ích Khiêm đến Hoàng Hoa Thám)',
  'Lê Duẩn', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-03', 'PLANNED_RISK', 'Khu vực đường Hà Huy Tập trước Trường Huỳnh Ngọc Huệ',
  'Hà Huy Tập trước Trường Huỳnh Ngọc Huệ', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-04', 'PLANNED_RISK', 'Đường Nguyễn Đình Tựu (Từ Hồ Tương đến Nguyễn Phước Thái)',
  'Nguyễn Đình Tựu', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-05', 'PLANNED_RISK', 'Đường Trường Chinh (khu vực trước trường Nguyễn Đình Chiểu)',
  'Trường Chinh', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-06', 'PLANNED_RISK', 'Số nhà 647 Trần Cao Vân (khu vực Quán Hộ)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-07', 'PLANNED_RISK', 'Đường Trần Cao Vân (764 đến 860); Kiệt 814 Trần Cao Vân, kiệt 814B Trần Cao Vân',
  'Trần Cao Vân', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-08', 'PLANNED_RISK', 'Hà Huy Tập (Đoạn từ số nhà 88 đến số nhà 100)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-09', 'PLANNED_RISK', 'Ngã tư Huỳnh Ngọc Huệ -Trần Xuân Lê',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-10', 'PLANNED_RISK', 'Tuyến đường Kỳ Đồng (đoạn từ Hà Đông 1 đến Nguyễn Đức Trung)',
  'Kỳ Đồng', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-11', 'PLANNED_RISK', 'Khu vực kiệt 96 Điện Biên Phủ (liên quan tuyến cống Xuân Hà)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-12', 'PLANNED_RISK', 'Cuối kiệt 246 Trần Cao Vân (liên quan tuyến cống Tam Thuận)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-13', 'PLANNED_RISK', 'Kiệt 279 Thái Thị Bôi (K67 Hà Huy Tập đến đoạn giao K251 Thái Thị Bôi và K96 Điện Biên Phủ)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-14', 'PLANNED_RISK', 'Khu vực kiệt 402 Lê Duẩn (từ Tịnh xá Ngọc Giáng đến Chợ Tân Chính)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-15', 'PLANNED_RISK', 'Kiệt 384 Điện Biên Phủ',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-16', 'PLANNED_RISK', 'Mai Xuân Thưởng (khu vực bờ hồ Xuân Hòa)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-17', 'PLANNED_RISK', 'K05 Cù Chính Lan',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-18', 'PLANNED_RISK', 'Kiệt 112 Trần Cao Vân (đoạn giáp đường Nguyễn Tất Thành)',
  'Nguyễn Tất Thành', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-19', 'PLANNED_RISK', 'Cuối kiệt 196 Trần Cao Vân',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-20', 'PLANNED_RISK', 'Cuối kiệt 236 Trần Cao Vân',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-21', 'PLANNED_RISK', 'Từ ngã tư 158 tiếp giáp với K112/137 đến K196 Trần Cao Vân',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-22', 'PLANNED_RISK', 'Cuối K272 Trần Cao Vân tiếp giáp với K01 Tôn Thất Đạm (giáp ranh phường Xuân Hà)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-23', 'PLANNED_RISK', 'K01 Tôn Thất Đạm từ cuối K246 Trần Cao Vân K196 Trần Cao Vân',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-24', 'PLANNED_RISK', 'K390 Lê Duẩn',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-25', 'PLANNED_RISK', 'Đường Thái Thị Bôi (từ nhà số 15 đến nhà số 55), trước Chợ Chính Gián',
  'Thái Thị Bôi', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-26', 'PLANNED_RISK', 'Đường Phan Thanh: đoạn từ Tản Đà đến số nhà 138',
  'Phan Thanh: đoạn từ Tản Đà đến số nhà 138', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-27', 'PLANNED_RISK', 'Đường Phạm Văn Nghị: đoạn từ trước nhà số 10 đến đường Tôn Thất Tùng',
  'Phạm Văn Nghị: đoạn từ trước nhà số 10 đế', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-28', 'PLANNED_RISK', 'Cuối đường Bàu Hạc 1, từ số 28-38 Bàu Hạc 1',
  'Bàu Hạc 1', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-29', 'PLANNED_RISK', 'Đường Đỗ Quang từ số 153 đến 191',
  'Đỗ Quang từ số 153 đến 191', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-30', 'PLANNED_RISK', 'Các tuyến kiệt 3m; K01, 05 Trần Tống, K21, 25 Tôn Thất Tùng chảy ra đường Đỗ Quang',
  'Đỗ Quang', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-31', 'PLANNED_RISK', 'Khu vực 01 phường Thanh Khê Tây - Dưới chân cầu vượt Ngã ba Huế',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 33
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-32', 'PLANNED_RISK', 'Khu vực 02 phường Thanh Khê Tây - đường Bàu Trảng 6',
  'Bàu Trảng 6', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-33', 'PLANNED_RISK', 'Ngã ba Trần Cao Vân - tuyến đường Mẹ Nhu',
  'Mẹ Nhu', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-34', 'PLANNED_RISK', 'Cuối kiệt 317 Nguyễn Phước Nguyên (Giáp KDC Phần Lăng 2 - GĐ2)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-35', 'PLANNED_RISK', 'Cuối kiệt 325 Nguyễn Phước Nguyên (Giáp KDC Phần Lăng 2 - GĐ2)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-36', 'PLANNED_RISK', 'Cuối kiệt 393 Nguyễn Phước Nguyên (Giáp KDC Phần Lăng 2 - GĐ2)',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-37', 'PLANNED_RISK', 'Đường Tân Hòa 1 (Trước trường THCS Nguyễn Đình Chiểu - CS2)',
  'Tân Hòa 1', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-38', 'PLANNED_RISK', 'Đường Phạm Ngọc Mậu',
  'Phạm Ngọc Mậu', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-39', 'PLANNED_RISK', 'Cuối đường Cần Giuộc, Nguyễn Giản Thanh, Phần Lăng 1',
  'Cần Giuộc', NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-40', 'PLANNED_RISK', 'Khu vực Khe Cạn',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-II-41', 'PLANNED_RISK', 'Hầm chui Điện Biên Phủ',
  NULL, NULL, 'Thanh Khê',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Thanh Khê', 'Phường Thanh Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-01', 'PLANNED_RISK', 'Khu vực cổng Khu công nghiệp Hòa Khánh',
  NULL, NULL, 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-02', 'PLANNED_RISK', 'Khu dân cư tổ 1, 2 phường Hòa Hiệp Bắc (nay thuộc Phường Hải Vân)',
  NULL, 'Phường Hải Vân', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hải Vân', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-03', 'PLANNED_RISK', 'Khu dân cư dọc sông Cu Đê',
  NULL, NULL, 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-04', 'PLANNED_RISK', 'Liên tổ 52, 53 phường Hòa Hiệp Nam (nay thuộc Phường Hải Vân)',
  NULL, 'Phường Hải Vân', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hải Vân', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-05', 'PLANNED_RISK', 'Đường Đàm Quang Trung, tổ 29 phường Hòa Hiệp Nam (nay thuộc Phường Hải Vân)',
  'Đàm Quang Trung', 'Phường Hải Vân', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hải Vân', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-06', 'PLANNED_RISK', 'Đường Đàm Quang Trung, tổ 25 phường Hòa Hiệp Nam (nay thuộc Phường Hải Vân)',
  'Đàm Quang Trung', 'Phường Hải Vân', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hải Vân', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-07', 'PLANNED_RISK', 'Kiệt 455, đường Nguyễn Lương Bằng, tổ03 phường Hòa Hiệp Nam, khu ký túc xá sinh viên (nay thuộc Phường Hải Vân)',
  'Nguyễn Lương Bằng', 'Phường Hải Vân', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hải Vân', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-08', 'PLANNED_RISK', 'Khu vực đường Lạc Long Quân, tổ 23 phường Hòa Khánh Bắc (nay thuộc Phường Liên Chiểu)',
  'Lạc Long Quân', 'Phường Liên Chiểu', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Liên Chiểu', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-09', 'PLANNED_RISK', 'Kiệt 383, đường Nguyễn Lương Bằng, tổ 24, phường Hòa Khánh Bắc (nay thuộc Phường Liên Chiểu)',
  'Nguyễn Lương Bằng', 'Phường Liên Chiểu', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Liên Chiểu', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-10', 'PLANNED_RISK', 'Cuối đường Bùi Chát, tổ 41 phường Hòa Khánh Bắc (nay thuộc Phường Liên Chiểu)',
  'Bùi Chát', 'Phường Liên Chiểu', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Liên Chiểu', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-11', 'PLANNED_RISK', 'Tổ 26, 27 Hòa Khánh Bắc khu vực Nguyễn Chánh giao Nguyễn An Ninh (nay thuộc Phường Liên Chiểu)',
  NULL, 'Phường Liên Chiểu', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Liên Chiểu', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-12', 'PLANNED_RISK', 'Kiệt 144, đường Nguyễn Lương Bằng, tổ 16 phường Hòa Khánh Bắc (nay thuộc Phường Liên Chiểu)',
  'Nguyễn Lương Bằng', 'Phường Liên Chiểu', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Liên Chiểu', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-13', 'PLANNED_RISK', 'Kiệt 82 Nguyễn Chánh, tổ 17, 28 phường Hòa Khánh Bắc (nay thuộc Phường Liên Chiểu)',
  NULL, 'Phường Liên Chiểu', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Liên Chiểu', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-14', 'PLANNED_RISK', 'Kiệt 317, đường Âu Cơ, tổ 66 phường Hòa Khánh Bắc (nay thuộc Phường Liên Chiểu)',
  NULL, 'Phường Liên Chiểu', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Liên Chiểu', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-15', 'PLANNED_RISK', 'Đường Thanh Vinh 11, 12, tổ 70 phường Hòa Khánh Bắc (nay thuộc Phường Liên Chiểu)',
  'Thanh Vinh 11', 'Phường Liên Chiểu', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Liên Chiểu', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-16', 'PLANNED_RISK', 'Khu vực bộ đội 971, phường Hòa Khánh Nam (nay thuộc Phường Hòa Khánh)',
  NULL, 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-17', 'PLANNED_RISK', 'Cầu Bà Xí, tổ 15, 35, 32 phường Hòa Khánh Nam (nay thuộc Phường Hòa Khánh)',
  NULL, 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-18', 'PLANNED_RISK', 'Kiệt 65, 81, 109, 119, 129 Phạm Như Xương, liên tổtừ13 đến 18 phường Hòa Khánh Nam (nay thuộc Phường Hòa Khánh)',
  NULL, 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-19', 'PLANNED_RISK', 'Tổ 36, 37 phường Hòa Khánh Nam (nay thuộc Phường Hòa Khánh)',
  NULL, 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-20', 'PLANNED_RISK', 'Tổ 42 phường Hòa Khánh Nam (nay thuộc Phường Hòa Khánh)',
  NULL, 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-21', 'PLANNED_RISK', 'Trước lò mổ Đà Sơn, tổ 45 - 47 phường Hòa Khánh Nam (nay thuộc Phường Hòa Khánh)',
  NULL, 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-22', 'PLANNED_RISK', 'Tổ 70 phường Hòa Khánh Nam, đường Phạm Thị Lam Anh (nay thuộc Phường Hòa Khánh)',
  'Phạm Thị Lam Anh', 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-23', 'PLANNED_RISK', 'Tổ 21, phường Hòa Minh (nay thuộc Phường Hòa Khánh)',
  NULL, 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-24', 'PLANNED_RISK', 'Khu dân cư Trung Nghĩa, khu vực Tân Trào, Hồng Thái',
  NULL, NULL, 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-25', 'PLANNED_RISK', 'Khu dân cư Trung Nghĩa, đường Nam Trân',
  'Nam Trân', NULL, 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-26', 'PLANNED_RISK', 'Khu dân cư cuối đường Bàu Năng 15, tổ 07, phường Hòa Minh',
  'Bàu Năng 15', 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'HISTORICAL_WARD_MAPPED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-27', 'PLANNED_RISK', 'Tổ 113 phường Hòa Minh (nay thuộc Phường Hòa Khánh)',
  NULL, 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-28', 'PLANNED_RISK', 'Tổ 123 phường Hòa Minh (nay thuộc Phường Hòa Khánh)',
  NULL, 'Phường Hòa Khánh', 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', 'Phường Hòa Khánh', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-III-29', 'PLANNED_RISK', 'Tổ 3,4,5, 6 (khu vực Khe Cạn)',
  NULL, NULL, 'Liên Chiểu',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Liên Chiểu', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-01', 'PLANNED_RISK', 'Bùng binh Phạm Văn Đồng - Ngô Quyền',
  NULL, NULL, 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường An Hải', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-02', 'PLANNED_RISK', 'Khu vực đường Nguyễn Công Trứ (số 150 – 184) (nay thuộc phường An Hải)',
  'Nguyễn Công Trứ', 'Phường An Hải', 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường An Hải', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-03', 'PLANNED_RISK', 'Đường Trần Hưng Đạo, khu vực đối diện Chung cư Monarchy, phường An Hải Tây (nay thuộc phường An Hải)',
  'Trần Hưng Đạo', 'Phường An Hải', 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường An Hải', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-04', 'PLANNED_RISK', 'Đường Trần Hưng Đạo (giao các đường Trần Quang Diệu, Hà Thị Thân, Triệu Việt Vương)',
  'Trần Hưng Đạo', NULL, 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường An Hải', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-05', 'PLANNED_RISK', 'Khu vực đường Vương Thừa Vũ - Trần Duy Chiến, phường An Hải Bắc (nay thuộc phường An Hải)',
  'Vương Thừa Vũ', 'Phường An Hải', 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường An Hải', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-06', 'PLANNED_RISK', 'Ngã tư đường Vân Đồn - Tôn Quang Phiệt, phường Nại Hiên Đông (nay thuộc phường Sơn Trà)',
  'Vân Đồn', 'Phường Sơn Trà', 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường Sơn Trà', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-07', 'PLANNED_RISK', 'Đường Lê Tấn Trung (Đoạn từ Phan Bá Phiến đến Hồ Ngọc Lãm)',
  'Lê Tấn Trung', NULL, 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường Sơn Trà', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-08', 'PLANNED_RISK', 'Đường Ngô Quyền - An Trung Đông 6',
  'Ngô Quyền', NULL, 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường An Hải', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-09', 'PLANNED_RISK', 'Đường Lê Tấn Trung (đoạn từ Đinh Công Trứ đến Nguyễn Thị Hồng)',
  'Lê Tấn Trung', NULL, 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường Sơn Trà', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 34
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-10', 'PLANNED_RISK', 'Khu vực An Thuần, An Vĩnh, phường An Hải Tây (nay thuộc phường An Hải)',
  NULL, 'Phường An Hải', 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường An Hải', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-11', 'PLANNED_RISK', 'Khu vực kiệt K259/H38 đường Ngô Quyền, phường Mân Thái (nay thuộc phường Sơn Trà)',
  'Ngô Quyền', 'Phường Sơn Trà', 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường Sơn Trà', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-12', 'PLANNED_RISK', 'Khu vực kiệt K267 đường Ngô Quyền (Tổ 34, 35), phường Mân Thái (nay thuộc phường Sơn Trà)',
  'Ngô Quyền', 'Phường Sơn Trà', 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường Sơn Trà', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-13', 'PLANNED_RISK', 'Khu vực kiệt K331 đường Ngô Quyền, phường Mân Thái (nay thuộc phường Sơn Trà)',
  'Ngô Quyền', 'Phường Sơn Trà', 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường Sơn Trà', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-IV-14', 'PLANNED_RISK', 'Kiệt 156 H70 Nguyễn Phan Vinh (tổ 72, 74, 75), phường Thọ Quang (nay thuộc phường Sơn Trà)',
  NULL, 'Phường Sơn Trà', 'Sơn Trà',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Sơn Trà', 'Phường Sơn Trà', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-V-01', 'PLANNED_RISK', 'Khu vực nút giao đường Dương Thị Xuân Quý – Trần Văn Dư, phường Mỹ An (nay thuộc phường Ngũ Hành Sơn)',
  'Dương Thị Xuân Quý', 'Phường Ngũ Hành Sơn', 'Ngũ Hành Sơn',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Ngũ Hành Sơn', 'Phường Ngũ Hành Sơn', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-V-02', 'PLANNED_RISK', 'Tổ63 phường Hòa Quý, gần giáp tường rào trường Đại học CNTT Việt Hàn, phường Hòa Quý (nay thuộc phường Ngũ Hành Sơn)',
  NULL, 'Phường Ngũ Hành Sơn', 'Ngũ Hành Sơn',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Ngũ Hành Sơn', 'Phường Ngũ Hành Sơn', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-V-03', 'PLANNED_RISK', 'Kiệt 16 đường Bà Bang Nhãn, phường Hòa Hải (nay thuộc phường Ngũ Hành Sơn)',
  'Bà Bang Nhãn', 'Phường Ngũ Hành Sơn', 'Ngũ Hành Sơn',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Ngũ Hành Sơn', 'Phường Ngũ Hành Sơn', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-V-04', 'PLANNED_RISK', 'Tổ 48- 51 (phía Đông đường Nguyễn Duy Trinh), phường Hòa Hải (nay thuộc phường Ngũ Hành Sơn)',
  'Nguyễn Duy Trinh', 'Phường Ngũ Hành Sơn', 'Ngũ Hành Sơn',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Ngũ Hành Sơn', 'Phường Ngũ Hành Sơn', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-V-05', 'PLANNED_RISK', 'Tổ 29 -30 (Khu vực Đa Mặn 10, gần cửa xả C28), phường Khuê Mỹ (nay thuộc phường Ngũ Hành Sơn)',
  NULL, 'Phường Ngũ Hành Sơn', 'Ngũ Hành Sơn',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Ngũ Hành Sơn', 'Phường Ngũ Hành Sơn', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-V-06', 'PLANNED_RISK', 'Khu vực nút giao đường Hải Triều – Lê Văn Hiến, phường Hòa Hải (nay thuộc phường Ngũ Hành Sơn)',
  'Hải Triều', 'Phường Ngũ Hành Sơn', 'Ngũ Hành Sơn',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Ngũ Hành Sơn', 'Phường Ngũ Hành Sơn', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-V-07', 'PLANNED_RISK', 'Một số khu vực trũng thấp thuộc các khu vực An Lưu, Thị An, phường Hòa Quý (nay thuộc phường Ngũ Hành Sơn)',
  NULL, 'Phường Ngũ Hành Sơn', 'Ngũ Hành Sơn',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Ngũ Hành Sơn', 'Phường Ngũ Hành Sơn', 'SOURCE_STATED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-V-08', 'PLANNED_RISK', 'Các vị trí thuộc các dự án đang triển khai dở dang (thuộc phường Ngũ Hành Sơn)',
  NULL, 'Phường Ngũ Hành Sơn', 'Ngũ Hành Sơn',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Ngũ Hành Sơn', 'Phường Ngũ Hành Sơn', 'DISTRICT_SINGLE_UNIT',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-01', 'PLANNED_RISK', 'Đường nhánh phía Bắc và phía Nam cầu vượt Hòa Cầm, đường Trường Chinh giao đường đường nhánh phía Bắc và phía Nam cầu vượt Hòa Cầm',
  'Trường Chinh giao đường đường nhánh phía', NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-02', 'PLANNED_RISK', 'Đường Trường Sơn (gần khu vực Trường Quân sự Quân khu 5), Km21+200 QL1AB',
  'Trường Sơn', NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-03', 'PLANNED_RISK', 'Kênh Yên Thế - Bắc Sơn (Cống qua đường Tôn Đức Thắng)',
  'Tôn Đức Thắng', NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-04', 'PLANNED_RISK', 'Khu vực đường Tôn Đản (từ đường Vũ Lăng đến khu lăng mộ Thái Thị Bôi và khu vực tổ 22, 25, 27)',
  'Tôn Đản', NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-05', 'PLANNED_RISK', 'Khu vực Bàu Sen - Tổ 3, 4 phường Hòa Thọ Đông thuộc dự án Khu dân cư Phong Bắc',
  NULL, NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-06', 'PLANNED_RISK', 'Khu vực Tổ 1B, 2A, phường Hòa Phát (khu vực nhà bà Huỳnh)',
  NULL, 'Phường An Khê', 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', 'Phường An Khê', 'HISTORICAL_WARD_MAPPED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-07', 'PLANNED_RISK', 'Khu vực phía Bắc đường Lê Trọng Tấn - Tổ 29, 30, 32, 34, 35, 36, 37 phường Hòa Phát',
  'Lê Trọng Tấn', 'Phường An Khê', 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', 'Phường An Khê', 'HISTORICAL_WARD_MAPPED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-08', 'PLANNED_RISK', 'Khu vực Đông Nam nút giao thông Hòa Cầm (giai đoạn 1), tổ 6, 7, 8, 9, 10, phường Hòa Thọ Đông',
  NULL, 'Phường Cẩm Lệ', 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', 'Phường Cẩm Lệ', 'HISTORICAL_WARD_MAPPED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-09', 'PLANNED_RISK', 'Tổ 40, 42, 43, 44 phường Hòa Phát (Thuộc khu vực Khu dân cư Phước Lý 5)',
  NULL, 'Phường An Khê', 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', 'Phường An Khê', 'HISTORICAL_WARD_MAPPED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-10', 'PLANNED_RISK', 'Đường Tuyên Sơn - Túy Loan (GĐ1+GĐ2), đoạn dưới cầu Đỏ và cầu Đường sắt',
  'Tuyên Sơn', NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-11', 'PLANNED_RISK', 'Đường Nguyễn Nhàn (trước khu vực Trung tâm y tế quận Cẩm Lệ)',
  'Nguyễn Nhàn', NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-12', 'PLANNED_RISK', 'Khu vực Ngã ba Huế',
  NULL, NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-13', 'PLANNED_RISK', 'Dự án cống Khe Cạn (Giai đoạn 2-Đoạn từ chợ Chiều, phường Hoà An đến Phước Tường, phường Hòa Phát)',
  NULL, NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-14', 'PLANNED_RISK', 'Khu đô thị sinh thái Hoà Xuân ngập cục bộ: Nút giao tuyến đường Nguyễn Hiến Lê - Phan Triêm',
  'Nguyễn Hiến Lê', NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-15', 'PLANNED_RISK', 'Khu vực Khe Cạn - Tổ25-34, 43, 44 phường Hòa An thuộc Tuyến cống Khe cạn thuộc dựán phát triển bền vững (Giai đoạn 1: Đoạn từ ngã ba Huế đến Chợ Chiều)',
  NULL, NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', 'Phường An Khê', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-16', 'PLANNED_RISK', 'Khu vực thượng lưu Khe Cạn - tổ 29, 30, 32, 34, 35, 36, 37 phường Hòa Phát (Giai đoạn 2: Đoạn từ chợ Chiều đến Phước Tường, phường Hòa Phát)',
  NULL, 'Phường An Khê', 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', 'Phường An Khê', 'HISTORICAL_WARD_MAPPED',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-17', 'PLANNED_RISK', 'Nút giao Phạm Xuân Ẩn - 29/3',
  NULL, NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VI-18', 'PLANNED_RISK', 'Các tuyến đường Nguyễn Thị Sáu, Thanh Lương 20, Thái Văn Lung',
  'Nguyễn Thị Sáu', NULL, 'Cẩm Lệ',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Cẩm Lệ', 'Phường Hòa Xuân', 'OSM_ADDRESS',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VII-01', 'PLANNED_RISK', 'Khu vực nút giao đường DT602 và đường tránh Nam hầm Hải Vân, huyện Hòa Vang',
  'DT602 và đường tránh Nam hầm Hải Vân', NULL, 'Hòa Vang',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hòa Vang', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);

INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at,
  source_district, current_unit, area_basis, area_note, decision_number, source_page
) VALUES (
  'PL8-VII-02', 'PLANNED_RISK', 'Ngã ba ĐT 605 - thôn Dương Sơn',
  NULL, NULL, 'Hòa Vang',
  'AREA', NULL, NULL, '2026-05-26',
  'https://pctt.danang.gov.vn/Portals/0/2026_QD%202322_QD_UBND_26_05_2026_PA%20UPTT%202026_PL.pdf', 'Phụ lục VIII — Danh sách các vị trí có nguy cơ ngập úng khi xảy ra mưa lớn trên địa bàn thành phố Đà Nẵng (kèm Quyết định 2322/QĐ-UBND ngày 26/05/2026)', '2026-11-21',
  'Hòa Vang', NULL, 'NO_AREA_IN_SOURCE',
  NULL, '2322/QĐ-UBND', 35
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text),
  street=VALUES(street), ward=VALUES(ward), district=VALUES(district),
  scope=VALUES(scope), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title),
  checked_at=VALUES(checked_at), source_district=VALUES(source_district),
  current_unit=VALUES(current_unit), area_basis=VALUES(area_basis),
  area_note=VALUES(area_note), decision_number=VALUES(decision_number),
  source_page=VALUES(source_page);


SELECT COUNT(*) AS planned_risk_rows FROM flood_records WHERE record_type='PLANNED_RISK';
SELECT COUNT(*) AS mapped FROM flood_records WHERE record_type='PLANNED_RISK' AND current_unit IS NOT NULL;
SELECT COUNT(*) AS unmapped FROM flood_records WHERE record_type='PLANNED_RISK' AND current_unit IS NULL;
