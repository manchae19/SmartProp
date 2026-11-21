-- Dữ liệu công khai đã đối chiếu cho mục Quy hoạch và Ngập lụt.
--
-- Chạy lại được: mỗi bản ghi có id cố định và dùng INSERT ... ON DUPLICATE KEY UPDATE.
-- Nguồn thật, giữ nguyên URL và ngày kiểm tra.

-- ---------------------------------------------------------------------------
-- Quy hoạch: thông báo niêm yết công bố công khai đồ án phê duyệt điều chỉnh
-- cục bộ quy hoạch chi tiết TL 1/500 Khu phức hợp thương mại, căn hộ du lịch
-- ALIZÉ (Lô đất A1, khu đất A3.2 góc đường Võ Nguyên Giáp – Võ Văn Kiệt).
-- Nguồn: UBND phường An Hải, đăng 07/09/2026, file đính kèm
-- 472_TB_UBND_07_09_2026_signed_signed_signed.pdf.
-- ---------------------------------------------------------------------------
INSERT INTO planning_publications (
  id, event_type, project_name, lot_code, land_parcel, ward, district,
  document_number, document_date, publication_date, scope,
  source_url, source_title, checked_at
) VALUES (
  'a1000000-0000-4000-8000-000000000001',
  'PUBLICATION_NOTICE',
  'Khu phức hợp thương mại, căn hộ du lịch ALIZÉ',
  'A1',
  'A3.2 (góc đường Võ Nguyên Giáp – Võ Văn Kiệt)',
  'An Hải',
  'Sơn Trà',
  '472/TB-UBND',
  '2026-09-07',
  '2026-09-07',
  'LAND_PARCEL',
  'https://anhai.danang.gov.vn/chi-tiet-tin/group/137/nid/2323/thong-bao-niem-yet-cong-bo-cong-khai-do-an-phe-duyet-dieu-chinh-cuc-bo-quy-hoach-chi-tiet-tl-1-5--khu-phuc-hop-thuong-mai-can-ho-du-lich-alize-lo-dat-a1-khu-dat-a3-2-goc-duong-vo-nguyen-giap--vo-van-kiet',
  'Thông báo niêm yết công bố công khai đồ án phê duyệt điều chỉnh cục bộ quy hoạch chi tiết TL 1/500 Khu phức hợp thương mại, căn hộ du lịch ALIZÉ (Lô đất A1, khu đất A3.2)',
  '2026-11-21'
) ON DUPLICATE KEY UPDATE
  event_type=VALUES(event_type), project_name=VALUES(project_name), lot_code=VALUES(lot_code),
  land_parcel=VALUES(land_parcel), ward=VALUES(ward), district=VALUES(district),
  document_number=VALUES(document_number), document_date=VALUES(document_date),
  publication_date=VALUES(publication_date), scope=VALUES(scope),
  source_url=VALUES(source_url), source_title=VALUES(source_title), checked_at=VALUES(checked_at);

-- ---------------------------------------------------------------------------
-- Ngập lụt: điểm ngập trước kiệt 643 đường Trưng Nữ Vương, phường Hòa Cường.
-- Nguồn: Cổng thông tin phường Hương Trà, đăng 22/10/2025, dẫn Tuổi Trẻ.
-- Phạm vi: điểm theo mô tả nguồn, chưa xác minh tọa độ.
-- ---------------------------------------------------------------------------
INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at
) VALUES (
  'b1000000-0000-4000-8000-000000000001',
  'RECORDED_POINT',
  'Điểm ngập trước kiệt 643 đường Trưng Nữ Vương, phường Hòa Cường, Đà Nẵng',
  'Trưng Nữ Vương',
  'Hòa Cường',
  'Hải Châu',
  'POINT',
  NULL,
  NULL,
  '2025-10-22',
  'https://huongtra.danang.gov.vn/chi-tiet-tin/group/144/nid/4388/theo-doi-toan-canh-diem-ngap-tai-da-nang-tranh-dua-xe-vao-vung-nuoc-dang-len',
  'Theo dõi toàn cảnh điểm ngập tại Đà Nẵng, tránh đưa xe vào vùng nước đang lên',
  '2026-11-21'
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text), street=VALUES(street),
  ward=VALUES(ward), district=VALUES(district), scope=VALUES(scope), depth_note=VALUES(depth_note),
  event_date=VALUES(event_date), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title), checked_at=VALUES(checked_at);

-- ---------------------------------------------------------------------------
-- Ngập lụt: bản tin cảnh báo ngập lụt của Đài Khí tượng Thuỷ văn Trung Bộ,
-- số NGLU-19/10h40/DNAN, ngày 28/10/2025. Đây là cảnh báo theo thời điểm,
-- không phải kết luận cho một căn cụ thể.
-- ---------------------------------------------------------------------------
INSERT INTO flood_records (
  id, record_type, location_text, street, ward, district, scope, depth_note,
  event_date, publication_date, source_url, source_title, checked_at
) VALUES (
  'b1000000-0000-4000-8000-000000000002',
  'WEATHER_WARNING',
  'Cảnh báo ngập lụt khu vực thành phố Đà Nẵng: ngập sâu diện rộng vùng trũng thấp ven sông, ngập úng khu đô thị',
  NULL,
  NULL,
  NULL,
  'WARNING',
  'Độ sâu phổ biến 0,75–1,25 m; lớn nhất 1,25–1,75 m tại nhiều xã/phường',
  '2025-10-28',
  '2025-10-28',
  'https://pctt.danang.gov.vn/Portals/0/DNAN_LULU_20251029_1040.pdf',
  'Tin cảnh báo ngập lụt trên khu vực thành phố Đà Nẵng — số NGLU-19/10h40/DNAN ngày 28/10/2025',
  '2026-11-21'
) ON DUPLICATE KEY UPDATE
  record_type=VALUES(record_type), location_text=VALUES(location_text), street=VALUES(street),
  ward=VALUES(ward), district=VALUES(district), scope=VALUES(scope), depth_note=VALUES(depth_note),
  event_date=VALUES(event_date), publication_date=VALUES(publication_date),
  source_url=VALUES(source_url), source_title=VALUES(source_title), checked_at=VALUES(checked_at);

SELECT id, event_type, project_name, lot_code, scope FROM planning_publications;
SELECT id, record_type, scope, street, ward FROM flood_records;
