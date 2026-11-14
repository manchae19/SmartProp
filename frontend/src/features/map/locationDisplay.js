import { validCoordinates } from '../property/postForm.js'

export function publicMapPoint(property) {
  return !!property && validCoordinates(property.latitude, property.longitude)
    && property.locationVisibility !== 'HIDDEN'
    && !(property.locationAccuracy === 'BUILDING_ONLY' && property.locationApproved !== true)
}
export function locationLabel(property) {
  switch (property?.locationAccuracy) {
    case 'EXACT_PROPERTY': return 'Vị trí chính xác do người đăng xác nhận'
    case 'BUILDING_ONLY': return 'Vị trí cấp tòa nhà, không xác định căn hộ cụ thể'
    case 'APPROXIMATE': return 'Vị trí tương đối, chỉ để tham khảo'
    default: return 'Vị trí do người đăng cung cấp; chưa xác minh độ chính xác'
  }
}
