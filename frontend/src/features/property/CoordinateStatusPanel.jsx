import React from "react";
import "./CoordinateStatusPanel.css";
import { coordinateHeadline, coordinateSourceLabel, coordinateTone } from "./coordinateStatus.js";

/**
 * Coordinate Provenance V1 — hiển thị trạng thái vị trí của tin đăng.
 *
 * Nguyên tắc: KHÔNG hiển thị badge "chính xác" chỉ vì backend trả
 * geographicValidationStatus = VERIFIED_EXACT. Trạng thái đó chỉ có nghĩa
 * "điểm nằm trong polygon quận", không phải cấp thửa.
 *
 * Ba cờ eligibility do backend tính sẵn — component không tự suy luận.
 */

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

export { coordinateHeadline, coordinateTone } from "./coordinateStatus.js";

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
            <dd>{coordinateSourceLabel(coordinate.coordinateSource)}</dd>
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

      {coordinate.referenceMapEligible === true && coordinate.parcelAnalysisEligible !== true && (
        <p className="coordinate-status__note">
          Bản đồ chỉ dùng làm vị trí tham khảo; thông tin này không xác nhận ranh giới
          hoặc danh tính thửa đất.
        </p>
      )}
    </section>
  );
}
