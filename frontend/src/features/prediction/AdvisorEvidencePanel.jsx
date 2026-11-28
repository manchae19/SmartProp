import React, { useState } from 'react'
import { visibleAdvisorComparables } from './advisorAnalysis.js'
import ComparableListingsCard from '../property/ComparableListingsCard.jsx'
import ValuationExplanationPanel from './ValuationExplanationPanel.js'
import { evidenceSections } from './advisorEvidenceModel.js'

const money = (value) =>
  new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(value) || 0)

const exactMoney = (value) => new Intl.NumberFormat('vi-VN').format(Number(value) || 0) + ' VNĐ'

/**
 * Independent evidence for one property: XGBoost V1.3 valuation with TreeSHAP
 * explanation, plus comparable-listing evidence when present. Renders only
 * fields the API actually returned and blocks research items unless both mode
 * and caller authorization explicitly permit research.
 */
export default function AdvisorEvidencePanel({ valuation, comparable, valuationComparables, mode = 'SAFE', allowResearch = false }) {
  const [openShap, setOpenShap] = useState(false)
  const hasValuation = valuation?.available === true
  const shap = valuation?.shapExplanation
  const sections = evidenceSections({
    explanation: valuation?.explanation, shap, openShap,
  })
  const renderComparables = (source, title, research) => {
    if (!source || source.status === 'SKIPPED_BY_REQUEST') return null
    const error = ['DEGRADED', 'SKIPPED_UNSUPPORTED_INPUT'].includes(source.status)
      ? source.warnings?.[0] || 'Chưa tải được tin tương đồng.' : null
    return <div data-comparable-evidence>
      <ComparableListingsCard title={title} error={error} allowResearch={research}
        result={{ ...source, evidence: source.cohort, comparables: visibleAdvisorComparables(source, mode, research) }} />
    </div>
  }
  if (!hasValuation && (!comparable || comparable.status === 'SKIPPED_BY_REQUEST') && !valuationComparables) return null

  return (
    <div className="ev-panel" data-advisor-evidence>
      {hasValuation ? (
        <section className="ev-block" data-valuation-evidence>
          <div className="ev-head">
            <span className="ev-title">Định giá tham chiếu độc lập</span>
            <span className="ev-model-tag">Model {valuation.modelVersion}</span>
          </div>
          <p className="ev-price" title={exactMoney(valuation.predictedAskingPriceVnd)}>{money(valuation.predictedAskingPriceVnd)}</p>
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
      ) : null}

      {renderComparables(comparable, 'Tin tương đồng theo giá rao', mode === 'INTERNAL_RESEARCH' && allowResearch)}
      {renderComparables(valuationComparables, 'Đối chiếu định giá bằng tin đăng', false)}
    </div>
  )
}
