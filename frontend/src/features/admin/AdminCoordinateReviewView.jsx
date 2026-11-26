import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api, errorText } from '../auth/api.js';
import ResourceState from '../../shared/components/ResourceState.jsx';
import CoordinateReviewMap from './CoordinateReviewMap.jsx';
import CoordinateVerificationForm from './CoordinateVerificationForm.jsx';
import {
  SOURCE_LABEL, ACCURACY_LABEL, VERIFICATION_LABEL, METHOD_LABEL,
  GEOGRAPHIC_LABEL, verificationTone, isDistrictMismatch, reviewHeadline,
  accuracyText, timeText, pendingQueueParams, pendingPageRange,
} from './coordinateReview.js';
import './AdminCoordinateReviewView.css';

const STATUS_FILTERS = [
  { value: '', label: 'Chờ xử lý' },
  { value: 'UNVERIFIED', label: 'Chưa xác minh' },
  { value: 'PENDING_REVIEW', label: 'Đang chờ kiểm tra' },
  { value: 'VERIFIED', label: 'Đã xác minh' },
  { value: 'REJECTED', label: 'Bị từ chối' },
  { value: 'STALE', label: 'Cần xác minh lại' },
];

/**
 * Admin Coordinate Review — xem, kiểm tra và xác minh tọa độ bất động sản.
 *
 * Nguyên tắc chống race condition:
 * - Mỗi lần chọn tin, đọc lại detail để lấy `revision` hiện hành.
 * - Gửi `expectedRevision` khi xác minh.
 * - 409 → không hiển thị thành công, cảnh báo, cho tải lại. KHÔNG tự gửi lại.
 */
