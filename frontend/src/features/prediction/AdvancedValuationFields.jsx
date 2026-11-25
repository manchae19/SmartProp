import React from "react";
import { advancedFieldsFor, NUMERIC_LIMITS, TEXT_LIMITS } from "./advancedValuation.js";

// Nhóm thông tin nâng cao cho AI định giá trong luồng đăng tin.
//
// Chỉ những field model V1.3 thực sự nhận mới xuất hiện ở đây. Mọi field đều
// không bắt buộc: bỏ trống nghĩa là "chưa xác định", và adapter giữ nguyên
// missing thay vì tự suy ra kích thước đường/mặt tiền.
//
// Các field này chỉ phục vụ ước lượng giá. Chúng KHÔNG được lưu vào tin đăng —
// payload đăng tin (postForm.js) không đọc chúng.

const DIRECTIONS = [
  "", "Đông", "Tây", "Nam", "Bắc",
  "Đông Nam", "Đông Bắc", "Tây Nam", "Tây Bắc",
];

const SUBTYPE = [
  ["", "Chưa xác định"],
  ["villa", "Biệt thự"],
  ["house_c4", "Nhà cấp 4"],
];

function Field({ label, hint, children }) {
  return (
    <label className="block text-xs">
      <span className="text-brand-navy/70">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-[11px] text-brand-navy/50">{hint}</span> : null}
    </label>
  );
}

const inputClass = "mt-1 w-full bg-brand-card text-[var(--ui-accent)] rounded-lg p-2";

export default function AdvancedValuationFields({ draft, propertyType, onChange, open, onToggle }) {
  const allowed = advancedFieldsFor(propertyType);
  const set = (patch) => onChange?.({ ...draft, ...patch });

  return (
    <div className="mt-4 border-t border-brand-line/30 pt-3">
      <button
        type="button"
        data-testid="valuation-advanced-toggle"
        aria-expanded={open ? "true" : "false"}
        onClick={() => onToggle?.(!open)}
        className="flex w-full items-center justify-between text-xs text-brand-navy/70"
      >
        <span>Thông tin bổ sung để AI định giá sát hơn</span>
        <span aria-hidden="true">{open ? "−" : "+"}</span>
      </button>

      {open ? (
        <div data-testid="valuation-advanced-fields" className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <p className="col-span-full text-[11px] text-brand-navy/60">
            Chỉ cung cấp những thông tin bạn biết. Có thể để trống nếu chưa xác định.
            Hệ thống không tự giả định kích thước đường hoặc mặt tiền.
          </p>

          {allowed.street ? (
            <Field label="Tên đường">
              <input
                type="text"
                data-testid="valuation-street-name"
                maxLength={TEXT_LIMITS.streetName}
                value={draft.streetName ?? ""}
                onChange={(e) => set({ streetName: e.target.value })}
                className={inputClass}
              />
            </Field>
          ) : null}

          {allowed.project ? (
            <Field label="Tên dự án">
              <input
                type="text"
                data-testid="valuation-project-name"
                maxLength={TEXT_LIMITS.projectName}
                value={draft.projectName ?? ""}
                onChange={(e) => set({ projectName: e.target.value })}
                className={inputClass}
              />
            </Field>
          ) : null}

          {allowed.road ? (
            <Field label="Chiều rộng đường (m)">
              <input
                type="number"
                data-testid="valuation-road-width"
                min={NUMERIC_LIMITS.roadWidthM.min}
                max={NUMERIC_LIMITS.roadWidthM.max}
                step="0.1"
                value={draft.roadWidthM ?? ""}
                onChange={(e) => set({ roadWidthM: e.target.value })}
                className={inputClass}
              />
            </Field>
          ) : null}

          {allowed.frontage ? (
            <Field label="Chiều rộng mặt tiền (m)">
              <input
                type="number"
                data-testid="valuation-frontage-width"
                min={NUMERIC_LIMITS.frontageWidthM.min}
                max={NUMERIC_LIMITS.frontageWidthM.max}
                step="0.1"
                value={draft.frontageWidthM ?? ""}
                onChange={(e) => set({ frontageWidthM: e.target.value })}
                className={inputClass}
              />
            </Field>
          ) : null}

          {allowed.floors ? (
            <Field label="Số tầng nhà" hint="Tổng số tầng của cả căn nhà, không phải tầng căn hộ.">
              <input
                type="number"
                data-testid="valuation-floors"
                min={NUMERIC_LIMITS.floors.min}
                max={NUMERIC_LIMITS.floors.max}
                step="1"
                value={draft.floors ?? ""}
                onChange={(e) => set({ floors: e.target.value })}
                className={inputClass}
              />
            </Field>
          ) : null}

          {allowed.subtype ? (
            <Field label="Kiểu nhà chi tiết">
              <select
                data-testid="valuation-house-subtype"
                value={draft.houseSubtype ?? ""}
                onChange={(e) => set({ houseSubtype: e.target.value })}
                className={inputClass}
              >
                {SUBTYPE.map(([value, label]) => (
                  <option key={value || "blank"} value={value}>{label}</option>
                ))}
              </select>
            </Field>
          ) : null}

          {allowed.directions ? (
            <Field label="Hướng ban công">
              <select
                data-testid="valuation-balcony-direction"
                value={draft.balconyDirection ?? ""}
                onChange={(e) => set({ balconyDirection: e.target.value })}
                className={inputClass}
              >
                {DIRECTIONS.map((value) => (
                  <option key={value || "blank"} value={value}>{value || "Chưa xác định"}</option>
                ))}
              </select>
            </Field>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
