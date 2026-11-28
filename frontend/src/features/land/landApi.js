// Hòa Xuân land demo: shared client for chat cards, the land map and the detail page.
// The chat service serves /land/*; the dev proxy maps it to same-origin /api/land/*.
export const LAND_BASE = '/api/land';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const CODE = /^[A-Za-z0-9._-]{1,80}$/;
export const LAND_KINDS = ['LAND_SEARCH', 'LAND_RECORD', 'LAND_COMPARISON', 'LAND_INFO', 'LAND_CLARIFICATION', 'FLOOD_CATALOG'];

export const PRICE_TYPE_LABEL = {
  SIMULATED_DEMO: 'Giá giả lập (demo)',
  ROAD_ASKING_ESTIMATE: 'Ước tính theo đường',
  HISTORICAL_ASKING: 'Giá chào lịch sử',
  SOURCE_ASKING: 'Giá chào theo nguồn',
  NONE: 'Chưa có giá',
};

// Planning colour groups, same grouping as the test bot legend.
export const PLANNING_GROUPS = [
  ['housing', 'Đất ở', '#c7a000'],
  ['commerce', 'Thương mại / dịch vụ', '#f44336'],
  ['green', 'Cây xanh / công viên', '#22c55e'],
  ['public', 'Công cộng / giáo dục', '#159fc5'],
  ['water', 'Mặt nước', '#3486eb'],
  ['agriculture', 'Nông nghiệp', '#a3a312'],
  ['other', 'Loại khác', '#929aa4'],
];
export function planningGroup(code = '', category = '') {
  if (category === 'RESIDENTIAL_PLANNING') return 'housing';
  if (code === 'QHNN') return 'agriculture';
  if (code === 'QHMN') return 'water';
  if (code === 'QHDL' || code === 'QHTM') return 'commerce';
  if (code.startsWith('QHCX')) return 'green';
  // QHCCDT công cộng, QHTHCS/QHTHPT trường học, QHCQ cơ quan, QHTTYT y tế, QHTTNC, QHTG tôn giáo.
  if (/^QH(CC|TH|CQ|TTYT|TTNC|TG|GD|YT)/.test(code)) return 'public';
  return 'other';
}

export function formatVnd(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return null;
  return (n / 1e9).toLocaleString('vi-VN', { maximumFractionDigits: 2 }) + ' tỷ';
}
export function formatArea(value) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n.toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' m²' : null;
}
export const landDetailPath = row => '/land/' + encodeURIComponent(row.landId || row.sourceCode);

export async function landFetch(path, { signal } = {}) {
  const response = await fetch(LAND_BASE + path, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) {
    const error = Error(response.status === 404 ? 'Không tìm thấy hồ sơ đất.' : 'Chưa tải được dữ liệu đất. Vui lòng thử lại.');
    error.status = response.status;
    throw error;
  }
  return response.json();
}
export const loadRecord = (id, options) => landFetch('/records/' + encodeURIComponent(id), options);
export const loadNeighbors = (id, options) => landFetch('/neighbors?id=' + encodeURIComponent(id), options);
export const loadFloodMap = (ids, options) => landFetch('/flood-map' + (ids ? '?ids=' + encodeURIComponent(ids.join(',')) : ''), options);

// Shape check for the chat packet. Rejecting is safer than rendering an unexpected record.
export function validLand(land) {
  if (!land || land.version !== 'LAND_V1' || !LAND_KINDS.includes(land.kind) || land.demoOnly !== true) return false;
  if (!Array.isArray(land.rows) || land.rows.length > 10 || !Array.isArray(land.floodRecords) || land.floodRecords.length > 10) return false;
  for (const r of land.rows) {
    if (!r || !CODE.test(r.sourceCode || '') || !UUID.test(r.landId || '') || typeof r.displayName !== 'string' || !r.displayName.trim()) return false;
    if (!['PLANNING_CELL', 'GULAND_PARCEL', 'PROJECT_LOT', 'PROJECT_LOT_UNLOCATED'].includes(r.kind)) return false;
    if (!Object.hasOwn(PRICE_TYPE_LABEL, r.priceType)) return false;
  }
  for (const f of land.floodRecords) if (!f || !/^[A-Za-z0-9-]{1,40}$/.test(f.id || '') || typeof f.location_text !== 'string') return false;
  return true;
}

let planningRequest;
export function loadPlanningCells() {
  if (!planningRequest) planningRequest = landFetch("/planning-cells").catch(error => { planningRequest = null; throw error; });
  return planningRequest;
}

// Compact display wording; provenance and synthetic flags remain explicit.
export function landDisplayValue(value) {
 return typeof value==='string' ? value.replace(/Giá mô phỏng(?: \(không phải giá thị trường\))?/gi,'Giá giả lập (demo)').replace(/\s*[—·-]\s*giả định demo/gi,'') : value;
}
