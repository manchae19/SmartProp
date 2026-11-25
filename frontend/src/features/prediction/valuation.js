import { areaInput, typeCodes } from '../property/postForm.js';
import { advancedValuationPayload } from './advancedValuation.js';
export const categoryFor = type => ({
  HOUSE: 'Nhà ở',
  VILLA: 'Nhà ở',
  LAND: 'Đất nền',
  APARTMENT: 'Căn hộ chung cư'
})[typeCodes[type]];
export function valuationInput(draft, location) {
  const propertyType = typeCodes[draft.propertyType],
    area = areaInput(draft.area);
  if (draft.transactionType !== 'Bán') return {
    reason: 'Model hiện chỉ hỗ trợ tin bán.'
  };
  if (!categoryFor(draft.propertyType)) return {
    reason: 'Loại bất động sản này chưa được model hỗ trợ.'
  };
  if (!area || Number(area) < 20 || Number(area) > 1000) return {
    reason: 'Nhập diện tích từ 20 đến 1000 m² để xem giá tham khảo.'
  };
  if (!location) return {
    reason: 'Chọn khu vực tham khảo phù hợp với địa chỉ của tin.'
  };
  const rooms = String(draft.bedrooms ?? '0');
  if (propertyType !== 'LAND' && (!/^\d+$/.test(rooms) || Number(rooms) > 30)) return {
    reason: 'Số phòng ngủ nằm ngoài phạm vi model (0–30; 0 là chưa khai báo).'
  };
  // Bathrooms is the only optional field the posting form collects that the model also
  // accepts. Backend allows 1–30 and rejects 0, so an empty or zero value is omitted
  // rather than sent as a number the request would refuse.
  const bathrooms = Number(draft.bathrooms ?? 0);
  const hasBathrooms = propertyType !== 'LAND' && Number.isInteger(bathrooms)
    && bathrooms >= 1 && bathrooms <= 30;
  // Optional fields the posting form already collects. Each is omitted when blank so
  // the model keeps it as missing data instead of receiving an invented value.
  const ward = String(draft.ward || '').trim();
  const houseDirection = String(draft.direction || '').trim();
  const optional = {};
  if (ward) optional.ward = ward.slice(0, 100);
  if (houseDirection) optional.houseDirection = houseDirection.slice(0, 50);
  // Advanced valuation-only fields. They live in the draft but are never part of the
  // posting payload, so they cannot change the asking price the user typed.
  Object.assign(optional, advancedValuationPayload(draft, draft.propertyType));
  return {
    body: {
      propertyType,
      transactionType: 'SALE',
      areaSqm: Number(area),
      locationFeature: location,
      bedrooms: propertyType === 'LAND' ? null : Number(rooms),
      ...(hasBathrooms ? { bathrooms } : {}),
      ...optional,
      title: String(draft.title || ''),
      description: String(draft.description || '')
    }
  };
}
// Ignore stale/unmounted requests; result state never has access to the posting draft.
export function createPreviewState(request, state) {
  let revision = 0,
    disposed = false;
  return {
    invalidate() {
      revision++;
      state.edit(draftValue => draftValue["result"] = null);
      state.edit(draftValue => draftValue["error"] = '');
      state.edit(draftValue => draftValue["busy"] = false);
    },
    dispose() {
      disposed = true;
      revision++;
    },
    async preview(body) {
      const current = ++revision;
      state.edit(draftValue => draftValue["result"] = null);
      state.edit(draftValue => draftValue["error"] = '');
      state.edit(draftValue => draftValue["busy"] = true);
      try {
        const result = await request(body);
        if (!disposed && current === revision) state.edit(draftValue => draftValue["result"] = result);
      } catch (e) {
        if (!disposed && current === revision) state.edit(draftValue => draftValue["error"] = e.message || 'Giá tham khảo chưa sẵn sàng.');
      } finally {
        if (!disposed && current === revision) state.edit(draftValue => draftValue["busy"] = false);
      }
    }
  };
}
export function exactVnd(value) {
  try {
    return BigInt(value).toLocaleString('vi-VN') + ' ₫';
  } catch {
    return '—';
  }
}

