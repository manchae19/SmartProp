const SOURCE_LABEL = {
  USER_PINNED: "Người đăng chọn trên bản đồ",
  GEOCODED: "Hệ thống tạo từ địa chỉ",
  IMPORTED: "Dữ liệu nhập từ nguồn ngoài",
  ADMIN_DEFAULT: "Vị trí mặc định do quản trị viên đặt",
  UNKNOWN: "Chưa xác định nguồn",
};

export function coordinateSourceLabel(source) {
  return SOURCE_LABEL[source] || "Chưa xác định nguồn";
}

export function coordinateHeadline(coordinate) {
  if (!coordinate) return "Chưa có thông tin vị trí";
  if (coordinate.parcelAnalysisEligible === true) return "Vị trí đủ điều kiện phân tích cấp thửa";
  if (coordinate.geographicValidationStatus === "INVALID_DISTRICT_MISMATCH") return "Vị trí không khớp địa bàn khai báo";
  if (coordinate.verificationStatus === "REJECTED") return "Vị trí bị từ chối xác minh";
  if (coordinate.verificationStatus === "STALE") return "Vị trí cần được xác minh lại";
  if (coordinate.verificationStatus === "VERIFIED") return "Vị trí đã được xác minh";
  if (coordinate.referenceMapEligible === true) return "Vị trí tham khảo, chưa xác minh cấp thửa";
  return "Chưa đủ dữ liệu để đánh giá vị trí";
}

export function coordinateTone(coordinate) {
  if (!coordinate) return "neutral";
  if (coordinate.geographicValidationStatus === "INVALID_DISTRICT_MISMATCH") return "warning";
  if (coordinate.parcelAnalysisEligible === true || coordinate.verificationStatus === "VERIFIED") return "verified";
  if (coordinate.referenceMapEligible === true) return "reference";
  return "neutral";
}
