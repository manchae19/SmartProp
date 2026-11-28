import React, { useId } from 'react'
import {
  comparableWarnings,
  hasResearchComparableMetadata,
  priceDelta,
  safeListingLink,
  similarityPercent,
  sourceKindLabel,
} from './comparables.js'
import './ComparableListingsCard.css'

const TYPE_LABELS = { HOUSE: 'Nhà phố', APARTMENT: 'Căn hộ', LAND: 'Đất nền', VILLA: 'Biệt thự' }
const STAGE_LABELS = { WARD: 'cùng phường', DISTRICT: 'cùng quận', ADJACENT: 'quận lân cận', NONE: 'không có kết quả' }
const BREAKDOWN_LABELS = {
  location: 'Vị trí',
  area: 'Diện tích',
  bedrooms: 'Phòng ngủ',
  floors: 'Số tầng',
  frontage: 'Mặt tiền',
  roadWidth: 'Bề rộng đường',
  project: 'Dự án',
  price: 'Giá',
  type: 'Loại hình',
}
const KIND_CLASS = {
  SMARTPROP: 'cmp-badge smartprop',
  EXTERNAL_LISTING: 'cmp-badge external',
  TINIX_RESEARCH: 'cmp-badge research',
}

function formatArea(value) {
  if (value == null) return '—'
  const n = Number(value)
  return Number.isFinite(n) ? `${n.toLocaleString('vi-VN', { maximumFractionDigits: 1 })} m²` : '—'
}

/** VND → compact "x,y tỷ" / "x triệu". */
function formatPrice(value) {
  const n = Number(value)
  if (!Number.isFinite(n) || n <= 0) return '—'
  if (n >= 1e9) return `${(n / 1e9).toLocaleString('vi-VN', { maximumFractionDigits: 2 })} tỷ`
  return `${(n / 1e6).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} triệu`
}

/**
 * Renders the comparable search result. It never fabricates rows: it shows the
 * API payload or a labelled empty/forbidden/error state.
 */
