import '../property/ListingsCardsPolish.css'
import { classNames } from '../../shared/lib/ui.js'
import { createStateStore, stateKey } from '../../shared/state/createStateStore.js'
import React, { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { SiteLink, useAppNavigation, useRouteState } from '../../app/navigation.jsx'
import { api } from '../auth/api.js'
import {
  DEFAULT_DISTRICT_SLUG,
  DISTRICT_LIST,
  DISTRICT_PROFILES,
  getDistrictProfile,
} from './marketData.js'
import {
  formatCount,
  formatPerSqm,
  isInsufficient,
  loadMarketAnalytics,
} from './marketAnalytics.js'
import { useComparison } from '../../shared/hooks/useComparison.js'
import PriceTrendChart from './PriceTrendChart.jsx'
import BrowseTileMap from '../map/BrowseTileMap.jsx'
import ListingCard from '../property/ListingCard.jsx'
import TopSearchedAreas from './TopSearchedAreas.jsx'
import './MarketInsightsView.css'

function formatSegmentMedian(stat, loading, error) {
  if (loading) return 'Đang tải…'
  if (error) return 'Tạm chưa khả dụng'
  if (!stat || isInsufficient(stat) || stat.medianPricePerSqm == null) {
    const n = stat?.count ?? 0
    return `Chưa đủ mẫu (n = ${formatCount(n)})`
  }
  return formatPerSqm(stat.medianPricePerSqm)
}

function useMarketInsightsViewState(inputProps) {
  const route = useRouteState()
  const routeLatest = useRef(route)
  routeLatest.current = route
  const router = useAppNavigation()
  const routerLatest = useRef(router)
  routerLatest.current = router
  const compare = useComparison()

  const routeDistrictParam = route.params?.district ? String(route.params.district).trim() : ''
  const effectiveSlug = routeDistrictParam || DEFAULT_DISTRICT_SLUG
  const currentDistrict = getDistrictProfile(effectiveSlug)
  const isUnknownDistrict = Boolean(routeDistrictParam) && currentDistrict === null

  function selectDistrict(slug) {
    routerLatest.current.push({
      path: `/market/${slug}`,
    })
  }

  const [properties] = useState(() => createStateStore([]))
  useSyncExternalStore(properties.subscribe, properties.getSnapshot)
  const [loadingProperties] = useState(() => createStateStore(false))
  useSyncExternalStore(loadingProperties.subscribe, loadingProperties.getSnapshot)
  const [selectedMapPropertyId] = useState(() => createStateStore(null))
  useSyncExternalStore(selectedMapPropertyId.subscribe, selectedMapPropertyId.getSnapshot)

  const [analyticsState] = useState(() =>
    createStateStore({
      loading: false,
      error: '',
      districtData: null,
      cityByDistrict: {},
      segments: { LAND: null, HOUSE: null, APARTMENT: null },
    })
  )
  useSyncExternalStore(analyticsState.subscribe, analyticsState.getSnapshot)

  const loadSeqRef = useRef(0)

  async function loadDistrictEvidence(profile) {
    const seq = ++loadSeqRef.current
    if (!profile) {
      properties.set([])
      selectedMapPropertyId.set(null)
      loadingProperties.set(false)
      analyticsState.set({
        loading: false,
        error: '',
        districtData: null,
        cityByDistrict: {},
        segments: { LAND: null, HOUSE: null, APARTMENT: null },
      })
      return
    }

    loadingProperties.set(true)
    analyticsState.edit((draft) => {
      draft.loading = true
      draft.error = ''
    })

    const districtName = profile.shortName

    const listingsTask = api(`/properties?district=${encodeURIComponent(districtName)}&size=6&limit=8`, {
      authenticated: false,
    })
      .then((res) => {
        if (seq !== loadSeqRef.current) return
        const items = Array.isArray(res) ? res : res?.items || []
        properties.set(items)
        selectedMapPropertyId.set(
          items.find((p) => Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude)))?.id || null
        )
      })
      .catch(() => {
        if (seq !== loadSeqRef.current) return
        properties.set([])
        selectedMapPropertyId.set(null)
      })
      .finally(() => {
        if (seq === loadSeqRef.current) loadingProperties.set(false)
      })

    const analyticsTask = Promise.all([
      loadMarketAnalytics({ district: districtName, includeResearch: false }),
      loadMarketAnalytics({ includeResearch: false }).catch(() => null),
      loadMarketAnalytics({ district: districtName, propertyType: 'LAND', includeResearch: false }).catch(() => null),
      loadMarketAnalytics({ district: districtName, propertyType: 'HOUSE', includeResearch: false }).catch(() => null),
      loadMarketAnalytics({ district: districtName, propertyType: 'APARTMENT', includeResearch: false }).catch(() => null),
    ])
      .then(([districtData, cityData, landData, houseData, apartmentData]) => {
        if (seq !== loadSeqRef.current) return
        const cityMap = {}
        for (const row of cityData?.byDistrict || []) {
          if (row?.key) cityMap[row.key] = row
        }
        analyticsState.set({
          loading: false,
          error: '',
          districtData,
          cityByDistrict: cityMap,
          segments: {
            LAND: landData?.overall || null,
            HOUSE: houseData?.overall || null,
            APARTMENT: apartmentData?.overall || null,
          },
        })
      })
      .catch(() => {
        if (seq !== loadSeqRef.current) return
        analyticsState.set({
          loading: false,
          error: 'Chưa tải được thống kê giá rao công khai từ máy chủ. Vui lòng thử lại.',
          districtData: null,
          cityByDistrict: {},
          segments: { LAND: null, HOUSE: null, APARTMENT: null },
        })
      })

    await Promise.allSettled([listingsTask, analyticsTask])
  }

  useEffect(() => {
    void loadDistrictEvidence(currentDistrict)
    return () => {
      loadSeqRef.current += 1
    }
  }, [stateKey([effectiveSlug, isUnknownDistrict])])

  const getMapPoints = () =>
    properties
      .getSnapshot()
      .filter((p) => Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude)))
      .map((p) => ({
        id: p.id,
        latitude: Number(p.latitude),
        longitude: Number(p.longitude),
        price: p.price,
        priceExact: p.priceExact,
        priceUnit: p.priceUnit,
        transactionType: p.transactionType,
        title: p.title,
      }))

  const [activeSection] = useState(() => createStateStore('overview'))
  useSyncExternalStore(activeSection.subscribe, activeSection.getSnapshot)
  const inPageTabs = [
    { id: 'overview', number: '01', label: 'Tổng quan & GIS' },
    { id: 'planning', number: '02', label: 'Quy hoạch hạ tầng' },
    { id: 'price-trend', number: '03', label: 'Phân bố đơn giá' },
    { id: 'listings', number: '04', label: 'Bất động sản mở bán' },
    { id: 'neighboring', number: '05', label: 'Khám phá 7 quận/huyện' },
  ]

  function scrollToSection(id) {
    activeSection.set(id)
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function focusOnDistrictMap(propertyId) {
    selectedMapPropertyId.set(propertyId)
    scrollToSection('overview')
  }

  const sectionObserverRef = useRef(null)
  useEffect(() => {
    if (isUnknownDistrict) return undefined
    let frame = null
    function updateActiveSection() {
      frame = null
      const nav = document.querySelector('[data-ui-view="MarketInsightsView"] .sticky')
      const threshold = (nav?.getBoundingClientRect().bottom || 128) + 64
      let current = inPageTabs[0].id
      for (const tab of inPageTabs) {
        const el = document.getElementById(tab.id)
        if (el && el.getBoundingClientRect().top <= threshold) current = tab.id
      }
      if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2) {
        current = inPageTabs.at(-1).id
      }
      if (activeSection.getSnapshot() !== current) activeSection.set(current)
    }
    function scheduleUpdate() {
      if (frame === null) frame = requestAnimationFrame(updateActiveSection)
    }
    if (typeof IntersectionObserver !== 'undefined') {
      sectionObserverRef.current = new IntersectionObserver(scheduleUpdate, {
        rootMargin: '-20% 0px -60% 0px',
        threshold: [0.05, 0.25, 0.5],
      })
      for (const tab of inPageTabs) {
        const el = document.getElementById(tab.id)
        if (el) sectionObserverRef.current.observe(el)
      }
    }
    window.addEventListener('scroll', scheduleUpdate, { passive: true })
    window.addEventListener('resize', scheduleUpdate)
    scheduleUpdate()
    return () => {
      window.removeEventListener('scroll', scheduleUpdate)
      window.removeEventListener('resize', scheduleUpdate)
      if (frame !== null) cancelAnimationFrame(frame)
      sectionObserverRef.current?.disconnect()
    }
  }, [isUnknownDistrict])

  const [expandedPanels] = useState(() =>
    createStateStore({
      planning1: true,
      planning2: true,
      planning3: false,
    })
  )
  useSyncExternalStore(expandedPanels.subscribe, expandedPanels.getSnapshot)
  function togglePanel(panelKey) {
    expandedPanels.edit((draftValue) => {
      draftValue[panelKey] = !expandedPanels.getSnapshot()[panelKey]
    })
  }

  function handleBack() {
    if (window.history.length > 1) routerLatest.current.back()
    else routerLatest.current.push('/listings')
  }

  const snap = analyticsState.getSnapshot()
  const overall = snap.districtData?.overall || null
  const minSample = snap.districtData?.meta?.minSample ?? 30

  return {
    ...inputProps,
    DISTRICT_PROFILES,
    DISTRICT_LIST,
    router,
    compare,
    routeDistrictParam,
    isUnknownDistrict,
    currentDistrict,
    selectDistrict,
    analytics: snap.districtData,
    analyticsLoading: snap.loading,
    analyticsError: snap.error,
    cityByDistrict: snap.cityByDistrict,
    overall,
    minSample,
    landMedianText: formatSegmentMedian(snap.segments.LAND, snap.loading, snap.error),
    houseMedianText: formatSegmentMedian(snap.segments.HOUSE, snap.loading, snap.error),
    apartmentMedianText: formatSegmentMedian(snap.segments.APARTMENT, snap.loading, snap.error),
    reloadAnalytics: () => loadDistrictEvidence(currentDistrict),
    properties: properties.getSnapshot(),
    loadingProperties: loadingProperties.getSnapshot(),
    selectedMapPropertyId: selectedMapPropertyId.getSnapshot(),
    mapPoints: getMapPoints(),
    focusOnDistrictMap,
    activeSection: activeSection.getSnapshot(),
    inPageTabs,
    scrollToSection,
    expandedPanels: expandedPanels.getSnapshot(),
    togglePanel,
    handleBack,
    rootAttributes: Object.fromEntries(
      Object.entries(inputProps || {}).filter(
        ([key]) =>
          !['children', 'ref', 'key'].includes(key)
          && (!key.startsWith('on')
            || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))
      )
    ),
  }
}

