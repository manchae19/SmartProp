import { validCoordinates } from './postForm.js'
import { projectPoint } from './postMap.js'

export const illustrativeAreaLabel = 'Vùng xanh chỉ minh họa quanh ghim đề xuất, không phải ranh giới tài sản hoặc bán kính sai số đã xác minh. Hãy kiểm tra và chỉnh ghim theo vị trí thực tế.'

// The current geocoding DTO exposes a center, not a provider boundary/bounding box.
// These display sizes are UI choices, never a confidence interval or persisted property data.
export function locationPreviewRegion(candidate) {
  if (!candidate || candidate.provider !== 'GEOAPIFY' || candidate.mapProvider !== 'OSM'
    || !validCoordinates(candidate.latitude, candidate.longitude) || Math.abs(Number(candidate.latitude)) > 85) return null
  const precision = candidate.context?.precision
  const street = precision === 'APPROXIMATE_STREET' || candidate.context?.resultType === 'street' || candidate.accuracy === 'INTERPOLATED'
  const area = precision === 'APPROXIMATE_AREA' || candidate.locationLevel === 'APPROXIMATE' || candidate.accuracy === 'APPROXIMATE'
  if (!street && !area) return null
  return Object.freeze({
    kind: 'ILLUSTRATIVE_CIRCLE', latitude: Number(candidate.latitude), longitude: Number(candidate.longitude),
    displayRadiusMeters: street ? 200 : 800, label: illustrativeAreaLabel,
  })
}

export function projectPreviewRegion(region, center, zoom, width, height) {
  if (region?.kind !== 'ILLUSTRATIVE_CIRCLE' || !validCoordinates(region.latitude, region.longitude)
    || !validCoordinates(center?.latitude, center?.longitude) || Math.abs(Number(region.latitude)) > 85
    || !Number.isInteger(zoom) || zoom < 3 || zoom > 19 || !(width > 0) || !(height > 0)
    || ![200, 800].includes(region.displayRadiusMeters)) return null
  const point = projectPoint(region.latitude, region.longitude, zoom)
  const origin = projectPoint(Number(center.latitude), Number(center.longitude), zoom)
  const world = 256 * 2 ** zoom
  // Use the closest wrapped world so panning across the date line cannot detach the overlay.
  const dx = ((point.x - origin.x + world / 2) % world + world) % world - world / 2
  const pixelsPerMeter = world / (40075016.68557849 * Math.cos(region.latitude * Math.PI / 180))
  return { cx: dx + width / 2, cy: point.y - origin.y + height / 2, radius: region.displayRadiusMeters * pixelsPerMeter }
}
