import React, { useState } from 'react'

const money = (value) =>
  new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(value) || 0)

const exactMoney = (value) => new Intl.NumberFormat('vi-VN').format(Number(value) || 0) + ' VNĐ'

const SOURCE_LABEL = { SMARTPROP: 'SmartProp', EXTERNAL_LISTING: 'Tin đăng ngoài', TINIX_RESEARCH: 'TiniX · nghiên cứu' }

/**
 * Independent evidence for one property: XGBoost V6 valuation with TreeSHAP
 * explanation, plus comparable-listing evidence when present. Renders only
 * fields the API actually returned.
 */
export default function AdvisorEvidencePanel({ valuation, comparable }) {
  const [openShap, setOpenShap] = useState(false)
  const hasValuation = valuation?.available === true
  const shap = valuation?.shapExplanation
  const comparables = comparable?.comparables || []
  if (!hasValuation && comparables.length === 0) return null

  return (
    <div className="ev-panel" data-advisor-evidence>
      {hasValuation ? (
        <section className="ev-block" data-valuation-evidence>
          <div className="ev-head">
            <span className="ev-title">Định giá tham chiếu độc lập</span>
            <span className="ev-model-tag">Model {valuation.modelVersion}</span>
          </div>
          <p className="ev-price" title={exactMoney(valuation.predictedAskingPriceVnd)}>{money(valuation.predictedAskingPriceVnd)}</p>
          {shap ? (
            <button type="button" className="ev-toggle" data-shap-toggle aria-expanded={openShap} onClick={() => setOpenShap((v) => !v)}>
              {openShap ? 'Ẩn giải thích SHAP' : 'Giải thích TreeSHAP'}
            </button>
          ) : null}
          {hasValuation && shap && openShap ? (
            <div className="shap-panel" data-shap-panel>
              {shap.summaryVi ? <p className="shap-summary">{shap.summaryVi}</p> : null}
              {Number.isFinite(Number(shap.basePriceVnd)) ? (
                <p className="shap-meta">Mức cơ sở phân khúc: <strong>{money(shap.basePriceVnd)}</strong></p>
              ) : null}
              {shap.method ? <p className="shap-meta">Phương pháp: <strong>{shap.method}</strong></p> : null}
              {shap.topFactors?.length ? (
                <ul className="shap-list">
                  {shap.topFactors.map((factor) => (
                    <li key={factor.featureName} className="shap-item">
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

      {comparables.length ? (
        <section className="ev-block" data-comparable-evidence>
          <div className="ev-head">
            <span className="ev-title">Đối chiếu tin tương đồng</span>
          </div>
          <ul className="comp-list">
            {comparables.map((item) => (
              <li key={item.candidateId} className="comp-item" data-comparable-source={item.sourceKind}>
                <span className="comp-source">{SOURCE_LABEL[item.sourceKind] ?? item.sourceKind}</span>
                {item.scoreBreakdown ? (
                  <div className="comp-tags">
                    {Object.entries(item.scoreBreakdown).map(([key, val]) => (
                      <span key={key}>{val}</span>
                    ))}
                  </div>
                ) : null}
                {item.sourceKind === 'TINIX_RESEARCH' ? (
                  <p className="comp-attribution">
                    {item.attribution || 'TiniX — Dữ liệu tham chiếu nghiên cứu, chưa xác minh còn giao dịch (CC BY-NC 4.0).'}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}
