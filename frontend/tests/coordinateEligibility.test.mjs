import { test } from 'node:test'
import assert from 'node:assert/strict'
import { publicMapPoint } from '../src/features/map/locationDisplay.js'
import { canAnalyzeDistance } from '../src/features/map/coordinateEligibility.js'
import { coordinateHeadline, coordinateSourceLabel } from '../src/features/property/coordinateStatus.js'

const point = { latitude: 16.05, longitude: 108.2 }

test('mismatch or false reference eligibility never becomes a map marker', () => {
  assert.equal(publicMapPoint({ ...point, coordinate: { referenceMapEligible: false, geographicValidationStatus: 'VERIFIED_EXACT', verificationStatus: 'UNVERIFIED' } }), false)
  assert.equal(publicMapPoint({ ...point, coordinate: { referenceMapEligible: true, geographicValidationStatus: 'INVALID_DISTRICT_MISMATCH', verificationStatus: 'UNVERIFIED' } }), false)
  assert.equal(publicMapPoint({ ...point, coordinate: { referenceMapEligible: true, geographicValidationStatus: 'VERIFIED_EXACT', verificationStatus: 'REJECTED' } }), false)
})

test('reference map may show while distance analysis remains disabled', () => {
  const property = { ...point, coordinate: { referenceMapEligible: true, distanceAnalysisEligible: false, geographicValidationStatus: 'VERIFIED_BOUNDARY_BUFFER', verificationStatus: 'UNVERIFIED' } }
  assert.equal(publicMapPoint(property), true)
  assert.equal(canAnalyzeDistance(property), false)
})

test('only explicit true distance eligibility enables analysis', () => {
  const eligible = { coordinate: { referenceMapEligible: true, distanceAnalysisEligible: true, geographicValidationStatus: 'VERIFIED_EXACT', verificationStatus: 'UNVERIFIED', coordinateSource: 'USER_PINNED', accuracyLevel: 'STREET' } }
  assert.equal(canAnalyzeDistance(eligible), true)
  assert.equal(canAnalyzeDistance({ coordinate: { ...eligible.coordinate, distanceAnalysisEligible: false } }), false)
  assert.equal(canAnalyzeDistance({ coordinate: { ...eligible.coordinate, geographicValidationStatus: 'INVALID_DISTRICT_MISMATCH' } }), false)
  assert.equal(canAnalyzeDistance({ coordinate: { ...eligible.coordinate, verificationStatus: 'REJECTED' } }), false)
  assert.equal(canAnalyzeDistance({ coordinate: { ...eligible.coordinate, verificationStatus: 'STALE' } }), false)
  assert.equal(canAnalyzeDistance({ coordinate: { ...eligible.coordinate, coordinateSource: 'UNKNOWN' } }), false)
  assert.equal(canAnalyzeDistance({ coordinate: { ...eligible.coordinate, accuracyLevel: 'UNKNOWN' } }), false)
  assert.equal(canAnalyzeDistance({ coordinate: { referenceMapEligible: true } }), false)
  assert.equal(canAnalyzeDistance({}), false)
  assert.equal(canAnalyzeDistance({ coordinate: { distanceAnalysisEligible: 1 } }), false)
})

test('coordinate source labels never invent user supplied provenance', () => {
  assert.equal(coordinateSourceLabel('UNKNOWN'), 'Chưa xác định nguồn')
  assert.equal(coordinateSourceLabel('GEOCODED'), 'Hệ thống tạo từ địa chỉ')
  assert.equal(coordinateSourceLabel('IMPORTED'), 'Dữ liệu nhập từ nguồn ngoài')
  assert.equal(coordinateSourceLabel('ADMIN_DEFAULT'), 'Vị trí mặc định do quản trị viên đặt')
  assert.equal(coordinateSourceLabel('USER_PINNED'), 'Người đăng chọn trên bản đồ')
  assert.match(coordinateHeadline({ parcelAnalysisEligible: false, verificationStatus: 'UNVERIFIED' }), /Chưa đủ dữ liệu/)
  assert.doesNotMatch(coordinateHeadline({ parcelAnalysisEligible: false, verificationStatus: 'VERIFIED' }), /cấp thửa/)
  assert.match(coordinateHeadline({ parcelAnalysisEligible: false, verificationStatus: 'UNVERIFIED', geographicValidationStatus: 'INVALID_DISTRICT_MISMATCH' }), /không khớp/)
})
