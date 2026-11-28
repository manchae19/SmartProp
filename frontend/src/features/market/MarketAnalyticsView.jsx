import React, { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { SiteLink as RouterLink } from '../../app/navigation.jsx'
import { api, errorText, session } from '../auth/api.js'
import {
  ANALYSIS_SOURCES,
  PROPERTY_TYPES,
  PUBLIC_ANALYSIS_SOURCES,
  bandWidth,
  formatBillion,
  formatCount,
  formatPerSqm,
} from './marketAnalytics.js'
import { createMarketAnalyticsController } from './marketAnalyticsState.js'
import './MarketAnalyticsView.css'
import { marketAnalyticsLabel } from './marketAnalyticsLabels.js'

// Static Da Nang districts; the API's own district keys are merged in when available.
const BASE_DISTRICTS = ['Hải Châu', 'Thanh Khê', 'Sơn Trà', 'Ngũ Hành Sơn', 'Cẩm Lệ', 'Liên Chiểu', 'Hòa Vang']

/**
 * Real-data Market Analytics page. Every number comes from the live
 * /properties/market-analytics API (asked-for, median-based, no forecasting);
 * nothing here is mock or hardcoded market data.
 *
 * An active ADMIN can explicitly opt in. TiniX results and filters appear
 * only after the server has authorized a research request.
 */
export default function MarketAnalyticsView() {
  const [controller] = useState(() => createMarketAnalyticsController({ api, session, errorText }))
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot)
  const { filters, data, busy, error, researchAvailable, researchError, canRequestResearch } = state

  useEffect(() => controller.mount(), [controller])

  const canViewResearch = canRequestResearch && researchAvailable
  const visibleData = data && (!data.meta?.researchIncluded || canViewResearch) ? data : null
  const sourceChoices = canViewResearch ? ANALYSIS_SOURCES : PUBLIC_ANALYSIS_SOURCES

  const districtOptions = useMemo(() => {
    const fromData = (visibleData?.byDistrict || []).map((d) => d.key)
    return [...new Set([...BASE_DISTRICTS, ...fromData])]
  }, [visibleData])

  const monthly = canViewResearch ? (visibleData?.monthly || []) : []
  const warnings = (visibleData?.meta?.dataQualityWarnings || []).filter(
    (w) => canViewResearch || (!String(w).includes('TINIX') && !String(w).includes('CC BY-NC'))
  )
  const researchIncluded = canViewResearch && visibleData?.meta?.researchIncluded === true
  const temporalAvailable = researchIncluded && visibleData?.meta?.temporalStatus === 'AVAILABLE'

  return (
    <section
      id="market-analytics"
      data-ui-view="MarketAnalyticsView"
      className="ma-section"
      data-market-analytics
      aria-busy={busy}
    >
      <div className="ma-container">
        <div className="ma-head">
          <div>
            <p className="ma-eyebrow">MARKET ANALYTICS · DỮ LIỆU THẬT</p>
            <h1 className="ma-title">Thống kê giá rao theo dữ liệu thực</h1>
            <p className="ma-sub">
              Giá rao bán tổng hợp từ MySQL theo nguồn · dùng <strong>trung vị</strong> để giảm ảnh hưởng của outlier.{' '}
              <strong>Không phải giá giao dịch</strong> và <strong>không phải dự báo</strong>.
            </p>
          </div>
          <div className="ma-filters">
            <label>
              Quận/Huyện
              <select value={filters.district} onChange={(e) => controller.patchFilter('district', e.target.value)}>
                <option value="">Tất cả</option>
                {districtOptions.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </label>
            <label>
              Loại BĐS
              <select value={filters.propertyType} onChange={(e) => controller.patchFilter('propertyType', e.target.value)}>
                {Object.entries(PROPERTY_TYPES).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              Nguồn
              <select
                value={canViewResearch ? filters.source : (filters.source === 'TINIX_RESEARCH' ? 'ALL' : filters.source)}
                onChange={(e) => controller.patchFilter('source', e.target.value)}
              >
                {Object.entries(sourceChoices).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </label>
            {canRequestResearch ? (
              <label className="ma-check" data-ma-research-toggle>
                <input
                  type="checkbox"
                  checked={filters.includeResearch === true}
                  onChange={(e) => controller.setResearchEnabled(e.target.checked)}
                />
                <span>Yêu cầu dữ liệu nghiên cứu</span>
              </label>
            ) : null}
          </div>
        </div>

        {researchError ? <p role="status" className="ma-status" data-ma-research-error>{researchError}</p> : null}
        {busy ? (
          <p role="status" className="ma-status" data-ma-loading>Đang tổng hợp dữ liệu thị trường…</p>
        ) : error ? (
          <p role="alert" className="ma-error" data-ma-error>
            {error}
            <button type="button" onClick={controller.retry}>Thử lại</button>
          </p>
        ) : null}

        {visibleData && !error ? (
          <>
            <div className="ma-cards">
              <div className="ma-card">
                <p className="ma-card-label">Tổng mẫu (tin rao)</p>
                <strong className="ma-card-value" data-ma-sample>{formatCount(visibleData.overall.count)}</strong>
                <p className="ma-card-note">Ngưỡng tối thiểu/ô: {visibleData.meta.minSample} · ô dưới ngưỡng bị ẩn số liệu</p>
              </div>
              <div className="ma-card">
                <p className="ma-card-label">Trung vị giá rao</p>
                <strong className="ma-card-value" data-ma-median-price>{formatBillion(visibleData.overall.medianAskingPriceVnd) || '—'}</strong>
                <p className="ma-card-note" data-ma-status>{marketAnalyticsLabel(visibleData.overall.dataStatus)}</p>
              </div>
              <div className="ma-card">
                <p className="ma-card-label">Trung vị giá rao / m²</p>
                <strong className="ma-card-value" data-ma-median-ppm2>{formatPerSqm(visibleData.overall.medianPricePerSqm) || '—'}</strong>
                {visibleData.overall.p25AskingPriceVnd ? (
                  <p className="ma-card-note">
                    P25 {formatBillion(visibleData.overall.p25AskingPriceVnd)} · P75 {formatBillion(visibleData.overall.p75AskingPriceVnd)}
                  </p>
                ) : null}
              </div>
              <div className="ma-card">
                <p className="ma-card-label">Cơ sở</p>
                <strong className="ma-card-value small">{marketAnalyticsLabel(visibleData.meta.priceBasis)}</strong>
                <p className="ma-card-note">{researchIncluded ? 'Gồm nghiên cứu nội bộ (ADMIN)' : 'Chỉ nguồn công khai hợp lệ'}</p>
              </div>
            </div>

            <div className="ma-grid">
              <div className="ma-panel">
                <h4>Giá rao trung vị theo quận/huyện</h4>
                {visibleData.byDistrict.length === 0 ? (
                  <p className="ma-muted">Không có ô nào đủ mẫu.</p>
                ) : (
                  <ul className="ma-bars">
                    {visibleData.byDistrict.map((d) => (
                      <li key={d.key} data-ma-district>
                        <span className="ma-bar-label">{d.key} <em>({formatCount(d.count)})</em></span>
                        <span className="ma-bar-track"><span className="ma-bar-fill" style={{ width: bandWidth(d.count, visibleData.byDistrict) + '%' }} /></span>
                        <span className="ma-bar-value">{formatPerSqm(d.medianPricePerSqm) || marketAnalyticsLabel('INSUFFICIENT_DATA')}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="ma-panel">
                <h4>Phân bố loại hình (số tin)</h4>
                <ul className="ma-bars">
                  {visibleData.byPropertyType.map((t) => (
                    <li key={t.key} data-ma-type>
                      <span className="ma-bar-label">{marketAnalyticsLabel(t.label)}</span>
                      <span className="ma-bar-track"><span className="ma-bar-fill alt" style={{ width: bandWidth(t.count, visibleData.byPropertyType) + '%' }} /></span>
                      <span className="ma-bar-value">{formatCount(t.count)}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="ma-panel">
                <h4>Phân bố khoảng giá rao</h4>
                <ul className="ma-bars">
                  {visibleData.priceBands.map((b) => (
                    <li key={b.label} data-ma-priceband>
                      <span className="ma-bar-label">{b.label}</span>
                      <span className="ma-bar-track"><span className="ma-bar-fill" style={{ width: bandWidth(b.count, visibleData.priceBands) + '%' }} /></span>
                      <span className="ma-bar-value">{formatCount(b.count)}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="ma-panel">
                <h4>Phân bố diện tích</h4>
                <ul className="ma-bars">
                  {visibleData.areaBands.map((b) => (
                    <li key={b.label} data-ma-areaband>
                      <span className="ma-bar-label">{b.label}</span>
                      <span className="ma-bar-track"><span className="ma-bar-fill alt" style={{ width: bandWidth(b.count, visibleData.areaBands) + '%' }} /></span>
                      <span className="ma-bar-value">{formatCount(b.count)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {canViewResearch ? (
              <div className="ma-panel ma-wide">
                <h4>Chuỗi theo tháng — dữ liệu nghiên cứu TiniX (CC BY-NC 4.0)</h4>
                {!researchIncluded ? (
                  <p className="ma-muted" data-ma-temporal>Chưa bật dữ liệu nghiên cứu nên không có chuỗi thời gian.</p>
                ) : !temporalAvailable ? (
                  <p className="ma-insufficient" data-ma-temporal>
                    <strong>{marketAnalyticsLabel('INSUFFICIENT_DATA')}.</strong> Dữ liệu thời gian chưa đủ điều kiện để mô tả xu hướng; hệ thống không tự tạo xu hướng.
                  </p>
                ) : (
                  <div className="ma-months" data-ma-monthly>
                    {monthly.map((p) => (
                      <div key={p.period} className="ma-month" data-ma-month-status={p.dataStatus}>
                        <span className="ma-month-period">{p.period}</span>
                        <strong>{formatPerSqm(p.medianPricePerSqm) || marketAnalyticsLabel('INSUFFICIENT_DATA')}</strong>
                        <span className="ma-month-count">{formatCount(p.count)} tin</span>
                      </div>
                    ))}
                  </div>
                )}
                <p className="ma-muted small">
                  Chuỗi này mô tả <strong>giá rao ghi nhận trong một lần trích xuất</strong>; biến động theo tháng có thể là thay đổi thành phần nguồn/duplicate, không phải mức tăng giá thị trường.
                </p>
              </div>
            ) : (
              <div className="ma-panel ma-wide">
                <h4>Chuỗi biến động theo thời gian</h4>
                <p className="ma-muted" data-ma-temporal>
                  Nguồn tin rao công khai hiện tại không cung cấp chuỗi lịch sử theo tháng đủ điều kiện kiểm định; hệ thống không tự tạo đường xu hướng hoặc dự báo giá.
                </p>
              </div>
            )}

            <div className="ma-panel ma-wide">
              <h4>Nguồn dữ liệu &amp; số mẫu</h4>
              <ul className="ma-sources">
                {visibleData.bySource
                  .filter((s) => canViewResearch || (s.source !== 'TINIX_RESEARCH' && !s.researchReference))
                  .map((s) => (
                    <li key={s.source} data-ma-source={s.source}>
                      <span className="ma-source-name">{s.label}</span>
                      {canViewResearch && s.researchReference ? <span className="ma-tag">NC · {s.license}</span> : null}
                      <span className="ma-source-count">{formatCount(s.count)}</span>
                    </li>
                  ))}
              </ul>
            </div>

            {warnings.length ? (
              <ul className="ma-warnings">
                {warnings.map((w) => (
                  <li key={w} data-ma-warning>{w}</li>
                ))}
              </ul>
            ) : null}
            <p className="ma-disclaimer" data-ma-disclaimer>{visibleData.meta.disclaimer}</p>

            <p className="ma-links">
              <RouterLink to="/market">Xem hồ sơ 7 quận/huyện Đà Nẵng →</RouterLink>
              <RouterLink to="/advisor/analysis">Mở Unified AI Advisor →</RouterLink>
              <RouterLink to="/advisor/chat">Trò chuyện với trợ lý AI →</RouterLink>
            </p>
          </>
        ) : null}
      </div>
    </section>
  )
}
