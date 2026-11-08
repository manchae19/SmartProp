import React from 'react'
import { poiLabel, poiSymbol } from '../map/nearbyPlaces.js'
import { advisorSelectedPois } from './advisorAnalysis.js'

function formatMeters(meters) {
  const m = Number(meters)
  if (!Number.isFinite(m)) return ''
  return m >= 1000 ? `${(m / 1000).toFixed(2).replace('.', ',')} km` : `${Math.round(m)} m`
}

function precisionBadge(loc) {
  if (!loc) return null
  if (loc.mapEligible) return { text: 'Tọa độ thực tế đã xác thực (WGS84 · SRID 4326)', cls: 'precision-verified' }
  if (loc.locationPrecision === 'WARD_FALLBACK') return { text: 'Fallback hành chính · Cấp Phường/Xã', cls: 'precision-fallback' }
  if (loc.locationPrecision === 'DISTRICT_FALLBACK') return { text: 'Fallback hành chính · Cấp Quận/Huyện', cls: 'precision-fallback' }
  return { text: 'Fallback hành chính · Cấp Thành phố', cls: 'precision-fallback' }
}

/** GIS location-intelligence card: verified POIs when mapEligible, explicit fallback otherwise. */
export default function AdvisorLocationCard({ property, selectedPoiId = '', onFocusPoi }) {
  const loc = property?.locationIntelligence
  if (!loc) return null
  const pois = advisorSelectedPois(property)
  const fit = loc.purposeLocationFit
  const badge = precisionBadge(loc)
  const purposeTag =
    fit?.purpose === 'INVESTMENT' ? 'Đầu tư (INVESTMENT)' : fit?.purpose === 'RENTAL' ? 'Khai thác thuê (RENTAL)' : 'Ở thực (LIVING)'

  return (
    <section
      className="gis-intel-card"
      data-location-intelligence={loc.locationPrecision}
      aria-label={`Phân tích vị trí & không gian: ${property.title}`}
    >
      <div className="gis-header">
        <span className="gis-eyebrow">TRÍ TUỆ VỊ TRÍ &amp; KHÔNG GIAN (GIS)</span>
        {badge ? <span className={`precision-pill ${badge.cls}`} data-location-precision-badge>{badge.text}</span> : null}
      </div>

      {loc.displayLabel ? <p className="gis-admin-label">Địa bàn chuẩn hóa: <strong>{loc.displayLabel}</strong></p> : null}
      {loc.adminHierarchyNote ? <p className="gis-provenance" data-admin-provenance>{loc.adminHierarchyNote}</p> : null}

      {fit ? (
        <div className="purpose-fit-box" data-purpose-fit={fit.purpose}>
          <div className="purpose-fit-head">
            <strong>{fit.headlineVi}</strong>
            <span className="purpose-chip">{purposeTag}</span>
          </div>
          {fit.highlightsVi?.length ? (
            <ul className="purpose-list">
              {fit.highlightsVi.map((line) => <li key={line}>{line}</li>)}
            </ul>
          ) : null}
          {fit.spatialBasisNote ? <p className="basis-note">{fit.spatialBasisNote}</p> : null}
        </div>
      ) : null}

      {loc.mapEligible && pois.length ? (
        <div className="nearby-pois-box" data-nearby-pois>
          <p className="nearby-heading">
            Tiện ích thực tế trong bán kính {formatMeters(loc.nearbyPoiRadiusMeters || 1500)} (đường chim bay <code>ST_Distance_Sphere</code> — bấm để xem ghim trên bản đồ):
          </p>
          <div className="poi-chip-list">
            {pois.map((poi) => (
              <button
                key={poi.id}
                type="button"
                className={`poi-chip${selectedPoiId === poi.id ? ' active' : ''}`}
                aria-pressed={selectedPoiId === poi.id}
                data-nearby-poi-chip={poi.id}
                onClick={() => onFocusPoi?.({ propertyId: property.id, poiId: poi.id })}
              >
                <span className="poi-sym" aria-hidden="true">{poiSymbol(poi.category)}</span>
                <span className="poi-name">{poi.name}</span>
                <span className="poi-cat">({poi.categoryLabelVi || poiLabel(poi.category)})</span>
                <strong className="poi-dist">{formatMeters(poi.distanceMeters)}</strong>
              </button>
            ))}
          </div>
        </div>
      ) : loc.mapEligible ? (
        <p className="fallback-box muted-box">
          Tọa độ bất động sản đã xác thực trên bản đồ nhưng chưa ghi nhận POI đã số hóa trong bán kính 1,5 km.
        </p>
      ) : loc.fallbackReason ? (
        <div className="fallback-box" data-location-fallback>
          <strong>Giới hạn dữ liệu tọa độ:</strong>
          <span> {loc.fallbackReason}</span>
        </div>
      ) : null}
    </section>
  )
}
