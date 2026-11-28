/**
 * WP-04 B5 — which evidence sections the Advisor panel may show for one valuation result.
 *
 * Kept as a pure function so the transition rules (legacy SHAP -> new explanation -> legacy again)
 * are testable without a DOM, and so no stale or duplicated section can be rendered by accident.
 */

/**
 * @param {{explanation?: unknown, shap?: unknown, openShap?: boolean}} input
 * @returns {{showExplanation: boolean, showLegacyShapToggle: boolean, showLegacyShapContent: boolean}}
 */
export function evidenceSections({ explanation, shap, openShap } = {}) {
  const hasExplanation = explanation !== null && explanation !== undefined;
  const hasLegacy = shap !== null && shap !== undefined;

  // The validated TreeSHAP explanation always wins. Legacy SHAP is a fallback for responses that
  // predate it, and it is never rendered alongside the new panel.
  return {
    showExplanation: hasExplanation,
    showLegacyShapToggle: hasLegacy && !hasExplanation,
    showLegacyShapContent: hasLegacy && !hasExplanation && openShap === true,
  };
}

/**
 * Legacy factors carry an `impactPct`-style field in some older payloads. It is a relative model
 * signal, not a share of the property price, so the UI must not render it as a percentage.
 */
export function legacyImpactIsPercentage() {
  return false;
}

const evidenceContract = {
  VALUATION: ['valuationEvidence', ['XGBOOST_V1_3']],
  EXPLANATION: ['valuationEvidence.explanation', ['WP04_TREESHAP']],
  SIMILAR_LISTING: ['comparableEvidence', ['WP02_COMPARABLE']],
  VALUATION_SUPPORT: ['valuationComparableEvidence', ['WP02_COMPARABLE']],
  LOCATION: ['locationIntelligence', ['SMARTPROP_GIS_POI']],
  RECOMMENDATION: ['source', ['SMARTPROP_LISTING', 'EXTERNAL_LISTING', 'TINIX_RESEARCH']],
}

const evidenceStatuses = new Set([
  'AVAILABLE', 'PARTIAL', 'MISSING', 'UNAVAILABLE', 'INVALID', 'NOT_REQUESTED', 'INSUFFICIENT_EVIDENCE',
])

const evidenceLimitations = new Set([
  'ESTIMATED_ASKING_PRICE', 'MODEL_ATTRIBUTION', 'ASKING_PRICE_ONLY', 'TOO_FEW_COMPARABLES',
  'COMPARABLE_EXAMPLES_ONLY', 'AREA_CONTEXT_ONLY', 'STRAIGHT_LINE_DISTANCE', 'HEURISTIC_FIT',
])

function evidenceInstant(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,9})?Z$/.test(value)) return null
  const date = new Date(value)
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 19) !== value.slice(0, 19)) return null
  return value
}

/** Ignore malformed optional metadata without discarding the legacy consult response. */
export function advisorEvidenceMetadata(evidence, allowResearch = false, now = Date.now()) {
  if (evidence == null) return null
  const entries = new Map()
  const duplicates = new Set()
  if (!Array.isArray(evidence) || evidence.length > Object.keys(evidenceContract).length) return entries
  for (const raw of evidence) {
    if (typeof raw?.kind !== 'string' || !Object.hasOwn(evidenceContract, raw.kind)) continue
    const { kind } = raw
    const [reference, sources] = evidenceContract[kind]
    if (entries.has(kind) || duplicates.has(kind)) {
      duplicates.add(kind)
      entries.delete(kind)
      continue
    }
    if (raw.reference !== reference || !evidenceStatuses.has(raw.status)) continue
    if (raw.source === 'TINIX_RESEARCH' && !allowResearch) continue
    if (raw.source != null && !sources.includes(raw.source)) continue

    const observedAt = evidenceInstant(raw.observedAt)
    const age = observedAt && raw.source ? now - Date.parse(observedAt) : NaN
    entries.set(kind, {
      kind,
      source: raw.source ?? null,
      status: raw.status,
      observedAt,
      generatedAt: evidenceInstant(raw.generatedAt),
      freshness: age >= 0 ? (age > 90 * 86400000 ? 'STALE' : 'RECENT') : 'UNKNOWN',
      limitations: Array.isArray(raw.limitations)
        ? [...new Set(raw.limitations.filter(code => evidenceLimitations.has(code)))].slice(0, 3) : [],
    })
  }
  return entries
}