// Standalone v6 estimation and private history complement the posting preview above.
const API_CATEGORIES = ['Nhà ở', 'Đất nền', 'Căn hộ chung cư'];
const LEGACY_LOCATIONS = new Set(['Cẩm Lệ', 'Hòa Vang', 'Hải Châu', 'Liên Chiểu', 'Ngũ Hành Sơn', 'Sơn Trà', 'Thanh Khê']);
function reviewedLocation(value, labels) {
  return LEGACY_LOCATIONS.has(value) || value.startsWith('new_unit:') && typeof labels[value] === 'string' && labels[value].trim();
}
export const featureLabels = {
  area_sqm: 'Diện tích',
  location_feature: 'Địa bàn',
  ward_source: 'Phường/xã theo tin',
  rooms: 'Phòng ngủ',
  floors: 'Số tầng nhà',
  access_type: 'Lối vào',
  house_subtype: 'Loại nhà chi tiết'
};
export class ValuationError extends Error {}
function isBlank(value) {
  return value === '' || value === null || value === undefined;
}
function numeric(value, label, min, max, integer = false) {
  const number = typeof value === 'boolean' || isBlank(value) ? NaN : Number(value);
  if (!Number.isFinite(number) || number < min || number > max || integer && !Number.isInteger(number)) {
    throw new ValuationError(`${label} phải ${integer ? 'là số nguyên ' : ''}từ ${min} đến ${max}.`);
  }
  return number;
}
export function buildValuationPayload(form, options) {
  const category = options.categories.find(item => item.category === form.category);
  if (!category || !API_CATEGORIES.includes(form.category)) throw new ValuationError('Vui lòng chọn loại bất động sản.');
  if (!category.locations.includes(form.location_feature)) throw new ValuationError('Vui lòng chọn địa bàn được hỗ trợ cho loại bất động sản này.');
  if (!reviewedLocation(form.location_feature, options.location_labels ?? {})) throw new ValuationError('Địa bàn chưa được xác nhận. Vui lòng tải lại danh sách lựa chọn.');
  const payload = {
    category: form.category,
    area_sqm: numeric(form.area_sqm, 'Diện tích (m²)', 20, 1000),
    location_feature: form.location_feature
  };
  const ward = String(form.ward ?? '').trim();
  if (ward.length > 100) throw new ValuationError('Tên phường/xã tối đa 100 ký tự.');
  if (ward) payload.ward = ward;
  if (form.category !== 'Đất nền' && !isBlank(form.rooms)) {
    payload.rooms = numeric(form.rooms, 'Số phòng ngủ', 1, 30, true);
  }
  if (form.category === 'Nhà ở') {
    if (!isBlank(form.floors)) payload.floors = numeric(form.floors, 'Số tầng nhà', 1, 20);
    if (form.house_subtype) {
      if (!['villa', 'house_c4'].includes(form.house_subtype)) throw new ValuationError('Loại nhà chi tiết không hợp lệ.');
      payload.house_subtype = form.house_subtype;
    }
  }
  if (form.category !== 'Căn hộ chung cư' && form.access_type) {
    if (!['alley', 'frontage'].includes(form.access_type)) throw new ValuationError('Lối vào không hợp lệ.');
    payload.access_type = form.access_type;
  }
  // Optional real measurements. An empty field stays absent so the model keeps it as
  // missing data instead of receiving a default. Apartments have no road or frontage.
  if (form.category !== 'Căn hộ chung cư') {
    if (!isBlank(form.road_width_m)) payload.road_width_m = numeric(form.road_width_m, 'Chiều rộng đường (m)', 0.1, 100);
    if (!isBlank(form.frontage_width_m)) payload.frontage_width_m = numeric(form.frontage_width_m, 'Chiều rộng mặt tiền (m)', 0.1, 500);
  }
  const street = String(form.street_name ?? '').trim();
  if (street.length > 200) throw new ValuationError('Tên đường tối đa 200 ký tự.');
  if (street) payload.street_name = street;
  const project = String(form.project_name ?? '').trim();
  if (project.length > 200) throw new ValuationError('Tên dự án tối đa 200 ký tự.');
  if (project) payload.project_name = project;
  if (form.category !== 'Đất nền' && !isBlank(form.bathrooms)) {
    payload.bathrooms = numeric(form.bathrooms, 'Số phòng tắm', 1, 30, true);
  }
  const houseDirection = String(form.house_direction ?? '').trim();
  if (houseDirection.length > 50) throw new ValuationError('Hướng nhà tối đa 50 ký tự.');
  if (houseDirection) payload.house_direction = houseDirection;
  const balconyDirection = String(form.balcony_direction ?? '').trim();
  if (balconyDirection.length > 50) throw new ValuationError('Hướng ban công tối đa 50 ký tự.');
  if (balconyDirection) payload.balcony_direction = balconyDirection;
  return payload;
}
export function formatPrice(vnd) {
  const billion = vnd >= 1_000_000_000;
  const value = vnd / (billion ? 1_000_000_000 : 1_000_000);
  return `${new Intl.NumberFormat('vi-VN', {
    maximumFractionDigits: 2
  }).format(value)} ${billion ? 'tỷ' : 'triệu'} đồng`;
}
export function locationLabel(value, labels = {}) {
  const label = labels?.[value];
  return typeof label === 'string' && label.trim() ? label : LEGACY_LOCATIONS.has(value) ? value : 'Địa bàn chưa được xác nhận';
}
export function warningLabel(value) {
  return value.replace(/^(floors|access_type|house_subtype):/, (_, field) => `${featureLabels[field]}:`).replaceAll('vocabulary', 'dữ liệu địa bàn của mô hình');
}
export function createValuationClient({
  fetchImpl = globalThis.fetch,
  timeoutMs = 12000,
  baseUrl = '/api/ai'
} = {}) {
  async function request(path, {
    payload,
    signal
  } = {}) {
    const controller = new AbortController();
    const cancel = () => controller.abort();
    if (signal?.aborted) throw new DOMException('Đã hủy yêu cầu.', 'AbortError');
    signal?.addEventListener('abort', cancel, {
      once: true
    });
    const timer = setTimeout(cancel, timeoutMs);
    try {
      const response = await fetchImpl(`${baseUrl}${path}`, {
        method: payload ? 'POST' : 'GET',
        signal: controller.signal,
        headers: {
          Accept: 'application/json',
          ...(payload ? {
            'Content-Type': 'application/json'
          } : {})
        },
        ...(payload ? {
          body: JSON.stringify(payload)
        } : {})
      });
      let data;
      try {
        data = await response.json();
      } catch {
        data = null;
      }
      if (!response.ok) {
        if (response.status === 422) {
          const detail = typeof data?.detail === 'string' ? warningLabel(data.detail) : 'Thông tin chưa hợp lệ. Vui lòng kiểm tra lại các trường đã nhập.';
          throw new ValuationError(detail);
        }
        throw new ValuationError('Dịch vụ định giá đang chưa sẵn sàng. Vui lòng thử lại sau.');
      }
      return data;
    } catch (error) {
      if (signal?.aborted) throw new DOMException('Đã hủy yêu cầu.', 'AbortError');
      if (error instanceof ValuationError) throw error;
      if (controller.signal.aborted) throw new ValuationError('Dịch vụ phản hồi chậm. Vui lòng thử lại.');
      throw new ValuationError('Chưa kết nối được dịch vụ định giá. Vui lòng thử lại sau.');
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener('abort', cancel);
    }
  }
  return {
    async getOptions({
      signal
    } = {}) {
      const data = await request('/model/options', {
        signal
      });
      // V1.3 is the model behind the public options route. It reports categories and
      // districts only; access types and house subtypes are not part of its schema.
      if (data?.model_version !== 'v1.3' || !Array.isArray(data.categories) || !data.categories.length || data.categories.some(item => !API_CATEGORIES.includes(item.category) || !Array.isArray(item.locations) || !item.locations.every(value => typeof value === 'string'))) {
        throw new ValuationError('Dữ liệu lựa chọn từ dịch vụ chưa hợp lệ. Vui lòng thử lại.');
      }
      const labels = data.location_labels ?? {};
      return {
        ...data,
        categories: data.categories.map(item => ({
          ...item,
          locations: item.locations.filter(code => reviewedLocation(code, labels))
        }))
      };
    },
    async predict(payload, {
      signal
    } = {}) {
      const data = await request('/predict', {
        payload,
        signal
      });
      // V1.3 answers with its own schema: a price band and calibration instead of
      // category/currency/warnings.
      if (data?.model_version !== 'v1.3' || !Number.isFinite(data.predicted_asking_price_vnd) || data.predicted_asking_price_vnd <= 0 || !data.features_used || !Array.isArray(data.missing_features)) {
        throw new ValuationError('Kết quả từ dịch vụ chưa hợp lệ. Vui lòng thử lại.');
      }
      return data;
    }
  };
}
