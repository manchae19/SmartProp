// Logic thuần cho nhóm thông tin định giá nâng cao.
//
// Tách khỏi component React để test bằng node --test không cần bundler.
// Chỉ những field model V1.3 thực sự nhận mới được map ở đây.

/**
 * Empty defaults for every advanced valuation field.
 *
 * reset() and initialize() use Object.assign(draft, initialDraft()), which only
 * overwrites keys that already exist. Listing the keys here is what makes a property
 * switch clear them.
 */
export const ADVANCED_DRAFT_DEFAULTS = {
  streetName: '',
  projectName: '',
  roadWidthM: '',
  frontageWidthM: '',
  floors: '',
  houseSubtype: '',
  balconyDirection: '',
};

export const NUMERIC_LIMITS = {
  roadWidthM: { min: 0.1, max: 100 },
  frontageWidthM: { min: 0.1, max: 500 },
  floors: { min: 1, max: 20 },
};

export const TEXT_LIMITS = {
  streetName: 200,
  projectName: 200,
  direction: 50,
};

/** Field nào áp dụng cho loại bất động sản nào. */
export function advancedFieldsFor(propertyType) {
  const type = String(propertyType || "");
  if (type === "Đất nền") {
    return { street: true, project: true, road: true, frontage: true, floors: false, houseDirection: true, balconyDirection: false, subtype: false };
  }
  if (type === "Căn hộ chung cư" || type === "Căn hộ") {
    return { street: true, project: true, road: false, frontage: false, floors: false, houseDirection: true, balconyDirection: true, subtype: false };
  }
  // Nhà phố / Biệt thự. access_type is not a model feature, so it is not collected.
  return {
    street: true, project: true, road: true, frontage: true,
    floors: true, houseDirection: true, balconyDirection: false,
    subtype: type !== "Biệt thự",
  };
}

function numberOrBlank(value) {
  const text = String(value ?? "").trim();
  if (!text) return "";
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : "";
}

/**
 * Chuẩn hoá field nâng cao thành payload gửi backend.
 * Bỏ qua field trống, field ngoài phạm vi và field không áp dụng cho loại BĐS.
 */
export function advancedValuationPayload(draft, propertyType) {
  const allowed = advancedFieldsFor(propertyType);
  const payload = {};

  if (allowed.street) {
    const street = String(draft.streetName ?? "").trim();
    if (street) payload.streetName = street.slice(0, TEXT_LIMITS.streetName);
  }
  if (allowed.project) {
    const project = String(draft.projectName ?? "").trim();
    if (project) payload.projectName = project.slice(0, TEXT_LIMITS.projectName);
  }
  if (allowed.road) {
    const road = numberOrBlank(draft.roadWidthM);
    if (road !== "" && road >= NUMERIC_LIMITS.roadWidthM.min && road <= NUMERIC_LIMITS.roadWidthM.max) {
      payload.roadWidthM = road;
    }
  }
  if (allowed.frontage) {
    const frontage = numberOrBlank(draft.frontageWidthM);
    if (frontage !== "" && frontage >= NUMERIC_LIMITS.frontageWidthM.min && frontage <= NUMERIC_LIMITS.frontageWidthM.max) {
      payload.frontageWidthM = frontage;
    }
  }
  if (allowed.floors) {
    const floors = numberOrBlank(draft.floors);
    if (floors !== "" && Number.isInteger(floors) && floors >= NUMERIC_LIMITS.floors.min && floors <= NUMERIC_LIMITS.floors.max) {
      payload.floors = floors;
    }
  }
  if (allowed.subtype) {
    const subtype = String(draft.houseSubtype ?? "").trim();
    if (subtype === "villa" || subtype === "house_c4") payload.houseSubtype = subtype;
  }
  if (allowed.balconyDirection) {
    const balcony = String(draft.balconyDirection ?? "").trim();
    if (balcony) payload.balconyDirection = balcony.slice(0, TEXT_LIMITS.direction);
  }
  return payload;
}
