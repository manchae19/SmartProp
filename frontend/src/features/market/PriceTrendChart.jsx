import { classNames } from '../../shared/lib/ui.js'
import React, { useState } from 'react'
import { SiteLink } from '../../app/navigation.jsx'
import { bandWidth, formatBillion, formatCount, formatPerSqm, isInsufficient } from './marketAnalytics.js'
import { marketAnalyticsLabel } from './marketAnalyticsLabels.js'

const TABS = [
  { id: 'priceBands', label: 'Khoảng tổng giá rao' },
  { id: 'byPropertyType', label: 'Cơ cấu loại hình' },
  { id: 'areaBands', label: 'Khoảng diện tích' },
]

/**
 * Public-safe Market Price & Distribution Evidence card on `/market` & `/market/:district`.
 * Replaces the former hardcoded 12-quarter curve: in public mode (`includeResearch=false`)
 * SmartProp has no verified quarterly/monthly series, so it displays live asking-price
 * distributions from `/api/v1/properties/market-analytics?includeResearch=false` and
 * explicitly states when sample size is insufficient or temporal series is unavailable.
 */
export default React.forwardRef(function PriceTrendChart(props, ref) {
  const {
    districtName = 'Đà Nẵng',
    analytics = null,
    loading = false,
    error = '',
    onRetry,
    className,
    history: _deprecatedStaticHistory,
    ...rest
  } = props || {}

  const [activeTab, setActiveTab] = useState('priceBands')

  const overall = analytics?.overall || null
  const minSample = analytics?.meta?.minSample ?? 30
  const rows = activeTab === 'byPropertyType'
    ? (analytics?.byPropertyType || []).map((t) => ({ key: t.key, label: marketAnalyticsLabel(t.label), count: t.count, sub: formatPerSqm(t.medianPricePerSqm) }))
    : activeTab === 'areaBands'
      ? (analytics?.areaBands || []).map((b) => ({ key: b.label, label: b.label, count: b.count, sub: '' }))
      : (analytics?.priceBands || []).map((b) => ({ key: b.label, label: b.label, count: b.count, sub: '' }))

  const rootAttributes = Object.fromEntries(
    Object.entries(rest).filter(
      ([key]) =>
        !['children', 'ref', 'key'].includes(key)
        && (!key.startsWith('on')
          || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))
    )
  )

  return (
    <div
      ref={ref}
      {...rootAttributes}
      className={classNames([
        'market-price-chart rounded-3xl bg-brand-card p-6 sm:p-8 border border-[var(--ui-border)] shadow-2xs',
        className,
      ])}
    >
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-5 pb-6 border-b border-[var(--ui-border)]">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2">
            03 / PHÂN BỐ GIÁ RAO CÔNG KHAI · KHÔNG DỰ BÁO
          </p>
          <h3 className="text-xl sm:text-2xl font-semibold text-[var(--ui-accent)] tracking-tight">
            Cấu trúc mặt bằng giá rao hiện hành tại <span>{districtName}.</span>
          </h3>
          <p className="text-xs text-[var(--ui-accent)] mt-1.5 leading-relaxed">
            Tổng hợp trực tiếp từ nguồn công khai hợp lệ (<code>includeResearch=false</code>) · Cơ sở tính:{' '}
            <strong className="text-[var(--ui-accent)]">Trung vị giá rao bán (asking price)</strong>
          </p>
        </div>

        <div
          className="chart-time-selector inline-flex items-center gap-1 bg-[var(--ui-surface)] p-1.5 rounded-full border border-[var(--ui-border)] self-start lg:self-auto text-xs"
          role="group"
          aria-label="Chiều phân tích phân bố tin rao"
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              aria-pressed={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={classNames([
                'px-3.5 py-1.5 rounded-full font-semibold transition-all cursor-pointer',
                activeTab === tab.id
                  ? 'bg-[var(--ui-soft)] text-[var(--ui-ink)] shadow-xs'
                  : 'text-[var(--ui-accent)] hover:text-[var(--ui-accent)]',
              ])}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <p className="price-data-note">
        Nguồn tin rao công khai hiện chưa có chuỗi quan sát lịch sử theo quý/tháng đủ điều kiện kiểm định. SmartProp không vẽ đường xu hướng giả lập và không dự báo tỷ lệ tăng giá.
      </p>

      {loading ? (
        <p role="status" className="py-8 text-sm text-[var(--ui-accent)]">
          Đang tải thống kê phân bố giá rao tại {districtName}…
        </p>
      ) : error ? (
        <div role="alert" className="rounded-2xl border border-[var(--ui-error-border)] bg-[var(--ui-error-bg)] p-5 text-xs sm:text-sm text-[var(--ui-error-text)]">
          <p>{error}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 font-bold underline underline-offset-4 cursor-pointer"
            >
              Thử tải lại dữ liệu thống kê
            </button>
          ) : null}
        </div>
      ) : !analytics ? (
        <p className="py-6 text-xs sm:text-sm text-[var(--ui-muted)]">
          Chưa có dữ liệu thống kê cho khu vực này.
        </p>
      ) : overall.count === 0 ? (
        <div className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-surface)] p-6 text-xs sm:text-sm text-[var(--ui-accent)]" data-market-empty-sample>
          <p className="font-semibold">
            Chưa đủ mẫu tin rao công khai hợp lệ (<code>n = 0</code>, ngưỡng tối thiểu <code>{minSample}</code>) tại {districtName}.
          </p>
          <p className="mt-1.5 text-[var(--ui-muted)]">
            Hệ thống giữ nguyên trạng thái trống trung thực, không điền giá trung vị mặc định và không nội suy từ quận lân cận.
          </p>
        </div>
      ) : (
        <div className="space-y-4 mt-3">
          {isInsufficient(overall) ? (
            <div className="rounded-2xl border border-[var(--ui-warning-border)] bg-[var(--ui-warning-bg)] p-4 text-xs text-[var(--ui-warning-text)]" data-market-insufficient-sample>
              Chưa đủ mẫu tin rao công khai hợp lệ (<code>n = {formatCount(overall.count)}</code>, ngưỡng tối thiểu <code>{minSample}</code>) để công bố trung vị đơn giá toàn khu vực; dưới đây là số lượng tin theo nhóm phân bố.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-surface)] p-4">
                <span className="text-[var(--ui-muted)] block">Cỡ mẫu hợp lệ</span>
                <strong className="text-lg text-[var(--ui-accent)] mt-1 block">{formatCount(overall.count)} tin rao</strong>
              </div>
              <div className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-surface)] p-4">
                <span className="text-[var(--ui-muted)] block">Trung vị tổng giá rao</span>
                <strong className="text-lg text-[var(--ui-accent)] mt-1 block">{formatBillion(overall.medianAskingPriceVnd) || '—'}</strong>
              </div>
              <div className="rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-surface)] p-4">
                <span className="text-[var(--ui-muted)] block">Trung vị đơn giá / m²</span>
                <strong className="text-lg text-[var(--ui-accent)] mt-1 block">{formatPerSqm(overall.medianPricePerSqm) || '—'}</strong>
              </div>
            </div>
          )}

          {rows.length > 0 ? (
            <ul className="space-y-2.5 pt-2" aria-label="Phân bố mẫu tin rao">
              {rows.map((row) => (
                <li key={row.key} className="grid grid-cols-[minmax(120px,1.2fr)_2fr_auto] items-center gap-3 text-xs">
                  <span className="font-semibold text-[var(--ui-accent)] truncate">{row.label}</span>
                  <span className="h-2.5 rounded-full bg-[var(--ui-soft)] overflow-hidden">
                    <span
                      className="block h-full rounded-full bg-[#168f89]"
                      style={{ width: `${bandWidth(row.count, rows)}%` }}
                    />
                  </span>
                  <span className="text-right font-semibold text-[var(--ui-accent)] tabular-nums">
                    {formatCount(row.count)} tin{row.sub ? ` · ${row.sub}` : ''}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-[var(--ui-muted)]">Chưa có phân nhóm đủ dữ liệu hiển thị.</p>
          )}

          <div className="pt-3 border-t border-[var(--ui-border)] flex flex-wrap items-center justify-between gap-3 text-xs">
            <span className="text-[var(--ui-muted)]">{analytics.meta?.disclaimer}</span>
            <SiteLink to="/market-analytics" className="font-bold text-[var(--ui-accent)] underline underline-offset-4">
              Mở bảng thống kê chi tiết toàn thành phố →
            </SiteLink>
          </div>
        </div>
      )}
    </div>
  )
})