export default function ComparableListingsCard({ loading, error, forbidden, result, referencePrice, onRetry,
  title = 'Tin đăng tương đồng', allowResearch = false }) {
  const heading = useId()
  const visible = loading || error || forbidden ? null : result
  const items = (visible?.comparables ?? []).filter(item => allowResearch
    || (item.sourceKind !== 'TINIX_RESEARCH' && !item.researchReference && item.datasetLicense !== 'CC BY-NC 4.0'))
  const warnings = [...new Set([...comparableWarnings(visible), ...(visible?.evidence?.limitations ?? [])])]
    .filter(warning => allowResearch || !/TiniX|TINIX_RESEARCH|tinix:|CC BY-NC/i.test(warning))
  const refPrice = referencePrice ?? Number(visible?.reference?.priceVnd)
  const evidence = allowResearch || !hasResearchComparableMetadata(visible?.evidence) ? visible?.evidence : null
  const stage = STAGE_LABELS[visible?.searchStage] ?? ''
  const stats = evidence?.scannedCohortAskingPrice
  const exact = value => Number(value).toLocaleString('vi-VN')

  return (
    <section className="cmp-card" aria-labelledby={heading} data-comparable-card aria-busy={Boolean(loading)}>
      <div className="cmp-head">
        <h4 id={heading}>{title}</h4>
        {visible && items.length > 0 ? <span className="cmp-count">{items.length} tin hiển thị · {stage}</span> : null}
      </div>

      {loading ? (
        <p role="status" className="cmp-muted">Đang tìm bất động sản tương đồng…</p>
      ) : null}

      {!loading && forbidden ? (
        <div role="alert" className="cmp-alert warn" data-comparable-forbidden>
          <p>Tính năng tìm tin tương đồng chỉ dành cho <strong>môi giới</strong> và <strong>quản trị viên</strong>. Vui lòng đăng nhập bằng tài khoản BROKER/ADMIN.</p>
          <button type="button" className="cmp-link" onClick={() => { window.location.assign('/login?reason=login-required') }}>Đăng nhập</button>
        </div>
      ) : null}

      {!loading && !forbidden && error ? (
        <div role="alert" className="cmp-alert error" data-comparable-error>
          <p>{error}</p>
          {onRetry ? <button type="button" className="cmp-link" onClick={onRetry}>Thử lại</button> : null}
        </div>
      ) : null}

      {evidence?.status === 'INSUFFICIENT_EVIDENCE' ? (
        <p role="status" className="cmp-muted" data-comparable-insufficient>Chưa đủ bằng chứng để hiển thị trung vị giá rao.</p>
      ) : null}
      {visible && items.length === 0 ? (
        <div className="cmp-empty" data-comparable-empty>
          {evidence?.scanComplete === false ? 'Chưa tìm thấy tin phù hợp trong phần dữ liệu đã quét.' : 'Chưa có tin tương đồng theo tiêu chí này.'}
        </div>
      ) : null}

      {evidence ? (
        <div className="cmp-cohort" data-comparable-cohort>
          <p>{evidence.retrievedCandidateCount} tin đã đọc · {evidence.uniqueEligibleCandidateCount} tin hợp lệ sau lọc trùng · {items.length} tin hiển thị</p>
          {evidence.status === 'AVAILABLE' && evidence.scanComplete && stats?.observations >= 5
            && stats.medianPriceVnd != null && stats.medianPricePerSqmVnd != null ? (
            <dl className="cmp-breakdown" aria-label="Thống kê tập tin đã quét">
              <div><dt>Trung vị giá rao trên {stats.observations} tin</dt><dd>{exact(stats.medianPriceVnd)} ₫</dd></div>
              <div><dt>Trung vị giá rao mỗi m²</dt><dd>{exact(stats.medianPricePerSqmVnd)} ₫/m²</dd></div>
            </dl>
          ) : null}
          {Object.entries(evidence.provenance ?? {}).filter(([source]) => allowResearch || source !== 'TINIX_RESEARCH')
            .map(([source, counts]) => counts.uniqueEligible > 0 ? (
              <p key={source}>{sourceKindLabel(source)} · {counts.uniqueEligible} tin trong tập đã quét{counts.attribution ? ` · ${counts.attribution}` : ''}</p>
            ) : null)}
        </div>
      ) : null}

      {!loading && items.length > 0 ? (
        <ul className="cmp-list">
          {items.map((item) => (
            <li key={item.candidateId} className="cmp-item" data-comparable-item data-comparable-source={item.sourceKind}>
              <div className="cmp-item-top">
                <span className={KIND_CLASS[item.sourceKind] ?? 'cmp-badge'}>{sourceKindLabel(item.sourceKind)}</span>
                <span className="cmp-sim">Điểm tương đồng {similarityPercent(item.similarityScore)}/100</span>
              </div>
              <p className="cmp-item-title">
                {TYPE_LABELS[item.propertyType] ?? item.propertyType} · {item.district}{item.ward ? `, ${item.ward}` : ''}
              </p>
              <p className="cmp-item-line">
                {formatArea(item.areaSqm)}{item.bedrooms ? ` · ${item.bedrooms} phòng ngủ` : ''}
              </p>
              {item.featureCoverage != null ? <p className="cmp-item-line">Độ phủ thuộc tính {similarityPercent(item.featureCoverage)}%</p> : null}
              <p className="cmp-item-price">
                {item.askingPriceVnd ? formatPrice(item.askingPriceVnd) : 'Chưa có giá rao'}
              </p>
              {item.askingPriceVnd && refPrice ? <p className="cmp-item-delta">{priceDelta(item)}</p> : null}

              {item.scoreBreakdown ? (
                <dl className="cmp-breakdown">
                  {Object.entries(item.scoreBreakdown).map(([key, reason]) => (
                    <div key={key}>
                      <dt>{BREAKDOWN_LABELS[key] ?? key}</dt>
                      <dd>{reason}</dd>
                    </div>
                  ))}
                </dl>
              ) : null}

              {safeListingLink(item) ? (
                <a className="cmp-source-link" href={safeListingLink(item)} target="_blank" rel="noopener noreferrer nofollow">
                  Xem tin gốc
                </a>
              ) : null}
              {item.sourceKind === 'TINIX_RESEARCH' && item.attribution ? (
                <p className="cmp-attribution">{item.attribution}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {warnings.length ? (
        <ul className="cmp-warnings">
          {warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      ) : null}

      {!evidence && visible?.eligibleCountsBySource ? (
        <p className="cmp-eligible">
          Nguồn dữ liệu hợp lệ: SmartProp {visible.eligibleCountsBySource.SMARTPROP ?? 0},
          {' '}tin ngoài {visible.eligibleCountsBySource.EXTERNAL_LISTING ?? 0}
          {allowResearch && visible.eligibleCountsBySource.TINIX_RESEARCH != null
            ? `, TiniX nghiên cứu ${visible.eligibleCountsBySource.TINIX_RESEARCH}`
            : ''}.
        </p>
      ) : null}
    </section>
  )
}
