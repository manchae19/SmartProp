import { classNames, chainHandlers } from '../../shared/lib/ui.js'
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { SiteLink, useAppNavigation } from '../../app/navigation.jsx'
import { DISTRICT_LIST, DISTRICT_PROFILES } from './marketData.js'
import { formatCount, formatPerSqm, isInsufficient, loadMarketAnalytics } from './marketAnalytics.js'

const MOTIF_GRADIENTS = {
  coastal: 'linear-gradient(135deg, #10243b 0%, #1b4965 55%, #168f89 100%)',
  'urban-core': 'linear-gradient(135deg, #142b45 0%, #24456b 60%, #3b6990 100%)',
  'port-tech': 'linear-gradient(135deg, #0f2537 0%, #1f4e68 58%, #2a7b88 100%)',
  'eco-coast': 'linear-gradient(135deg, #122d42 0%, #1c5868 55%, #2b8a7e 100%)',
  'river-eco': 'linear-gradient(135deg, #142b45 0%, #1f5368 56%, #3f7d7a 100%)',
  'transit-hub': 'linear-gradient(135deg, #162a42 0%, #2b4c6f 60%, #4a6e8a 100%)',
  'highland-rural': 'linear-gradient(135deg, #132c3d 0%, #24525a 56%, #457b6c 100%)',
}

function DistrictNeutralVisual({ district }) {
  const bg = MOTIF_GRADIENTS[district.motif] || MOTIF_GRADIENTS['urban-core']
  return (
    <div
      className="absolute inset-0 w-full h-full overflow-hidden"
      style={{ background: bg }}
      role="img"
      aria-label={`Minh họa bản đồ biểu trưng ${district.name} (không phải ảnh chụp thực địa)`}
      data-district-placeholder={district.slug}
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 480 320"
        preserveAspectRatio="xMidYMid slice"
        className="w-full h-full opacity-35 transition-transform duration-500 group-hover:scale-[1.03]"
      >
        <defs>
          <pattern id={`grid-${district.id}`} width="36" height="36" patternUnits="userSpaceOnUse">
            <path d="M 36 0 L 0 0 0 36" fill="none" stroke="#dce7f0" strokeWidth="0.6" strokeOpacity="0.32" />
          </pattern>
        </defs>
        <rect width="480" height="320" fill={`url(#grid-${district.id})`} />
        <path
          d="M -20 230 C 90 185, 175 255, 290 195 C 365 155, 425 180, 500 135"
          fill="none"
          stroke="#d9ad55"
          strokeWidth="2.2"
          strokeOpacity="0.7"
        />
        <path
          d="M -10 268 C 115 225, 210 280, 330 228 C 395 200, 445 215, 505 182"
          fill="none"
          stroke="#7fd8d2"
          strokeWidth="1.6"
          strokeDasharray="5 5"
          strokeOpacity="0.65"
        />
        <g stroke="#eef6fa" strokeOpacity="0.48" strokeWidth="1.4" fill="none">
          <rect x="292" y="64" width="38" height="86" rx="4" />
          <rect x="338" y="44" width="44" height="106" rx="4" />
          <rect x="390" y="78" width="34" height="72" rx="4" />
          <circle cx="122" cy="112" r="28" stroke="#d9ad55" strokeOpacity="0.55" />
          <circle cx="122" cy="112" r="5" fill="#d9ad55" fillOpacity="0.75" />
        </g>
      </svg>
    </div>
  )
}

