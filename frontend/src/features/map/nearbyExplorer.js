export const POI_GROUPS = [
  { id: 'education', label: 'Trường học', icon: '🎓', color: '#2563eb' },
  { id: 'health', label: 'Y tế', icon: '✚', color: '#ef476f' },
  { id: 'shopping', label: 'Mua sắm', icon: '▤', color: '#e28a16' },
  { id: 'park', label: 'Công viên', icon: '♣', color: '#38975c' },
  { id: 'dining', label: 'Nhà hàng · Cà phê', icon: '♨', color: '#d97443' },
  { id: 'bank', label: 'Ngân hàng', icon: '▥', color: '#6d5bd0' },
  { id: 'tourism', label: 'Du lịch · Khách sạn', icon: '⚑', color: '#0898bc' },
  { id: 'entertainment', label: 'Giải trí', icon: '★', color: '#bb47c4' }
]
export const RADII = [500, 1000, 2000, 5000]
export const DEFAULT_GROUPS = ['education', 'health', 'shopping', 'park']
export function validPoint(p) {
  return p && p.latitude !== null && p.longitude !== null && p.latitude !== '' && p.longitude !== ''
    && Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude))
    && Math.abs(Number(p.latitude)) <= 90 && Number(p.longitude) > -180 && Number(p.longitude) <= 180
}
export function distanceMeters(a, b) {
  const rad = n => n * Math.PI / 180, dlat = rad(b.latitude - a.latitude), dlon = rad(b.longitude - a.longitude)
  const x = Math.sin(dlat/2)**2 + Math.cos(rad(a.latitude))*Math.cos(rad(b.latitude))*Math.sin(dlon/2)**2
  return 6371008.8 * 2 * Math.atan2(Math.sqrt(Math.min(1,x)), Math.sqrt(Math.max(0,1-x)))
}
export function filteredPlaces(items, origin, radius, groups) {
  if (!validPoint(origin) || !RADII.includes(Number(radius))) return []
  const seen = new Set()
  return (Array.isArray(items) ? items : []).filter(p => {
    if (!p?.id || !p.name || !validPoint(p) || seen.has(p.id) || !(p.categoryGroups || [p.category]).some(c => groups.includes(c))) return false
    seen.add(p.id); return true
  }).map(p => ({ ...p, distanceMeters: distanceMeters(origin, p) }))
    .filter(p => p.distanceMeters <= radius).sort((a,b) => a.distanceMeters - b.distanceMeters || a.id.localeCompare(b.id))
}
export function distanceLabel(m) { return m >= 1000 ? (m/1000).toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' km' : Math.round(m) + ' m' }
export function safePropertyId(id) { return /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id || '') }
export function nearbyPath(id, radius, groups) {
  if (!safePropertyId(id) || !RADII.includes(Number(radius)) || !groups.length || groups.some(g => !POI_GROUPS.some(x => x.id === g))) return null
  return '/properties/' + encodeURIComponent(id) + '/nearby?' + new URLSearchParams({ radius, categories: [...new Set(groups)].sort().join(',') })
}
