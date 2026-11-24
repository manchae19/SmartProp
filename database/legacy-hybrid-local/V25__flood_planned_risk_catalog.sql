-- Phụ lục VIII (Quyết định 2322/QĐ-UBND ngày 26/05/2026): danh mục vị trí có
-- nguy cơ ngập úng khi mưa lớn trên địa bàn thành phố Đà Nẵng.
--
-- Đây là loại bằng chứng thứ ba, tách khỏi hai loại đã có:
--   RECORDED_POINT  — điểm ngập đã ghi nhận
--   WEATHER_WARNING — cảnh báo theo thời điểm
--   PLANNED_RISK    — vị trí có nguy cơ ngập theo văn bản quy hoạch/phòng chống thiên tai
--
-- Mỗi dòng giữ nguyên mô tả và địa bàn như văn bản ghi, kèm phường/xã hiện tại khi
-- đối chiếu được. Dòng chưa đối chiếu được địa bàn vẫn nằm trong danh mục với
-- current_unit NULL và area_basis = 'NO_AREA_IN_SOURCE'.

ALTER TABLE flood_records
  DROP CONSTRAINT ck_flood_type,
  ADD CONSTRAINT ck_flood_type CHECK(record_type IN (
    'RECORDED_POINT','RISK_AREA','WEATHER_WARNING','PLANNED_RISK','OTHER'));

ALTER TABLE flood_records
  -- Địa bàn như văn bản ghi (quận/huyện cũ), giữ nguyên để đối chiếu về sau.
  ADD COLUMN source_district VARCHAR(100) NULL,
  -- Phường/xã hiện tại sau sắp xếp 2025; NULL khi chưa đối chiếu được.
  ADD COLUMN current_unit VARCHAR(100) NULL,
  -- Cách xác định current_unit: SOURCE_STATED, HISTORICAL_WARD_MAPPED,
  -- DISTRICT_SINGLE_UNIT, NO_AREA_IN_SOURCE.
  ADD COLUMN area_basis VARCHAR(40) NULL,
  ADD COLUMN area_note VARCHAR(300) NULL,
  -- Số quyết định và trang PDF của dòng nguồn.
  ADD COLUMN decision_number VARCHAR(60) NULL,
  ADD COLUMN source_page SMALLINT NULL;

CREATE INDEX idx_flood_current_unit ON flood_records(current_unit);
CREATE INDEX idx_flood_source_district ON flood_records(source_district);
