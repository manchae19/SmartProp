import { api } from '../auth/api.js';
import { validCoordinates } from '../property/postForm.js';
export function geocodingInput(value) {
  return Object.fromEntries(['address', 'city', 'district', 'ward'].map(key => [key, String(value[key] || '')]));
}
// Explicit address components win over optional fields left over from an older address.
export function addressComponents(value) {
  const fields = geocodingInput(value),
    wards = new Map(),
    districts = new Map();
  for (const part of fields.address.split(',')) {
    const text = part.trim(),
      ward = text.match(/^(?:phường|p\.?|xã|ward)\s+(.+)$/iu),
      district = text.match(/^(?:quận|q\.?|huyện|district)\s+(.+)$/iu);
    if (ward) wards.set(administrativeKey(ward[1]), ward[1].trim());
    if (district) districts.set(administrativeKey(district[1]), district[1].trim());
  }
  return {
    wards: [...wards.values()],
    districts: [...districts.values()]
  };
}
export function addressScopeConflict(value) {
  const explicit=addressComponents(value);
  if(explicit.districts.length>1||explicit.wards.length>1)return 'Địa chỉ có nhiều phường/quận. Hãy giữ một địa bàn trước khi tìm.';
  const conflicts=[];
  if(value.district&&explicit.districts.length===1&&administrativeKey(value.district)!==administrativeKey(explicit.districts[0]))conflicts.push('quận trong địa chỉ: '+explicit.districts[0]+'; quận đang chọn: '+value.district);
  if(value.ward&&explicit.wards.length===1&&administrativeKey(value.ward)!==administrativeKey(explicit.wards[0]))conflicts.push('phường trong địa chỉ: '+explicit.wards[0]+'; phường đang chọn: '+value.ward);
  return conflicts.length?'Địa chỉ và bộ lọc không khớp ('+conflicts.join(' · ')+'). Bấm “Dùng phường/quận từ địa chỉ” phía trên hoặc sửa lại các trường địa bàn.':'';
}
export function effectiveGeocodingInput(value) {
  const fields = geocodingInput(value),
    explicit = addressComponents(value);
  if (explicit.wards.length) fields.ward = explicit.wards.length === 1 ? explicit.wards[0] : '';else if (explicit.districts.length) fields.ward = '';
  if (explicit.districts.length) fields.district = explicit.districts.length === 1 ? explicit.districts[0] : '';else if (explicit.wards.length) fields.district = '';
  return fields;
}
export function geocodingErrorMessage(error) {
  switch (error.code) {
    case 'GEOCODING_TIMEOUT':
      return 'Dịch vụ tìm vị trí chưa phản hồi trong thời gian cho phép. Hãy thử lại hoặc đặt ghim thủ công.';
    case 'GEOCODING_QUOTA':
      return 'Geoapify đang giới hạn hoặc đã hết hạn mức tìm kiếm. Hãy chờ rồi thử lại hoặc đặt ghim thủ công.';
    case 'RATE_LIMITED':
      return 'Bạn đang tìm quá nhanh. Hãy chờ trước khi thử lại.';
    case 'GEOCODING_AUTH_FAILED':
      return 'Key hoặc quyền truy cập Geoapify chưa hợp lệ. Vui lòng liên hệ quản trị viên; bạn vẫn có thể đặt ghim thủ công.';
    case 'GEOCODING_PROVIDER_ERROR':
      return 'Dịch vụ tìm vị trí đang gặp lỗi. Hãy thử lại sau hoặc đặt ghim thủ công.';
    default:
      return error.message || 'Không kết nối được dịch vụ tìm vị trí. Hãy thử lại hoặc đặt ghim thủ công.';
  }
}
export const geocodingSignature = value => JSON.stringify(geocodingInput(value));
export const geocodingConfiguration = (request = api) => request('/geocoding/config');
export async function searchLocations(value, request = api) {
  if (!String(value.address || '').trim() || !String(value.city || '').trim()) throw Error('Nhập địa chỉ đầy đủ và thành phố trước khi tìm vị trí.');
  if (value.shareAddress !== true) throw Error('Cần đồng ý gửi địa chỉ tới dịch vụ tìm vị trí trước khi tìm kiếm.');
  // Selected geography must reach the Backend unchanged, even when the address text conflicts.
  const result = await request('/geocoding/search', {
    method: 'POST',
    body: {
      ...geocodingInput(value),
      shareAddress: true,
      districtOnly: value.districtOnly === true
    }
  });
  return {
    ...result,
    candidates: (result.candidates || []).filter(candidate => validCoordinates(candidate.latitude, candidate.longitude))
  };
}
export function candidateCanBeConfirmed(candidate) {
  return !!candidate && validCoordinates(candidate.latitude, candidate.longitude) && candidate.provider === 'GEOAPIFY' && candidate.mapProvider === 'OSM' && candidate.storageAllowed === true && candidate.addressMatched === true && candidate.context?.localityMatched === true && candidate.locationLevel === 'BUILDING_ONLY' && !['INTERPOLATED', 'APPROXIMATE'].includes(candidate.accuracy);
}
export function accuracyLabel(candidate) {
  let label;
  if (candidate.accuracy === 'INTERPOLATED') label = 'Vị trí nội suy theo số nhà, cần chỉnh ghim';else if (candidate.context?.precision === 'APPROXIMATE_STREET') label = 'Chỉ xác định đường, chưa xác định số nhà/lô đất';else if (candidate.accuracy === 'APPROXIMATE' || candidate.locationLevel === 'APPROXIMATE') label = 'Chỉ xác định khu vực, cần chỉnh ghim';else if (candidate.accuracy === 'EXACT') label = 'Nguồn xác định tới số nhà; chưa xác minh bất động sản';else if (candidate.locationLevel === 'BUILDING_ONLY') label = 'Gợi ý cấp tòa nhà; chưa xác minh căn hộ hoặc ranh giới';else label = 'Chưa xác định độ chính xác; cần kiểm tra vị trí thực tế';
  return candidate.context?.warning ? label + ' · ' + candidate.context.warning : label;
}
const fold = value => String(value || '').normalize('NFD').replace(/\p{M}/gu, '').replace(/đ/gi, 'd').toLowerCase().replace(/\./g, ' ').trim().replace(/\s+/g, ' ');
const administrativeKey = value => fold(value).replace(/^(?:thanh pho|thi xa|tp|tx|quan|q|huyen|phuong|p|xa|city|province|district|ward)\s+/, '');
export function normalizeAddressQuery(value) {
  const fields = effectiveGeocodingInput(value),
    parts = new Map();
  for (const [kind, raw] of [['', fields.address], ['ward', fields.ward], ['district', fields.district], ['city', fields.city], ['country', 'Việt Nam']]) for (const part of raw.split(',')) {
    const text = part.trim().replace(/\s+/g, ' ');
    if (!text) continue;
    const plain = fold(text);
    let actual = /^(?:phuong|p|xa|ward)\s/.test(plain) ? 'ward' : /^(?:quan|q|huyen|district)\s/.test(plain) ? 'district' : /^(?:thanh pho|tp|city|province)\s/.test(plain) ? 'city' : kind,
      key = administrativeKey(text);
    if (['viet nam', 'vietnam', 'vn'].includes(key)) {
      actual = 'country';
      key = 'viet nam';
    }
    if (!actual) {
      const matching = ['ward', 'district', 'city'].filter(k => administrativeKey(fields[k]) && administrativeKey(fields[k]) === key);
      if (matching.length === 1) actual = matching[0];
    }
    const id = actual + ':' + key;
    if (!parts.has(id)) parts.set(id, text);
  }
  return [...parts.values()].join(', ');
}
export function administrativeHints(value, knownDistricts = []) {
  const explicit = addressComponents(value);
  if (explicit.districts.length > 1 || explicit.wards.length > 1) return { district: '', ward: '' };
  const districtNames = [],
    wardNames = [];
  for (const raw of String(value.address || '').split(',')) {
    const text = raw.trim(),
      district = text.match(/^(?:quận|q\.?|huyện)\s+(.+)$/iu),
      ward = text.match(/^(?:phường|p\.?|xã)\s+(.+)$/iu);
    if (district) {
      const matched = knownDistricts.filter(name => administrativeKey(name) === administrativeKey(district[1]));
      if (matched.length === 1) districtNames.push(matched[0]);
    }
    if (ward && ward[1].trim().length <= 100) wardNames.push(ward[1].trim());
  }
  const unique = a => [...new Set(a)];
  return {
    district: unique(districtNames).length === 1 && administrativeKey(value.district)!==administrativeKey(districtNames[0]) ? districtNames[0] : '',
    ward: unique(wardNames).length === 1 && administrativeKey(value.ward)!==administrativeKey(wardNames[0]) ? wardNames[0] : ''
  };
}
