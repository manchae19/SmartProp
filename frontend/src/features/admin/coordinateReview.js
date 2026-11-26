/**
 * Coordinate Provenance V1 — nhãn hiển thị cho giao diện quản trị.
 *
 * Tách khỏi component để test được logic nhãn mà không cần render.
 * Nguyên tắc: không khẳng định quá mức bằng chứng. `VERIFIED_EXACT` chỉ là hợp lệ
 * địa giới cấp quận, KHÔNG phải xác minh cấp thửa.
 */

export const SOURCE_LABEL = {
  USER_PINNED: 'Người đăng chọn trên bản đồ',
  GEOCODED: 'Hệ thống tạo từ địa chỉ',
  IMPORTED: 'Dữ liệu nhập từ nguồn ngoài',
  ADMIN_DEFAULT: 'Quản trị viên đặt',
  UNKNOWN: 'Chưa xác định nguồn',
};

export const ACCURACY_LABEL = {
  UNKNOWN: 'Chưa xác định',
  CITY: 'Cấp thành phố',
  DISTRICT: 'Cấp quận',
  WARD: 'Cấp phường',
  STREET: 'Cấp tuyến đường',
  BUILDING: 'Cấp tòa nhà',
  PARCEL: 'Cấp thửa đất',
};

export const VERIFICATION_LABEL = {
  UNVERIFIED: 'Chưa xác minh',
  PENDING_REVIEW: 'Đang chờ kiểm tra',
  VERIFIED: 'Đã xác minh',
  REJECTED: 'Bị từ chối',
  STALE: 'Cần xác minh lại',
};

export const METHOD_LABEL = {
  FIELD_SURVEY: 'Khảo sát thực địa',
  CADASTRAL_RECORD: 'Đối chiếu hồ sơ địa chính',
  AERIAL_IMAGERY: 'Ảnh hàng không',
  ADMIN_REVIEW: 'Quản trị viên duyệt',
};

export const GEOGRAPHIC_LABEL = {
  VERIFIED_EXACT: 'Nằm trong ranh giới quận đã khai báo',
  VERIFIED_BOUNDARY_BUFFER: 'Sát biên ranh giới quận (trong dung sai)',
  INVALID_DISTRICT_MISMATCH: 'Không khớp quận đã khai báo',
  INVALID_OUT_OF_CITY: 'Ngoài địa bàn thành phố',
  INVALID_GEOMETRY: 'Hình học không hợp lệ',
  INVALID_COORDINATE: 'Tọa độ ngoài khoảng hợp lệ',
  UNKNOWN: 'Chưa đánh giá',
};

/** Màu trạng thái — không dùng đỏ cho "chưa xác minh". */
export function verificationTone(status) {
  switch (status) {
    case 'VERIFIED': return 'verified';
    case 'REJECTED': return 'danger';
    case 'STALE': return 'warning';
    case 'PENDING_REVIEW': return 'pending';
    default: return 'neutral';
  }
}

/** Cảnh báo khi tọa độ không khớp địa bàn khai báo. */
export function isDistrictMismatch(status) {
  return status === 'INVALID_DISTRICT_MISMATCH';
}

/**
 * Nhãn tổng hợp cho admin — mô tả mức bằng chứng thực tế.
 *
 * Chỉ nói "cấp thửa" khi backend trả `parcelAnalysisEligible`.
 */
export function reviewHeadline(detail) {
  if (!detail) return 'Chưa có dữ liệu';
  if (detail.parcelAnalysisEligible === true) return 'Đã xác minh cấp thửa đất';
  if (detail.verificationStatus === 'VERIFIED') return 'Đã xác minh (chưa đủ cấp thửa)';
  if (detail.verificationStatus === 'REJECTED') return 'Đã từ chối';
  if (isDistrictMismatch(detail.geographicValidationStatus)) {
    return 'Tọa độ không khớp địa bàn khai báo';
  }
  if (detail.verificationStatus === 'PENDING_REVIEW') return 'Đang chờ kiểm tra';
  return 'Chưa xác minh';
}

/** Định dạng khoảng cách chính xác. */
export function accuracyText(level, meters) {
  const label = ACCURACY_LABEL[level] || 'Chưa xác định';
  if (meters == null) return label;
  return `${label} (±${meters} m)`;
}

/** Định dạng thời điểm, an toàn với null. */
export function timeText(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('vi-VN');
  } catch {
    return '—';
  }
}

/**
 * Kiểm tra form xác minh trước khi gửi.
 *
 * Backend cũng kiểm tra, nhưng chặn sớm ở client tránh round-trip vô ích.
 * Trả mảng lỗi; rỗng nghĩa là hợp lệ.
 */
export function validateVerification(form) {
  const errors = [];
  if (!form.expectedRevision || form.expectedRevision < 1) {
    errors.push('Thiếu revision cần xác minh');
  }
  if (!form.verificationStatus) {
    errors.push('Chọn quyết định xác minh');
  }
  if (!form.accuracyLevel) {
    errors.push('Chọn mức độ chính xác');
  }
  if (form.verificationStatus === 'VERIFIED') {
    if (!form.verificationMethod) {
      errors.push('Xác minh cần phương pháp');
    }
    if (!form.evidenceReference || !form.evidenceReference.trim()) {
      errors.push('Xác minh cần tham chiếu bằng chứng');
    }
  }
  if (form.accuracyLevel === 'PARCEL') {
    if (form.verificationStatus !== 'VERIFIED') {
      errors.push('Cấp thửa chỉ hợp lệ khi đã xác minh');
    }
    if (!form.accuracyMeters || form.accuracyMeters <= 0) {
      errors.push('Cấp thửa cần sai số (mét) dương');
    }
  }
  return errors;
}

export function pendingQueueParams({ page = 0, limit = 50, statusFilter = '', search = '' } = {}) {
  const safePage = Math.max(0, Math.floor(Number(page) || 0));
  const safeLimit = Math.max(1, Math.floor(Number(limit) || 50));
  const params = new URLSearchParams({ limit: String(safeLimit), offset: String(safePage * safeLimit) });
  if (statusFilter) params.set('verificationStatus', statusFilter);
  if (search.trim()) params.set('q', search.trim());
  return params;
}

export function pendingPageRange(page, total, limit = 50) {
  const safePage = Math.max(0, Math.floor(Number(page) || 0));
  const safeLimit = Math.max(1, Math.floor(Number(limit) || 50));
  const safeTotal = Number.isFinite(Number(total)) ? Math.max(0, Number(total)) : 0;
  return {
    start: safeTotal === 0 ? 0 : safePage * safeLimit + 1,
    end: safeTotal === 0 ? 0 : Math.min((safePage + 1) * safeLimit, safeTotal),
    total: safeTotal,
  };
}
