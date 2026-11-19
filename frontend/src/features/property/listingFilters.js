// URL is the shared source of truth for Home, Listings and GIS. Values use the API's units.
import { types as propertyTypes } from './property.js';
export { propertyTypes };
export const sortOptions = {
  newest: 'Mới nhất',
  priceAsc: 'Giá tăng dần',
  priceDesc: 'Giá giảm dần',
  areaAsc: 'Diện tích tăng dần',
  areaDesc: 'Diện tích giảm dần'
};
const textKeys = {
  keyword: 200,
  city: 100,
  district: 100,
  ward: 100
};
const numberKeys = ['minPrice', 'maxPrice', 'minArea', 'maxArea', 'bedrooms'];
const first = value => String((Array.isArray(value) ? value[0] : value) ?? '').trim();
export function normalizeFilters(input = {}) {
  const result = {};
  for (const [key, limit] of Object.entries(textKeys)) {
    const value = first(input[key]).slice(0, limit);
    if (value && value !== 'Tất cả') result[key] = value;
  }
  if (Object.hasOwn(propertyTypes, first(input.propertyType))) result.propertyType = first(input.propertyType);
  if (['SALE', 'RENT'].includes(first(input.transactionType))) result.transactionType = first(input.transactionType);
  for (const key of numberKeys) {
    const value = first(input[key]);
    if (/^\d+(?:\.\d{1,2})?$/.test(value) && Number.isFinite(Number(value)) && Number(value) >= 0 && (key !== 'bedrooms' || Number(value) <= 100 && Number.isInteger(Number(value)))) result[key] = value;
  }
  result.sort = Object.hasOwn(sortOptions, first(input.sort)) ? first(input.sort) : 'newest';
  return result;
}
export function filterError(input) {
  const labels = {
    minPrice: 'Giá tối thiểu',
    maxPrice: 'Giá tối đa',
    minArea: 'Diện tích tối thiểu',
    maxArea: 'Diện tích tối đa',
    bedrooms: 'Phòng ngủ'
  };
  for (const key of numberKeys) {
    const value = first(input[key]);
    if (value && (!/^\d+(?:\.\d{1,2})?$/.test(value) || !Number.isFinite(Number(value)) || key === 'bedrooms' && (!Number.isInteger(Number(value)) || Number(value) > 100))) return `${labels[key]}: nhập số không âm, tối đa 2 chữ số thập phân; phòng ngủ phải là số nguyên từ 0–100.`;
  }
  const decimal = value => {
    const [whole, fraction = ''] = first(value).split('.');
    return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
  };
  for (const [min, max, label] of [['minPrice', 'maxPrice', 'giá'], ['minArea', 'maxArea', 'diện tích']]) {
    if (first(input[min]) && first(input[max]) && decimal(input[min]) > decimal(input[max])) return `Khoảng ${label}: giá trị tối thiểu phải nhỏ hơn hoặc bằng tối đa.`;
  }
  return '';
}
export function listingLink(path, filters, extra = {}) {
  const query = {
    ...normalizeFilters(filters),
    ...extra
  };
  if (query.sort === 'newest') delete query.sort;
  return {
    path,
    query
  };
}
export const lifestylePresets = [{
  id: 'coast',
  title: 'Sống gần biển',
  icon: '≈',
  image: 'sun-cosmo',
  filters: {
    district: 'Sơn Trà'
  },
  districts: ['Sơn Trà', 'Ngũ Hành Sơn'],
  explanation: 'Gợi ý khu vực Sơn Trà / Ngũ Hành Sơn. Chưa xác định khoảng cách từng tin đến biển; hãy kiểm tra trên bản đồ.'
}, {
  id: 'central',
  title: 'Trung tâm năng động',
  icon: '◇',
  image: 'the-filmore',
  filters: {
    district: 'Hải Châu'
  },
  explanation: 'Lọc theo khu vực Hải Châu do người đăng cung cấp. Không khẳng định khoảng cách đến trung tâm.'
}, {
  id: 'family',
  title: 'Không gian gia đình',
  icon: '⌂',
  image: 'sunneva-island',
  filters: {
    bedrooms: '2'
  },
  explanation: 'Tin có từ 2 phòng ngủ theo dữ liệu người đăng. Chưa đánh giá trường học, độ yên tĩnh hay mức độ an toàn.'
}, {
  id: 'rental',
  title: 'Đầu tư & cho thuê',
  icon: '↗',
  image: 'fpt-plaza-3',
  filters: {
    transactionType: 'RENT'
  },
  explanation: 'Khám phá nguồn cung tin cho thuê để tham khảo. Không cam kết tỷ suất đầu tư, khả năng cho thuê hoặc dòng tiền.'
}, {
  id: 'retreat',
  title: 'Không gian nghỉ dưỡng',
  icon: '☀',
  image: 'sun-symphony',
  filters: {
    propertyType: 'VILLA'
  },
  explanation: 'Lọc loại hình biệt thự. Tiện ích, mục đích khai thác và khả năng cho thuê ngắn hạn cần xác minh riêng.'
}, {
  id: 'business',
  title: 'Mặt bằng kinh doanh',
  icon: '▤',
  image: 'sun-ponte',
  filters: {
    propertyType: 'COMMERCIAL'
  },
  explanation: 'Lọc loại hình mặt bằng theo thông tin tin đăng. Mục đích sử dụng, giấy phép và khả năng kinh doanh cần xác minh riêng.'
}, {
  id: 'green',
  title: 'Khám phá không gian xanh',
  icon: '♧',
  image: 'sunneva-island',
  filters: {
    district: 'Hòa Vang'
  },
  explanation: 'Gợi ý khu vực Hòa Vang để khám phá thêm. Chưa có dữ liệu xác minh cây xanh hoặc khoảng cách đến công viên cho từng tin.'
}];
