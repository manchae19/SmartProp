import { api } from './api.js'
import { validCoordinates } from './postForm.js'

export function geocodingInput(value) {
  return Object.fromEntries(['address', 'city', 'district', 'ward'].map(key => [key, String(value[key] || '')]))
}
export const geocodingSignature = value => JSON.stringify(geocodingInput(value))
export async function searchLocations(value, request = api) {
  if (!String(value.address || '').trim() || !String(value.city || '').trim()) throw Error('Nhập địa chỉ đầy đủ và thành phố trước khi tìm vị trí.')
  const result = await request('/geocoding/search', { method: 'POST', body: { ...geocodingInput(value), shareAddress: true } })
  return { ...result, candidates: (result.candidates || []).filter(candidate => validCoordinates(candidate.latitude, candidate.longitude)) }
}
export function candidateCanBeConfirmed(candidate) {
  return !!candidate && validCoordinates(candidate.latitude, candidate.longitude) && candidate.provider === 'GEOAPIFY'
    && candidate.mapProvider === 'OSM' && candidate.storageAllowed === true && candidate.addressMatched === true
    && candidate.locationLevel === 'BUILDING_ONLY' && !['INTERPOLATED', 'APPROXIMATE'].includes(candidate.accuracy)
}
export function accuracyLabel(candidate) {
  if (candidate.accuracy === 'INTERPOLATED') return 'Vị trí nội suy theo số nhà, cần chỉnh ghim'
  if (candidate.accuracy === 'APPROXIMATE' || candidate.locationLevel === 'APPROXIMATE') return 'Chỉ xác định đường hoặc khu vực, cần chỉnh ghim'
  if (candidate.accuracy === 'EXACT') return 'Nhà cung cấp xác định tới số nhà; chưa xác minh bất động sản'
  return 'Gợi ý cấp tòa nhà; chưa xác minh căn hộ hoặc ranh giới bất động sản'
}
