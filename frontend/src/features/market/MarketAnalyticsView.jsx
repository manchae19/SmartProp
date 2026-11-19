import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { SiteLink as RouterLink } from '../../app/navigation.jsx'
import { errorText } from '../auth/api.js'
import {
  ANALYSIS_SOURCES,
  PROPERTY_TYPES,
  bandWidth,
  formatBillion,
  formatCount,
  formatPerSqm,
  loadMarketAnalytics,
} from './marketAnalytics.js'
import './MarketAnalyticsView.css'

// Static Da Nang districts; the API's own district keys are merged in when available.
const BASE_DISTRICTS = ['Hải Châu', 'Thanh Khê', 'Sơn Trà', 'Ngũ Hành Sơn', 'Cẩm Lệ', 'Liên Chiểu', 'Hòa Vang']

const EMPTY_FILTERS = { district: '', propertyType: '', source: 'ALL', includeResearch: false }

/**
 * Real-data Market Analytics page. Every number comes from the live
 * /properties/market-analytics API (asked-for, median-based, no forecasting);
 * nothing here is mock or hardcoded market data.
 */
export default function MarketAnalyticsView() {
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const sequence = useRef(0)

  const load = useCallback(async (next = filters) => {
    const run = ++sequence.current
    setBusy(true)
    setError('')
    try {
      const result = await loadMarketAnalytics(next)
      if (run === sequence.current) setData(result)
    } catch (failure) {
      if (run === sequence.current) {
        const text = failure?.status ? errorText(failure) : failure?.message
        setError(text || 'Chưa tải được dữ liệu thị trường. Vui lòng thử lại.')
        setData(null)
      }
    } finally {
      if (run === sequence.current) setBusy(false)
    }
  }, [filters])

  useEffect(() => {
    load(filters)
  }, [filters, load])

  const patch = (key, value) => setFilters((current) => ({ ...current, [key]: value }))

  const districtOptions = useMemo(() => {
    const fromData = (data?.byDistrict || []).map((d) => d.key)
    return [...new Set([...BASE_DISTRICTS, ...fromData])]
  }, [data])

  const monthly = data?.monthly || []
  const warnings = data?.meta?.dataQualityWarnings || []
  const researchIncluded = data?.meta?.researchIncluded === true
  const temporalAvailable = data?.meta?.temporalStatus === 'AVAILABLE'

  return (
    <section id="market-analytics" className="ma-section" data-market-analytics aria-busy={busy}>
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
              <select value={filters.district} onChange={(e) => patch('district', e.target.value)}>
                <option value="">Tất cả</option>
                {districtOptions.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </label>
            <label>
              Loại BĐS
              <select value={filters.propertyType} onChange={(e) => patch('propertyType', e.target.value)}>
                {Object.entries(PROPERTY_TYPES).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </label>
            <label>
              Nguồn
              <select value={filters.source} onChange={(e) => patch('source', e.target.value)}>
                {Object.entries(ANALYSIS_SOURCES).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </label>
            <label className="ma-check">
              <input
                type="checkbox"
                checked={filters.includeResearch}
                onChange={(e) => patch('includeResearch', e.target.checked)}
              />
              <span>Bao gồm dữ liệu nghiên cứu TiniX (CC BY-NC 4.0)</span>
            </label>
          </div>
        </div>

        {busy ? (
          <p role="status" className="ma-status" data-ma-loading>Đang tổng hợp dữ liệu thị trường…</p>
        ) : error ? (
          <p role="alert" className="ma-error" data-ma-error>
            {error}
            <button type="button" onClick={() => load(filters)}>Thử lại</button>
          </p>
        ) : null}

        {data && !error ? (
          <>
            <div className="ma-cards">
              <div className="ma-card">
                <p className="ma-card-label">Tổng mẫu (tin rao)</p>
                <strong className="ma-card-value" data-ma-sample>{formatCount(data.overall.count)}</strong>
                <p className="ma-card-note">Ngưỡng tối thiểu/ô: {data.meta.minSample} · ô dưới ngưỡng bị ẩn số liệu</p>
              </div>
              <div className="ma-card">
                <p className="ma-card-label">Trung vị giá rao</p>
                <strong className="ma-card-value" data-ma-median-price>{formatBillion(data.overall.medianAskingPriceVnd) || '—'}</strong>
                <p className="ma-card-note" data-ma-status>{data.overall.dataStatus}</p>
              </div>
              <div className="ma-card">
                <p className="ma-card-label">Trung vị giá rao / m²</p>
                <strong className="ma-card-value" data-ma-median-ppm2>{formatPerSqm(data.overall.medianPricePerSqm) || '—'}</strong>
                {data.overall.p25AskingPriceVnd ? (
                  <p className="ma-card-note">
                    P25 {formatBillion(data.overall.p25AskingPriceVnd)} · P75 {formatBillion(data.overall.p75AskingPriceVnd)}
                  </p>
                ) : null}
              </div>
              <div className="ma-card">
                <p className="ma-card-label">Cơ sở</p>
                <strong className="ma-card-value small">{data.meta.priceBasis}</strong>
                <p className="ma-card-note">{researchIncluded ? 'Gồm nghiên cứu TiniX' : 'Chỉ nguồn công khai'}</p>
              </div>
            </div>

            <div className="ma-grid">
              <div className="ma-panel">
                <h4>Giá rao trung vị theo quận/huyện</h4>
                {data.byDistrict.length === 0 ? (
                  <p className="ma-muted">Không có ô nào đủ mẫu.</p>
                ) : (
                  <ul className="ma-bars">
                    {data.byDistrict.map((d) => (
                      <li key={d.key} data-ma-district>
                        <span className="ma-bar-label">{d.key} <em>({formatCount(d.count)})</em></span>
                        <span className="ma-bar-track"><span className="ma-bar-fill" style={{ width: bandWidth(d.count, data.byDistrict) + '%' }} /></span>
                        <span className="ma-bar-value">{formatPerSqm(d.medianPricePerSqm) || 'INSUFFICIENT_DATA'}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="ma-panel">
                <h4>Phân bố loại hình (số tin)</h4>
                <ul className="ma-bars">
                  {data.byPropertyType.map((t) => (
                    <li key={t.key} data-ma-type>
                      <span className="ma-bar-label">{t.label}</span>
                      <span className="ma-bar-track"><span className="ma-bar-fill alt" style={{ width: bandWidth(t.count, data.byPropertyType) + '%' }} /></span>
                      <span className="ma-bar-value">{formatCount(t.count)}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="ma-panel">
                <h4>Phân bố khoảng giá rao</h4>
                <ul className="ma-bars">
                  {data.priceBands.map((b) => (
                    <li key={b.label} data-ma-priceband>
                      <span className="ma-bar-label">{b.label}</span>
                      <span className="ma-bar-track"><span className="ma-bar-fill" style={{ width: bandWidth(b.count, data.priceBands) + '%' }} /></span>
                      <span className="ma-bar-value">{formatCount(b.count)}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="ma-panel">
                <h4>Phân bố diện tích</h4>
                <ul className="ma-bars">
                  {data.areaBands.map((b) => (
                    <li key={b.label} data-ma-areaband>
                      <span className="ma-bar-label">{b.label}</span>
                      <span className="ma-bar-track"><span className="ma-bar-fill alt" style={{ width: bandWidth(b.count, data.areaBands) + '%' }} /></span>
                      <span className="ma-bar-value">{formatCount(b.count)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="ma-panel ma-wide">
              <h4>Chuỗi theo tháng — dữ liệu nghiên cứu TiniX (CC BY-NC 4.0)</h4>
              {!researchIncluded ? (
                <p className="ma-muted" data-ma-temporal>Chưa bật dữ liệu nghiên cứu nên không có chuỗi thời gian.</p>
              ) : !temporalAvailable ? (
                <p className="ma-insufficient" data-ma-temporal>
                  <strong>INSUFFICIENT_DATA.</strong> Dữ liệu thời gian chưa đủ điều kiện để mô tả xu hướng; hệ thống không tự tạo xu hướng.
                </p>
              ) : (
                <div className="ma-months" data-ma-monthly>
                  {monthly.map((p) => (
                    <div key={p.period} className="ma-month" data-ma-month-status={p.dataStatus}>
                      <span className="ma-month-period">{p.period}</span>
                      <strong>{formatPerSqm(p.medianPricePerSqm) || 'INSUFFICIENT_DATA'}</strong>
                      <span className="ma-month-count">{formatCount(p.count)} tin</span>
                    </div>
                  ))}
                </div>
              )}
              <p className="ma-muted small">
                Chuỗi này mô tả <strong>giá rao ghi nhận trong một lần trích xuất</strong>; biến động theo tháng có thể là thay đổi thành phần nguồn/duplicate, không phải mức tăng giá thị trường.
              </p>
            </div>

            <div className="ma-panel ma-wide">
              <h4>Nguồn dữ liệu &amp; số mẫu</h4>
              <ul className="ma-sources">
                {data.bySource.map((s) => (
                  <li key={s.source} data-ma-source={s.source}>
                    <span className="ma-source-name">{s.label}</span>
                    {s.researchReference ? <span className="ma-tag">NC · {s.license}</span> : null}
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
            <p className="ma-disclaimer" data-ma-disclaimer>{data.meta.disclaimer}</p>

            <p className="ma-links">
              <RouterLink to="/advisor/analysis">Mở Unified AI Advisor →</RouterLink>
              <RouterLink to="/advisor/chat">Trò chuyện với trợ lý AI →</RouterLink>
            </p>
          </>
        ) : null}
      </div>
    </section>
  )
}
