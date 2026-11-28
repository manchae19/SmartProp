// Only add a grant after reviewing evidence covering image display by SmartProp.
// No publisher is currently verified. This is not a runtime/user-controlled flag.
export const NEWS_IMAGE_PERMISSIONS = Object.freeze({});
const hosts = Object.freeze({
  'https://vnexpress.net': 'vcdn1-vnexpress.vnecdn.net',
  'https://baoxaydung.vn': 'baoxaydung.mediacdn.vn',
  'https://bnews.vn': 'image.bnews.vn',
});
export function permittedNewsImage(article, permissions = NEWS_IMAGE_PERMISSIONS) {
  const grant = permissions[article.sourceUrl];
  if (!grant || grant.displayAllowed !== true || grant.context !== 'SmartProp'
    || typeof grant.evidence !== 'string' || !grant.evidence.trim()) return null;
  try {
    const url = new URL(article.imageUrl);
    if (url.protocol !== 'https:' || url.hostname !== hosts[article.sourceUrl]
      || url.username || url.password || url.port && url.port !== '443' || url.hash
      || article.imageUrl.length > 4096) return null;
    const path = decodeURIComponent(url.pathname).toLowerCase();
    if (!/\.(?:jpe?g|png|webp|gif|avif)$/.test(path)
      || /(?:^|[/_.-])(?:logo|favicon|tracking|pixel|spacer|beacon|1x1)(?:[/_.-]|$)/.test(path)) return null;
    for (const [key,value] of url.searchParams) {
      if (['w','h','width','height'].includes(key.toLowerCase()) && value.trim()
        && Number.isFinite(Number(value)) && Number(value) <= 2) return null;
    }
    return url.href;
  } catch { return null; }
}
