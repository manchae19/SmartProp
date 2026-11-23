import test from 'node:test'
import assert from 'node:assert/strict'
import {
  SOURCE_LABEL,
  ACCURACY_LABEL,
  VERIFICATION_LABEL,
  GEOGRAPHIC_LABEL,
  verificationTone,
  isDistrictMismatch,
  reviewHeadline,
  accuracyText,
  timeText,
  validateVerification,
} from '../src/features/admin/coordinateReview.js'

// ---------- Nhãn ----------

test('mọi enum backend đều có nhãn tiếng Việt', () => {
  for (const value of ['USER_PINNED', 'GEOCODED', 'IMPORTED', 'ADMIN_DEFAULT', 'UNKNOWN']) {
    assert.ok(SOURCE_LABEL[value], `thiếu nhãn cho source ${value}`)
  }
  for (const value of ['UNKNOWN', 'CITY', 'DISTRICT', 'WARD', 'STREET', 'BUILDING', 'PARCEL']) {
    assert.ok(ACCURACY_LABEL[value], `thiếu nhãn cho accuracy ${value}`)
  }
  for (const value of ['UNVERIFIED', 'PENDING_REVIEW', 'VERIFIED', 'REJECTED', 'STALE']) {
    assert.ok(VERIFICATION_LABEL[value], `thiếu nhãn cho verification ${value}`)
  }
  assert.ok(GEOGRAPHIC_LABEL.INVALID_DISTRICT_MISMATCH)
})

// ---------- Màu trạng thái ----------

test('UNVERIFIED không dùng màu đỏ', () => {
  assert.equal(verificationTone('UNVERIFIED'), 'neutral')
  assert.notEqual(verificationTone('UNVERIFIED'), 'danger')
})

test('REJECTED dùng màu cảnh báo', () => {
  assert.equal(verificationTone('REJECTED'), 'danger')
})

test('VERIFIED dùng màu xác minh', () => {
  assert.equal(verificationTone('VERIFIED'), 'verified')
})

test('STALE dùng màu cảnh báo', () => {
  assert.equal(verificationTone('STALE'), 'warning')
})

// ---------- Phát hiện sai địa bàn ----------

test('isDistrictMismatch chỉ đúng với INVALID_DISTRICT_MISMATCH', () => {
  assert.equal(isDistrictMismatch('INVALID_DISTRICT_MISMATCH'), true)
  assert.equal(isDistrictMismatch('VERIFIED_EXACT'), false)
  assert.equal(isDistrictMismatch('VERIFIED_BOUNDARY_BUFFER'), false)
  assert.equal(isDistrictMismatch(null), false)
})

// ---------- Headline: không khẳng định quá mức bằng chứng ----------

test('VERIFIED_EXACT không được gọi là xác minh cấp thửa', () => {
  const detail = {
    verificationStatus: 'UNVERIFIED',
    geographicValidationStatus: 'VERIFIED_EXACT',
    parcelAnalysisEligible: false,
  }
  const headline = reviewHeadline(detail)
  assert.ok(!headline.includes('thửa'), `headline không được nhắc thửa: ${headline}`)
  assert.ok(headline.includes('Chưa xác minh'))
})

test('chỉ parcelAnalysisEligible mới được gọi là cấp thửa', () => {
  const detail = {
    verificationStatus: 'VERIFIED',
    geographicValidationStatus: 'VERIFIED_EXACT',
    parcelAnalysisEligible: true,
  }
  assert.ok(reviewHeadline(detail).includes('cấp thửa'))
})

test('VERIFIED nhưng chưa đủ cấp thửa phải nói rõ', () => {
  const detail = {
    verificationStatus: 'VERIFIED',
    geographicValidationStatus: 'VERIFIED_EXACT',
    parcelAnalysisEligible: false,
  }
  const headline = reviewHeadline(detail)
  assert.ok(headline.includes('chưa đủ cấp thửa'), headline)
})

