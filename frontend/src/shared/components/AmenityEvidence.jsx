import { classNames } from "../lib/ui.js";
import React, { useRef } from "react";
import "./AmenityEvidence.css";
function useAmenityEvidenceState(inputProps, forwardedRef) {
  inputProps = {
    evidence: null,
    compact: false,
    area: false,
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    evidence: null,
    compact: false,
    area: false,
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const num = value => Number.isFinite(value) ? new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: 1
  }).format(value) : null;
  const getCategories = () => {
    const scores = _props.current.evidence?.categoryScores;
    if (!scores) return [];
    return [{
      key: "essentials",
      icon: "🛒",
      label: "Chợ & siêu thị",
      score: scores.essentials
    }, {
      key: "education",
      icon: "🎓",
      label: "Trường học",
      score: scores.education
    }, {
      key: "healthcare",
      icon: "🏥",
      label: "Y tế",
      score: scores.healthcare
    }, {
      key: "transit",
      icon: "🚌",
      label: "Giao thông công cộng",
      score: scores.transit
    }, {
      key: "recreation",
      icon: "🌳",
      label: "Công viên & biển",
      score: scores.recreation
    }].filter(c => Number.isFinite(c.score));
  };
  const getBasisLabel = () => ({
    DIRECT_WARD_EVIDENCE: "Theo đúng phường/xã của bất động sản",
    DISTRICT_SHARED_AMENITY: "Theo quận/huyện (tiện ích dùng chung)",
    NO_AREA_MATCH: "Chưa xác định được địa bàn"
  })[_props.current.evidence?.evidenceBasis] || "Chưa xác định";
  const getHasProfile = () => _props.current.evidence != null && _props.current.evidence.areaAmenityScore != null;
  const getVisibleEvidence = () => (_props.current.evidence?.poiEvidence || []).slice(0, _props.current.compact ? 4 : 8);
  return {
    ...inputProps,
    num,
    categories: getCategories(),
    basisLabel: getBasisLabel(),
    hasProfile: getHasProfile(),
    visibleEvidence: getVisibleEvidence(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["evidence", "compact", "area", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function AmenityEvidence(props, ref) {
  const view = useAmenityEvidenceState(props, ref);
  return <><section data-amenity-evidence="" data-sp-8b7e0c1f="" {...view.rootAttributes} className={classNames([classNames(["amenity-evidence", {
      compact: view.compact,
      "area-mode": view.area
    }]), view.rootAttributes.className])}>
      <header className="ae-head" data-sp-8b7e0c1f="">
        <div data-sp-8b7e0c1f="">
          <p className="ae-eyebrow" data-sp-8b7e0c1f="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.area ? "TIỆN ÍCH KHU VỰC" : "TIỆN ÍCH KHU VỰC SINH SỐNG")}
          </p>
          {view.hasProfile ? <h4 data-sp-8b7e0c1f="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.num(view.evidence.areaAmenityScore))}
              <small data-sp-8b7e0c1f="">
                {"/100"}
              </small>{" "}
              <span className="ae-name" data-sp-8b7e0c1f="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.evidence.areaName)}
              </span>
            </h4> : <h4 className="ae-na" data-sp-8b7e0c1f="">
              {"Chưa có điểm tiện ích"}
            </h4>}
        </div>
        {view.hasProfile && Number.isFinite(view.evidence.confidence) ? <span className="ae-confidence" title={view.basisLabel} data-sp-8b7e0c1f="">
            {"Tin cậy "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(Math.round(view.evidence.confidence * 100))}
            {"%"}
          </span> : null}
      </header>
      <p className="ae-basis" data-sp-8b7e0c1f="">
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.basisLabel)}
        {" · "}
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.evidence.areaLevel === "WARD" ? "cấp phường/xã" : view.evidence.areaLevel === "DISTRICT" ? "cấp quận/huyện" : "không xác định")}
      </p>
      {view.categories.length ? <ul className="ae-bars" data-sp-8b7e0c1f="">
          {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.categories, c => <li key={c.key} data-sp-8b7e0c1f="">
              <span className="ae-label" data-sp-8b7e0c1f="">
                <span aria-hidden="true" data-sp-8b7e0c1f="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(c.icon)}
                </span>{" "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(c.label)}
              </span>
              <span className="ae-track" role="meter" aria-label={c.label} aria-valuemin="0" aria-valuemax="100" aria-valuenow={c.score} data-sp-8b7e0c1f="">
                <span style={{
              width: c.score + "%"
            }} data-sp-8b7e0c1f="" />
              </span>
              <span className="ae-value" data-sp-8b7e0c1f="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.num(c.score))}
              </span>
            </li>)}
        </ul> : null}
      {view.visibleEvidence.length ? <div className="ae-pois" data-sp-8b7e0c1f="">
          <p className="ae-pois-title" data-sp-8b7e0c1f="">
            {"Tiện ích đã số hóa trong khu vực"}
          </p>
          <ul data-sp-8b7e0c1f="">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.visibleEvidence, poi => <li key={poi.name + poi.category} data-sp-8b7e0c1f="">
                <span className="ae-poi-name" data-sp-8b7e0c1f="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(poi.name)}
                </span>
                <span className="ae-poi-cat" data-sp-8b7e0c1f="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(poi.category)}
                </span>
              </li>)}
          </ul>
        </div> : view.hasProfile ? <p className="ae-note" data-sp-8b7e0c1f="">
          {"Hồ sơ khu vực không kèm tên tiện ích cụ thể."}
        </p> : null}
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))((view.evidence?.dataLimitations || []).slice(0, view.compact ? 1 : 3), limitation => <p key={limitation} className="ae-note" data-sp-8b7e0c1f="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(limitation)}
          </p>)}
      {view.hasProfile ? <p className="ae-note ae-note-strong" data-sp-8b7e0c1f="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.evidence.note)}
        </p> : null}
    </section></>;
});
