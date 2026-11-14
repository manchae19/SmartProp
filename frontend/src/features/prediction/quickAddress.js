const DISTRICT_NAMES = ["Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn", "Cẩm Lệ", "Liên Chiểu", "Hòa Vang"];

// Legacy ward → district, used only to fill the valuation selector.
// Ambiguous post-2025 names are intentionally omitted.
const WARD_DISTRICT = {
  "hai chau i": "Hải Châu", "hai chau 1": "Hải Châu", "hai chau 01": "Hải Châu",
  "hai chau ii": "Hải Châu", "hai chau 2": "Hải Châu", "hai chau 02": "Hải Châu",
  "hai chau": "Hải Châu", "thach thang": "Hải Châu", "thanh binh": "Hải Châu",
  "thuan phuoc": "Hải Châu", "phuoc ninh": "Hải Châu", "nam duong": "Hải Châu",
  "binh hien": "Hải Châu", "binh thuan": "Hải Châu", "hoa thuan dong": "Hải Châu",
  "hoa thuan tay": "Hải Châu", "hoa cuong bac": "Hải Châu", "hoa cuong nam": "Hải Châu",
  "tam thuan": "Thanh Khê", "xuan ha": "Thanh Khê", "tan chinh": "Thanh Khê",
  "chinh gian": "Thanh Khê", "vinh trung": "Thanh Khê", "thac gian": "Thanh Khê",
  "hoa khe": "Thanh Khê", "thanh khe dong": "Thanh Khê", "thanh khe tay": "Thanh Khê",
  "tho quang": "Sơn Trà", "nai hien dong": "Sơn Trà", "man thai": "Sơn Trà",
  "an hai bac": "Sơn Trà", "phuoc my": "Sơn Trà", "an hai dong": "Sơn Trà",
  "an hai tay": "Sơn Trà", "an hai nam": "Sơn Trà", "my an": "Ngũ Hành Sơn",
  "khue my": "Ngũ Hành Sơn", "hoa hai": "Ngũ Hành Sơn", "hoa quy": "Ngũ Hành Sơn",
  "bac my an": "Ngũ Hành Sơn", "hoa hiep bac": "Liên Chiểu", "hoa hiep nam": "Liên Chiểu",
  "hoa khanh bac": "Liên Chiểu", "hoa khanh nam": "Liên Chiểu", "hoa minh": "Liên Chiểu",
  "khue trung": "Cẩm Lệ", "hoa phat": "Cẩm Lệ", "hoa an": "Cẩm Lệ",
  "hoa tho tay": "Cẩm Lệ", "hoa tho dong": "Cẩm Lệ", "hoa xuan": "Cẩm Lệ",
  "hoa bac": "Hòa Vang", "hoa lien": "Hòa Vang", "hoa ninh": "Hòa Vang",
  "hoa son": "Hòa Vang", "hoa nhon": "Hòa Vang", "hoa phu": "Hòa Vang",
  "hoa phong": "Hòa Vang", "hoa chau": "Hòa Vang", "hoa tien": "Hòa Vang",
  "hoa phuoc": "Hòa Vang", "hoa khuong": "Hòa Vang"
};

export function normalizeQuickAddress(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "d")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

export function parseQuickAddress(addressText) {
  if (!addressText || typeof addressText !== "string") return null;
  const clean = addressText.trim();
  if (!clean) return null;
  const whole = normalizeQuickAddress(clean);
  const parts = clean.split(",").map((part) => part.trim()).filter(Boolean);
  const normalizedParts = parts.map(normalizeQuickAddress);

  let district = "";
  for (const name of DISTRICT_NAMES) {
    const key = normalizeQuickAddress(name).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const explicit = new RegExp(`(?:quan|q|huyen|h)\\.?\\s*${key}\\b`, "i");
    if (normalizedParts.some((part) => part === key || part === `quan ${key}` || part === `q ${key}` || part === `huyen ${key}` || part === `h ${key}` || explicit.test(part)) || explicit.test(whole)) {
      district = name;
      break;
    }
  }
  if (!district) {
    for (const name of DISTRICT_NAMES) {
      if (whole.includes(normalizeQuickAddress(name))) { district = name; break; }
    }
  }

  let ward = "";
  const wardLead = /^(?:phuong|thi tran|xa|tt|p|x)\.?\s+/;
  for (let i = 0; i < parts.length; i += 1) {
    if (wardLead.test(normalizedParts[i])) {
      ward = parts[i].replace(/^(?:phường|phuong|thị trấn|thi tran|xã|xa|tt|p|x)\.?\s+/iu, "").trim();
      break;
    }
  }
  if (!ward) {
    const match = clean.match(/(?:phường|phuong|xã|xa|thị trấn|thi tran)\s+([^,]+)/iu);
    if (match?.[1]) ward = match[1].trim();
  }

  if (!district && ward) district = WARD_DISTRICT[normalizeQuickAddress(ward)] || "";
  if (!district) {
    for (const [key, value] of Object.entries(WARD_DISTRICT)) {
      if (whole === key || normalizedParts.some((part) => part === key || part.endsWith(` ${key}`) || part.startsWith(`${key} `))) {
        district = value;
        break;
      }
    }
  }
  return { district, ward };
}
