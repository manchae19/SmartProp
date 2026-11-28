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
