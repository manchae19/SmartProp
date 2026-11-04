import { validCoordinates } from './postForm.js'

const categories = {
  SCHOOL: { label: 'Trường học', symbol: '▣' },
  HOSPITAL: { label: 'Bệnh viện & Y tế', symbol: '✚' },
  PARK: { label: 'Công viên & Biển', symbol: '♧' },
  SUPERMARKET: { label: 'Siêu thị & Chợ', symbol: '▤' },
  TRANSPORT: { label: 'Giao thông', symbol: '↔' },
  PUBLIC_TRANSPORT: { label: 'Giao thông công cộng', symbol: '↔' },
  BEACH: { label: 'Bãi biển', symbol: '≈' },
  MARKET: { label: 'Chợ', symbol: '▤' },
  PHARMACY: { label: 'Nhà thuốc', symbol: '✚' },
}

export const poiLabel = category => categories[String(category || '').toUpperCase()]?.label || String(category || 'Tiện ích')
export const poiSymbol = category => categories[String(category || '').toUpperCase()]?.symbol || '●'

export function poiColor(category) {
  const cat = String(category || '').toUpperCase()
  if (cat === 'SCHOOL') return '#2563eb' // Blue
  if (cat === 'HOSPITAL') return '#e11d48' // Rose / Red
  if (cat === 'PARK') return '#059669' // Emerald Green
  if (cat === 'SUPERMARKET') return '#d97706' // Amber / Orange
  if (cat === 'TRANSPORT') return '#7c3aed' // Violet
  if (cat === 'PUBLIC_TRANSPORT') return '#7c3aed'
  if (cat === 'BEACH') return '#0284c7'
  if (cat === 'MARKET') return '#9a5b15'
  if (cat === 'PHARMACY') return '#0f766e'
  return '#1e325a' // Default Navy
}

export function poiColorBg(category) {
  const cat = String(category || '').toUpperCase()
  if (cat === 'SCHOOL') return '#eff6ff'
  if (cat === 'HOSPITAL') return '#fff1f2'
  if (cat === 'PARK') return '#ecfdf5'
  if (cat === 'SUPERMARKET') return '#fffbeb'
  if (cat === 'TRANSPORT') return '#f5f3ff'
  return '#f1f5f9'
}

export function poiColorBorder(category) {
  const cat = String(category || '').toUpperCase()
  if (cat === 'SCHOOL') return '#bfdbfe'
  if (cat === 'HOSPITAL') return '#fecdd3'
  if (cat === 'PARK') return '#a7f3d0'
  if (cat === 'SUPERMARKET') return '#fde68a'
  if (cat === 'TRANSPORT') return '#ddd6fe'
  return '#cbd5e1'
}

export function poiSvgPath(category) {
  const cat = String(category || '').toUpperCase()
  if (cat === 'BEACH') return 'M3 17q3-4 6 0t6 0t6 0M3 21q3-4 6 0t6 0t6 0M5 9a7 7 0 0 1 14 0H5zm7-7v11'
  if (cat === 'MARKET') return 'M3 10h18l-2-6H5l-2 6zm2 0v11h14V10M9 21v-7h6v7'
  if (cat === 'PHARMACY') return 'M9 3h6v6h6v6h-6v6H9v-6H3V9h6z'
  if (cat === 'PUBLIC_TRANSPORT') return poiSvgPath('TRANSPORT')
  if (cat === 'SCHOOL') return 'M22 10v6M2 10l10-5 10 5-10 5z M6 12v5c3 3 9 3 12 0v-5'
  if (cat === 'HOSPITAL') return 'M12 7v10M7 12h10 M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z'
  if (cat === 'PARK') return 'M12 2l-5 7h3l-4 7h6v4h2v-4h6l-4-7h3z'
  if (cat === 'SUPERMARKET') return 'M1 1h4l2.6 12h11.8l2.6-8H6M9 20a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm9 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z'
  if (cat === 'TRANSPORT') return 'M4 4h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm0 8h16M7 17v3m10-3v3M6 8.5h.01M18 8.5h.01'
  return 'M12 2L7 9h3l-4 7h6v4h2v-4h6l-4-7h3z'
}

export function poiSvgIcon(category) {
  const p = poiSvgPath(category)
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;"><path d="${p}" /></svg>`
}

export function poiHasPoint(poi) {
  return !!poi && typeof poi.latitude === 'number' && typeof poi.longitude === 'number' && validCoordinates(poi.latitude, poi.longitude)
}

export function nearbyPlaces(input, radiusMeters) {
  const radius = Number(radiusMeters)
  if (!Array.isArray(input) || !Number.isFinite(radius) || radius < 1 || radius > 50000) return []
  const seen = new Set()
  return input.filter(poi => {
    if (!poi || typeof poi.id !== 'string' || !poi.id.trim() || typeof poi.name !== 'string' || !poi.name.trim()
      || typeof poi.distanceMeters !== 'number' || !Number.isFinite(poi.distanceMeters) || poi.distanceMeters < 0 || poi.distanceMeters > radius || seen.has(poi.id)) return false
    seen.add(poi.id)
    return true
  }).map(poi => ({ ...poi })).sort((a, b) => a.distanceMeters - b.distanceMeters)
}
