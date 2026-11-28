import { createPortal } from "react-dom";
import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useAppNavigation, useRouteState } from "../../app/navigation.jsx";
import { api, session, errorText } from "../auth/api.js";
import { adapt } from "./listingPresentation.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import ImageAnalysisSection from "./ImageAnalysisSection.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import { mapUrl } from "./property.js";
import { isPublicProperty } from "./usePublicListings.js";
import ContactPanel from "./ContactPanel.jsx";
import { chatSession } from "../prediction/chatRuntime.js";
import { safeListingsReturnTo } from "./listingJourney.js";
import PropertyExplorer from "../map/PropertyExplorer.jsx";
import PrePurchaseChecks from "./PrePurchaseChecks.jsx";
import CoordinateStatusPanel from "./CoordinateStatusPanel.jsx";
import { locationLabel } from "../map/locationDisplay.js";
import "./ListingDetailView.css";
function useListingDetailViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  function formatPostDate(isoStr) {
    if (!isoStr) return "Chưa có thời điểm đăng";
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return "Chưa có thời điểm đăng";
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    const hour = String(d.getHours()).padStart(2, "0");
    const minute = String(d.getMinutes()).padStart(2, "0");
    return `${hour}:${minute} - ${day}/${month}/${year}`;
  }
  const [copiedShareLink] = useState(() => createStateStore(false));
  useSyncExternalStore(copiedShareLink.subscribe, copiedShareLink.getSnapshot);
  function shareListing() {
    try {
      navigator.clipboard.writeText(window.location.href);
      copiedShareLink.set(true);
      setTimeout(() => copiedShareLink.set(false), 2500);
    } catch (e) {
      // fallback
    }
  }
  const getIsLandProperty = () => property.getSnapshot()?.propertyType === "LAND";
  const route = useRouteState(),
    router = useAppNavigation(),
    [state] = useState(() => createStateStore({
      busy: false,
      error: "",
      notice: "",
      notFound: false
    })),
    [property] = useState(() => createStateStore(null)),
    [revealedContact] = useState(() => createStateStore(null)),
    [isFavorite] = useState(() => createStateStore(false)),
    [showGallery] = useState(() => createStateStore(false)),
    [currentImageIndex] = useState(() => createStateStore(0)),
    [pois] = useState(() => createStateStore([]));
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  useSyncExternalStore(pois.subscribe, pois.getSnapshot);
  useSyncExternalStore(currentImageIndex.subscribe, currentImageIndex.getSnapshot);
  useSyncExternalStore(showGallery.subscribe, showGallery.getSnapshot);
  useSyncExternalStore(isFavorite.subscribe, isFavorite.getSnapshot);
  useSyncExternalStore(revealedContact.subscribe, revealedContact.getSnapshot);
  useSyncExternalStore(property.subscribe, property.getSnapshot);
  useSyncExternalStore(state.subscribe, state.getSnapshot);
  const galleryDialog = useRef(null), galleryOpener = useRef(null);
  const galleryOpen = showGallery.getSnapshot();
  useEffect(() => {
    if (!galleryOpen || !galleryDialog.current) return;
    const dialog = galleryDialog.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () => Array.from(dialog.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'))
      .filter(node => node.getClientRects().length && getComputedStyle(node).visibility !== "hidden");
    const focusFirst = () => (focusable()[0] || dialog).focus({ preventScroll: true });
    focusFirst();
    const keyboard = event => {
      if (event.key === "Escape") {
        event.preventDefault(); event.stopPropagation(); showGallery.set(false);
      } else if (event.key === "Tab") {
        const items = focusable(), first = items[0], last = items.at(-1);
        if (!items.length) { event.preventDefault(); dialog.focus(); }
        else if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault(); first.focus();
        }
      }
    };
    const containFocus = event => { if (!dialog.contains(event.target)) focusFirst(); };
    document.addEventListener("keydown", keyboard, true);
    document.addEventListener("focusin", containFocus);
    return () => {
      document.removeEventListener("keydown", keyboard, true);
      document.removeEventListener("focusin", containFocus);
      document.body.style.overflow = previousOverflow;
      if (galleryOpener.current?.isConnected) galleryOpener.current.focus({ preventScroll: true });
    };
  }, [galleryOpen]);
  const getListing = () => adapt(property.getSnapshot()),
    getListingId = () => _routeLatest.current.params.id,
    getImages = () => property.getSnapshot()?.images?.map(i => i.url) || [];
  const openGallery = (index = 0, opener = document.activeElement) => {
      if (!getImages().length) return;
      galleryOpener.current = opener;
      currentImageIndex.set(Math.min(index, getImages().length - 1));
      showGallery.set(true);
    },
    closeGallery = () => {
      showGallery.set(false);
    },
    nextImage = () => currentImageIndex.set((currentImageIndex.getSnapshot() + 1) % Math.max(getImages().length, 1)),
    prevImage = () => currentImageIndex.set((currentImageIndex.getSnapshot() - 1 + getImages().length) % Math.max(getImages().length, 1)),
    selectImage = i => currentImageIndex.set(i);
  const goHome = () => _routerLatest.current.push("/home"),
    goMap = () => _routerLatest.current.push({
      path: "/map",
      query: {
        propertyId: String(_routeLatest.current.params.id)
      }
    }),
    goAccount = () => _routerLatest.current.push("/account");
  const handleBack = () => {
    if (_routeLatest.current.query.own === "1") return _routerLatest.current.push("/my-listing");
    return _routerLatest.current.push(safeListingsReturnTo(_routeLatest.current.query.returnTo));
  };
  const askAboutProperty = () => {
    const p = property.getSnapshot();
    if (!p || !isPublicProperty(p)) return;
    chatSession.getSnapshot().focusProperty(p.id, p.listingCode || p.title);
    window.dispatchEvent(new CustomEvent("smartprop:advisor-open"));
  };
  const _loadSequenceRef = useRef(0);
  async function load() {
    const run = ++_loadSequenceRef.current,
      id = _routeLatest.current.params.id,
      own = _routeLatest.current.query.own === "1";
    closeGallery();
    property.set(null);
    isFavorite.set(false);
    state.edit(draftValue => Object.assign(draftValue, {
      busy: true,
      error: "",
      notice: "",
      notFound: false
    }));
    try {
      const result = await api((own ? "/users/me/properties/" : "/properties/") + encodeURIComponent(id), {
        authenticated: own
      });
      if (run !== _loadSequenceRef.current) return;
      const value = own ? result.property : result;
      if (!own && !isPublicProperty(value)) throw Object.assign(Error(), {
        status: 404
      });
      property.set(value);

      if (!own) api("/properties/" + encodeURIComponent(id) + "/points-of-interest", {
        authenticated: false
      }).then(items => {
        if (run === _loadSequenceRef.current) pois.set(items);
      }).catch(() => {
        if (run === _loadSequenceRef.current) state.edit(draftValue => draftValue["notice"] = "Chưa tải được tiện ích xung quanh.");
      });
    } catch (e) {
      if (run === _loadSequenceRef.current) {
        state.edit(draftValue => draftValue["notFound"] = e.status === 404 || e.status === 400);
        state.edit(draftValue => draftValue["error"] = state.getSnapshot().notFound ? "Tin đăng không tồn tại hoặc không còn được công khai." : errorText(e));
      }
    } finally {
      if (run === _loadSequenceRef.current) state.edit(draftValue => draftValue["busy"] = false);
    }
  }
  async function messageOwner() {
    if (!session.getSnapshot().token) return _routerLatest.current.push("/login");
    state.edit(draftValue => draftValue["busy"] = true);
    state.edit(draftValue => draftValue["error"] = "");
    try {
      const c = await api("/conversations", {
        method: "POST",
        body: {
          propertyId: _routeLatest.current.params.id
        }
      });
      await _routerLatest.current.push({
        path: "/account/messages",
        query: {
          conversation: c.id
        }
      });
    } catch (e) {
      state.edit(draftValue => draftValue["error"] = errorText(e));
    } finally {
      state.edit(draftValue => draftValue["busy"] = false);
    }
  }
  async function toggleFavorite() {
    if (!session.getSnapshot().token) return _routerLatest.current.push("/login");
    try {
      await api("/users/me/saved-properties/" + _routeLatest.current.params.id, {
        method: isFavorite.getSnapshot() ? "DELETE" : "PUT"
      });
      isFavorite.set(!isFavorite.getSnapshot());
    } catch (e) {
      state.edit(draftValue => draftValue["error"] = errorText(e));
    }
  }
  const _watched = (() => [_routeLatest.current.params.id, _routeLatest.current.query.own])();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = load(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => () => (() => {
    _loadSequenceRef.current++;
    closeGallery();
  })(), []);
  return {
    ...inputProps,
    session: session.getSnapshot(),
    mapUrl,
    locationLabel,
    formatPostDate,
    copiedShareLink: copiedShareLink.getSnapshot(),
    shareListing,
    isLandProperty: getIsLandProperty(),
    route,
    router,
    state: state.getSnapshot(),
    property: property.getSnapshot(),
    revealedContact: revealedContact.getSnapshot(),
    isFavorite: isFavorite.getSnapshot(),
    showGallery: showGallery.getSnapshot(),
    currentImageIndex: currentImageIndex.getSnapshot(),
    listing: getListing(),
    listingId: getListingId(),
    images: getImages(),
    galleryDialog,
    openGallery,
    closeGallery,
    nextImage,
    prevImage,
    selectImage,
    goMap,
    handleBack,
    load,
    messageOwner,
    askAboutProperty,
    toggleFavorite,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateRevealedContactValue: revealedContact.set
  };
}
export default React.forwardRef(function ListingDetailView(props, ref) {
  const view = useListingDetailViewState(props, ref);
  return <><div data-ui-view="ListingDetailView" data-sp-4f294819="" {...view.rootAttributes} className={classNames(["min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)] antialiased selection:bg-[var(--ui-soft)] selection:text-brand-navy pb-24 lg:pb-16 font-sans", view.rootAttributes.className])}>
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-5" data-sp-4f294819="">
        <ResourceState state={{
          ...view.state,
          load: view.load
        }} data-sp-4f294819="" />
        <div className="flex flex-wrap items-center justify-between gap-3 mb-5" data-sp-4f294819="">
          <div className="flex items-center gap-3" data-sp-4f294819="">
            <button type="button" onClick={$event => {
              return view.handleBack?.($event);
            }} className="inline-flex items-center gap-2 px-3.5 py-2 rounded-full bg-brand-card text-[var(--ui-accent)] border border-brand-line shadow-2xs hover:bg-brand-card hover:border-[var(--ui-border)]/40 transition-all duration-150 cursor-pointer text-xs font-bold group" title="Quay lại" data-sp-4f294819="">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="transition-transform group-hover:-translate-x-0.5" data-sp-4f294819="">
                <line x1="19" y1="12" x2="5" y2="12" data-sp-4f294819="" />
                <polyline points="12 19 5 12 12 5" data-sp-4f294819="" />
              </svg>
              <span data-sp-4f294819="">
                {"Quay lại"}
              </span>
            </button>
            <nav aria-label="Breadcrumb" className="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-card border border-brand-line shadow-2xs text-xs font-medium text-brand-muted" data-sp-4f294819="">
              <SiteLink to="/" className="hover:text-[var(--ui-accent)] flex items-center gap-1.5 transition" data-sp-4f294819="">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" data-sp-4f294819="" />
                  <polyline points="9 22 9 12 15 12 15 22" data-sp-4f294819="" />
                </svg>
                <span data-sp-4f294819="">
                  {"Trang chủ"}
                </span>
              </SiteLink>
              <span className="text-brand-navy" data-sp-4f294819="">
                {"/"}
              </span>
              <SiteLink to="/listings" className="hover:text-[var(--ui-accent)] transition" data-sp-4f294819="">
                {"Bất động sản Đà Nẵng"}
              </SiteLink>
              <span className="text-brand-navy" data-sp-4f294819="">
                {"/"}
              </span>
              <span className="text-[var(--ui-accent)] font-bold truncate max-w-[240px] flex items-center gap-1.5" data-sp-4f294819="">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--ui-success-bg)] animate-pulse" data-sp-4f294819="" />{" "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property?.district ? view.property.district + ", Đà Nẵng" : "Chi tiết tin đăng")}
              </span>
            </nav>
          </div>
          <div className="flex items-center gap-2" data-sp-4f294819="">
            <button type="button" onClick={$event => {
              return view.shareListing?.($event);
            }} className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-brand-card border border-brand-line shadow-2xs hover:bg-brand-card text-brand-muted text-xs font-semibold transition cursor-pointer" title={view.copiedShareLink ? "Đã sao chép link!" : "Chia sẻ tin đăng"} data-sp-4f294819="">
              {view.copiedShareLink ? <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-[var(--ui-success-text)]" data-sp-4f294819="">
                  <polyline points="20 6 9 17 4 12" data-sp-4f294819="" />
                </svg> : <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                  <circle cx="18" cy="5" r="3" data-sp-4f294819="" />
                  <circle cx="6" cy="12" r="3" data-sp-4f294819="" />
                  <circle cx="18" cy="19" r="3" data-sp-4f294819="" />
                  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" data-sp-4f294819="" />
                  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" data-sp-4f294819="" />
                </svg>}
              <span data-sp-4f294819="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.copiedShareLink ? "Đã chép link" : "Chia sẻ")}
              </span>
            </button>
            <button type="button" onClick={$event => {
              return view.toggleFavorite?.($event);
            }} className={classNames(["inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-brand-card border shadow-2xs text-xs font-semibold transition cursor-pointer", view.isFavorite ? "text-[var(--ui-error-text)] border-[var(--ui-error-border)] bg-[var(--ui-error-bg)]/50" : "text-brand-muted border-brand-line hover:bg-brand-card"])} title="Lưu tin yêu thích" data-sp-4f294819="">
              <svg width="13" height="13" viewBox="0 0 24 24" fill={view.isFavorite ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" data-sp-4f294819="" />
              </svg>
              <span data-sp-4f294819="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.isFavorite ? "Đã lưu" : "Lưu tin")}
              </span>
            </button>
            <button type="button" onClick={$event => {
              view.router.push(`/listing/${view.route.params.id}/report`);
            }} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-brand-card border border-brand-line shadow-2xs hover:bg-brand-card text-brand-muted hover:text-[var(--ui-error-text)] text-xs font-medium transition cursor-pointer" title="Báo cáo tin đăng" data-sp-4f294819="">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" data-sp-4f294819="" />
                <line x1="4" y1="22" x2="4" y2="15" data-sp-4f294819="" />
              </svg>
            </button>
          </div>
        </div>
        {!view.property && !view.state.busy ? <div className="rounded-3xl bg-brand-card p-8 text-center border border-brand-line shadow-sm max-w-lg mx-auto my-12" data-sp-4f294819="">
            <div className="w-16 h-16 rounded-full bg-brand-card flex items-center justify-center mx-auto mb-4 text-brand-muted" data-sp-4f294819="">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" data-sp-4f294819="">
                <circle cx="12" cy="12" r="10" data-sp-4f294819="" />
                <line x1="12" y1="8" x2="12" y2="12" data-sp-4f294819="" />
                <line x1="12" y1="16" x2="12.01" y2="16" data-sp-4f294819="" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-[var(--ui-accent)] mb-1" data-sp-4f294819="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.notFound ? "Tin đăng không tồn tại" : "Chưa tải được thông tin")}
            </h3>
            <p className="text-xs text-brand-muted mb-5" data-sp-4f294819="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.notFound ? "Tin đăng này đã bị ẩn, đã giao dịch thành công hoặc không còn công khai." : "Vui lòng kiểm tra lại kết nối mạng hoặc thử lại.")}
            </p>
            <div className="flex items-center justify-center gap-3" data-sp-4f294819="">
              <button type="button" className="px-4 py-2 rounded-xl bg-[var(--ui-soft)] text-brand-navy text-xs font-bold hover:bg-[var(--ui-soft)] transition cursor-pointer" onClick={$event => {
              return view.load?.($event);
            }} data-sp-4f294819="">
                {" Tải lại trang "}
              </button>
              <SiteLink to="/listings" className="px-4 py-2 rounded-xl bg-brand-card text-[var(--ui-accent)] text-xs font-bold hover:bg-brand-card transition" data-sp-4f294819="">
                {" Khám phá danh sách BĐS "}
              </SiteLink>
            </div>
          </div> : null}
        {view.property && !view.state.busy ? <React.Fragment>
            <section className={classNames(["listing-gallery", view.images.length > 1 && "has-secondary"])} data-sp-4f294819="">
              <div className="relative min-h-[300px] lg:min-h-0 rounded-3xl overflow-hidden bg-brand-card border border-brand-line cursor-pointer group shadow-sm" data-sp-4f294819="">
                <PrivateImage src={view.images[0]} alt={view.listing.title} className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.02]" data-sp-4f294819="" />
                <button type="button" className="absolute inset-0 z-[1] cursor-pointer rounded-3xl focus-visible:outline-2 focus-visible:outline-offset-[-4px] focus-visible:outline-brand-gold" aria-label={`Mở thư viện ảnh: ${view.listing.title}`} onClick={event => view.openGallery(0, event.currentTarget)} />
                <div className="absolute inset-0 bg-gradient-to-t from-brand-cream/60 via-transparent to-brand-cream/20 pointer-events-none" data-sp-4f294819="" />
                <div className="absolute top-4 left-4 flex flex-wrap items-center gap-2 z-10 pointer-events-none" data-sp-4f294819="">
                  <span className="px-3 py-1 rounded-full bg-[var(--ui-soft)]/85 backdrop-blur-md text-brand-navy text-[11px] font-bold border border-brand-line/20 shadow-xs flex items-center gap-1.5" data-sp-4f294819="">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--ui-success-bg)] animate-pulse" data-sp-4f294819="" />
                    {" Ảnh do người đăng cung cấp "}
                  </span>
                </div>
                <div className="absolute bottom-4 left-4 z-10 pointer-events-none" data-sp-4f294819="">
                  <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-brand-card/90 backdrop-blur-md text-[var(--ui-accent)] font-bold text-xs shadow-md border border-brand-line/40" data-sp-4f294819="">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" data-sp-4f294819="" />
                      <circle cx="12" cy="13" r="4" data-sp-4f294819="" />
                    </svg>
                    <span data-sp-4f294819="">
                      {"Xem "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.images.length)}
                      {" ảnh chụp"}
                    </span>
                  </div>
                </div>
                <button onClick={$event => {
                $event.stopPropagation();
                return view.toggleFavorite?.($event);
              }} className={classNames(["absolute top-4 right-4 w-10 h-10 rounded-full bg-brand-card/90 backdrop-blur-md shadow-md flex items-center justify-center transition-all duration-150 active:scale-90 z-20 cursor-pointer hover:bg-brand-card", view.isFavorite ? "text-[var(--ui-error-text)]" : "text-[var(--ui-accent)]"])} title="Lưu tin" data-sp-4f294819="">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill={view.isFavorite ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" data-sp-4f294819="" />
                  </svg>
                </button>
              </div>
              {view.images.length > 1 ? <div className="hidden lg:grid grid-rows-2 gap-3.5 h-full" data-sp-4f294819="">
                  <div onClick={$event => {
                  view.openGallery(1, $event.currentTarget);
              }} role="button" tabIndex={0} aria-label="Mở ảnh bất động sản 2" onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); view.openGallery(1, event.currentTarget); } }} className="relative rounded-3xl overflow-hidden bg-brand-card border border-brand-line cursor-pointer group shadow-2xs" data-sp-4f294819="">
                    <PrivateImage src={view.images[1]} alt="Ảnh bất động sản 2" className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" data-sp-4f294819="" />
                    <div className="absolute inset-0 bg-brand-cream/10 group-hover:bg-transparent transition" data-sp-4f294819="" />
                  </div>
                  <div className="grid grid-cols-2 gap-3.5 h-full" data-sp-4f294819="">
                    {view.images.length > 2 ? <div onClick={$event => {
                  view.openGallery(2, $event.currentTarget);
                }} role="button" tabIndex={0} aria-label="Mở ảnh bất động sản 3" onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); view.openGallery(2, event.currentTarget); } }} className="relative rounded-3xl overflow-hidden bg-brand-card border border-brand-line cursor-pointer group shadow-2xs" data-sp-4f294819="">
                        <PrivateImage src={view.images[2]} alt="Ảnh bất động sản 3" className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" data-sp-4f294819="" />
                        <div className="absolute inset-0 bg-brand-cream/10 group-hover:bg-transparent transition" data-sp-4f294819="" />
                      </div> : null}
                    {view.images.length > 3 ? <div onClick={$event => {
                  view.openGallery(3, $event.currentTarget);
                }} role="button" tabIndex={0} aria-label="Mở các ảnh bất động sản còn lại" onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); view.openGallery(3, event.currentTarget); } }} className="relative rounded-3xl overflow-hidden bg-[var(--ui-soft)] border border-brand-line cursor-pointer group shadow-2xs" data-sp-4f294819="">
                        <PrivateImage src={view.images[3]} alt="Ảnh bất động sản 4" className="absolute inset-0 w-full h-full object-cover opacity-60 transition-transform duration-500 group-hover:scale-105" data-sp-4f294819="" />
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[var(--ui-soft)]/50 text-brand-navy backdrop-blur-[2px]" data-sp-4f294819="">
                          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mb-1 text-[var(--ui-ink)]" data-sp-4f294819="">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" data-sp-4f294819="" />
                            <circle cx="8.5" cy="8.5" r="1.5" data-sp-4f294819="" />
                            <polyline points="21 15 16 10 5 21" data-sp-4f294819="" />
                          </svg>
                          <span className="text-xs font-black tracking-wide" data-sp-4f294819="">
                            {" +"}
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.images.length - 3)}
                            {" ảnh "}
                          </span>
                        </div>
                      </div> : null}
                  </div>
                </div> : null}
            </section>
            <div className="detail-layout grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8 mt-8 items-start" data-sp-4f294819="">
              <div className="space-y-6" data-sp-4f294819="">
                <section className="detail-overview bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs" data-sp-4f294819="">
                  <div className="flex flex-wrap items-center gap-2 mb-4" data-sp-4f294819="">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[var(--ui-surface)] text-[var(--ui-accent)] border border-[var(--ui-border)]" data-sp-4f294819="">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--ui-soft)]" data-sp-4f294819="" />{" "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.type || "Bất động sản")}
                    </span>
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-brand-card text-brand-muted" data-sp-4f294819="">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                        <circle cx="12" cy="12" r="10" data-sp-4f294819="" />
                        <polyline points="12 6 12 12 16 14" data-sp-4f294819="" />
                      </svg>{" "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property?.transactionType === "RENT" ? "Cho thuê" : "Đang bán")}
                    </span>
                    <span className="detail-unverified inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[var(--ui-success-bg)] text-[var(--ui-success-text)] border border-[var(--ui-success-border)]" data-sp-4f294819="">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" data-sp-4f294819="">
                        <circle cx="12" cy="12" r="9" />
                        <path d="M12 7v6m0 3h.01" />
                      </svg>
                      {" Chưa xác minh thực địa "}
                    </span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-[var(--ui-accent)] tracking-tight leading-snug" data-sp-4f294819="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.title)}
                  </h1>
                  <div className="flex items-start gap-2 mt-3 text-brand-muted text-xs sm:text-sm" data-sp-4f294819="">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--ui-accent)] shrink-0 mt-0.5" data-sp-4f294819="">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" data-sp-4f294819="" />
                      <circle cx="12" cy="10" r="3" data-sp-4f294819="" />
                    </svg>
                    <span className="font-medium leading-relaxed" data-sp-4f294819="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.location)}
                    </span>
                  </div>
                  <div className="detail-price mt-6 p-5 sm:p-6 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] flex flex-col sm:flex-row sm:items-center justify-between gap-4" data-sp-4f294819="">
                    <div data-sp-4f294819="">
                      <p className="text-[11px] font-bold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-4f294819="">
                        {"Mức giá chào niêm yết"}
                      </p>
                      <div className="flex flex-wrap items-baseline gap-3 mt-1" data-sp-4f294819="">
                        <span className="text-3xl sm:text-4xl font-black text-[var(--ui-muted)] tracking-tight" data-sp-4f294819="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.price)}
                        </span>
                        <span className="px-2.5 py-1 rounded-lg bg-brand-card border border-brand-line text-xs font-bold text-[var(--ui-accent)] shadow-2xs" data-sp-4f294819="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.pricePerM2)}
                        </span>
                      </div>
                    </div>
                    <div className="sm:text-right border-t sm:border-t-0 pt-3 sm:pt-0 border-brand-line" data-sp-4f294819="">
                      <span className="detail-source-price inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--ui-success-text)] bg-[var(--ui-success-bg)] px-3 py-1.5 rounded-full border border-[var(--ui-success-border)]" data-sp-4f294819="">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" data-sp-4f294819="">
                          <circle cx="12" cy="12" r="9" />
                          <path d="M12 11v6m0-10h.01" />
                        </svg>
                        {" Giá chào do người đăng cung cấp "}
                      </span>
                      <p className="text-[11px] text-brand-muted mt-1" data-sp-4f294819="">
                        {"Không thu phí người mua / xem nhà"}
                      </p>
                    </div>
                  </div>
                  <div className="detail-specs grid grid-cols-2 sm:grid-cols-4 gap-3.5 mt-6 pt-6 border-t border-brand-line" data-sp-4f294819="">
                    <div className="bg-brand-card hover:bg-brand-card hover:border-[var(--ui-border)]/30 border border-brand-line rounded-2xl p-4 transition-all duration-150" data-sp-4f294819="">
                      <div className="w-9 h-9 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center mb-2.5 border border-brand-line" data-sp-4f294819="">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                          <path d="M21 3H3v18h18V3z" data-sp-4f294819="" />
                          <path d="M3 9h18" data-sp-4f294819="" />
                          <path d="M9 21V9" data-sp-4f294819="" />
                        </svg>
                      </div>
                      <p className="text-[11px] font-semibold text-brand-muted uppercase tracking-wider" data-sp-4f294819="">
                        {"Diện tích"}
                      </p>
                      <p className="text-sm font-extrabold text-[var(--ui-accent)] truncate mt-0.5" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.area)}
                      </p>
                    </div>
                    <div className="bg-brand-card hover:bg-brand-card hover:border-[var(--ui-border)]/30 border border-brand-line rounded-2xl p-4 transition-all duration-150" data-sp-4f294819="">
                      <div className="w-9 h-9 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center mb-2.5 border border-brand-line" data-sp-4f294819="">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                          <circle cx="12" cy="12" r="10" data-sp-4f294819="" />
                          <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" data-sp-4f294819="" />
                        </svg>
                      </div>
                      <p className="text-[11px] font-semibold text-brand-muted uppercase tracking-wider" data-sp-4f294819="">
                        {"Hướng nhà"}
                      </p>
                      <p className="text-sm font-extrabold text-[var(--ui-accent)] truncate mt-0.5" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property?.direction || "Chưa cung cấp")}
                      </p>
                    </div>
                    <div className="bg-brand-card hover:bg-brand-card hover:border-[var(--ui-border)]/30 border border-brand-line rounded-2xl p-4 transition-all duration-150" data-sp-4f294819="">
                      <div className="w-9 h-9 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center mb-2.5 border border-brand-line" data-sp-4f294819="">
                        {view.isLandProperty ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" data-sp-4f294819="" />
                            <polyline points="14 2 14 8 20 8" data-sp-4f294819="" />
                            <line x1="16" y1="13" x2="8" y2="13" data-sp-4f294819="" />
                            <line x1="16" y1="17" x2="8" y2="17" data-sp-4f294819="" />
                          </svg> : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                            <path d="M2 4v16" data-sp-4f294819="" />
                            <path d="M2 8h18a2 2 0 0 1 2 2v10" data-sp-4f294819="" />
                            <path d="M2 17h20" data-sp-4f294819="" />
                            <path d="M6 8v9" data-sp-4f294819="" />
                          </svg>}
                      </div>
                      <p className="text-[11px] font-semibold text-brand-muted uppercase tracking-wider" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.isLandProperty ? "Pháp lý" : "Phòng ngủ")}
                      </p>
                      <p className="text-sm font-extrabold text-[var(--ui-accent)] truncate mt-0.5" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.isLandProperty ? "Chưa xác minh pháp lý" : view.property?.bedrooms != null ? view.property.bedrooms + " phòng ngủ" : "Chưa cung cấp")}
                      </p>
                    </div>
                    <div className="bg-brand-card hover:bg-brand-card hover:border-[var(--ui-border)]/30 border border-brand-line rounded-2xl p-4 transition-all duration-150" data-sp-4f294819="">
                      <div className="w-9 h-9 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center mb-2.5 border border-brand-line" data-sp-4f294819="">
                        {view.isLandProperty ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                            <rect x="2" y="5" width="20" height="14" rx="2" data-sp-4f294819="" />
                            <line x1="2" y1="10" x2="22" y2="10" data-sp-4f294819="" />
                          </svg> : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                            <path d="M9 6h6" data-sp-4f294819="" />
                            <path d="M12 6v6" data-sp-4f294819="" />
                            <circle cx="12" cy="14" r="2" data-sp-4f294819="" />
                            <path d="M4 21h16a2 2 0 0 0 2-2v-5a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2z" data-sp-4f294819="" />
                          </svg>}
                      </div>
                      <p className="text-[11px] font-semibold text-brand-muted uppercase tracking-wider" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.isLandProperty ? "Lộ giới" : "Phòng tắm")}
                      </p>
                      <p className="text-sm font-extrabold text-[var(--ui-accent)] truncate mt-0.5" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.isLandProperty ? "Chưa có dữ liệu đường" : view.property?.bathrooms != null ? view.property.bathrooms + " phòng tắm" : "Chưa cung cấp")}
                      </p>
                    </div>
                  </div>
                </section>
                <section className="rounded-3xl p-6 border border-brand-line bg-brand-card" data-sp-4f294819="">
                  <h2 className="font-bold text-sm mb-2">Thông tin cần đối chiếu</h2>
                  <p className="text-sm text-brand-muted">Duyệt hiển thị tin không phải xác nhận pháp lý, thực địa hoặc an toàn giao dịch. Hãy đối chiếu hồ sơ gốc và tình trạng tài sản.</p>
                </section>
                <CoordinateStatusPanel coordinate={view.property?.coordinate} />
                <PrePurchaseChecks property={view.property} />
                <section className="bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs" data-sp-4f294819="">
                  <h2 className="text-base font-bold text-[var(--ui-accent)] mb-4 flex items-center gap-2" data-sp-4f294819="">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--ui-accent)]" data-sp-4f294819="">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" data-sp-4f294819="" />
                      <polyline points="14 2 14 8 20 8" data-sp-4f294819="" />
                      <line x1="16" y1="13" x2="8" y2="13" data-sp-4f294819="" />
                      <line x1="16" y1="17" x2="8" y2="17" data-sp-4f294819="" />
                    </svg>
                    <span data-sp-4f294819="">
                      {"Mô tả chi tiết bất động sản"}
                    </span>
                  </h2>
                  <div className="detail-description text-xs sm:text-sm text-brand-muted leading-relaxed space-y-3 whitespace-pre-line font-normal" data-sp-4f294819="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property?.description || view.listing.description1)}
                  </div>
                </section>
                {view.property.declaredAmenities?.length ? <section className="detail-amenities bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs" data-sp-4f294819="">
                    <h2 className="text-base font-bold text-[var(--ui-accent)] mb-4 flex items-center gap-2" data-sp-4f294819="">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--ui-accent)]" data-sp-4f294819="">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" data-sp-4f294819="" />
                      </svg>
                      <span data-sp-4f294819="">
                        {"Tiện ích & Đặc điểm nổi bật"}
                      </span>
                    </h2>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3" data-sp-4f294819="">
                      {((items, render) => typeof items === "number" ? Array.from({
                    length: Math.max(0, items)
                  }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.property.declaredAmenities, amenity => <div key={amenity} className="flex items-center gap-2.5 p-3 rounded-2xl bg-brand-card border border-brand-line text-xs font-semibold text-[var(--ui-accent)] hover:border-[var(--ui-border)]/40 hover:bg-brand-card transition-all shadow-2xs" data-sp-4f294819="">
                          <span className="w-6 h-6 rounded-lg bg-[var(--ui-success-bg)] text-[var(--ui-success-text)] flex items-center justify-center text-xs shrink-0 font-bold" data-sp-4f294819="">
                            {" ✓ "}
                          </span>
                          <span className="truncate" data-sp-4f294819="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(amenity)}
                          </span>
                        </div>)}
                    </div>
                  </section> : null}
                <section className="bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs" data-sp-4f294819="">
                  <div className="flex items-center justify-between mb-5" data-sp-4f294819="">
                    <h2 className="text-base font-bold text-[var(--ui-accent)] flex items-center gap-2" data-sp-4f294819="">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--ui-accent)]" data-sp-4f294819="">
                        <circle cx="12" cy="12" r="10" data-sp-4f294819="" />
                        <path d="M16.2 7.8l-2 6.3-6.4 2 2-6.3z" data-sp-4f294819="" />
                      </svg>
                      <span data-sp-4f294819="">
                        {"Liên kết vùng & Tiện ích lân cận (Đà Nẵng)"}
                      </span>
                    </h2>
                    <span className="text-xs font-semibold text-brand-muted" data-sp-4f294819="">
                      {"Khoảng cách đường chim bay"}
                    </span>
                  </div>

                </section>
                <ImageAnalysisSection propertyId={view.property?.id} />
                <section className="bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs" data-sp-4f294819="">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4" data-sp-4f294819="">
                    <div data-sp-4f294819="">
                      <h2 className="text-base font-bold text-[var(--ui-accent)] flex items-center gap-2" data-sp-4f294819="">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--ui-accent)]" data-sp-4f294819="">
                          <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" data-sp-4f294819="" />
                          <line x1="8" y1="2" x2="8" y2="18" data-sp-4f294819="" />
                          <line x1="16" y1="6" x2="16" y2="22" data-sp-4f294819="" />
                        </svg>
                        <span data-sp-4f294819="">
                          {"Vị trí trên bản đồ vệ tinh"}
                        </span>
                      </h2>
                      <p className="text-xs text-brand-muted mt-0.5" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.location)}
                      </p>
                    </div>
                    <button type="button" onClick={$event => {
                    return view.goMap?.($event);
                  }} className="px-4 py-2 rounded-xl bg-[var(--ui-soft)] hover:bg-[var(--ui-soft)] text-brand-navy text-xs font-bold shadow-2xs flex items-center gap-1.5 self-start sm:self-center transition cursor-pointer" data-sp-4f294819="">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                        <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" data-sp-4f294819="" />
                      </svg>
                      <span data-sp-4f294819="">
                        {"Mở SmartProp GIS"}
                      </span>
                    </button>
                  </div>
                  <div className="relative rounded-2xl overflow-hidden bg-brand-card border border-brand-line" data-sp-4f294819="">
                    {view.mapUrl(view.property) ? <PropertyExplorer items={[view.property]} selectedId={view.property.id} data-sp-4f294819="" /> : <div className="h-full flex items-center justify-center p-6 text-sm text-brand-muted" data-sp-4f294819="">
                        {" Chưa có vị trí bản đồ cho tin đăng này. "}
                      </div>}
                    <div className="absolute bottom-3 left-3 pointer-events-none" data-sp-4f294819="">
                      <div className="bg-[var(--ui-soft)] text-brand-navy font-bold px-3.5 py-1.5 rounded-full text-xs shadow-lg border border-brand-line/20 flex items-center gap-1.5" data-sp-4f294819="">
                        <span className="w-2 h-2 rounded-full bg-[var(--ui-soft)]" data-sp-4f294819="" />
                        <span data-sp-4f294819="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.price)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <p className="text-[11px] leading-relaxed text-[var(--ui-accent)] mt-3" data-sp-4f294819="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.locationLabel(view.property))}
                    {" · Công cụ tìm địa chỉ: "}
                    <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer" className="underline hover:text-[var(--ui-accent)]" data-sp-4f294819="">
                      {"Geoapify"}
                    </a>
                    {" · "}
                    <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" className="underline hover:text-[var(--ui-accent)]" data-sp-4f294819="">
                      {"© OpenStreetMap contributors"}
                    </a>
                  </p>
                </section>
                <section className="listing-evidence bg-brand-card rounded-3xl p-6 border border-brand-line" data-sp-4f294819="">
                  <h2 className="font-bold mb-3">Giá tham khảo và mức độ xác minh</h2>
                  <p className="text-sm text-brand-muted">Chưa có kết quả định giá cho tin này. Giá đang hiển thị là giá chào của người đăng, không phải giá giao dịch hay kết quả thẩm định.</p>
                  <p className="text-sm text-brand-muted mt-3">Hồ sơ pháp lý và tình trạng thực tế của tài sản chưa được xác minh trong dữ liệu công khai.</p>
                  <SiteLink to="/valuation" className="mt-4 inline-block underline text-sm">Mở công cụ ước tính giá</SiteLink>
                </section>
              </div>
              <aside className="listing-detail-sidebar space-y-5 lg:sticky lg:top-5" data-sp-4f294819="">
                <section className="bg-brand-card rounded-3xl p-6 shadow-sm border border-brand-line relative" data-sp-4f294819="">
                  <div className="mb-5 pb-4 border-b border-brand-line">
                    <h2 className="font-bold text-base">Người đăng tin</h2>
                    <p className="mt-2 text-sm text-brand-muted">{view.revealedContact?.contactName || "Tên liên hệ chưa được cung cấp công khai."}</p>
                    <p className="mt-1 text-xs text-brand-muted">Thông tin liên hệ được lấy từ tin đăng khi bạn chọn xem liên hệ.</p>
                  </div>
                  {view.route.query.own === "1" || view.session.user?.role === "ADMIN" ? <SiteLink to={"/account/properties/" + view.listingId + "/legal-documents"} className="mb-3 block text-xs underline font-semibold text-[var(--ui-accent)] hover:text-[var(--ui-accent)]" data-sp-4f294819="">
                      {" Quản lý hồ sơ pháp lý riêng "}
                    </SiteLink> : null}
                  {view.property?.status === "PUBLISHED" && <button type="button" className="listing-ai-action" onClick={view.askAboutProperty}>Hỏi AI về căn này</button>}
                  <ContactPanel key={view.listingId} propertyId={view.listingId} onRevealed={$event => {
                  return (data => view.updateRevealedContactValue(data))?.($event);
                }} data-sp-4f294819="" />
                  <button type="button" className="mt-3 w-full rounded-2xl border border-brand-line hover:border-[var(--ui-border)]/40 hover:bg-brand-card py-3 px-4 text-xs font-bold text-[var(--ui-accent)] transition flex items-center justify-center gap-2 cursor-pointer shadow-2xs" disabled={view.state.busy} onClick={$event => {
                  return view.messageOwner?.($event);
                }} data-sp-4f294819="">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" data-sp-4f294819="" />
                    </svg>
                    <span data-sp-4f294819="">
                      {"Nhắn tin tư vấn trực tiếp"}
                    </span>
                  </button>
                  <div className="mt-4 pt-3.5 border-t border-brand-line flex items-center gap-2 text-[11px] text-brand-muted" data-sp-4f294819="">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--ui-warning-text)] shrink-0" data-sp-4f294819="">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" data-sp-4f294819="" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" data-sp-4f294819="" />
                    </svg>
                    <span data-sp-4f294819="">
                      {"Giao dịch an toàn, không cọc trước khi xác minh"}
                    </span>
                  </div>
                </section>
                <section className="bg-brand-card rounded-3xl p-6 shadow-sm border border-brand-line" data-sp-4f294819="">
                  <div className="flex items-center justify-between mb-4 pb-3 border-b border-brand-line" data-sp-4f294819="">
                    <h3 className="text-sm font-bold text-[var(--ui-accent)] flex items-center gap-2" data-sp-4f294819="">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--ui-accent)]" data-sp-4f294819="">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" data-sp-4f294819="" />
                        <polyline points="14 2 14 8 20 8" data-sp-4f294819="" />
                      </svg>
                      <span data-sp-4f294819="">
                        {"Thông tin niêm yết"}
                      </span>
                    </h3>
                    <span className="detail-display-status inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[var(--ui-success-bg)] text-[var(--ui-success-text)] border border-[var(--ui-success-border)]" data-sp-4f294819="">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--ui-success-bg)] animate-pulse" data-sp-4f294819="" />
                      {" Đang hiển thị "}
                    </span>
                  </div>
                  <div className="space-y-3.5 text-xs" data-sp-4f294819="">
                    <div className="flex items-center justify-between py-0.5" data-sp-4f294819="">
                      <span className="text-brand-muted flex items-center gap-2" data-sp-4f294819="">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-brand-muted" data-sp-4f294819="">
                          <line x1="4" y1="9" x2="20" y2="9" data-sp-4f294819="" />
                          <line x1="4" y1="15" x2="20" y2="15" data-sp-4f294819="" />
                          <line x1="10" y1="3" x2="8" y2="21" data-sp-4f294819="" />
                          <line x1="16" y1="3" x2="14" y2="21" data-sp-4f294819="" />
                        </svg>
                        <span data-sp-4f294819="">
                          {"Mã tin"}
                        </span>
                      </span>
                      <span className="font-bold text-[var(--ui-accent)] font-mono" data-sp-4f294819="">
                        {" #SP-"}
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(String(view.property?.id || "").slice(-6).toUpperCase() || "654321")}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-0.5" data-sp-4f294819="">
                      <span className="text-brand-muted flex items-center gap-2" data-sp-4f294819="">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-brand-muted" data-sp-4f294819="">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" data-sp-4f294819="" />
                          <line x1="16" y1="2" x2="16" y2="6" data-sp-4f294819="" />
                          <line x1="8" y1="2" x2="8" y2="6" data-sp-4f294819="" />
                          <line x1="3" y1="10" x2="21" y2="10" data-sp-4f294819="" />
                        </svg>
                        <span data-sp-4f294819="">
                          {"Ngày đăng"}
                        </span>
                      </span>
                      <span className="font-semibold text-[var(--ui-accent)]" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.formatPostDate(view.property?.publishedAt || view.property?.createdAt))}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-0.5" data-sp-4f294819="">
                      <span className="text-brand-muted flex items-center gap-2" data-sp-4f294819="">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-brand-muted" data-sp-4f294819="">
                          <circle cx="12" cy="12" r="10" data-sp-4f294819="" />
                          <polyline points="12 6 12 12 16 14" data-sp-4f294819="" />
                        </svg>
                        <span data-sp-4f294819="">
                          {"Hình thức"}
                        </span>
                      </span>
                      <span className="font-semibold text-[var(--ui-accent)]" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property?.transactionType === "RENT" ? "Cho thuê BĐS" : "Bán BĐS")}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-0.5" data-sp-4f294819="">
                      <span className="text-brand-muted flex items-center gap-2" data-sp-4f294819="">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-brand-muted" data-sp-4f294819="">
                          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" data-sp-4f294819="" />
                        </svg>
                        <span data-sp-4f294819="">
                          {"Pháp lý"}
                        </span>
                      </span>
                      <span className="detail-legal-pending font-semibold text-[var(--ui-success-text)] bg-[var(--ui-success-bg)] px-2 py-0.5 rounded border border-[var(--ui-success-border)]" data-sp-4f294819="">
                        {" Chưa có bằng chứng pháp lý công khai "}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-0.5" data-sp-4f294819="">
                      <span className="text-brand-muted flex items-center gap-2" data-sp-4f294819="">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-brand-muted" data-sp-4f294819="">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" data-sp-4f294819="" />
                          <circle cx="12" cy="12" r="3" data-sp-4f294819="" />
                        </svg>
                        <span data-sp-4f294819="">
                          {"Lượt xem"}
                        </span>
                      </span>
                      <span className="font-semibold text-[var(--ui-accent)]" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))("Chưa có thống kê")}

                      </span>
                    </div>
                  </div>
                  <div className="detail-source-note mt-4 pt-3.5 border-t border-brand-line flex items-center gap-2 text-[11px] text-brand-muted bg-brand-card -mx-2 -mb-2 p-3 rounded-2xl border border-brand-line" data-sp-4f294819="">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0" data-sp-4f294819="">
                      <circle cx="12" cy="12" r="9" />
                      <path d="M12 11v6m0-10h.01" />
                    </svg>
                    <span data-sp-4f294819="">
                      {"Thông tin do người đăng cung cấp"}
                    </span>
                  </div>
                </section>
                <section className="bg-brand-card rounded-3xl p-5 shadow-sm border border-brand-line" data-sp-4f294819="">
                  <p className="text-xs text-brand-muted leading-relaxed" data-sp-4f294819="">
                    {" Bạn phát hiện tin đăng này sai vị trí, sai giá hoặc hình ảnh không khớp thực tế? "}
                  </p>
                  <button type="button" onClick={$event => {
                  view.router.push(`/listing/${view.route.params.id}/report`);
                }} className="mt-3 inline-flex items-center gap-1.5 text-xs font-bold text-[var(--ui-muted)] hover:underline cursor-pointer" data-sp-4f294819="">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" data-sp-4f294819="" />
                      <line x1="4" y1="22" x2="4" y2="15" data-sp-4f294819="" />
                    </svg>
                    <span data-sp-4f294819="">
                      {"Báo cáo tin đăng vi phạm"}
                    </span>
                  </button>
                </section>
              </aside>
            </div>
          </React.Fragment> : null}
      </div>
      {view.property && !view.state.busy ? <div className="listing-mobile-actions lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-brand-card/95 backdrop-blur-md border-t border-brand-line px-4 py-3 flex items-center justify-between gap-3 shadow-lg" data-sp-4f294819="">
          <div className="min-w-0" data-sp-4f294819="">
            <p className="text-[10px] text-brand-muted font-bold uppercase" data-sp-4f294819="">
              {"Giá niêm yết"}
            </p>
            <p className="text-base font-black text-[var(--ui-muted)] truncate" data-sp-4f294819="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.price)}
            </p>
          </div>
          <div className="flex items-center gap-2" data-sp-4f294819="">
            <button type="button" onClick={$event => {
            return view.messageOwner?.($event);
          }} className="px-3.5 py-2.5 rounded-xl border border-brand-line text-[var(--ui-accent)] text-xs font-bold flex items-center gap-1.5 active:scale-95 transition" data-sp-4f294819="">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" data-sp-4f294819="" />
              </svg>
              <span data-sp-4f294819="">
                {"Nhắn tin"}
              </span>
            </button>
            {view.revealedContact?.contactPhone ? <a href={"tel:" + view.revealedContact.contactPhone.replace(/[^0-9]/g, "")} className="px-4 py-2.5 rounded-xl bg-[var(--ui-soft)] text-brand-navy text-xs font-bold flex items-center gap-1.5 active:scale-95 transition shadow-sm" data-sp-4f294819="">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-4f294819="">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" data-sp-4f294819="" />
                </svg>
                <span data-sp-4f294819="">
                  {"Gọi ngay"}
                </span>
              </a> : null}
          </div>
        </div> : null}{createPortal(<>
        {view.showGallery ? <div ref={view.galleryDialog} role="dialog" aria-modal="true" aria-label={`Thư viện ảnh: ${view.listing.title}`} tabIndex={-1} className="signature-gallery fixed inset-0 z-[9999] bg-brand-cream/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-5" onClick={$event => {
          if ($event.target !== $event.currentTarget) return;
          return view.closeGallery?.($event);
        }} data-sp-4f294819="">
            <div className="relative w-full max-w-[1500px] h-[95vh] bg-[var(--ui-soft)] rounded-3xl overflow-hidden flex flex-col shadow-2xl border border-brand-line/10" data-sp-4f294819="">
              <div className="flex items-center justify-between gap-4 px-6 py-4 text-brand-navy border-b border-brand-line/10" data-sp-4f294819="">
                <div className="flex items-center gap-4 min-w-0" data-sp-4f294819="">
                  <div className="min-w-0" data-sp-4f294819="">
                    <h2 className="text-xs sm:text-sm font-bold truncate text-brand-navy" data-sp-4f294819="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.title)}
                    </h2>
                    <p className="text-[11px] text-brand-navy/50 truncate mt-0.5" data-sp-4f294819="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.location)}
                    </p>
                  </div>
                  <div className="hidden sm:block px-3 py-1 rounded-full bg-brand-card/10 text-xs text-brand-navy/80 font-bold whitespace-nowrap" data-sp-4f294819="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentImageIndex + 1)}
                    {" / "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.images.length)}
                    {" ảnh "}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0" data-sp-4f294819="">
                  <button type="button" onClick={$event => {
                  return view.closeGallery?.($event);
                }} className="w-9 h-9 rounded-full bg-brand-card/10 border border-brand-line/10 flex items-center justify-center text-brand-navy/70 hover:bg-brand-card/20 hover:text-brand-navy transition cursor-pointer" title="Đóng (Esc)" data-sp-4f294819="">
                    {" ✕ "}
                  </button>
                </div>
              </div>
              <div className="relative flex-1 min-h-0 flex items-center justify-center px-4 sm:px-16" data-sp-4f294819="">
                <PrivateImage src={view.images[view.currentImageIndex]} alt={`Ảnh ${view.currentImageIndex + 1} của ${view.listing.title}`} className="w-full h-full object-contain rounded-2xl" data-sp-4f294819="" />
                <button type="button" onClick={$event => {
                return view.prevImage?.($event);
              }} className="absolute left-3 sm:left-6 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-brand-cream/50 border border-brand-line/10 text-brand-navy text-2xl flex items-center justify-center hover:bg-brand-cream/80 hover:scale-105 transition cursor-pointer" aria-label="Ảnh trước" data-sp-4f294819="">
                  {" ‹ "}
                </button>
                <button type="button" onClick={$event => {
                return view.nextImage?.($event);
              }} className="absolute right-3 sm:right-6 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-brand-cream/50 border border-brand-line/10 text-brand-navy text-2xl flex items-center justify-center hover:bg-brand-cream/80 hover:scale-105 transition cursor-pointer" aria-label="Ảnh tiếp theo" data-sp-4f294819="">
                  {" › "}
                </button>
                <div className="sm:hidden absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-brand-cream/70 text-brand-navy text-xs font-bold" data-sp-4f294819="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentImageIndex + 1)}
                  {" / "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.images.length)}
                </div>
              </div>
              <div className="px-6 py-4 border-t border-brand-line/10 bg-[var(--ui-soft)]/80" data-sp-4f294819="">
                <div className="flex gap-2.5 overflow-x-auto pb-1 gallery-scroll" data-sp-4f294819="">
                  {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.images, (image, index) => <button key={index} type="button" onClick={$event => {
                  view.selectImage(index);
                }} className={classNames(["relative shrink-0 w-[100px] sm:w-[120px] h-[64px] sm:h-[74px] rounded-xl overflow-hidden border-2 transition cursor-pointer", view.currentImageIndex === index ? "border-[var(--ui-border)] opacity-100 ring-2 ring-[var(--ui-border)]/50" : "border-transparent opacity-50 hover:opacity-100"])} data-sp-4f294819="">
                      <PrivateImage src={image} alt={`Ảnh thu nhỏ ${index + 1}`} className="w-full h-full object-cover" data-sp-4f294819="" />
                      <div className="absolute bottom-1 left-1 px-1.5 py-0.2 rounded-full bg-brand-cream/70 text-brand-navy text-[9px] font-bold" data-sp-4f294819="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(index + 1)}
                      </div>
                    </button>)}
                </div>
              </div>
            </div>
          </div> : null}
      </>, document.body)}</div></>;
});
