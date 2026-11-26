// Rows for the listing page's "Tiện ích lân cận" list, from /properties/{id}/points-of-interest.
// Only well-formed items are shown; distance is straight-line from the listing pin.
export const MAX_NEARBY_ROWS = 12;

export function nearbyPoiRows(items, limit = MAX_NEARBY_ROWS) {
  if (!Array.isArray(items)) return [];
  return items
    .filter(p => p && typeof p.id === 'string' && typeof p.name === 'string' && p.name.trim()
      && typeof p.category === 'string' && Number.isFinite(p.distanceMeters) && p.distanceMeters >= 0)
    .sort((a, b) => a.distanceMeters - b.distanceMeters)
    .slice(0, limit)
    .map(p => ({ id: p.id, name: p.name.trim(), category: p.category, distance: distanceText(p.distanceMeters) }));
}

export function distanceText(meters) {
  return meters >= 1000 ? (meters / 1000).toFixed(1).replace('.', ',') + ' km' : Math.round(meters) + ' m';
}
