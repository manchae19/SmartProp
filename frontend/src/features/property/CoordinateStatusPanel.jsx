import React from "react";
import "./CoordinateStatusPanel.css";

/**
 * Coordinate Provenance V1 — hiển thị trạng thái vị trí của tin đăng.
 *
 * Nguyên tắc: KHÔNG hiển thị badge "chính xác" chỉ vì backend trả
 * geographicValidationStatus = VERIFIED_EXACT. Trạng thái đó chỉ có nghĩa
 * "điểm nằm trong polygon quận", không phải cấp thửa.
 *
 * Ba cờ eligibility do backend tính sẵn — component không tự suy luận.
 */

const SOURCE_LABEL = {
  USER_PINNED: "Người đăng chọn trên bản đồ",
  GEOCODED: "Hệ thống tạo từ địa chỉ",
  IMPORTED: "Dữ liệu nhập từ nguồn ngoài",
  ADMIN_DEFAULT: "Vị trí do quản trị viên đặt",
  UNKNOWN: "Chưa xác định nguồn",
};

const ACCURACY_LABEL = {
  UNKNOWN: "Chưa xác định",
  CITY: "Cấp thành phố",
  DISTRICT: "Cấp quận",
  WARD: "Cấp phường",
  STREET: "Cấp tuyến đường",
  BUILDING: "Cấp tòa nhà",
  PARCEL: "Cấp thửa đất",
};

const VERIFICATION_LABEL = {
  UNVERIFIED: "Chưa xác minh",
  PENDING_REVIEW: "Đang chờ duyệt",
  VERIFIED: "Đã xác minh",
  REJECTED: "Bị từ chối",
  STALE: "Cần xác minh lại",
};

const METHOD_LABEL = {
  FIELD_SURVEY: "Khảo sát thực địa",
  CADASTRAL_RECORD: "Đối chiếu hồ sơ địa chính",
  AERIAL_IMAGERY: "Ảnh hàng không",
  ADMIN_REVIEW: "Quản trị viên duyệt",
};

/** Nhãn tổng hợp cho người mua — không khẳng định quá mức bằng chứng. */
export function coordinateHeadline(coordinate) {
  if (!coordinate) return "Chưa có thông tin vị trí";
  if (coordinate.parcelAnalysisEligible) {
    return "Vị trí đã xác minh cấp thửa đất";
  }
  if (coordinate.verificationStatus === "VERIFIED") {
    return "Vị trí đã được xác minh";
  }
  if (coordinate.geographicValidationStatus === "INVALID_DISTRICT_MISMATCH") {
    return "Vị trí không khớp địa bàn khai báo";
  }
  if (coordinate.referenceMapEligible) {
    return "Vị trí tham khảo, chưa xác minh cấp thửa";
  }
  return "Chưa đủ dữ liệu để đánh giá vị trí";
}

/** Mức độ cảnh báo để chọn màu hiển thị. */
export function coordinateTone(coordinate) {
  if (!coordinate) return "neutral";
  if (coordinate.geographicValidationStatus === "INVALID_DISTRICT_MISMATCH") return "warning";
  if (coordinate.parcelAnalysisEligible) return "verified";
  if (coordinate.verificationStatus === "VERIFIED") return "verified";
  if (coordinate.referenceMapEligible) return "reference";
  return "neutral";
}

export default function CoordinateStatusPanel({ coordinate, compact = false }) {
  if (!coordinate) return null;

  const tone = coordinateTone(coordinate);
  const headline = coordinateHeadline(coordinate);
  const mismatch = coordinate.geographicValidationStatus === "INVALID_DISTRICT_MISMATCH";

  return (
    <section
      className={`coordinate-status coordinate-status--${tone}`}
      aria-label="Trạng thái vị trí"
    >
      <p className="coordinate-status__headline">{headline}</p>

      {mismatch && (
        <p className="coordinate-status__warning" role="alert">
          Tọa độ không nằm trong địa bàn quận đã khai báo. Vị trí này cần được
          người đăng kiểm tra lại — hệ thống không tự di chuyển điểm.
        </p>
      )}

      {!compact && (
        <dl className="coordinate-status__details">
          <div>
            <dt>Nguồn vị trí</dt>
            <dd>{SOURCE_LABEL[coordinate.coordinateSource] || "Chưa xác định nguồn"}</dd>
          </div>
          <div>
            <dt>Độ chính xác</dt>
            <dd>
              {ACCURACY_LABEL[coordinate.accuracyLevel] || "Chưa xác định"}
              {coordinate.accuracyMeters != null
                ? ` (±${coordinate.accuracyMeters} m)`
                : ""}
            </dd>
          </div>
          <div>
            <dt>Xác minh</dt>
            <dd>
              {VERIFICATION_LABEL[coordinate.verificationStatus] || "Chưa xác minh"}
              {coordinate.verificationMethod
                ? ` — ${METHOD_LABEL[coordinate.verificationMethod] || coordinate.verificationMethod}`
                : ""}
            </dd>
          </div>
        </dl>
      )}

      {coordinate.referenceMapEligible && !coordinate.parcelAnalysisEligible && (
        <p className="coordinate-status__note">
          Vị trí được cung cấp khi đăng tin, chưa được xác minh chính xác đến
          từng thửa đất.
        </p>
      )}
    </section>
  );
}
