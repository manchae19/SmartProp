export const NEWS_COPY = Object.freeze({
  featuredHeading: 'Tin nổi bật',
  featuredDescription: 'Ưu tiên bài có nhắc đến Đà Nẵng trong tiêu đề hoặc trích đoạn RSS.',
  homeHeading: 'Tin tức & góc nhìn bất động sản.',
});
export const NEWS_MAX_AGE_MS = 90 * 60 * 1000;
export function newsSourceStatus(source, now = Date.now()) {
  if (source.status !== 'AVAILABLE') return source.status;
  const succeeded = Date.parse(source.lastSuccessAt);
  return !Number.isFinite(succeeded) || now - succeeded >= NEWS_MAX_AGE_MS ? 'STALE' : 'AVAILABLE';
}
export function hasNewNewsSnapshot(sources, lastUpdatedAt) {
  const baseline = Date.parse(lastUpdatedAt);
  const list = Array.isArray(sources) ? sources : Array.isArray(sources?.sources) ? sources.sources : [];
  return Number.isFinite(baseline) && list.some(source => Date.parse(source?.lastSuccessAt) > baseline);
}
export function isNewsSnapshotStale(data, now = Date.now()) {
  const updated = Date.parse(data?.lastUpdatedAt);
  return Boolean(data?.stale) || !Number.isFinite(updated) || now - updated >= NEWS_MAX_AGE_MS
    || (data?.sources || []).some(source => newsSourceStatus(source,now) !== 'AVAILABLE');
}
export function isNewsArticleStale(article, sources = [], now = Date.now()) {
  const fetched = Date.parse(article.fetchedAt);
  const source = sources.find(item => item.name === article.sourceName);
  return !Number.isFinite(fetched) || now - fetched >= NEWS_MAX_AGE_MS
    || Boolean(source && newsSourceStatus(source,now) !== 'AVAILABLE');
}
export function newsDate(value, full = false) {
  const parsed = new Date(value);
  return value && !Number.isNaN(parsed.getTime())
    ? new Intl.DateTimeFormat('vi-VN', {timeZone: 'Asia/Ho_Chi_Minh',
      ...(full ? {dateStyle: 'short', timeStyle: 'short'} : {dateStyle: 'medium'})}).format(parsed)
    : null;
}
