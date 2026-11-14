import { classNames } from "../../shared/lib/ui.js";
import React, { useRef } from "react";
import { useRouteState } from "../../app/navigation.jsx";
import { listingsReturnFor } from "./listingJourney.js";
import { SiteLink } from "../../app/navigation.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import { price, compactPrice, displayDecimal, types, states } from "./property.js";
import "./ListingCard.css";
function useListingCardState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const route = useRouteState();
  const getDetail = () => ({
    path: "/listing/" + _props.current.property.id,
    query: _props.current.own ? {
      own: "1"
    } : {returnTo: listingsReturnFor(route)}
  });
  const getCover = () => (_props.current.property.images?.find(image => image.cover) || _props.current.property.images?.[0])?.url;
  const getImageCount = () => _props.current.property.images?.length || 0;
  const getFullAddress = () => {
    const parts = [_props.current.property.address, _props.current.property.ward, _props.current.property.district].filter(Boolean);
    if (parts.length) return parts.join(", ");
    return [_props.current.property.district, _props.current.property.city].filter(Boolean).join(", ") || "Đà Nẵng";
  };
  const getArea = () => displayDecimal(_props.current.property.areaSqmExact ?? _props.current.property.areaSqm);
  const getUnitPriceText = () => {
    const pr = Number(_props.current.property.priceExact ?? _props.current.property.price ?? 0);
    const ar = Number(_props.current.property.areaSqmExact ?? _props.current.property.areaSqm ?? 0);
    if (pr > 0 && ar > 0 && _props.current.property.transactionType === "SALE" && _props.current.property.priceUnit === "TOTAL") {
      const perSqm = Math.round(pr / ar);
      if (perSqm >= 1000000) {
        return `~ ${(perSqm / 1000000).toLocaleString("vi-VN", {
          maximumFractionDigits: 1
        })} tr/m²`;
      }
      return `~ ${perSqm.toLocaleString("vi-VN")} đ/m²`;
    }
    return null;
  };
  return {
    ...inputProps,
    price,
    compactPrice,
    types,
    states,
    detail: getDetail(),
    cover: getCover(),
    imageCount: getImageCount(),
    fullAddress: getFullAddress(),
    area: getArea(),
    unitPriceText: getUnitPriceText(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["property", "own", "list", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function ListingCard(props, ref) {
  const view = useListingCardState(props, ref);
  return <><article data-sp-d0ec4fcb="" {...view.rootAttributes} className={classNames([classNames(["property-card", {
      "property-card-list": view.list
    }]), view.rootAttributes.className])}>
      <SiteLink to={view.detail} className="property-main" aria-label={"Xem chi tiết " + view.property.title} data-sp-d0ec4fcb="">
        <div className="property-image" data-sp-d0ec4fcb="">
          <PrivateImage src={view.cover} alt={view.property.title} data-sp-d0ec4fcb="" />
          <div className="image-top-tags" data-sp-d0ec4fcb="">
            <span className={classNames(["badge-transaction", view.property.transactionType === "RENT" ? "rent" : "sale"])} data-sp-d0ec4fcb="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.own ? view.states[view.property.status] : view.property.transactionType === "SALE" ? "Bán" : "Cho thuê")}
            </span>
            <span className="badge-type" data-sp-d0ec4fcb="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.types[view.property.propertyType] || view.property.propertyType)}
            </span>
          </div>
          <div className="image-bottom-tags" data-sp-d0ec4fcb="">
            {view.imageCount > 1 ? <span className="badge-photo-count" data-sp-d0ec4fcb="">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" data-sp-d0ec4fcb="">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" data-sp-d0ec4fcb="" />
                  <circle cx="12" cy="13" r="4" data-sp-d0ec4fcb="" />
                </svg>{" "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.imageCount)}
                {" ảnh "}
              </span> : null}
          </div>
        </div>
        <div className="property-body" data-sp-d0ec4fcb="">
          <h3 className="property-title" title={view.property.title} data-sp-d0ec4fcb="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property.title)}
          </h3>
          <div className="property-metrics" data-sp-d0ec4fcb="">
            <div className="price-container" data-sp-d0ec4fcb="">
              <span className="main-price" title={view.price(view.property)} data-sp-d0ec4fcb="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.compactPrice(view.property))}
              </span>
              {view.unitPriceText ? <span className="unit-price" data-sp-d0ec4fcb="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.unitPriceText)}
                </span> : null}
            </div>
            <div className="area-container" aria-label={"Diện tích " + view.area + " m²"} data-sp-d0ec4fcb="">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" data-sp-d0ec4fcb="">
                <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 3l6 6m12-6-6 6M3 21l6-6m12 6-6-6" data-sp-d0ec4fcb="" />
              </svg>
              <span data-sp-d0ec4fcb="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.area)}
                {" m²"}
              </span>
            </div>
          </div>
          <p className="property-location" title={view.fullAddress} data-sp-d0ec4fcb="">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" data-sp-d0ec4fcb="">
              <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" data-sp-d0ec4fcb="" />
              <circle cx="12" cy="10" r="2.5" data-sp-d0ec4fcb="" />
            </svg>
            <span data-sp-d0ec4fcb="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.fullAddress)}
            </span>
          </p>
          <div className="property-specs" data-sp-d0ec4fcb="">
            {view.property.direction ? <span className="spec-pill" data-sp-d0ec4fcb="">
                {" 🧭 Hướng "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property.direction)}
              </span> : null}
            {view.property.bedrooms > 0 ? <span className="spec-pill" data-sp-d0ec4fcb="">
                {" 🛏️ "}
                <strong data-sp-d0ec4fcb="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property.bedrooms)}
                </strong>
                {" PN "}
              </span> : null}
            {view.property.bathrooms > 0 ? <span className="spec-pill" data-sp-d0ec4fcb="">
                {" 🚿 "}
                <strong data-sp-d0ec4fcb="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property.bathrooms)}
                </strong>
                {" PT "}
              </span> : null}
            {view.property.propertyType === "LAND" ? <span className="spec-pill land-tag" data-sp-d0ec4fcb="">
                {" 📑 Sổ đỏ sẵn sàng "}
              </span> : null}
          </div>
        </div>
      </SiteLink>
      <div className="property-actions" data-sp-d0ec4fcb="">
        <SiteLink to={view.detail} className="detail-link" data-sp-d0ec4fcb="">
          {"Xem chi tiết ↗"}
        </SiteLink>
        {view.children ?? null}
      </div>
    </article></>;
});
