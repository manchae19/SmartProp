import { validCoordinates } from './postForm.js'

const categories = {
  SCHOOL: { label: 'Trường học', symbol: '▣' },
  HOSPITAL: { label: 'Bệnh viện', symbol: '✚' },
  PARK: { label: 'Công viên', symbol: '♧' },
  SUPERMARKET: { label: 'Siêu thị', symbol: '▤' },
  TRANSPORT: { label: 'Giao thông', symbol: '↔' },
}
export const poiLabel = category => categories[String(category || '').toUpperCase()]?.label || String(category || 'Tiện ích')
export const poiSymbol = category => categories[String(category || '').toUpperCase()]?.symbol || '●'
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