test('sai địa bàn được ưu tiên cảnh báo trong headline', () => {
  const detail = {
    verificationStatus: 'UNVERIFIED',
    geographicValidationStatus: 'INVALID_DISTRICT_MISMATCH',
    parcelAnalysisEligible: false,
  }
  assert.ok(reviewHeadline(detail).includes('không khớp địa bàn'))
})

test('reviewHeadline an toàn với null', () => {
  assert.equal(reviewHeadline(null), 'Chưa có dữ liệu')
})

// ---------- Định dạng ----------

test('accuracyText hiển thị sai số khi có', () => {
  assert.equal(accuracyText('PARCEL', 3.5), 'Cấp thửa đất (±3.5 m)')
  assert.equal(accuracyText('UNKNOWN', null), 'Chưa xác định')
})

test('timeText an toàn với null và giá trị lạ', () => {
  assert.equal(timeText(null), '—')
  assert.equal(timeText(undefined), '—')
  assert.notEqual(timeText('2026-11-23T12:00:00Z'), '—')
})

// ---------- Validate form ----------

test('form hợp lệ khi xác minh có phương pháp và bằng chứng', () => {
  const errors = validateVerification({
    expectedRevision: 3,
    verificationStatus: 'VERIFIED',
    verificationMethod: 'CADASTRAL_RECORD',
    evidenceReference: 'HS-2026-001',
    accuracyLevel: 'STREET',
  })
  assert.deepEqual(errors, [])
})

test('thiếu expectedRevision bị chặn', () => {
  const errors = validateVerification({
    verificationStatus: 'VERIFIED',
    verificationMethod: 'CADASTRAL_RECORD',
    evidenceReference: 'X',
    accuracyLevel: 'STREET',
  })
  assert.ok(errors.some(e => e.includes('revision')))
})

test('xác minh thiếu bằng chứng bị chặn', () => {
  const errors = validateVerification({
    expectedRevision: 1,
    verificationStatus: 'VERIFIED',
    verificationMethod: 'CADASTRAL_RECORD',
    evidenceReference: '   ',
    accuracyLevel: 'STREET',
  })
  assert.ok(errors.some(e => e.includes('bằng chứng')))
})

test('xác minh thiếu phương pháp bị chặn', () => {
  const errors = validateVerification({
    expectedRevision: 1,
    verificationStatus: 'VERIFIED',
    evidenceReference: 'X',
    accuracyLevel: 'STREET',
  })
  assert.ok(errors.some(e => e.includes('phương pháp')))
})

test('PARCEL khi chưa xác minh bị chặn', () => {
  const errors = validateVerification({
    expectedRevision: 1,
    verificationStatus: 'UNVERIFIED',
    accuracyLevel: 'PARCEL',
    accuracyMeters: 3,
  })
  assert.ok(errors.some(e => e.includes('Cấp thửa')))
})

test('PARCEL thiếu sai số bị chặn', () => {
  const errors = validateVerification({
    expectedRevision: 1,
    verificationStatus: 'VERIFIED',
    verificationMethod: 'CADASTRAL_RECORD',
    evidenceReference: 'X',
    accuracyLevel: 'PARCEL',
  })
  assert.ok(errors.some(e => e.includes('sai số')))
})

test('PARCEL đủ điều kiện được chấp nhận', () => {
  const errors = validateVerification({
    expectedRevision: 1,
    verificationStatus: 'VERIFIED',
    verificationMethod: 'CADASTRAL_RECORD',
    evidenceReference: 'HS-2026-001',
    accuracyLevel: 'PARCEL',
    accuracyMeters: 3.5,
  })
  assert.deepEqual(errors, [])
})

test('từ chối không bắt buộc bằng chứng', () => {
  const errors = validateVerification({
    expectedRevision: 1,
    verificationStatus: 'REJECTED',
    accuracyLevel: 'UNKNOWN',
  })
  assert.deepEqual(errors, [])
})
