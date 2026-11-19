const limit = 85.05112878;
export function projectPoint(latitude, longitude, zoom) {
  const scale = 256 * 2 ** zoom,
    lat = Math.max(-limit, Math.min(limit, latitude)) * Math.PI / 180;
  return {
    x: (longitude + 180) / 360 * scale,
    y: (1 - Math.log(Math.tan(lat) + 1 / Math.cos(lat)) / Math.PI) / 2 * scale
  };
}
export function unprojectPoint(x, y, zoom) {
  const scale = 256 * 2 ** zoom;
  return {
    latitude: Math.atan(Math.sinh(Math.PI * (1 - 2 * Math.max(0, Math.min(scale, y)) / scale))) * 180 / Math.PI,
    longitude: (x / scale * 360 % 360 + 360) % 360 - 180
  };
}
export function visibleTiles(center, zoom, width, height) {
  const p = projectPoint(center.latitude, center.longitude, zoom),
    left = p.x - width / 2,
    top = p.y - height / 2,
    n = 2 ** zoom,
    out = [];
  for (let x = Math.floor(left / 256); x < Math.ceil((left + width) / 256); x++) for (let y = Math.floor(top / 256); y < Math.ceil((top + height) / 256); y++) if (y >= 0 && y < n) out.push({
    key: zoom + '/' + (x % n + n) % n + '/' + y,
    x: (x % n + n) % n,
    y,
    z: zoom,
    left: x * 256 - left,
    top: y * 256 - top
  });
  return out;
}
