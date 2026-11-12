import { createStateStore } from "../../shared/state/createStateStore.js";
import { createHttpClient } from '../../shared/lib/httpClient.js';
import { publicChatResponse } from './chat.js';
export const amenityCategories = Object.freeze({
  SCHOOL: 'Trường học',
  HOSPITAL: 'Bệnh viện / cơ sở y tế',
  PHARMACY: 'Nhà thuốc',
  MARKET: 'Chợ',
  SUPERMARKET: 'Siêu thị',
  PARK: 'Công viên',
  BEACH: 'Bãi biển',
  PUBLIC_TRANSPORT: 'Giao thông công cộng'
});
const districts = ['Hải Châu', 'Cẩm Lệ', 'Sơn Trà', 'Ngũ Hành Sơn', 'Liên Chiểu', 'Thanh Khê', 'Hòa Vang'];
const norm = s => String(s || '').normalize('NFD').replace(/\p{M}/gu, '').replace(/đ/g, 'd').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const has = (s, word) => (' ' + s + ' ').includes(' ' + norm(word) + ' ');

// Deterministic question-to-tool routing. It does not alter the RAG packet, ranking,
// citations, model or property locations. Never broaden an unresolved ward/street.
export function amenityIntent(question, packet) {
  const data = publicChatResponse(packet),
    q = norm(question);
  const categories = [];
  if (/benh vien|co so y te|phong kham/.test(q)) categories.push('HOSPITAL');
  if (/truong hoc|truong |giao duc|mam non|tieu hoc|trung hoc|dai hoc/.test(q)) categories.push('SCHOOL');
  if (/cong vien/.test(q)) categories.push('PARK');
  if (/bai bien|bien nao/.test(q)) categories.push('BEACH');
  if (/sieu thi/.test(q)) categories.push('SUPERMARKET');
  if (/chợ/iu.test(question) || /khu cho|cho nao|cac cho/.test(q)) categories.push('MARKET');
  if (/nha thuoc|hieu thuoc/.test(q)) categories.push('PHARMACY');
  if (/xe buyt|giao thong|ben xe/.test(q)) categories.push('PUBLIC_TRANSPORT');
  const housingResult = data.recommendedProperties.length > 0 && data.evidence?.needs && !data.evidence?.amenityIntent?.categories?.length;
  const requested = !housingResult && (categories.length > 0 || /tien ich/.test(q));
  const narrow = /\b(phuong|xa|duong|kiet|hem)\b/.test(q);
  // A district the user typed always wins. A follow-up such as "co benh vien nao trong
  // khu vuc do?" names none, but the server resolved it from this conversation and the
  // citations come from that same resolution, so reuse it instead of dropping the map.
  let found = districts.filter(d => has(q, d));
  const server = data.evidence?.amenityIntent;
  if (!found.length && server && typeof server.district === 'string') {
    found = districts.filter(d => norm(d) === norm(server.district));
  }
  if (!found.length && data.recommendedProperties.length) {
    const names = [...new Set(data.recommendedProperties.map(p => p.district))];
    if (names.length === 1) found = districts.filter(d => norm(d) === norm(names[0]));
  }
  // Category fallback is equally server-resolved: a rephrasing the local regex misses
  // still maps to the exact category the answer was validated against.
  const serverCategories = Array.isArray(server?.categories) ? server.categories : [];
  if (!categories.length) {
    for (const c of serverCategories) if (amenityCategories[c] && !categories.includes(c)) categories.push(c);
  }
  // A category the map cannot render must not silently widen to ALL: refuse instead.
  const unsupported = serverCategories.length > 0 && categories.length === 0;
  return {
    district: found.length === 1 ? found[0] : null,
    categories,
    requested: requested && !unsupported,
    narrow,
    enabled: found.length === 1 && !narrow && !unsupported && (requested || data.recommendedProperties.length > 0),
    message: narrow ? 'Chưa có tọa độ tiện ích được đối chiếu riêng cho phường/xã hoặc tuyến đường này.' : found.length !== 1 ? 'Bạn hãy nêu một quận/huyện để xem tiện ích trên bản đồ.' : ''
  };
}
export function validateAmenityMap(data, intent) {
  if (!data || data.version !== 'POI_MAP_V1' || data.visibility !== 'PUBLIC' || data.district !== intent.district || data.category !== (intent.categories.length === 1 ? intent.categories[0] : 'ALL') || !Array.isArray(data.items) || data.items.length > 80 || !Number.isInteger(data.eligibleCount) || data.eligibleCount < data.items.length || !Array.isArray(data.dataLimitations)) throw Error('INVALID_AMENITY_MAP');
  const ids = new Set();
  for (const p of data.items) {
    const kind = {
      OSM_NODE: 'node',
      OSM_WAY_CENTER: 'way',
      OSM_RELATION_CENTER: 'relation'
    }[p?.coordinateBasis];
    if (!p || typeof p.id !== 'string' || ids.has(p.id) || typeof p.name !== 'string' || !p.name.trim() || !amenityCategories[p.category] || p.district !== intent.district || p.reviewStatus !== 'VALID' || p.sourceName !== 'openstreetmap_overpass' || !kind || !new RegExp('^https://www\\.openstreetmap\\.org/' + kind + '/[1-9][0-9]*$').test(p.sourceUrl) || typeof p.latitude !== 'number' || typeof p.longitude !== 'number' || !Number.isFinite(p.latitude) || !Number.isFinite(p.longitude) || p.latitude < 15 || p.latitude > 17 || p.longitude < 107 || p.longitude > 109 || typeof p.attribution !== 'string' || !p.attribution || typeof p.sourceLicense !== 'string' || !p.sourceLicense || ['distanceMeters', 'rawPayload', 'research', 'sampleListingCount', 'protectedHoldout'].some(k => k in p)) throw Error('INVALID_AMENITY_MAP');
    ids.add(p.id);
  }
  if (data.boundary != null) {
    const b = data.boundary,
      g = b.geometry;
    if (b.name !== intent.district || b.version !== 'OCHA-2020-geoBoundaries-9469f09' || b.sourceUrl !== 'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/VNM/ADM2/geoBoundaries-VNM-ADM2.geojson' || !b.attribution || !b.license || !g || !['Polygon', 'MultiPolygon'].includes(g.type) || !Array.isArray(g.coordinates)) throw Error('INVALID_AMENITY_BOUNDARY');
    const polygons = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
    let count = 0;
    if (!polygons.length) throw Error('INVALID_AMENITY_BOUNDARY');
    for (const rings of polygons) {
      if (!Array.isArray(rings) || !rings.length) throw Error('INVALID_AMENITY_BOUNDARY');
      for (const ring of rings) {
        if (!Array.isArray(ring) || ring.length < 4 || JSON.stringify(ring[0]) !== JSON.stringify(ring.at(-1))) throw Error('INVALID_AMENITY_BOUNDARY');
        for (const p of ring) if (++count > 30000 || !Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite) || p[0] < 107 || p[0] > 109 || p[1] < 15 || p[1] > 17) throw Error('INVALID_AMENITY_BOUNDARY');
      }
    }
  }
  return {
    ...data,
    items: data.items.filter(p => !intent.categories.length || intent.categories.includes(p.category))
  };
}
const client = createHttpClient({
  baseUrl: '/api/v1',
  session: createStateStore({
    token: null
  }),
  refreshEnabled: false,
  timeoutForPath: () => 15000,
  fetcher: (url, options) => fetch(url, {
    ...options,
    credentials: 'omit',
    cache: 'no-store'
  })
});
export async function loadAmenityMap(intent) {
  if (!intent.enabled) return null;
  const query = new URLSearchParams({
    district: intent.district,
    category: intent.categories.length === 1 ? intent.categories[0] : 'ALL'
  });
  return validateAmenityMap(await client.request('/amenities/map?' + query, {
    authenticated: false
  }), intent);
}
export function amenitySummary(data) {
  if (!data?.items.length) return 'Chưa có tiện ích với tọa độ đủ điều kiện hiển thị cho yêu cầu này.';
  const names = data.items.filter(p => p.category !== 'PUBLIC_TRANSPORT').concat(data.items.filter(p => p.category === 'PUBLIC_TRANSPORT')).slice(0, 3).map(p => p.name);
  return `Tại ${data.district}, dữ liệu bản đồ có ${names.join(', ')}${data.items.length > names.length ? ' và các địa điểm bên dưới' : ''}. Bạn có thể chạm vào ghim để xem nguồn.`;
}