export default function AdminCoordinateReviewView() {
  const [stats, setStats] = useState(null);
  const [items, setItems] = useState([]);
  const [listBusy, setListBusy] = useState(false);
  const [listError, setListError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);

  const [detail, setDetail] = useState(null);
  const [selectedPropertyId, setSelectedPropertyId] = useState(null);
  const [detailBusy, setDetailBusy] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState('');

  const [pendingSubmissions, setPendingSubmissions] = useState(() => new Set());
  const [notice, setNotice] = useState('');
  const [conflicts, setConflicts] = useState(() => new Map());

  const listSeq = useRef(0);
  const detailSeq = useRef(0);
  const selectedPropertyRef = useRef(null);
  const pendingSubmissionsRef = useRef(new Set());
  const conflictsRef = useRef(new Map());
  const loadListRef = useRef(null);
  const loadStatsRef = useRef(null);
  const loadDetailRef = useRef(null);
  const pageRange = pendingPageRange(page, total);

  const loadStats = useCallback(async () => {
    try {
      setStats(await api('/admin/coordinates/stats'));
    } catch {
      setStats(null);
    }
  }, []);

  const loadList = useCallback(async () => {
    const run = ++listSeq.current;
    setListBusy(true);
    setListError('');
    try {
      const params = pendingQueueParams({ page, statusFilter, search });
      const result = await api(`/admin/coordinates/pending?${params}`);
      if (run === listSeq.current) {
        setItems(result?.items || []);
        setTotal(result?.total || 0);
      }
    } catch (e) {
      if (run === listSeq.current) setListError(errorText(e));
    } finally {
      if (run === listSeq.current) setListBusy(false);
    }
  }, [statusFilter, search, page]);
  loadListRef.current = loadList;
  loadStatsRef.current = loadStats;

  const loadDetail = useCallback(async propertyId => {
    const run = ++detailSeq.current;
    selectedPropertyRef.current = propertyId;
    setSelectedPropertyId(propertyId);
    setDetailBusy(true);
    setDetailError('');
    setHistoryError('');
    setNotice('');
    setDetail(null);
    setHistory([]);
    try {
      const [detailResult, historyResult] = await Promise.allSettled([
        api(`/admin/coordinates/${propertyId}`),
        api(`/properties/${propertyId}/coordinate/history`),
      ]);
      if (run !== detailSeq.current) return;
      if (detailResult.status === 'rejected') throw detailResult.reason;
      const loadedDetail = detailResult.value;
      setDetail(loadedDetail);
      if (historyResult.status === 'fulfilled') setHistory(historyResult.value || []);
      else setHistoryError(errorText(historyResult.reason));
    } catch (e) {
      if (run === detailSeq.current) {
        setDetail(null);
        setHistory([]);
        setHistoryError('');
        setDetailError(errorText(e));
      }
    } finally {
      if (run === detailSeq.current) setDetailBusy(false);
    }
  }, []);
  loadDetailRef.current = loadDetail;

  useEffect(() => {
    loadStats();
    loadList();
  }, [loadStats, loadList]);

  useEffect(() => {
    if (!listBusy && page > 0 && page * 50 >= total) {
      setPage(Math.max(0, Math.ceil(total / 50) - 1));
    }
  }, [listBusy, page, total]);

  async function submitVerification(form) {
    if (!detail || selectedPropertyRef.current !== detail.propertyId) return;
    const selectedPropertyId = detail.propertyId;
    const selectedRevision = Number(form.expectedRevision);
    const requestSequence = detailSeq.current;
    const key = `${selectedPropertyId}:${selectedRevision}`;
    if (selectedRevision !== detail.revision
      || conflictsRef.current.has(key)
      || pendingSubmissionsRef.current.has(key)) return;
    pendingSubmissionsRef.current.add(key);
    setPendingSubmissions(new Set(pendingSubmissionsRef.current));
    setNotice('');
    try {
      await api(`/properties/${selectedPropertyId}/coordinate/verify`, {
        method: 'POST',
        body: form,
      });
      if (selectedPropertyRef.current === selectedPropertyId
        && detailSeq.current === requestSequence) setNotice('Đã ghi nhận quyết định xác minh.');
      // The query may have changed while the POST was pending. Read the latest callback
      // so an old filter/page snapshot cannot become the newest list request.
      await Promise.all([
        loadListRef.current?.(),
        loadStatsRef.current?.(),
        selectedPropertyRef.current === selectedPropertyId && detailSeq.current === requestSequence
          ? loadDetailRef.current?.(selectedPropertyId)
          : Promise.resolve(),
      ]);
    } catch (e) {
      if (e.status === 409) {
        // Không tự gửi lại: revision đã đổi, admin phải xem dữ liệu mới trước.
        const next = new Map(conflictsRef.current);
        next.set(key, { propertyId: selectedPropertyId, revision: selectedRevision });
        conflictsRef.current = next;
        setConflicts(next);
        if (selectedPropertyRef.current === selectedPropertyId) {
          setNotice('');
          setDetailError('');
        }
      } else if (selectedPropertyRef.current === selectedPropertyId
        && detailSeq.current === requestSequence) {
        setDetailError(errorText(e));
      }
    } finally {
      const next = new Set(pendingSubmissionsRef.current);
      next.delete(key);
      pendingSubmissionsRef.current = next;
      setPendingSubmissions(next);
    }
  }

  return (
    <div className="coord-review">
      <header className="coord-review__header">
        <div>
          <h1>Xác minh tọa độ</h1>
          <p className="coord-review__subtitle">
            Kiểm tra vị trí tin đăng và ghi nhận bằng chứng xác minh.
          </p>
        </div>
        <button type="button" className="coord-review__refresh" onClick={() => {
          loadStats();
          loadList();
          if (selectedPropertyId) loadDetail(selectedPropertyId);
        }}>
          Làm mới
        </button>
      </header>

      {stats && (
        <section className="coord-review__stats" aria-label="Thống kê hàng đợi">
          <Stat label="Tổng audit hiện hành" value={stats.total} />
          <Stat label="Chưa xác minh" value={stats.unverified} tone="neutral" />
          <Stat label="Đang chờ kiểm tra" value={stats.pendingReview} tone="pending" />
          <Stat label="Đã xác minh" value={stats.verified} tone="verified" />
          <Stat label="Bị từ chối" value={stats.rejected} tone="danger" />
          <Stat label="Cần xác minh lại" value={stats.stale} tone="warning" />
          <Stat label="Sai địa bàn" value={stats.districtMismatch} tone="warning" />
        </section>
      )}

      <div className="coord-review__body">
        <section className="coord-review__list" aria-label="Danh sách tin cần xác minh">
          <div className="coord-review__filters">
            <label>
              <span>Trạng thái</span>
              <select value={statusFilter} onChange={e => { setPage(0); setStatusFilter(e.target.value); }}>
                {STATUS_FILTERS.map(option => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Tìm kiếm</span>
              <input
                type="search"
                value={search}
                onChange={e => { setPage(0); setSearch(e.target.value); }}
                placeholder="Mã tin, tiêu đề, địa chỉ"
              />
            </label>
          </div>

          <ResourceState state={{ error: listError, busy: listBusy, load: loadList }} />

          {!listBusy && !listError && items.length === 0 && (
            <p className="coord-review__empty" role="status">
              Không có tin nào cần xử lý với bộ lọc hiện tại.
            </p>
          )}

          <ul className="coord-review__items">
            {!listBusy && !listError && items.map(item => (
              <li key={item.propertyId}>
                <button
                  type="button"
                  className={
                    'coord-review__item'
                    + (detail?.propertyId === item.propertyId ? ' is-selected' : '')
                  }
                  onClick={() => loadDetail(item.propertyId)}
                  aria-current={detail?.propertyId === item.propertyId ? 'true' : undefined}
                >
                  <span className="coord-review__code">{item.listingCode}</span>
                  <span className="coord-review__title">{item.title || '—'}</span>
                  <span className="coord-review__address">{item.address || '—'}</span>
                  <span className="coord-review__meta">
                    <Badge tone={verificationTone(item.verificationStatus)}>
                      {VERIFICATION_LABEL[item.verificationStatus] || item.verificationStatus}
                    </Badge>
                    {isDistrictMismatch(item.geographicValidationStatus) && (
                      <Badge tone="warning">Sai địa bàn</Badge>
                    )}
                    <span className="coord-review__rev">rev {item.revision}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <nav className="coord-review__pagination" aria-label="Phân trang hàng đợi">
            <button type="button" disabled={listBusy || page === 0} onClick={() => setPage(value => value - 1)}>Trước</button>
            <span aria-live="polite">{pageRange.total === 0 ? '0 kết quả' : `${pageRange.start}-${pageRange.end} / ${pageRange.total}`}</span>
            <button type="button" disabled={listBusy || (page + 1) * 50 >= total} onClick={() => setPage(value => value + 1)}>Sau</button>
          </nav>
        </section>

        <section className="coord-review__detail" aria-label="Chi tiết tin đang chọn">
          {!detail && !detailBusy && !detailError && (
            <p className="coord-review__empty" role="status">
              Chọn một tin ở danh sách để xem chi tiết và xác minh.
            </p>
          )}

          <ResourceState state={{ error: detailError, busy: detailBusy }} />

          {notice && <p className="coord-review__notice" role="status">{notice}</p>}

          {[...conflicts.values()].some(value => value.propertyId === selectedPropertyId
            && (!detail || value.revision === detail.revision)) && (
            <div className="coord-review__conflict" role="alert">
              <p>
                Dữ liệu tọa độ đã thay đổi kể từ khi bạn mở tin này. Quyết định chưa được ghi.
                Tải lại chi tiết để xem revision mới trước khi xác minh.
              </p>
              <button type="button" onClick={() => loadDetail(selectedPropertyId)}>
                Tải lại dữ liệu mới
              </button>
            </div>
          )}

          {detail && (
            <>
              <div className="coord-review__detail-head">
                <h2>{detail.title || detail.listingCode}</h2>
                <p>{detail.address}</p>
                <p className="coord-review__muted">
                  {[detail.ward, detail.district, detail.city].filter(Boolean).join(', ')}
                  {' · '}{detail.propertyStatus}
                </p>
                <p className="coord-review__headline">{reviewHeadline(detail)}</p>
              </div>

              {isDistrictMismatch(detail.geographicValidationStatus) && (
                <p className="coord-review__warning" role="alert">
                  Tọa độ không khớp quận đã khai báo. Cần kiểm tra lại trước khi xác minh.
                  {detail.geographicValidationNote ? ` (${detail.geographicValidationNote})` : ''}
                </p>
              )}

              <CoordinateReviewMap
                latitude={detail.latitude}
                longitude={detail.longitude}
                address={detail.address}
                district={detail.district}
                ward={detail.ward}
                mismatch={isDistrictMismatch(detail.geographicValidationStatus)}
              />

              <div className="coord-review__panels">
                <Panel title="Hợp lệ địa giới">
                  <Row label="Kết quả" value={
                    GEOGRAPHIC_LABEL[detail.geographicValidationStatus]
                    || detail.geographicValidationStatus || '—'
                  } />
                  <Row label="Địa bàn khai báo" value={
                    [detail.ward, detail.district].filter(Boolean).join(', ') || '—'
                  } />
                  <Row label="Ghi chú" value={detail.geographicValidationNote || '—'} />
                  <Row label="Phiên bản validator" value={detail.validatorScopeVersion || '—'} />
                  <Row label="Thời điểm" value={timeText(detail.validatedAt)} />
                </Panel>

                <Panel title="Nguồn gốc tọa độ">
                  <Row label="Nguồn" value={SOURCE_LABEL[detail.coordinateSource] || '—'} />
                  <Row label="Tham chiếu" value={detail.sourceReference || '—'} />
                  <Row label="Ghi nhận lúc" value={timeText(detail.sourceRecordedAt)} />
                  <Row label="Revision" value={String(detail.revision)} />
                  <Row label="Tạo lúc" value={timeText(detail.createdAt)} />
                </Panel>

                <Panel title="Độ chính xác & xác minh">
                  <Row label="Mức chính xác" value={accuracyText(detail.accuracyLevel, detail.accuracyMeters)} />
                  <Row label="Cách xác định" value={detail.accuracyMethod || '—'} />
                  <Row label="Trạng thái" value={
                    VERIFICATION_LABEL[detail.verificationStatus] || detail.verificationStatus
                  } />
                  <Row label="Phương pháp" value={METHOD_LABEL[detail.verificationMethod] || '—'} />
                  <Row label="Xác minh lúc" value={timeText(detail.verifiedAt)} />
                  <Row label="Bằng chứng" value={detail.evidenceReference || '—'} />
                </Panel>
              </div>

              <CoordinateVerificationForm
                key={`${detail.propertyId}:${detail.revision}`}
                detail={detail}
                busy={pendingSubmissions.has(`${detail.propertyId}:${detail.revision}`)}
                locked={conflicts.has(`${detail.propertyId}:${detail.revision}`)}
                onSubmit={submitVerification}
              />

              <section className="coord-review__history" aria-label="Lịch sử tọa độ">
                <h3>Lịch sử thay đổi</h3>
                {historyError && <p role="alert" className="coord-review__error">{historyError}</p>}
                {!historyError && history.length === 0
                  ? <p className="coord-review__muted">Chưa có lịch sử.</p>
                  : !historyError && (
                    <ol>
                      {history.map(row => (
                        <li key={row.revision}>
                          <span className="coord-review__rev">rev {row.revision}</span>
                          <span>{VERIFICATION_LABEL[row.verificationStatus] || row.verificationStatus}</span>
                          <span className="coord-review__muted">
                            {SOURCE_LABEL[row.coordinateSource] || row.coordinateSource}
                            {' · '}{timeText(row.createdAt)}
                          </span>
                          {row.supersededAt && (
                            <span className="coord-review__muted">
                              Đã thay thế: {row.supersedeReason || '—'}
                            </span>
                          )}
                        </li>
                      ))}
                    </ol>
                  )}
              </section>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function Stat({ label, value, tone = 'neutral' }) {
  return (
    <div className={`coord-review__stat coord-review__stat--${tone}`}>
      <span className="coord-review__stat-value">{value ?? '—'}</span>
      <span className="coord-review__stat-label">{label}</span>
    </div>
  );
}

function Badge({ tone, children }) {
  return <span className={`coord-review__badge coord-review__badge--${tone}`}>{children}</span>;
}

function Panel({ title, children }) {
  return (
    <section className="coord-review__panel">
      <h3>{title}</h3>
      <dl>{children}</dl>
    </section>
  );
}

function Row({ label, value }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
}
