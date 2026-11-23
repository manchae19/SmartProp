import React, { useState } from 'react';
import { validateVerification, METHOD_LABEL, ACCURACY_LABEL } from './coordinateReview.js';
import './CoordinateVerificationForm.css';

/**
 * Form xác minh tọa độ — chỉ ADMIN.
 *
 * Nguyên tắc:
 * - `expectedRevision` do backend trả, không cho sửa. Gửi lại đúng revision admin đã xem.
 * - Xác minh bắt buộc phương pháp và tham chiếu bằng chứng.
 * - Không điền sẵn `PARCEL`, không tự đặt `accuracyMeters`.
 * - Không coi việc admin nhấn nút là bằng chứng độc lập.
 */
export default function CoordinateVerificationForm({ detail, busy, onSubmit }) {
  const [verificationStatus, setVerificationStatus] = useState('VERIFIED');
  const [verificationMethod, setVerificationMethod] = useState('');
  const [evidenceReference, setEvidenceReference] = useState('');
  const [accuracyLevel, setAccuracyLevel] = useState('UNKNOWN');
  const [accuracyMeters, setAccuracyMeters] = useState('');
  const [accuracyMethod, setAccuracyMethod] = useState('');
  const [errors, setErrors] = useState([]);

  if (!detail) return null;

  const alreadyDecided = ['VERIFIED', 'REJECTED'].includes(detail.verificationStatus);

  function submit(event) {
    event.preventDefault();
    const form = {
      expectedRevision: detail.revision,
      verificationStatus,
      verificationMethod: verificationMethod || null,
      evidenceReference: evidenceReference.trim() || null,
      accuracyLevel,
      accuracyMeters: accuracyMeters === '' ? null : Number(accuracyMeters),
      accuracyMethod: accuracyMethod.trim() || null,
    };
    const found = validateVerification(form);
    setErrors(found);
    if (found.length) return;
    onSubmit(form);
  }

  if (alreadyDecided) {
    return (
      <section className="verify-form verify-form--locked" aria-label="Trạng thái xác minh">
        <p>
          Revision <strong>{detail.revision}</strong> đã có quyết định cuối:
          {' '}<strong>{detail.verificationStatus}</strong>.
        </p>
        <p className="verify-form__hint">
          Muốn thay đổi quyết định cần luồng thu hồi riêng có lưu vết — chưa có trong V1.
        </p>
      </section>
    );
  }

  return (
    <form className="verify-form" onSubmit={submit} aria-label="Form xác minh tọa độ">
      <div className="verify-form__revision">
        <span>Revision đang xem</span>
        <strong>{detail.revision}</strong>
        <span className="verify-form__hint">
          Nếu người đăng sửa tọa độ trong lúc bạn xem, hệ thống sẽ từ chối và báo xung đột.
        </span>
      </div>

      <fieldset>
        <legend>Quyết định</legend>
        <label>
          <input
            type="radio"
            name="verificationStatus"
            value="VERIFIED"
            checked={verificationStatus === 'VERIFIED'}
            onChange={() => setVerificationStatus('VERIFIED')}
          />
          Xác minh
        </label>
        <label>
          <input
            type="radio"
            name="verificationStatus"
            value="REJECTED"
            checked={verificationStatus === 'REJECTED'}
            onChange={() => setVerificationStatus('REJECTED')}
          />
          Từ chối
        </label>
        <label>
          <input
            type="radio"
            name="verificationStatus"
            value="PENDING_REVIEW"
            checked={verificationStatus === 'PENDING_REVIEW'}
            onChange={() => setVerificationStatus('PENDING_REVIEW')}
          />
          Chờ bổ sung thông tin
        </label>
      </fieldset>

      <label className="verify-form__field">
        <span>Phương pháp xác minh</span>
        <select
          value={verificationMethod}
          onChange={event => setVerificationMethod(event.target.value)}
          required={verificationStatus === 'VERIFIED'}
        >
          <option value="">— Chọn phương pháp —</option>
          {Object.entries(METHOD_LABEL).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </label>

      <label className="verify-form__field">
        <span>Tham chiếu bằng chứng</span>
        <input
          type="text"
          value={evidenceReference}
          onChange={event => setEvidenceReference(event.target.value)}
          placeholder="Số hồ sơ, mã ảnh, biên bản khảo sát…"
          maxLength={500}
          required={verificationStatus === 'VERIFIED'}
        />
        <small>Không nhập thông tin cá nhân nhạy cảm.</small>
      </label>

      <label className="verify-form__field">
        <span>Mức độ chính xác</span>
        <select
          value={accuracyLevel}
          onChange={event => setAccuracyLevel(event.target.value)}
        >
          {Object.entries(ACCURACY_LABEL).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <small>
          Chỉ chọn cấp thửa khi có bằng chứng địa chính. Hệ thống không tự suy từ
          tọa độ nằm đúng quận.
        </small>
      </label>

      {accuracyLevel !== 'UNKNOWN' && (
        <label className="verify-form__field">
          <span>Sai số (mét)</span>
          <input
            type="number"
            min="0.1"
            step="0.1"
            value={accuracyMeters}
            onChange={event => setAccuracyMeters(event.target.value)}
            required={accuracyLevel === 'PARCEL'}
          />
        </label>
      )}

      {accuracyLevel !== 'UNKNOWN' && (
        <label className="verify-form__field">
          <span>Cách xác định sai số</span>
          <input
            type="text"
            value={accuracyMethod}
            onChange={event => setAccuracyMethod(event.target.value)}
            placeholder="Đối chiếu hồ sơ địa chính, GPS thực địa…"
            maxLength={40}
          />
        </label>
      )}

      {errors.length > 0 && (
        <ul className="verify-form__errors" role="alert">
          {errors.map(message => <li key={message}>{message}</li>)}
        </ul>
      )}

      <button type="submit" className="verify-form__submit" disabled={busy}>
        {busy ? 'Đang gửi…' : 'Ghi nhận quyết định'}
      </button>
    </form>
  );
}
