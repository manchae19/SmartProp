export function marketResponse({ district = null, research = false, sufficient = false } = {}) {
  const count = sufficient ? (research ? 224 : 128) : 2
  const median = sufficient ? 4_350_000_000 : null
  const perSqm = sufficient ? 145_000_000 : null
  const dataStatus = sufficient ? 'OK' : 'INSUFFICIENT_DATA'
  const stat = (key, label) => ({
    key, label, count, dataStatus, medianAskingPriceVnd: median, medianPricePerSqm: perSqm,
    p25AskingPriceVnd: null, p75AskingPriceVnd: null, meanAskingPriceVnd: null,
    medianAreaSqm: null, qualityFlags: [],
  })
  const name = district || (sufficient ? 'Hải Châu' : 'Hòa Vang')
  const license = 'CC BY-NC 4.0'
  return {
    meta: {
      generatedAt: '2026-11-28T00:00:00Z',
      filters: { district, ward: null, propertyType: null, source: 'ALL', includeResearch: research },
      priceBasis: 'ASKING_SALE_VND_TOTAL', totalSampleCount: count, minSample: 30,
      disclaimer: 'Giá rao bán tổng hợp, không phải giá giao dịch.',
      dataQualityWarnings: research ? ['TINIX dữ liệu nghiên cứu'] : [],
      researchIncluded: research, researchLicense: research ? license : null,
      temporalStatus: research ? 'AVAILABLE' : 'NOT_REQUESTED',
    },
    overall: stat('ALL', 'Tổng hợp'),
    byDistrict: [stat(name, name)], byWard: [], byPropertyType: [stat('HOUSE', 'Nhà ở')],
    bySource: [
      { source: 'SMARTPROP', label: 'SmartProp', count: research ? 128 : count, researchReference: false, license: null },
      ...(research ? [{ source: 'TINIX_RESEARCH', label: 'TiniX', count: 96, researchReference: true, license }] : []),
    ],
    priceBands: [{ label: '3–5 tỷ', count }], areaBands: [{ label: '50–100 m²', count }],
    monthly: research ? ['2026-02', '2026-03', '2026-04'].map(period => ({
      period, count: 32, medianAskingPriceVnd: median, medianPricePerSqm: perSqm, dataStatus,
    })) : [],
  }
}
