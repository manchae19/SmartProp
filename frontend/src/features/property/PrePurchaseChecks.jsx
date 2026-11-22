import React, { useEffect, useState } from "react";
import { api } from "../auth/api.js";

/**
 * Pre-purchase checks for a public listing: legal, planning and flood.
 *
 * Every row states what is known, where it came from and how wide the evidence is.
 * Planning and flood rows come from reviewed public records attached to the listing;
 * a section without a record says "Chưa xác minh" and points the buyer at the official
 * lookup instead of guessing.
 */

const LEGAL_LOOKUP_URL =
  "https://vpcp.dichuvcong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-hanh-chinh.html?ma_thu_tuc=1.012789";
const PLANNING_LOOKUP = "https://thongtinquyhoachxaydung.danang.gov.vn/";
const FLOOD_LOOKUP = "https://muangap.danang.gov.vn/";

const PROPERTY_TYPE_LABEL = {
  HOUSE: "Nhà ở",
  VILLA: "Biệt thự",
  APARTMENT: "Căn hộ chung cư",
  LAND: "Đất nền",
  ROOM: "Phòng trọ",
  COMMERCIAL: "Kho / Mặt bằng",
};

const EVENT_LABEL = {
  PUBLICATION_NOTICE: "Thông báo công bố công khai",
  PUBLIC_CONSULTATION: "Văn bản lấy ý kiến",
  APPROVAL_DECISION: "Quyết định phê duyệt",
  OTHER: "Văn bản quy hoạch",
};

// How closely the record matches this listing, not what the source itself covers.
// SUGGESTED means the title merely names the project or lot: worth reading, not evidence.
const MATCH_LABEL = {
  LAND_PARCEL: "Đã đối chiếu lô đất",
  PROJECT: "Thông tin cấp dự án",
  REGION: "Thông tin khu vực",
  STREET: "Có ghi nhận ngập trên cùng tuyến đường",
  SUGGESTED: "Văn bản liên quan · Chưa xác minh cho tin này",
};

// What the source document itself covers.
const SOURCE_SCOPE_LABEL = {
  LAND_PARCEL: "phạm vi thửa đất",
  PROJECT: "phạm vi dự án",
  REGION: "phạm vi khu vực",
  POINT: "điểm theo mô tả nguồn",
  ROAD_SEGMENT: "đoạn đường theo mô tả nguồn",
  AREA: "khu vực",
  WARNING: "cảnh báo toàn thành phố",
};

const FLOOD_TYPE_LABEL = {
  RECORDED_POINT: "Điểm ngập ghi nhận",
  RISK_AREA: "Vùng nguy cơ ngập",
  WEATHER_WARNING: "Cảnh báo theo thời điểm",
  PLANNED_RISK: "Vị trí có nguy cơ ngập khi mưa lớn",
  OTHER: "Ghi nhận ngập lụt",
};

// Nhãn theo loại bằng chứng, không theo mức khớp: mỗi loại nguồn nói một điều khác nhau.
const FLOOD_MATCH_LABEL = {
  PLANNED_RISK: "Có vị trí nguy cơ ngập trên cùng tuyến đường",
  RECORDED_POINT: "Có ghi nhận ngập trên cùng tuyến đường",
  WEATHER_WARNING: "Cảnh báo ngập theo thời điểm",
  RISK_AREA: "Có vùng nguy cơ ngập trên cùng tuyến đường",
};

const STATUS = {
  verified: { label: "Có căn cứ", tone: "text-[var(--ui-accent)]" },
  declared: { label: "Người đăng cung cấp", tone: "text-[var(--ui-warning-text)]" },
  unverified: { label: "Chưa xác minh", tone: "text-brand-muted" },
};

function Badge({ kind }) {
  const status = STATUS[kind] || STATUS.unverified;
  return (
    <span className={`text-[11px] font-semibold uppercase tracking-wide ${status.tone}`}>
      {status.label}
    </span>
  );
}