export default React.forwardRef(function TopSearchedAreas(inputProps, ref) {
  const {
    currentSlug = '',
    eyebrow = 'KHÁM PHÁ ĐỊA BÀN · ĐÀ NẴNG',
    mode = 'market',
    homeAreaImages: _unusedHomeAreaImages,
    onSelectDistrict,
    className,
    ...rest
  } = inputProps || {}

  const router = useAppNavigation()
  const routerRef = useRef(router)
  routerRef.current = router

  const [byDistrictMap, setByDistrictMap] = useState(() => new Map())
  const [analyticsReady, setAnalyticsReady] = useState(false)

  useEffect(() => {
    let active = true
    loadMarketAnalytics({ includeResearch: false })
      .then((res) => {
        if (!active) return
        const map = new Map()
        for (const item of res?.byDistrict || []) {
          if (item?.key) map.set(item.key, item)
        }
        setByDistrictMap(map)
        setAnalyticsReady(true)
      })
      .catch(() => {
        if (active) {
          setByDistrictMap(new Map())
          setAnalyticsReady(false)
        }
      })
    return () => {
      active = false
    }
  }, [])

  const orderedDistricts = useMemo(() => {
    const all = DISTRICT_LIST.map((name) => DISTRICT_PROFILES[name]).filter(Boolean)
    if (currentSlug) {
      return all.filter((d) => d.slug !== currentSlug)
    }
    return all
  }, [currentSlug])

  const featuredDistrict = orderedDistricts[0] || null
  // Show remaining 6 districts when viewing a specific district (6 remaining of 7) or all 6 remaining on overview
  const secondaryDistricts = orderedDistricts.slice(1, 7)

  function handleSelect(district) {
    onSelectDistrict?.(district.slug)
    if (mode === 'listings') {
      routerRef.current.push({
        path: '/listings',
        query: { district: district.shortName },
      })
    } else {
      routerRef.current.push({
        path: `/market/${district.slug}`,
      })
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  function districtStatSummary(district) {
    const stat = byDistrictMap.get(district.shortName)
    if (!analyticsReady || !stat) {
      return {
        countLabel: `${district.administrativeType} · Xem tin rao công khai`,
        priceLabel: 'Minh họa biểu trưng',
      }
    }
    const countLabel = `${formatCount(stat.count)} tin rao hợp lệ`
    const priceLabel = !isInsufficient(stat) && stat.medianPricePerSqm != null
      ? `Trung vị ${formatPerSqm(stat.medianPricePerSqm)}`
      : 'Chưa đủ mẫu trung vị'
    return { countLabel, priceLabel }
  }

  const rootAttributes = Object.fromEntries(
    Object.entries(rest).filter(
      ([key]) =>
        !['children', 'ref', 'key'].includes(key)
        && (!key.startsWith('on')
          || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))
    )
  )

  return (
    <div ref={ref} {...rootAttributes} className={classNames(['top-searched-areas', className])}>
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2">
            {String(eyebrow ?? '')}
          </p>
          <h2 className="text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight">
            {'Khám phá 7 quận/huyện '}
            <span className="text-[var(--ui-accent)]">{'Đà Nẵng.'}</span>
          </h2>
        </div>
        <SiteLink
          to={mode === 'listings' ? '/market' : '/listings'}
          className="inline-flex items-center gap-2 text-xs font-bold text-[var(--ui-accent)] hover:text-[var(--ui-accent)] transition self-start sm:self-auto"
        >
          <span>
            {mode === 'listings'
              ? 'Xem hồ sơ thị trường 7 quận/huyện'
              : 'Khám phá toàn bộ tin đăng Đà Nẵng'}
          </span>
          <span aria-hidden="true">{'→'}</span>
        </SiteLink>
      </div>

      {featuredDistrict ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          {(() => {
            const summary = districtStatSummary(featuredDistrict)
            return (
              <article
                onClick={() => handleSelect(featuredDistrict)}
                role="button"
                tabIndex={0}
                onKeyDown={chainHandlers(
                  (event) => {
                    if (event.key !== 'Enter') return
                    event.preventDefault()
                    handleSelect(featuredDistrict)
                  },
                  (event) => {
                    if (event.key !== ' ') return
                    event.preventDefault()
                    handleSelect(featuredDistrict)
                  }
                )}
                aria-label={`${featuredDistrict.name}, Đà Nẵng — ${summary.countLabel}`}
                className="lg:col-span-5 relative min-h-[320px] sm:min-h-[380px] lg:h-full rounded-[22px] overflow-hidden cursor-pointer group shadow-md border border-[var(--ui-border)] select-none"
              >
                <DistrictNeutralVisual district={featuredDistrict} />
                <div
                  className="absolute inset-0 bg-gradient-to-t from-[#10243b]/95 via-[#10243b]/40 to-transparent"
                  aria-hidden="true"
                />
                <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[var(--ui-surface)]/95 backdrop-blur-md text-[var(--ui-ink)] text-xs font-bold shadow-md border border-[var(--ui-border)]">
                    <span>{featuredDistrict.administrativeType}</span>
                  </span>
                </div>
                <div className="absolute top-4 right-4 z-10">
                  <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-[#10243b]/85 backdrop-blur-md text-white text-xs font-semibold border border-white/25">
                    <span>{summary.priceLabel}</span>
                  </span>
                </div>
                <div className="absolute inset-x-0 bottom-0 p-6 sm:p-7 z-10 flex items-end justify-between gap-4">
                  <div className="min-w-0">
                    <span className="inline-block text-[10px] uppercase tracking-wider text-[#d9ad55] font-semibold mb-1">
                      Minh họa biểu trưng · Không phải ảnh thực địa
                    </span>
                    <h3 className="text-2xl sm:text-[26px] font-bold text-white tracking-tight leading-tight">
                      {featuredDistrict.name}, Đà Nẵng
                    </h3>
                    <p className="text-xs sm:text-sm text-[#dce7f0] font-medium mt-1.5">
                      {summary.countLabel}
                    </p>
                  </div>
                  <span className="w-10 h-10 rounded-full bg-white/15 backdrop-blur-md border border-white/30 text-white flex items-center justify-center group-hover:bg-white group-hover:text-[#142b45] transition-all shrink-0">
                    {'↗'}
                  </span>
                </div>
              </article>
            )
          })()}

          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {secondaryDistricts.map((item) => {
              const summary = districtStatSummary(item)
              return (
                <article
                  key={item.id}
                  onClick={() => handleSelect(item)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={chainHandlers(
                    (event) => {
                      if (event.key !== 'Enter') return
                      event.preventDefault()
                      handleSelect(item)
                    },
                    (event) => {
                      if (event.key !== ' ') return
                      event.preventDefault()
                      handleSelect(item)
                    }
                  )}
                  aria-label={`${item.name}, Đà Nẵng — ${summary.countLabel}`}
                  className="relative min-h-[196px] rounded-[20px] overflow-hidden cursor-pointer group shadow-sm border border-[var(--ui-border)] select-none"
                >
                  <DistrictNeutralVisual district={item} />
                  <div
                    className="absolute inset-0 bg-gradient-to-t from-[#10243b]/95 via-[#10243b]/40 to-transparent"
                    aria-hidden="true"
                  />
                  <div className="absolute top-3.5 left-3.5 z-10">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-[var(--ui-surface)]/95 backdrop-blur-md text-[var(--ui-ink)] text-[11px] font-bold shadow-sm border border-[var(--ui-border)]">
                      <span>{item.shortName}</span>
                    </span>
                  </div>
                  <div className="absolute top-3.5 right-3.5 z-10">
                    <span className="px-2.5 py-1 rounded-lg bg-[#10243b]/80 backdrop-blur-md text-white text-[10px] font-semibold border border-white/20">
                      {summary.priceLabel}
                    </span>
                  </div>
                  <div className="absolute inset-x-0 bottom-0 p-4 z-10 flex items-end justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="text-base font-bold text-white tracking-tight leading-snug">
                        {item.name}
                      </h3>
                      <p className="text-xs text-[#dce7f0] font-medium mt-0.5 truncate">
                        {summary.countLabel}
                      </p>
                    </div>
                    <span className="w-8 h-8 rounded-full bg-white/15 backdrop-blur-md border border-white/25 text-white text-xs flex items-center justify-center group-hover:bg-white group-hover:text-[#142b45] transition-all shrink-0">
                      {'↗'}
                    </span>
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      ) : null}
    </div>
  )
})
