import React from 'react'
import AmenityEvidence from './AmenityEvidence.jsx'
import AdvisorLocationCard from './AdvisorLocationCard.jsx'
import AdvisorEvidencePanel from './AdvisorEvidencePanel.jsx'
import { advisorWarning, safeAdvisorPropertyUrl } from './advisorAnalysis.js'

const money = (value) =>
  new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(value) || 0)
const score = (value) => (Number.isFinite(Number(value)) ? Math.round(Number(value)) : '—')
const area = (value) => (Number.isFinite(Number(value)) ? `${Number(value).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} m²` : '—')

/** Results of one Unified Advisor consultation: areas + ranked properties with evidence. */
export default function AdvisorResults({ result, selectedPoiId = '', onFocusPoi }) {
  const properties = result?.recommendedProperties || []
  const isResearch = result?.mode === 'INTERNAL_RESEARCH'
  const isPartial = Boolean(result?.serviceStatus?.partialResult)

  return (
    <div className="ar-root" data-advisor-results>
      <div className={`ar-mode-note${isResearch ? ' research' : ''}`} data-advisor-mode={result?.mode}>
        {isResearch
          ? 'Chế độ nghiên cứu nội bộ (ADMIN · TiniX CC BY-NC 4.0) — quan sát lịch sử đã lọc holdout, không phải tin đang bán.'
          : 'Chế độ công khai an toàn (SAFE) — chỉ bất động sản đang công khai hợp lệ.'}
      </div>

      {isPartial ? (
        <p className="ar-partial" role="status" data-advisor-partial>
          Kết quả một phần: một dịch vụ bằng chứng chưa khả dụng.
          {result.serviceStatus?.valuationService === 'UNAVAILABLE' ? ' Định giá V6 tạm không khả dụng.' : ''}
        </p>
      ) : null}

      {result?.topAreas?.length ? (
        <section className="ar-section">
          <h3>Khu vực phù hợp nhất</h3>
          <div className="area-grid">
            {result.topAreas.map((item, index) => (
              <article className="area-card" key={`${item.district}:${item.ward || ''}:${index}`} data-top-area>
                <div className="area-card-head">
                  <strong>{item.district}{item.ward ? ` · ${item.ward}` : ''}</strong>
                  <span className="area-score">{score(item.areaScore)}<small>/100</small></span>
                </div>
                {item.headlineVi ? <p className="area-headline">{item.headlineVi}</p> : null}
                {item.highlightsVi?.length ? (
                  <ul className="area-list">
                    {item.highlightsVi.map((line) => <li key={line}>{line}</li>)}
                  </ul>
                ) : null}
                <p className="area-basis">
                  {item.amenityEvidenceBasis === 'DIRECT_WARD_EVIDENCE' ? 'Hồ sơ cấp phường/xã' : 'Hồ sơ cấp quận/huyện'}
                  {item.amenityConfidence != null ? ` · độ phủ ${Math.round(item.amenityConfidence * 100)}%` : ''}
                </p>
                {(item.warnings || []).map((warning, index) => (
                  <p key={index + ':' + warning} className="quality-note">{advisorWarning(warning)}</p>
                ))}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="ar-section">
        <h3>Bất động sản đề xuất</h3>
        {properties.length === 0 ? (
          <p className="ar-empty">Không có bất động sản nào thoả tiêu chí trong dữ liệu hiện có.</p>
        ) : (
          <ul className="ar-properties">
            {properties.map((property) => {
              const url = safeAdvisorPropertyUrl(property)
              return (
                <li className="ar-property" key={property.id} data-advisor-property>
                  <div className="ar-property-head">
                    <div>
                      <h4>{property.title || `Bất động sản #${property.id}`}</h4>
                      <p className="ar-property-loc">
                        {property.district}{property.ward ? `, ${property.ward}` : ''} · {area(property.areaSqm)}
                        {property.researchReference ? ' · nguồn nghiên cứu TiniX' : ''}
                      </p>
                    </div>
                    <div className="ar-property-score" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow={score(property.recommendationScore)}>
                      <span className="ar-score-num">{score(property.recommendationScore)}<small>/100</small></span>
                      <span className="ar-score-track"><span style={{ width: `${Math.min(100, Math.max(0, property.recommendationScore || 0))}%` }} /></span>
                    </div>
                  </div>

                  <p className="ar-price">{money(property.priceVnd)}</p>

                  {Number.isFinite(Number(property.distanceMeters)) ? (
                    // Nearby results carry a straight-line distance; say so rather than
                    // letting the number read as a travel distance.
                    <p className="ar-distance" data-nearby-distance>
                      Cách vị trí đã xác nhận {Math.round(Number(property.distanceMeters))} m
                      (đường chim bay)
                    </p>
                  ) : null}

                  {property.scoreBreakdown ? (
                    <dl className="ar-breakdown" data-score-breakdown>
                      {Object.entries(property.scoreBreakdown).map(([key, value]) => (
                        <div key={key}>
                          <dt>{key}</dt>
                          <dd>{value}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : null}

                  <AdvisorEvidencePanel valuation={property.valuationEvidence} comparable={property.comparableEvidence} />

                  {property.amenityEvidence ? <AmenityEvidence evidence={property.amenityEvidence} compact /> : null}

                  <AdvisorLocationCard property={property} selectedPoiId={selectedPoiId} onFocusPoi={onFocusPoi} />

                  {(property.warnings || []).map((warning, index) => (
                    <p key={index + ':' + warning} className="quality-note">{advisorWarning(warning)}</p>
                  ))}

                  {url ? <a className="ar-link" href={url}>Xem tin đăng →</a> : null}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {result?.warnings?.length ? (
        <ul className="ar-warnings">
          {result.warnings.map((warning, index) => <li key={index + ':' + warning}>{advisorWarning(warning)}</li>)}
        </ul>
      ) : null}
    </div>
  )
}
