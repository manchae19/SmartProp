import React from 'react'

const num = (value) =>
  Number.isFinite(value) ? new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 }).format(value) : null

const BASIS = {
  DIRECT_WARD_EVIDENCE: 'Theo đúng phường/xã của bất động sản',
  DISTRICT_SHARED_AMENITY: 'Theo quận/huyện (tiện ích dùng chung)',
  NO_AREA_MATCH: 'Chưa xác định được địa bàn',
}

/** Amenity evidence card (ward/district area profile with POIs). Pure props render. */
export default function AmenityEvidence({ evidence, compact = false, area = false }) {
  const scores = evidence?.categoryScores
  const categories = scores
    ? [
        { key: 'essentials', icon: '🛒', label: 'Chợ & siêu thị', score: scores.essentials },
        { key: 'education', icon: '🎓', label: 'Trường học', score: scores.education },
        { key: 'healthcare', icon: '🏥', label: 'Y tế', score: scores.healthcare },
        { key: 'transit', icon: '🚌', label: 'Giao thông công cộng', score: scores.transit },
        { key: 'recreation', icon: '🌳', label: 'Công viên & biển', score: scores.recreation },
      ].filter((c) => Number.isFinite(c.score))
    : []
  const basisLabel = BASIS[evidence?.evidenceBasis] ?? 'Chưa xác định'
  const hasProfile = evidence != null && evidence.areaAmenityScore != null
  const levelLabel = evidence?.areaLevel === 'WARD' ? 'cấp phường/xã' : evidence?.areaLevel === 'DISTRICT' ? 'cấp quận/huyện' : 'không xác định'
  const visibleEvidence = (evidence?.poiEvidence || []).slice(0, compact ? 4 : 8)

  return (
    <section className={`amenity-evidence${compact ? ' compact' : ''}${area ? ' area-mode' : ''}`} data-amenity-evidence>
      <header className="ae-head">
        <div>
          <p className="ae-eyebrow">{area ? 'TIỆN ÍCH KHU VỰC' : 'TIỆN ÍCH KHU VỰC SINH SỐNG'}</p>
          {hasProfile ? (
            <h4>{num(evidence.areaAmenityScore)}<small>/100</small> <span className="ae-name">{evidence.areaName}</span></h4>
          ) : (
            <h4 className="ae-na">Chưa có điểm tiện ích</h4>
          )}
        </div>
        {hasProfile && Number.isFinite(evidence.confidence) ? (
          <span className="ae-confidence" title={basisLabel}>Tin cậy {Math.round(evidence.confidence * 100)}%</span>
        ) : null}
      </header>
      <p className="ae-basis">{basisLabel} · {levelLabel}</p>
      {categories.length ? (
        <ul className="ae-bars">
          {categories.map((c) => (
            <li key={c.key}>
              <span className="ae-label"><span aria-hidden="true">{c.icon}</span> {c.label}</span>
              <span className="ae-track" role="meter" aria-label={c.label} aria-valuemin="0" aria-valuemax="100" aria-valuenow={c.score}>
                <span style={{ width: `${c.score}%` }} />
              </span>
              <span className="ae-value">{num(c.score)}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {visibleEvidence.length ? (
        <div className="ae-pois">
          <p className="ae-pois-title">Tiện ích đã số hóa trong khu vực</p>
          <ul>
            {visibleEvidence.map((poi) => (
              <li key={poi.name + poi.category}>
                <span className="ae-poi-name">{poi.name}</span>
                <span className="ae-poi-cat">{poi.category}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : hasProfile ? (
        <p className="ae-note">Hồ sơ khu vực không kèm tên tiện ích cụ thể.</p>
      ) : null}
      {(evidence?.dataLimitations || []).slice(0, compact ? 1 : 3).map((limitation) => (
        <p key={limitation} className="ae-note">{limitation}</p>
      ))}
      {hasProfile ? <p className="ae-note ae-note-strong">{evidence.note}</p> : null}
    </section>
  )
}