function Row({ label, value, kind, source }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-brand-line/40 py-2 last:border-b-0">
      <span className="text-xs text-brand-muted">{label}</span>
      <span className="flex items-baseline gap-2 text-right">
        <span className="text-xs sm:text-sm text-brand-ink">{value}</span>
        {kind ? <Badge kind={kind} /> : null}
      </span>
      {source ? <span className="w-full text-[11px] text-brand-muted">{source}</span> : null}
    </div>
  );
}

function Section({ title, icon, children }) {
  return (
    <section
      className="bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs"
      data-testid="pre-purchase-section"
    >
      <h2 className="text-base font-bold text-[var(--ui-accent)] mb-3 flex items-center gap-2">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          {icon}
        </svg>
        <span>{title}</span>
      </h2>
      {children}
    </section>
  );
}

function Lookup({ href, children }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-3 inline-block text-xs underline text-[var(--ui-accent)]"
    >
      {children}
    </a>
  );
}

function vnDate(value) {
  if (!value) return null;
  const [year, month, day] = String(value).split("-");
  if (!year || !month || !day) return null;
  return `${day}/${month}/${year}`;
}

function SourceLink({ url, title }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="underline text-[var(--ui-accent)]"
    >
      {title}
    </a>
  );
}

export default function PrePurchaseChecks({ property }) {
  const [checks, setChecks] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!property?.id) return;
    let cancelled = false;
    api(`/properties/${encodeURIComponent(property.id)}/pre-purchase-checks`)
      .then((value) => {
        if (!cancelled) setChecks(value);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [property?.id]);

  if (!property) return null;

  const typeLabel = PROPERTY_TYPE_LABEL[property.propertyType] || null;
  const hasCoordinates =
    Number.isFinite(Number(property.latitude)) && Number.isFinite(Number(property.longitude));
  const location = [property.ward, property.district].filter(Boolean).join(", ");
  const planning = checks?.planning || [];
  const flood = checks?.flood || [];

  return (
    <div className="space-y-5" data-testid="pre-purchase-checks">
      <section className="rounded-3xl p-6 border border-brand-line bg-brand-card">
        <h2 className="font-bold text-sm mb-2">Kiểm tra trước khi mua</h2>
        <p className="text-sm text-brand-muted">
          Ba mục dưới đây cho biết thông tin nào đã có căn cứ, thông tin nào còn cần xác minh và
          tra ở đâu. Duyệt hiển thị tin không phải xác nhận pháp lý, quy hoạch hay an toàn ngập lụt.
        </p>
      </section>

      <Section
        title="Pháp lý"
        icon={<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></>}
      >
        {typeLabel ? (
          <Row
            label="Loại bất động sản"
            value={typeLabel}
            kind="declared"
            source="Theo loại tin người đăng chọn khi tạo tin."
          />
        ) : (
          <Row label="Loại bất động sản" value="Chưa có thông tin" kind="unverified" />
        )}
        <Row
          label="Nguồn gốc và thời hạn sử dụng"
          value="Chưa có hồ sơ công khai để đối chiếu"
          kind="unverified"
          source="Hồ sơ pháp lý do người đăng tải lên chỉ hiển thị cho chủ tin và quản trị viên."
        />
        <Row
          label="Tranh chấp, quy hoạch treo, thế chấp"
          value="Chưa xác minh"
          kind="unverified"
          source="Cần đối chiếu tại cơ quan đăng ký đất đai hoặc văn phòng công chứng."
        />
        <Lookup href={LEGAL_LOOKUP_URL}>
          Tra cứu thủ tục yêu cầu thông tin thửa đất trên Cổng Dịch vụ công Quốc gia
        </Lookup>
      </Section>

      <Section
        title="Quy hoạch"
        icon={<><path d="M3 3h18v18H3z" /><path d="M3 9h18M9 3v18" /></>}
      >
        {planning.length ? (
          planning.map((item) => (
            <div key={item.id} className="border-b border-brand-line/40 py-2 last:border-b-0">
              <Row
                label={MATCH_LABEL[item.match] || "Thông tin quy hoạch"}
                value={item.projectName}
                kind={item.match === "SUGGESTED" ? "unverified" : "verified"}
                source={`Nguồn: ${SOURCE_SCOPE_LABEL[item.sourceScope] || item.sourceScope}${
                  item.lotCode ? ` · Lô ${item.lotCode}` : ""
                }${item.landParcel ? ` · Khu đất ${item.landParcel}` : ""}`}
              />
              <Row
                label="Số và ngày văn bản"
                value={[item.documentNumber, vnDate(item.documentDate)].filter(Boolean).join(" · ") || "Nguồn không nêu số văn bản"}
                source={`Công bố ${vnDate(item.publicationDate) || "—"} · Kiểm tra ${vnDate(item.checkedAt) || "—"}`}
              />
              <p className="mt-1 text-[11px] text-brand-muted">
                Nguồn: <SourceLink url={item.sourceUrl} title={item.sourceTitle} />
              </p>
            </div>
          ))
        ) : (
          <>
            <Row
              label="Văn bản quy hoạch đã đối chiếu"
              value={failed ? "Chưa tải được dữ liệu quy hoạch" : "Chưa có văn bản nào gắn với tin này"}
              kind="unverified"
              source="Hệ thống chưa lưu văn bản quy hoạch cho tin đăng, dự án hay thửa đất này."
            />
            <Row
              label="Cấp thông tin"
              value={location ? `Khu vực: ${location}` : "Chưa xác định được khu vực"}
              kind="unverified"
              source="Chỉ là khu vực hành chính của tin, không phải kết quả đối chiếu thửa đất."
            />
          </>
        )}
        <Lookup href={PLANNING_LOOKUP}>
          Mở cổng thông tin quy hoạch xây dựng Đà Nẵng
        </Lookup>
      </Section>

      <Section
        title="Ngập lụt"
        icon={<><path d="M12 2v20M2 12h20" /><path d="M5 7l3 3M19 7l-3 3" /></>}
      >
        {flood.length ? (
          flood.map((item) => (
            <div key={item.id} className="border-b border-brand-line/40 py-2 last:border-b-0">
              <Row
                label={FLOOD_MATCH_LABEL[item.recordType] || "Ghi nhận ngập lụt"}
                value={item.locationText}
                kind="verified"
                source={`${FLOOD_TYPE_LABEL[item.recordType] || "Ghi nhận ngập lụt"} · Nguồn: ${
                  SOURCE_SCOPE_LABEL[item.sourceScope] || item.sourceScope
                }${item.currentUnit ? ` · ${item.currentUnit}` : ""}${
                  item.depthNote ? ` · ${item.depthNote}` : ""
                }`}
              />
              <Row
                label="Thời gian"
                value={[
                  item.eventDate ? `Sự kiện ${vnDate(item.eventDate)}` : null,
                  item.publicationDate ? `Công bố ${vnDate(item.publicationDate)}` : null,
                ].filter(Boolean).join(" · ") || "Nguồn không nêu ngày"}
                source={`Kiểm tra ${vnDate(item.checkedAt) || "—"}`}
              />
              <p className="mt-1 text-[11px] text-brand-muted">
                Nguồn: <SourceLink url={item.sourceUrl} title={item.sourceTitle} />
              </p>
            </div>
          ))
        ) : (
          <>
            {hasCoordinates ? (
              <Row
                label="Đối chiếu với bản đồ mưa ngập"
                value="Chưa có dữ liệu ngập lụt gắn với vị trí này"
                kind="unverified"
                source={`Tin có tọa độ (${Number(property.latitude).toFixed(4)}, ${Number(property.longitude).toFixed(4)}) nhưng hệ thống chưa lưu điểm ngập hay vùng nguy cơ ngập.`}
              />
            ) : (
              <Row
                label="Đối chiếu với bản đồ mưa ngập"
                value="Tin chưa có tọa độ nên không đối chiếu được"
                kind="unverified"
                source="Cần xác nhận vị trí thửa đất trước khi tra bản đồ ngập."
              />
            )}
            <Row
              label="Loại thông tin cần tra"
              value="Điểm ngập ghi nhận và vùng nguy cơ ngập"
              kind="unverified"
              source="Tra theo thửa đất cụ thể; kết quả cấp khu vực chỉ để tham khảo."
            />
          </>
        )}
        <Lookup href={FLOOD_LOOKUP}>Mở bản đồ mưa ngập Đà Nẵng</Lookup>
      </Section>
    </div>
  );
}
