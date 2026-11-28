// Display labels only. Backend values remain intact in data/state/attributes.
// Verified against MarketAnalyticsService.buildMeta/status and property.js.
const labels = Object.freeze({
  ASKING_SALE_VND_TOTAL: 'Tổng giá rao bán (VNĐ)',
  INSUFFICIENT_DATA: 'Chưa đủ dữ liệu',
  OK: 'Đủ mẫu thống kê',
  COMMERCIAL: 'Mặt bằng',
});
export function marketAnalyticsLabel(value) {
  return Object.hasOwn(labels, value) ? labels[value] : value || '—';
}