export default React.forwardRef(function MarketInsightsView(props, ref) {
  const view = useMarketInsightsViewState(props)

  if (view.isUnknownDistrict || !view.currentDistrict) {
    return (
      <div
        ref={ref}
        data-ui-view="MarketInsightsView"
        data-sp-f9d979a0=""
        {...view.rootAttributes}
        className={classNames([
          'market-luxury min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)] antialiased pb-20',
          view.rootAttributes.className,
        ])}
      >
        <div className="max-w-[1280px] mx-auto px-5 sm:px-8 pt-10">
          <section
            role="alert"
            data-market-not-found
            className="rounded-3xl bg-brand-card border border-[var(--ui-border)] p-8 sm:p-12 shadow-sm space-y-5"
          >
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-[var(--ui-muted)]">
              KHÔNG TÌM THẤY KHU VỰC · ĐÀ NẴNG
            </p>
            <h1 className="text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)]">
              Khu vực “{view.routeDistrictParam}” không thuộc 7 quận/huyện Đà Nẵng trên hệ thống.
            </h1>
            <p className="text-sm text-[var(--ui-muted)] max-w-2xl leading-relaxed">
              Hệ thống không tự động thay thế sang quận khác để tránh sai lệch địa bàn. Vui lòng chọn một trong 7 đơn vị hành chính hợp lệ bên dưới:
            </p>
            <div className="flex flex-wrap gap-2.5 pt-2">
              {view.DISTRICT_LIST.map((name) => {
                const profile = view.DISTRICT_PROFILES[name]
                return (
                  <SiteLink
                    key={profile.slug}
                    to={`/market/${profile.slug}`}
                    className="px-4 py-2.5 rounded-full bg-[var(--ui-soft)] text-[var(--ui-ink)] border border-[var(--ui-border)] text-xs font-bold hover:opacity-90 transition"
                  >
                    {profile.name}
                  </SiteLink>
                )
              })}
            </div>
          </section>
        </div>
      </div>
    )
  }

  const overallMedianLabel = view.analyticsLoading
    ? 'Đang tổng hợp…'
    : view.analyticsError
      ? 'Tạm chưa khả dụng'
      : view.overall && !isInsufficient(view.overall) && view.overall.medianPricePerSqm != null
        ? formatPerSqm(view.overall.medianPricePerSqm)
        : 'Chưa đủ mẫu'

  const overallSampleSub = view.analyticsLoading
    ? 'Đang truy vấn nguồn công khai hợp lệ'
    : view.analyticsError
      ? 'Không tự điền số liệu giả lập'
      : view.overall
        ? isInsufficient(view.overall)
          ? `n = ${formatCount(view.overall.count)} / ngưỡng tối thiểu ${view.minSample}`
          : `Trung vị giá rao · n = ${formatCount(view.overall.count)} tin`
        : 'Chỉ tính nguồn công khai hợp lệ'

  return (
    <div
      ref={ref}
      data-ui-view="MarketInsightsView"
      data-sp-f9d979a0=""
      {...view.rootAttributes}
      className={classNames([
        'market-luxury min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)] antialiased selection:bg-[var(--ui-soft)] selection:text-[var(--ui-ink)] pb-20',
        view.rootAttributes.className,
      ])}
    >
      <div className="max-w-[1280px] mx-auto px-5 sm:px-8 pt-6" data-sp-f9d979a0="">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6" data-sp-f9d979a0="">
          <div className="flex items-center gap-3" data-sp-f9d979a0="">
            <button
              type="button"
              onClick={(event) => view.handleBack?.(event)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-card text-[var(--ui-accent)] border border-[var(--ui-border)] shadow-2xs hover:bg-[var(--ui-surface)] hover:border-[var(--ui-border)] transition-all cursor-pointer text-xs font-bold group"
              data-sp-f9d979a0=""
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                className="transition-transform group-hover:-translate-x-0.5"
                data-sp-f9d979a0=""
              >
                <line x1="19" y1="12" x2="5" y2="12" data-sp-f9d979a0="" />
                <polyline points="12 19 5 12 12 5" data-sp-f9d979a0="" />
              </svg>
              <span data-sp-f9d979a0="">Quay lại</span>
            </button>
            <nav
              aria-label="Breadcrumb"
              className="hidden sm:inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-brand-card border border-[var(--ui-border)] text-xs font-medium text-[var(--ui-accent)]"
              data-sp-f9d979a0=""
            >
              <SiteLink to="/" className="hover:text-[var(--ui-accent)] transition" data-sp-f9d979a0="">
                Trang chủ
              </SiteLink>
              <span className="text-[var(--ui-ink)]" data-sp-f9d979a0="">/</span>
              <SiteLink to="/market" className="hover:text-[var(--ui-accent)] transition" data-sp-f9d979a0="">
                Dữ liệu thị trường
              </SiteLink>
              <span className="text-[var(--ui-ink)]" data-sp-f9d979a0="">/</span>
              <span className="text-[var(--ui-accent)] font-bold flex items-center gap-1.5" data-sp-f9d979a0="">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--ui-soft)]" data-sp-f9d979a0="" />{' '}
                {view.currentDistrict.name}
              </span>
            </nav>
          </div>
          <div className="flex flex-wrap items-center gap-2.5" data-sp-f9d979a0="">
            <SiteLink
              to={{ path: '/listings', query: { district: view.currentDistrict.shortName } }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-card border border-[var(--ui-border)] hover:border-[var(--ui-border)] text-xs font-bold text-[var(--ui-accent)] transition"
              data-sp-f9d979a0=""
            >
              <span data-sp-f9d979a0="">Tin đăng {view.currentDistrict.shortName}</span>
              <span aria-hidden="true" data-sp-f9d979a0="">↗</span>
            </SiteLink>
            <SiteLink
              to="/market-analytics"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--ui-soft)] text-[var(--ui-ink)] hover:bg-[var(--ui-soft)] text-xs font-bold transition shadow-xs"
              data-sp-f9d979a0=""
            >
              <span data-sp-f9d979a0="">Thống kê trung vị toàn TP</span>
              <span aria-hidden="true" data-sp-f9d979a0="">→</span>
            </SiteLink>
          </div>
        </div>

        <section
          className="market-intro-banner relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[var(--ui-soft)] via-[var(--ui-soft)] to-[var(--ui-soft)] text-brand-navy p-7 sm:p-10 lg:p-12 border border-[var(--ui-border)]/30 shadow-xl"
          data-sp-f9d979a0=""
        >
          <div className="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full bg-[var(--ui-soft)]/8 blur-3xl" aria-hidden="true" data-sp-f9d979a0="" />
          <div className="pointer-events-none absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-[var(--ui-soft)]/10 blur-3xl" aria-hidden="true" data-sp-f9d979a0="" />
          <div className="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-8 pb-8 border-b border-brand-line/12" data-sp-f9d979a0="">
            <div className="max-w-3xl" data-sp-f9d979a0="">
              <div className="inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.24em] text-[var(--ui-ink)] mb-3" data-sp-f9d979a0="">
                <span data-sp-f9d979a0="">⌖</span>
                <span data-sp-f9d979a0="">HỒ SƠ THỊ TRƯỜNG ĐỊA BÀN · ĐÀ NẴNG</span>
              </div>
              <h1 className="text-3xl sm:text-4xl lg:text-[46px] font-semibold tracking-tight leading-[1.14] text-brand-navy" data-sp-f9d979a0="">
                {'Hồ sơ thị trường '}
                <span className="text-[var(--ui-ink)] block sm:inline" data-sp-f9d979a0="">
                  {view.currentDistrict.name}.
                </span>
              </h1>
              <p className="text-sm sm:text-[15px] text-brand-navy/80 mt-3.5 leading-relaxed max-w-2xl" data-sp-f9d979a0="">
                {view.currentDistrict.tagline}
              </p>
            </div>

            <div className="flex flex-wrap sm:flex-nowrap items-stretch gap-3 shrink-0" data-sp-f9d979a0="">
              <div className="market-hero-metric px-5 py-4 min-w-[165px]" data-sp-f9d979a0="">
                <p className="text-[11px] uppercase tracking-wider text-brand-navy/65 font-semibold" data-sp-f9d979a0="">
                  Trung vị giá rao / m²
                </p>
                <p className="text-xl sm:text-2xl font-bold text-[var(--ui-ink)] mt-1 tracking-tight" data-sp-f9d979a0="" data-market-hero-median>
                  {overallMedianLabel}
                </p>
                <p className="text-[11px] text-brand-navy/70 mt-1" data-sp-f9d979a0="">
                  {overallSampleSub}
                </p>
              </div>
              <div className="market-hero-metric px-5 py-4 min-w-[155px]" data-sp-f9d979a0="">
                <p className="text-[11px] uppercase tracking-wider text-brand-navy/65 font-semibold" data-sp-f9d979a0="">
                  Mẫu tin rao hợp lệ
                </p>
                <p className="text-xl sm:text-2xl font-bold text-brand-navy mt-1 tracking-tight" data-sp-f9d979a0="" data-market-hero-sample>
                  {view.analyticsLoading
                    ? '…'
                    : view.overall
                      ? `${formatCount(view.overall.count)} tin`
                      : '—'}
                </p>
                <p className="text-[11px] text-brand-navy/70 mt-1" data-sp-f9d979a0="">
                  Giá rao bán · Không dự báo
                </p>
              </div>
            </div>
          </div>

          <div className="market-district-selector relative z-10 pt-6" data-sp-f9d979a0="">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3.5" data-sp-f9d979a0="">
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand-navy/60" data-sp-f9d979a0="">
                CHỌN QUẬN / HUYỆN KHẢO SÁT TẠI ĐÀ NẴNG
              </p>
              <span className="text-xs text-[var(--ui-ink)]/90 font-medium" data-sp-f9d979a0="">
                7 quận/huyện Đà Nẵng · Trung vị giá rao công khai (không phải giá giao dịch)
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5" data-sp-f9d979a0="">
              {view.DISTRICT_LIST.map((name) => {
                const profile = view.DISTRICT_PROFILES[name]
                const districtStat = view.cityByDistrict[name]
                const subText = districtStat
                  ? !isInsufficient(districtStat) && districtStat.medianPricePerSqm != null
                    ? formatPerSqm(districtStat.medianPricePerSqm)
                    : `${formatCount(districtStat.count)} tin rao`
                  : profile.administrativeType
                const isCurrent = view.currentDistrict.shortName === name
                return (
                  <button
                    key={name}
                    type="button"
                    aria-pressed={isCurrent}
                    onClick={() => view.selectDistrict(profile.slug)}
                    className={classNames([
                      'group px-3.5 py-3 rounded-2xl text-left transition-all cursor-pointer border flex flex-col justify-between',
                      isCurrent
                        ? 'bg-[var(--ui-soft)] text-[var(--ui-accent)] border-[var(--ui-border)] shadow-lg'
                        : 'bg-brand-card/7 text-brand-navy border-brand-line/12 hover:bg-brand-card/14 hover:border-[var(--ui-border)]/50',
                    ])}
                    data-sp-f9d979a0=""
                  >
                    <div className="flex items-center justify-between gap-2 w-full mb-1" data-sp-f9d979a0="">
                      <span className="text-xs font-bold tracking-tight" data-sp-f9d979a0="">
                        {name}
                      </span>
                      <span
                        className={classNames([
                          'w-2 h-2 rounded-full transition',
                          isCurrent ? 'bg-[var(--ui-soft)]' : 'bg-brand-card/25 group-hover:bg-[var(--ui-soft)]',
                        ])}
                        data-sp-f9d979a0=""
                      />
                    </div>
                    <span
                      className={classNames([
                        'text-[11px] font-semibold',
                        isCurrent ? 'text-[var(--ui-accent)]/80' : 'text-brand-navy/65',
                      ])}
                      data-sp-f9d979a0=""
                    >
                      {subText}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          <p className="market-hero-source relative z-10">
            Số liệu giá hiển thị từ API thống kê tin rao công khai hợp lệ (<code>includeResearch=false</code>); các ô dưới ngưỡng mẫu tối thiểu được ẩn trung vị thay vì điền số giả định. Thông tin địa lý – quy hoạch là tư liệu tham khảo hành chính.
          </p>
        </section>

        <div className="sticky top-[calc(var(--sp-header-height,64px)+10px)] z-30 my-7" data-sp-f9d979a0="">
          <div className="rounded-full bg-brand-card/95 backdrop-blur-md border border-[var(--ui-border)] shadow-sm p-1.5 flex items-center justify-between gap-1 overflow-x-auto" data-sp-f9d979a0="">
            {view.inPageTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => view.scrollToSection(tab.id)}
                className={classNames([
                  'flex-1 min-w-fit px-4 py-2.5 rounded-full text-xs font-bold transition-all whitespace-nowrap cursor-pointer flex items-center justify-center gap-2',
                  view.activeSection === tab.id
                    ? 'bg-[var(--ui-soft)] text-[var(--ui-ink)] shadow-xs'
                    : 'text-[var(--ui-accent)] hover:text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]',
                ])}
                data-sp-f9d979a0=""
              >
                <span className="text-[10px] opacity-70 font-mono" data-sp-f9d979a0="">
                  {tab.number}
                </span>
                <span data-sp-f9d979a0="">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-12" data-sp-f9d979a0="">
          <section id="overview" className="scroll-mt-32 grid grid-cols-1 lg:grid-cols-12 gap-7 items-start" data-sp-f9d979a0="">
            <div className="market-overview-card lg:col-span-7 bg-brand-card rounded-3xl p-6 sm:p-8 border border-[var(--ui-border)] shadow-2xs" data-sp-f9d979a0="">
              <div className="pb-5 mb-6 border-b border-[var(--ui-border)]" data-sp-f9d979a0="">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2" data-sp-f9d979a0="">
                  01 / TỔNG QUAN ĐỊA LÝ &amp; GIÁ RAO TRUNG VỊ
                </p>
                <h2 className="text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight" data-sp-f9d979a0="">
                  {'Bức tranh địa bàn '}
                  <span className="text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {view.currentDistrict.name}.
                  </span>
                </h2>
              </div>

              <div className="market-analysis-cards space-y-4 mb-7" data-sp-f9d979a0="">
                <div className="p-5 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] border-l-4 border-l-[#183e54]" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--ui-accent)] uppercase tracking-wider mb-2" data-sp-f9d979a0="">
                    <svg className="size-4 text-[var(--ui-accent)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-f9d979a0="">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" data-sp-f9d979a0="" />
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" data-sp-f9d979a0="" />
                    </svg>
                    <span data-sp-f9d979a0="">Vị trí địa lý &amp; Kết nối giao thông cốt lõi</span>
                  </div>
                  <p className="text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {view.currentDistrict.overview}
                  </p>
                </div>

                <div className="p-5 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] border-l-4 border-l-[#198692]" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--ui-accent)] uppercase tracking-wider mb-2" data-sp-f9d979a0="">
                    <svg className="size-4 text-[var(--ui-accent)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-f9d979a0="">
                      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" data-sp-f9d979a0="" />
                      <polyline points="17 6 23 6 23 12" data-sp-f9d979a0="" />
                    </svg>
                    <span data-sp-f9d979a0="">Đặc điểm không gian &amp; phân bố cư trú</span>
                  </div>
                  <p className="text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {view.currentDistrict.regionalNotes.urbanCharacteristics}
                  </p>
                </div>
              </div>

              <div className="pt-6 border-t border-[var(--ui-border)]" data-sp-f9d979a0="">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-4" data-sp-f9d979a0="">
                  <p className="text-xs font-bold text-[var(--ui-accent)] uppercase tracking-[0.18em]" data-sp-f9d979a0="">
                    THÔNG TIN HÀNH CHÍNH &amp; TRUNG VỊ GIÁ RAO THỰC TẾ
                  </p>
                  <span className="text-[11px] text-[var(--ui-muted)]" data-sp-f9d979a0="">
                    Trung vị asking price · Ngưỡng mẫu ≥ {view.minSample}
                  </span>
                </div>

                <div className="market-overview-stats grid grid-cols-2 sm:grid-cols-3 gap-4" data-sp-f9d979a0="">
                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      Diện tích tự nhiên
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                      {view.currentDistrict.macro.areaKm2}
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)] mt-1" data-sp-f9d979a0="">
                      Địa giới tham khảo hành chính
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      Quy mô dân số
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                      {view.currentDistrict.macro.population}
                    </p>
                    <p className="text-[11px] text-[var(--ui-accent)] font-semibold mt-1" data-sp-f9d979a0="">
                      {view.currentDistrict.macro.density}
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      Trung vị Đất nền
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="" data-market-median-land>
                      {view.landMedianText}
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)] mt-1" data-sp-f9d979a0="">
                      Nguồn công khai hợp lệ
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      Trung vị Nhà phố
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="" data-market-median-house>
                      {view.houseMedianText}
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)] mt-1" data-sp-f9d979a0="">
                      Nguồn công khai hợp lệ
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      Trung vị Căn hộ
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="" data-market-median-apartment>
                      {view.apartmentMedianText}
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)] mt-1" data-sp-f9d979a0="">
                      Nguồn công khai hợp lệ
                    </p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      Tin công khai hiển thị
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                      {view.properties.length} BĐS
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)] mt-1" data-sp-f9d979a0="">
                      {view.overall ? `Tổng mẫu thống kê: ${formatCount(view.overall.count)}` : 'Đang kiểm duyệt trên SmartProp'}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="market-spatial-card lg:col-span-5 bg-brand-card rounded-3xl p-5 sm:p-6 border border-[var(--ui-border)] shadow-2xs lg:sticky lg:top-28" data-sp-f9d979a0="">
              <div className="flex items-center justify-between gap-3 mb-4" data-sp-f9d979a0="">
                <div data-sp-f9d979a0="">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    GIS SPATIAL EXPLORER
                  </p>
                  <h3 className="text-base font-bold text-[var(--ui-accent)] mt-0.5" data-sp-f9d979a0="">
                    Bản đồ phân bố BĐS {view.currentDistrict.shortName}
                  </h3>
                </div>
                <span className="text-xs text-[var(--ui-accent)] font-bold bg-[var(--ui-surface)] border border-[var(--ui-border)] px-3 py-1 rounded-full" data-sp-f9d979a0="">
                  {view.mapPoints.length} ghim tọa độ
                </span>
              </div>
              <div className="h-[430px] rounded-2xl overflow-hidden border border-[var(--ui-border)] relative bg-[var(--ui-surface)]" data-sp-f9d979a0="">
                {view.mapPoints.length ? (
                  <BrowseTileMap
                    points={view.mapPoints}
                    selectedId={view.selectedMapPropertyId}
                    onSelect={(id) => view.router.push(`/listing/${id}`)}
                    data-sp-f9d979a0=""
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center bg-[var(--ui-surface)] text-[var(--ui-accent)] text-xs p-6 text-center" data-sp-f9d979a0="">
                    <p className="font-semibold text-[var(--ui-accent)] mb-1" data-sp-f9d979a0="">
                      {view.loadingProperties ? 'Đang tải tọa độ không gian…' : 'Chưa có ghim tọa độ công khai tại khu vực này'}
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)]" data-sp-f9d979a0="">
                      Hiển thị các bất động sản có tọa độ tham khảo hợp lệ tại {view.currentDistrict.name}
                    </p>
                  </div>
                )}
              </div>
              <div className="mt-4 pt-3 border-t border-[var(--ui-border)] flex items-center justify-between text-xs text-[var(--ui-accent)]" data-sp-f9d979a0="">
                <span data-sp-f9d979a0="">Chọn nhãn giá trên bản đồ để mở chi tiết BĐS</span>
                <SiteLink
                  to={{ path: '/map', query: { district: view.currentDistrict.shortName } }}
                  className="text-[var(--ui-accent)] hover:text-[var(--ui-accent)] font-bold transition inline-flex items-center gap-1"
                  data-sp-f9d979a0=""
                >
                  <span data-sp-f9d979a0="">Mở toàn cảnh GIS</span>
                  <span aria-hidden="true" data-sp-f9d979a0="">↗</span>
                </SiteLink>
              </div>
            </div>
          </section>

          <section id="planning" className="scroll-mt-32 bg-brand-card rounded-3xl p-6 sm:p-8 lg:p-10 border border-[var(--ui-border)] shadow-2xs" data-sp-f9d979a0="">
            <p className="planning-source-note">
              Nội dung và trạng thái hạ tầng dưới đây là tư liệu tổng hợp địa lý – hành chính tham khảo; không thay thế văn bản quy hoạch chi tiết 1/500 hoặc xác nhận pháp lý của cơ quan có thẩm quyền.
            </p>
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 mb-7 border-b border-[var(--ui-border)]" data-sp-f9d979a0="">
              <div data-sp-f9d979a0="">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2" data-sp-f9d979a0="">
                  02 / ĐỊNH HƯỚNG KHÔNG GIAN ĐÔ THỊ 2030 – 2045
                </p>
                <h2 className="text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight" data-sp-f9d979a0="">
                  {'Hạ tầng giao thông '}
                  <span className="text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    &amp; Liên kết không gian.
                  </span>
                </h2>
              </div>
              <p className="text-xs text-[var(--ui-accent)] max-w-md leading-relaxed" data-sp-f9d979a0="">
                Các trục giao thông chính và định hướng phát triển không gian đô thị tại {view.currentDistrict.name}.
              </p>
            </div>

            <div className="space-y-4" data-sp-f9d979a0="">
              <div className="rounded-2xl border border-[var(--ui-border)] overflow-hidden transition-all" data-sp-f9d979a0="">
                <button
                  type="button"
                  id="planning-toggle-1"
                  aria-expanded={!!view.expandedPanels.planning1}
                  aria-controls="planning-panel-1"
                  onClick={() => view.togglePanel('planning1')}
                  className={classNames([
                    'w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors',
                    view.expandedPanels.planning1
                      ? 'bg-[var(--ui-soft)] text-brand-navy'
                      : 'bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]',
                  ])}
                  data-sp-f9d979a0=""
                >
                  <div className="flex items-center gap-3.5" data-sp-f9d979a0="">
                    <span
                      className={classNames([
                        'text-xs font-mono px-2.5 py-1 rounded-full border',
                        view.expandedPanels.planning1
                          ? 'border-[var(--ui-border)]/40 text-[var(--ui-ink)] bg-brand-card/8'
                          : 'border-[var(--ui-border)] text-[var(--ui-accent)] bg-brand-card',
                      ])}
                      data-sp-f9d979a0=""
                    >
                      01
                    </span>
                    <span data-sp-f9d979a0="">
                      Liên kết vùng &amp; tổ chức không gian tại {view.currentDistrict.name}
                    </span>
                  </div>
                  <span
                    className={classNames([
                      'text-xs transition-transform duration-200',
                      view.expandedPanels.planning1 ? 'rotate-180 text-[var(--ui-ink)]' : 'text-[var(--ui-accent)]',
                    ])}
                    data-sp-f9d979a0=""
                  >
                    ▼
                  </span>
                </button>
                <div
                  id="planning-panel-1"
                  role="region"
                  aria-labelledby="planning-toggle-1"
                  className="p-6 bg-brand-card text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)] space-y-4 border-t border-[var(--ui-border)]"
                  data-sp-f9d979a0=""
                  style={{ display: view.expandedPanels.planning1 ? undefined : 'none' }}
                >
                  <p data-sp-f9d979a0="">{view.currentDistrict.regionalNotes.spatialContext}</p>
                </div>
              </div>

              <div className="rounded-2xl border border-[var(--ui-border)] overflow-hidden transition-all" data-sp-f9d979a0="">
                <button
                  type="button"
                  id="planning-toggle-2"
                  aria-expanded={!!view.expandedPanels.planning2}
                  aria-controls="planning-panel-2"
                  onClick={() => view.togglePanel('planning2')}
                  className={classNames([
                    'w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors',
                    view.expandedPanels.planning2
                      ? 'bg-[var(--ui-soft)] text-brand-navy'
                      : 'bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]',
                  ])}
                  data-sp-f9d979a0=""
                >
                  <div className="flex items-center gap-3.5" data-sp-f9d979a0="">
                    <span
                      className={classNames([
                        'text-xs font-mono px-2.5 py-1 rounded-full border',
                        view.expandedPanels.planning2
                          ? 'border-[var(--ui-border)]/40 text-[var(--ui-ink)] bg-brand-card/8'
                          : 'border-[var(--ui-border)] text-[var(--ui-accent)] bg-brand-card',
                      ])}
                      data-sp-f9d979a0=""
                    >
                      02
                    </span>
                    <span data-sp-f9d979a0="">
                      Danh mục trục hạ tầng &amp; công trình tiêu biểu tại {view.currentDistrict.shortName}
                    </span>
                  </div>
                  <span
                    className={classNames([
                      'text-xs transition-transform duration-200',
                      view.expandedPanels.planning2 ? 'rotate-180 text-[var(--ui-ink)]' : 'text-[var(--ui-accent)]',
                    ])}
                    data-sp-f9d979a0=""
                  >
                    ▼
                  </span>
                </button>
                <div
                  id="planning-panel-2"
                  role="region"
                  aria-labelledby="planning-toggle-2"
                  className="p-6 bg-brand-card border-t border-[var(--ui-border)]"
                  data-sp-f9d979a0=""
                  style={{ display: view.expandedPanels.planning2 ? undefined : 'none' }}
                >
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-sp-f9d979a0="">
                    {view.currentDistrict.infrastructure.map((item) => (
                      <div
                        key={item.name}
                        className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] flex flex-col justify-between gap-3"
                        data-sp-f9d979a0=""
                      >
                        <div data-sp-f9d979a0="">
                          <span
                            data-planning-status={item.status}
                            className="text-[10px] font-bold px-2.5 py-1 rounded-full inline-block mb-2.5 bg-brand-card border border-[var(--ui-border)] text-[var(--ui-accent)] uppercase tracking-wider"
                            data-sp-f9d979a0=""
                          >
                            ● {item.status}
                          </span>
                          <p className="font-bold text-[var(--ui-accent)] text-xs sm:text-[13px] leading-snug" data-sp-f9d979a0="">
                            {item.name}
                          </p>
                        </div>
                        <p className="text-[11px] text-[var(--ui-muted)]" data-sp-f9d979a0="">
                          Thông tin hạ tầng tham khảo trên địa bàn
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-[var(--ui-border)] overflow-hidden transition-all" data-sp-f9d979a0="">
                <button
                  type="button"
                  id="planning-toggle-3"
                  aria-expanded={!!view.expandedPanels.planning3}
                  aria-controls="planning-panel-3"
                  onClick={() => view.togglePanel('planning3')}
                  className={classNames([
                    'w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors',
                    view.expandedPanels.planning3
                      ? 'bg-[var(--ui-soft)] text-brand-navy'
                      : 'bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]',
                  ])}
                  data-sp-f9d979a0=""
                >
                  <div className="flex items-center gap-3.5" data-sp-f9d979a0="">
                    <span
                      className={classNames([
                        'text-xs font-mono px-2.5 py-1 rounded-full border',
                        view.expandedPanels.planning3
                          ? 'border-[var(--ui-border)]/40 text-[var(--ui-ink)] bg-brand-card/8'
                          : 'border-[var(--ui-border)] text-[var(--ui-accent)] bg-brand-card',
                      ])}
                      data-sp-f9d979a0=""
                    >
                      03
                    </span>
                    <span data-sp-f9d979a0="">Lưu ý đối chiếu thực địa &amp; pháp lý</span>
                  </div>
                  <span
                    className={classNames([
                      'text-xs transition-transform duration-200',
                      view.expandedPanels.planning3 ? 'rotate-180 text-[var(--ui-ink)]' : 'text-[var(--ui-accent)]',
                    ])}
                    data-sp-f9d979a0=""
                  >
                    ▼
                  </span>
                </button>
                <div
                  id="planning-panel-3"
                  role="region"
                  aria-labelledby="planning-toggle-3"
                  className="p-6 bg-brand-card text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)] border-t border-[var(--ui-border)]"
                  data-sp-f9d979a0=""
                  style={{ display: view.expandedPanels.planning3 ? undefined : 'none' }}
                >
                  <p data-sp-f9d979a0="">{view.currentDistrict.regionalNotes.surveyChecklist}</p>
                </div>
              </div>
            </div>
          </section>

          <section id="price-trend" className="scroll-mt-32 space-y-6" data-sp-f9d979a0="">
            <PriceTrendChart
              districtName={view.currentDistrict.name}
              analytics={view.analytics}
              loading={view.analyticsLoading}
              error={view.analyticsError}
              onRetry={view.reloadAnalytics}
              data-sp-f9d979a0=""
            />

            <div className="market-ai-insights rounded-3xl p-6 sm:p-8 lg:p-10 bg-gradient-to-br from-[var(--ui-soft)] via-[var(--ui-soft)] to-[var(--ui-soft)] text-brand-navy shadow-xl border border-[var(--ui-border)]/35 relative overflow-hidden" data-sp-f9d979a0="">
              <div className="pointer-events-none absolute -right-16 -bottom-16 h-64 w-64 rounded-full bg-[var(--ui-soft)]/10 blur-3xl" aria-hidden="true" data-sp-f9d979a0="" />
              <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 mb-6 border-b border-brand-line/12" data-sp-f9d979a0="">
                <div data-sp-f9d979a0="">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-card/10 text-[var(--ui-ink)] text-[11px] font-bold border border-[var(--ui-border)]/30 tracking-wider uppercase mb-3" data-sp-f9d979a0="">
                    <span className="w-2 h-2 rounded-full bg-[var(--ui-success-bg)]" data-sp-f9d979a0="" />
                    <span data-sp-f9d979a0="">THÔNG TIN ĐỊA BÀN THAM KHẢO · KHÔNG PHẢI DỰ BÁO AI</span>
                  </div>
                  <h3 className="text-xl sm:text-2xl font-semibold text-brand-navy tracking-tight" data-sp-f9d979a0="">
                    {'Ghi chú khảo sát địa lý & hạ tầng '}
                    <span className="text-[var(--ui-ink)]" data-sp-f9d979a0="">
                      {view.currentDistrict.name}.
                    </span>
                  </h3>
                </div>
                <SiteLink
                  to="/valuation"
                  className="self-start md:self-auto inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[var(--ui-soft)] hover:bg-[var(--ui-soft)] text-[var(--ui-accent)] text-xs font-bold transition shadow-sm"
                  data-sp-f9d979a0=""
                >
                  <span data-sp-f9d979a0="">Ước tính từng BĐS cụ thể (XGBoost V1.3)</span>
                  <span aria-hidden="true" data-sp-f9d979a0="">→</span>
                </SiteLink>
              </div>
              <p className="ai-data-note relative z-10">
                Thông tin tổng quan địa bàn tham khảo, không phải kết quả định giá, dự báo tăng trưởng hay khuyến nghị đầu tư từ mô hình định giá từng bất động sản.
              </p>
              <div className="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-5 text-xs sm:text-[13px] leading-relaxed" data-sp-f9d979a0="">
                <div className="bg-brand-card/8 backdrop-blur-md rounded-2xl p-5 border border-brand-line/12" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 font-bold text-[var(--ui-ink)] uppercase tracking-wider text-xs mb-2.5" data-sp-f9d979a0="">
                    <span data-sp-f9d979a0="">Kết nối không gian</span>
                  </div>
                  <p className="text-brand-navy/85" data-sp-f9d979a0="">
                    {view.currentDistrict.regionalNotes.spatialContext}
                  </p>
                </div>
                <div className="bg-brand-card/8 backdrop-blur-md rounded-2xl p-5 border border-brand-line/12" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 font-bold text-[var(--ui-success-text)] uppercase tracking-wider text-xs mb-2.5" data-sp-f9d979a0="">
                    <span data-sp-f9d979a0="">Đặc trưng nguồn cung rao bán</span>
                  </div>
                  <p className="text-brand-navy/85" data-sp-f9d979a0="">
                    {view.currentDistrict.regionalNotes.urbanCharacteristics}
                  </p>
                </div>
                <div className="bg-brand-card/8 backdrop-blur-md rounded-2xl p-5 border border-brand-line/12" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 font-bold text-brand-navy uppercase tracking-wider text-xs mb-2.5" data-sp-f9d979a0="">
                    <span data-sp-f9d979a0="">Kiểm tra trước giao dịch</span>
                  </div>
                  <p className="text-brand-navy/85" data-sp-f9d979a0="">
                    {view.currentDistrict.regionalNotes.surveyChecklist}
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section id="listings" className="scroll-mt-32 bg-[var(--ui-surface)] rounded-3xl p-6 sm:p-8 lg:p-10 border border-[var(--ui-border)]" data-sp-f9d979a0="">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 mb-7 border-b border-[var(--ui-border)]" data-sp-f9d979a0="">
              <div data-sp-f9d979a0="">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2" data-sp-f9d979a0="">
                  04 / BẤT ĐỘNG SẢN THỰC TẾ ĐANG NIÊM YẾT
                </p>
                <h2 className="text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight" data-sp-f9d979a0="">
                  {'Tin đăng công khai tại '}
                  <span className="text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {view.currentDistrict.name}.
                  </span>
                </h2>
                <p className="text-xs text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                  Tin đã kiểm duyệt trên hệ thống SmartProp · Hỗ trợ đối chiếu bản đồ GIS và so sánh trực tiếp
                </p>
              </div>
              <SiteLink
                to={{ path: '/listings', query: { district: view.currentDistrict.shortName } }}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[var(--ui-soft)] text-brand-navy hover:bg-[var(--ui-soft)] text-xs font-bold transition self-start sm:self-auto shadow-xs"
                data-sp-f9d979a0=""
              >
                <span data-sp-f9d979a0="">Xem tất cả tại {view.currentDistrict.shortName}</span>
                <span aria-hidden="true" data-sp-f9d979a0="">→</span>
              </SiteLink>
            </div>

            {view.loadingProperties ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-sp-f9d979a0="">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-[420px] rounded-3xl bg-brand-card/60 animate-pulse border border-[var(--ui-border)]" data-sp-f9d979a0="" />
                ))}
              </div>
            ) : view.properties.length ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-sp-f9d979a0="">
                {view.properties.slice(0, 6).map((item) => (
                  <ListingCard
                    key={item.id}
                    property={item}
                    className={classNames({
                      'ring-2 ring-[var(--ui-border)] ring-offset-2': view.selectedMapPropertyId === item.id,
                    })}
                    data-sp-f9d979a0=""
                  >
                    <button
                      type="button"
                      className="market-card-action"
                      aria-pressed={view.selectedMapPropertyId === item.id}
                      onClick={() => view.focusOnDistrictMap(item.id)}
                      data-sp-f9d979a0=""
                    >
                      ⌖ Bản đồ
                    </button>
                    <button
                      type="button"
                      className="market-card-action compare"
                      aria-pressed={view.compare.has(item.id)}
                      onClick={() => view.compare.toggle(item)}
                      data-sp-f9d979a0=""
                    >
                      {view.compare.has(item.id) ? '✓ Đã chọn' : '+ So sánh'}
                    </button>
                  </ListingCard>
                ))}
              </div>
            ) : (
              <div className="rounded-3xl bg-brand-card p-12 text-center border border-[var(--ui-border)]" data-sp-f9d979a0="">
                <p className="text-lg font-semibold text-[var(--ui-accent)]" data-sp-f9d979a0="">
                  Chưa có tin đăng công khai tại {view.currentDistrict.name}
                </p>
                <p className="text-xs text-[var(--ui-accent)] mt-2 mb-5" data-sp-f9d979a0="">
                  Hãy khám phá các quận/huyện khác hoặc xem toàn bộ danh sách bất động sản Đà Nẵng.
                </p>
                <SiteLink
                  to="/listings"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[var(--ui-soft)] text-brand-navy text-xs font-bold"
                  data-sp-f9d979a0=""
                >
                  <span data-sp-f9d979a0="">Mở danh sách BĐS</span>
                  <span aria-hidden="true" data-sp-f9d979a0="">→</span>
                </SiteLink>
              </div>
            )}
          </section>

          <section id="neighboring" className="scroll-mt-32 bg-brand-card rounded-3xl p-6 sm:p-8 lg:p-10 border border-[var(--ui-border)] shadow-2xs space-y-8" data-sp-f9d979a0="">
            <p className="district-data-note">
              Thẻ khu vực sử dụng minh họa bản đồ biểu trưng trung lập của SmartProp (không dùng ảnh chụp địa điểm chưa xác minh quyền sử dụng) và hiển thị số lượng / trung vị tin rao công khai hợp lệ khi có dữ liệu.
            </p>
            <TopSearchedAreas
              currentSlug={view.currentDistrict.slug}
              eyebrow="05 / KHÁM PHÁ CÁC QUẬN / HUYỆN KHÁC · ĐÀ NẴNG"
              mode="market"
              onSelectDistrict={(slug) => view.selectDistrict(slug)}
              data-sp-f9d979a0=""
            />
          </section>
        </div>
      </div>
    </div>
  )
})
