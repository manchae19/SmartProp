import React, { useState } from 'react'
import { visibleAdvisorComparables } from './advisorAnalysis.js'
import ComparableListingsCard from '../property/ComparableListingsCard.jsx'
import ValuationExplanationPanel from './ValuationExplanationPanel.js'
import { advisorEvidenceMetadata, evidenceSections } from './advisorEvidenceModel.js'
import { validateExplanation, vndDigits } from './explanationModel.js'

const money = (value) =>
  new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(value) || 0)

const evidenceLabels = {
  VALUATION: 'Định giá AI V1.3',
  EXPLANATION: 'Giải thích TreeSHAP',
  SIMILAR_LISTING: 'Tin tương đồng theo giá rao',
  VALUATION_SUPPORT: 'Đối chiếu định giá bằng tin đăng',
  LOCATION: 'Vị trí và tiện ích',
  RECOMMENDATION: 'Tin đề xuất theo tiêu chí',
}

const sourceLabels = {
  XGBOOST_V1_3: 'XGBoost V1.3', WP04_TREESHAP: 'TreeSHAP của XGBoost',
  WP02_COMPARABLE: 'Tin đăng đủ điều kiện theo Comparable',
  SMARTPROP_GIS_POI: 'Dữ liệu vị trí và tiện ích SmartProp',
  SMARTPROP_LISTING: 'Tin đăng SmartProp', EXTERNAL_LISTING: 'Tin đăng ngoài sàn',
  TINIX_RESEARCH: 'TiniX · nghiên cứu nội bộ',
}

const statusLabels = {
  AVAILABLE: 'Có dữ liệu', PARTIAL: 'Có dữ liệu một phần', MISSING: 'Thiếu dữ liệu',
  UNAVAILABLE: 'Chưa khả dụng', INVALID: 'Dữ liệu không hợp lệ',
  NOT_REQUESTED: 'Không được yêu cầu', INSUFFICIENT_EVIDENCE: 'Chưa đủ bằng chứng',
}

const limitationLabels = {
  ESTIMATED_ASKING_PRICE: 'Ước tính giá rao, không phải kết quả thẩm định.',
  MODEL_ATTRIBUTION: 'Mô tả đóng góp trong mô hình, không xác lập quan hệ nhân quả.',
  ASKING_PRICE_ONLY: 'Giá rao chưa xác nhận giao dịch.',
  TOO_FEW_COMPARABLES: 'Cần ít nhất 3 tin hợp lệ sau lọc trùng để hiển thị ví dụ.',
  COMPARABLE_EXAMPLES_ONLY: 'Chỉ có ví dụ. Chưa đủ điều kiện hiển thị trung vị.',
  AREA_CONTEXT_ONLY: 'Chỉ tham khảo khu vực. Chưa xác định khoảng cách từ bất động sản.',
  STRAIGHT_LINE_DISTANCE: 'Khoảng cách theo đường chim bay.',
  HEURISTIC_FIT: 'Điểm phù hợp theo quy tắc, không thể hiện độ tin cậy của định giá.',
}

function EvidenceMetadata({ metadata, valuation }) {
  const [expanded, setExpanded] = useState(false)
  const showStatus = (entry) => {
    if (entry.kind !== 'EXPLANATION' || !valuation?.explanation) return entry.status
    const result = validateExplanation(valuation.explanation, { priceVnd: vndDigits(valuation.predictedAskingPriceVnd) })
    if (result.view?.priceConsistent === false) return 'INVALID'
    if (result.status === 'NOT_SUPPORTED') return 'UNAVAILABLE'
    return result.status === 'ABSENT' ? 'MISSING' : result.status
  }
  const displayDate = (value) => new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium', timeZone: 'Asia/Ho_Chi_Minh',
  }).format(new Date(value))
  return (
    <details className="ev-block ev-details" data-wp07-evidence onToggle={(event) => setExpanded(event.currentTarget.open)}>
      <summary>Nguồn và giới hạn của bằng chứng</summary>
      {expanded && (metadata.size ? (
        <dl className="ev-metadata">
          {[...metadata.values()].map(entry => {
            const status = showStatus(entry)
            return (
              <div key={entry.kind} data-evidence-kind={entry.kind} data-evidence-status={status} data-evidence-freshness={entry.freshness}>
                <dt>{evidenceLabels[entry.kind]}</dt>
                <dd>{sourceLabels[entry.source] ?? 'Chưa rõ nguồn'} · {statusLabels[status]}</dd>
                <dd>{entry.freshness === 'STALE' ? 'Dữ liệu cũ hơn 90 ngày' : entry.freshness === 'RECENT' ? 'Quan sát trong 90 ngày qua' : 'Chưa rõ độ mới'}</dd>
                {entry.observedAt ? <dd>Quan sát <time dateTime={entry.observedAt}>{displayDate(entry.observedAt)}</time></dd> : null}
                {entry.generatedAt ? <dd>Tạo dữ liệu <time dateTime={entry.generatedAt}>{displayDate(entry.generatedAt)}</time></dd> : null}
                {entry.limitations.map(code => <dd key={code}>{limitationLabels[code]}</dd>)}
              </div>
            )
          })}
        </dl>
      ) : <p>Chi tiết nguồn bằng chứng chưa tải được.</p>)}
    </details>
  )
}


