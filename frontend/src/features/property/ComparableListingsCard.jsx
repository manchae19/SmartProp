import React from 'react'
import {
  comparableWarnings,
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
  price: 'Giá',
  type: 'Loại hình',
}
const KIND_CLASS = {
  SMARTPROP: 'cmp-badge smartprop',
  EXTERNAL_LISTING: 'cmp-badge external',
  TINIX_RESEARCH: 'cmp-badge research',
}

function formatArea(value) {
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
export default function ComparableListingsCard({ loading, error, forbidden, result, referencePrice, onRetry }) {
  const items = result?.comparables ?? []
  const warnings = comparableWarnings(result)
  const refPrice = referencePrice ?? Number(result?.reference?.priceVnd) ?? null
  const stage = STAGE_LABELS[result?.searchStage] ?? ''

  return (
    <section className="cmp-card" aria-labelledby="comparable-heading" data-comparable-card>
      <div className="cmp-head">
        <h4 id="comparable-heading">Tin đăng tương đồng</h4>
        {result ? <span className="cmp-count">{items.length}/5 · {stage}</span> : null}
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
          <button type="button" className="cmp-link" onClick={onRetry}>Thử lại</button>
        </div>
      ) : null}

      {!loading && !forbidden && !error && result && items.length === 0 ? (
        <div className="cmp-empty" data-comparable-empty>
          Chưa tìm thấy tin tương đồng trong dữ liệu hiện có. Hãy thử địa bàn khác hoặc điều chỉnh diện tích.
        </div>
      ) : null}

      {!loading && items.length > 0 ? (
        <ul className="cmp-list">
          {items.map((item) => (
            <li key={item.candidateId} className="cmp-item" data-comparable-item>
              <div className="cmp-item-top">
                <span className={KIND_CLASS[item.sourceKind] ?? 'cmp-badge'}>{sourceKindLabel(item.sourceKind)}</span>
                <span className="cmp-sim">Tương đồng {similarityPercent(item.similarityScore)}%</span>
              </div>
              <p className="cmp-item-title">
                {TYPE_LABELS[item.propertyType] ?? item.propertyType} · {item.district}{item.ward ? `, ${item.ward}` : ''}
              </p>
              <p className="cmp-item-line">
                {formatArea(item.areaSqm)}{item.bedrooms ? ` · ${item.bedrooms} phòng ngủ` : ''}
              </p>
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

      {result?.eligibleCountsBySource ? (
        <p className="cmp-eligible">
          Nguồn dữ liệu hợp lệ: SmartProp {result.eligibleCountsBySource.SMARTPROP ?? 0},
          {' '}tin ngoài {result.eligibleCountsBySource.EXTERNAL_LISTING ?? 0},
          {' '}TiniX nghiên cứu {result.eligibleCountsBySource.TINIX_RESEARCH ?? 0}.
        </p>
      ) : null}
    </section>
  )
}
