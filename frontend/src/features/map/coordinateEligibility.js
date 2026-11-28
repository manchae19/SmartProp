const GEOGRAPHICALLY_VALID = new Set(['VERIFIED_EXACT', 'VERIFIED_BOUNDARY_BUFFER']);
const SPATIALLY_USABLE_VERIFICATION = new Set(['UNVERIFIED', 'PENDING_REVIEW', 'VERIFIED']);
const KNOWN_SOURCES = new Set(['USER_PINNED', 'GEOCODED', 'IMPORTED', 'ADMIN_DEFAULT']);
const KNOWN_ACCURACY = new Set(['CITY', 'DISTRICT', 'WARD', 'STREET', 'BUILDING', 'PARCEL']);

export function canShowReferenceMap(property) {
  const coordinate = property?.coordinate;
  return coordinate?.referenceMapEligible === true
    && GEOGRAPHICALLY_VALID.has(coordinate.geographicValidationStatus)
    && SPATIALLY_USABLE_VERIFICATION.has(coordinate.verificationStatus);
}

export function canAnalyzeDistance(property) {
  const coordinate = property?.coordinate;
  return canShowReferenceMap(property)
    && coordinate?.distanceAnalysisEligible === true
    && KNOWN_SOURCES.has(coordinate.coordinateSource)
    && KNOWN_ACCURACY.has(coordinate.accuracyLevel);
}

// Legacy listing pins are reference points, never verified property positions.
export function canExploreNearby(property) {
  return canShowReferenceMap(property);
}