/**
 * Independent evidence for one property: XGBoost V1.3 valuation with TreeSHAP
 * explanation, plus comparable-listing evidence when present. Renders only
 * fields the API actually returned and blocks research items unless both mode
 * and caller authorization explicitly permit research.
 */
export default function AdvisorEvidencePanel({ valuation, comparable, valuationComparables, evidence, mode = 'SAFE', allowResearch = false }) {
  const [openShap, setOpenShap] = useState(false)
  const metadata = advisorEvidenceMetadata(evidence, mode === 'INTERNAL_RESEARCH' && allowResearch)
  const priceDigits = vndDigits(valuation?.predictedAskingPriceVnd)
  const hasValuation = valuation?.available === true && priceDigits !== null
  const exactVnd = hasValuation ? new Intl.NumberFormat('vi-VN').format(BigInt(priceDigits)) : null
  const shap = valuation?.shapExplanation
  const sections = evidenceSections({
    explanation: valuation?.explanation, shap, openShap,
  })
  const renderComparables = (source, kind, research) => {
    const title = evidenceLabels[kind]
    if (!source || source.status === 'SKIPPED_BY_REQUEST') return null
    const status = metadata?.get(kind)?.status ?? 'MISSING'
    if (metadata && ['MISSING', 'INVALID', 'INSUFFICIENT_EVIDENCE'].includes(status)) {
      return <section className='ev-block' data-comparable-evidence data-comparable-unavailable={status}>
        <h4 className='ev-title'>{title}</h4>
        <p>{status === 'INSUFFICIENT_EVIDENCE' ? 'Chưa đủ tin tương đồng sau lọc trùng.' : statusLabels[status]}</p>
      </section>
    }
    const error = ['DEGRADED', 'SKIPPED_UNSUPPORTED_INPUT'].includes(source.status)
      ? source.warnings?.[0] || 'Chưa tải được tin tương đồng.' : null
    return <div data-comparable-evidence>
      <ComparableListingsCard title={title} error={error} allowResearch={research}
        result={{ ...source, evidence: source.cohort, comparables: visibleAdvisorComparables(source, mode, research) }} />
    </div>
  }
  if (!metadata && !hasValuation && (!comparable || comparable.status === 'SKIPPED_BY_REQUEST') && !valuationComparables) return null

  return (
    <div className="ev-panel" data-advisor-evidence>
      {hasValuation ? (
        <section className="ev-block" data-valuation-evidence>
          <div className="ev-head">
            <span className="ev-title">Định giá tham chiếu độc lập</span>
            <span className="ev-model-tag">Model {valuation.modelVersion}</span>
          </div>
          <p className="ev-price" title={exactVnd + ' VNĐ'}>{exactVnd} ₫</p>
          {sections.showExplanation ? (
            <ValuationExplanationPanel
              explanation={valuation.explanation}
              predictedPriceVnd={valuation.predictedAskingPriceVnd}
              modelVersion={valuation.modelVersion}
              surface="advisor"
              className="mt-3"
            />
          ) : null}
          {sections.showLegacyShapToggle ? (
            <button type="button" className="ev-toggle" data-shap-toggle aria-expanded={openShap} onClick={() => setOpenShap((v) => !v)}>
              {openShap ? 'Ẩn giải thích SHAP' : 'Giải thích TreeSHAP'}
            </button>
          ) : null}
          {sections.showLegacyShapContent ? (
            <div className="shap-panel" data-shap-panel>
              {shap.summaryVi ? <p className="shap-summary">{shap.summaryVi}</p> : null}
              {Number.isFinite(Number(shap.basePriceVnd)) ? (
                <p className="shap-meta">Mức cơ sở phân khúc: <strong>{money(shap.basePriceVnd)}</strong></p>
              ) : null}
              {shap.method ? <p className="shap-meta">Phương pháp: <strong>{shap.method}</strong></p> : null}
              {shap.topFactors?.length ? (
                <ul className="shap-list">
                  {shap.topFactors.map((factor, index) => (
                    <li key={index + ':' + factor.featureName} className="shap-item">
                      <span>
                        {factor.labelVi || factor.featureName}
                        {factor.noteVi ? <small>{factor.noteVi}</small> : null}
                      </span>
                      <span className={factor.direction === 'increase' ? 'shap-up' : 'shap-down'}>
                        {factor.direction === 'increase' ? '▲ tăng' : '▼ giảm'}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : metadata && metadata.get('VALUATION')?.status !== 'NOT_REQUESTED' ? (
        <p className="ev-block" data-valuation-evidence-unavailable>Định giá AI V1.3 · {statusLabels[metadata.get('VALUATION')?.status ?? 'MISSING']}</p>
      ) : null}

      {renderComparables(comparable, 'SIMILAR_LISTING', mode === 'INTERNAL_RESEARCH' && allowResearch)}
      {renderComparables(valuationComparables, 'VALUATION_SUPPORT', false)}
      {metadata ? <EvidenceMetadata metadata={metadata} valuation={valuation} /> : null}
    </div>
  )
}
