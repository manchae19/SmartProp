export const applicationStatuses = Object.freeze({
  NOT_REQUESTED: 'Chưa đăng ký',
  PENDING: 'Đang chờ duyệt',
  APPROVED: 'Đã được duyệt',
  REJECTED: 'Bị từ chối',
  NEEDS_INFORMATION: 'Cần bổ sung thông tin',
  SUSPENDED: 'Tạm ngưng quyền đăng tin'
});
export const applicationActions = Object.freeze({
  APPROVE: 'Duyệt',
  REJECT: 'Từ chối',
  REQUEST_INFORMATION: 'Yêu cầu bổ sung',
  SUSPEND: 'Tạm ngưng'
});
export const canRequestBroker = user => !!user?.id && user.role === 'BUYER' && user.status === 'ACTIVE';
export const canApply = (state, user) => canRequestBroker(user) && !!state && !state.canPublish && ['NOT_REQUESTED', 'REJECTED', 'NEEDS_INFORMATION'].includes(state.status);
export const reviewActions = status => status === 'PENDING' ? ['APPROVE', 'REJECT', 'REQUEST_INFORMATION'] : status === 'APPROVED' ? ['SUSPEND'] : status === 'SUSPENDED' ? ['APPROVE'] : [];
export function applicationPayload(form, state, user) {
  if (!canApply(state, user)) throw Error('Hồ sơ hiện không thể gửi yêu cầu.');
  const body = {
    applicantType: form.applicantType,
    displayName: form.displayName.trim(),
    contactPhone: form.contactPhone.trim(),
    operatingArea: form.operatingArea.trim(),
    requestMessage: form.requestMessage.trim(),
    responsibilityAccepted: form.responsibilityAccepted === true
  };
  if (state.application) body.expectedVersion = state.application.contentVersion;
  return body;
}
const fieldLabels = {
  applicantType: 'Loại người đăng',
  displayName: 'Họ tên / tên đơn vị',
  contactPhone: 'Số điện thoại',
  operatingArea: 'Khu vực hoạt động',
  requestMessage: 'Nội dung yêu cầu',
  responsibilityAccepted: 'Xác nhận trách nhiệm',
  expectedVersion: 'Phiên bản hồ sơ',
  reason: 'Lý do xét duyệt'
};
export function brokerErrorKind(error) {
  if (error?.status === 503 && error.code === 'FEATURE_DISABLED') return 'disabled';
  if (error?.status === 503) return 'unavailable';
  return {
    400: 'validation',
    401: 'session',
    403: 'forbidden',
    404: 'not-found',
    409: 'conflict',
    422: 'validation',
    429: 'rate-limit',
    500: 'server'
  }[error?.status] || (error?.status ? 'http' : 'network');
}
export function brokerErrorText(error) {
  if (error?.code === 'AUTH_RETRY_REQUIRED') return error.message;
  const kind = brokerErrorKind(error);
  const messages = {
    disabled: 'Đăng ký quyền đăng tin đang tạm tắt trên máy chủ (HTTP 503 · FEATURE_DISABLED). Quản trị viên cần kiểm tra schema và hoàn tất rollout được phê duyệt trước khi bật tính năng.',
    unavailable: 'Dịch vụ đăng ký quyền đăng tin chưa sẵn sàng (HTTP 503). Vui lòng thử lại sau hoặc liên hệ quản trị viên.',
    session: 'Phiên đăng nhập không còn hợp lệ (HTTP 401). Vui lòng đăng nhập lại.',
    forbidden: 'Bạn không có quyền thực hiện thao tác này (HTTP 403).',
    'not-found': 'Không tìm thấy API hoặc hồ sơ đăng ký (HTTP 404). Vui lòng tải lại; nếu vẫn lỗi, quản trị viên cần kiểm tra phiên bản máy chủ.',
    conflict: 'Hồ sơ đã tồn tại hoặc đã thay đổi (HTTP 409). Tải lại trạng thái và kiểm tra hồ sơ trước khi gửi lại.',
    validation: `Thông tin chưa hợp lệ (HTTP ${error?.status}). Vui lòng kiểm tra các trường bắt buộc.`,
    'rate-limit': 'Bạn đã gửi quá nhiều yêu cầu (HTTP 429). Vui lòng chờ rồi thử lại.',
    server: 'Máy chủ gặp lỗi khi xử lý hồ sơ (HTTP 500). Vui lòng thử lại sau; lỗi này không có nghĩa là tính năng đang tắt.',
    http: `Yêu cầu đăng ký chưa được xử lý (HTTP ${error?.status}). Vui lòng thử lại sau.`,
    network: error?.message || 'Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối.'
  };
  // Only approved field labels are shown; never reflect raw backend exceptions into the page.
  const fields = kind === 'validation' ? Object.keys(error?.fields || {}).filter(k => fieldLabels[k]).map(k => fieldLabels[k]).join(', ') : '';
  return messages[kind] + (fields ? ' Cần kiểm tra: ' + fields + '.' : '');
}
