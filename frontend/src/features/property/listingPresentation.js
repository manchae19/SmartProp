import {types,states} from "./property.js";
export function money(p) {
  const n = Number(p?.priceExact ?? p?.price ?? 0);
  const suffix = {
    PER_MONTH: "/tháng",
    PER_YEAR: "/năm",
    PER_DAY: "/ngày"
  }[p?.priceUnit] || "";
  if (!n || n <= 0) return "Thỏa thuận";
  if (n >= 1e9) {
    const val = (n / 1e9).toLocaleString("vi-VN", {
      maximumFractionDigits: 2
    });
    return `${val} tỷ${suffix}`;
  }
  if (n >= 1e6) {
    const val = (n / 1e6).toLocaleString("vi-VN", {
      maximumFractionDigits: 2
    });
    return `${val} triệu${suffix}`;
  }
  return `${n.toLocaleString("vi-VN")} ₫${suffix}`;
}
export function adapt(input) {
  const p = input?.property || input || {};
  return {
    ...p,
    raw: p,
    title: p.title || "",
    location: [p.address, p.ward, p.district, p.city].filter(Boolean).join(", "),
    type: types[p.propertyType] || "",
    area: (p.areaSqm ?? "—") + " m²",
    price: money(p),
    priceText: money(p),
    priceValue: Number(p.price || 0) / 1e9,
    priceShort: money(p),
    pricePerM2: p.areaSqm ? money({
      price: Number(p.price) / Number(p.areaSqm)
    }) + "/m²" : "—",
    info: [(p.areaSqm ?? "—") + " m²", (p.bedrooms ?? "—") + " PN", (p.bathrooms ?? "—") + " WC"].join(" · "),
    detail: [(p.areaSqm ?? "—") + " m²", (p.bedrooms ?? "—") + " PN", (p.bathrooms ?? "—") + " WC"].join(" · "),
    image: (p.images?.find(i => i.cover) || p.images?.[0])?.url,
    badge: states[p.status] || "Đã duyệt",
    badgeColor: "green",
    status: {
      PUBLISHED: "showing",
      PENDING: "pending",
      REJECTED: "rejected",
      EXPIRED: "expired",
      HIDDEN: "hidden",
      DRAFT: "draft",
      CLOSED: "closed"
    }[p.status] || "",
    statusText: states[p.status] || "",
    statusType: "good",
    saved: "Đã lưu",
    views: null,
    saves: null,
    hasWarning: false,
    valuation: "Chưa có dữ liệu",
    description1: p.description || "Chưa có mô tả.",
    description2: "",
    direction: p.direction || "—"
  };
}
export const ownStatus = {
  draft: 'DRAFT',
  showing: 'PUBLISHED',
  pending: 'PENDING',
  rejected: 'REJECTED',
  hidden: 'HIDDEN',
  closed: 'CLOSED',
  expired: 'EXPIRED'
};
export const typeCode = {
  'Nhà phố': 'HOUSE',
  'Căn hộ': 'APARTMENT',
  'Đất nền': 'LAND',
  'Biệt thự': 'VILLA',
  'Phòng trọ': 'ROOM',
  'Kho / Mặt bằng': 'COMMERCIAL'
};
