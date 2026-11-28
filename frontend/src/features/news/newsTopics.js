// Presentation only: never changes the publisher's category or RSS payload.
export const NEWS_TOPICS = Object.freeze({
  market: 'Thị trường bất động sản', apartments: 'Chung cư, căn hộ',
  legal: 'Pháp lý, sổ hồng', planning: 'Quy hoạch, hạ tầng',
  projects: 'Dự án bất động sản', construction: 'Xây dựng',
});
const normalize = value => String(value || '').normalize('NFC').toLocaleLowerCase('vi');
const rules = [
  ['legal', /sổ (?:hồng|đỏ)|giấy chứng nhận|luật đất đai|pháp lý|quyền sử dụng đất|cấp sổ/u],
  ['planning', /quy hoạch|hạ tầng|cao tốc|vành đai|đường sắt|phát triển đô thị|đô thị (?:xanh|bền vững)|công viên/u],
  ['apartments', /chung cư|căn hộ|nhà ở xã hội/u],
  ['construction', /thi công|công trường|vật liệu xây dựng|giấy phép xây dựng|an toàn xây dựng|tiến độ xây dựng/u],
  ['market', /thị trường (?:bất động sản|bđs)|giá nhà|giá đất|thanh khoản|m&a bất động sản|bất động sản (?:văn phòng|tạo dòng tiền)/u],
  ['projects', /dự án (?:bất động sản|khu đô thị|nhà ở|khu dân cư)|khu đô thị|residence|alphanam|chủ đầu tư.*(?:mở bán|ra mắt)/u],
];
export function newsTopic(article) {
  if (!article) return null;
  // A precise title phrase takes precedence over incidental summary mentions.
  const title = normalize(article.title), summary = normalize(article.summary);
  for (const [topic, pattern] of rules) if (pattern.test(title)) return topic;
  // Summary alone needs both a precise phrase and matching publisher context.
  const category = normalize(article.category);
  const context = {legal:/pháp lý|chính sách/u, planning:/quy hoạch|hạ tầng/u,
    apartments:/thị trường|nhà ở/u, construction:/xây dựng/u,
    market:/thị trường/u, projects:/dự án/u};
  for (const [topic, pattern] of rules) if (context[topic].test(category) && pattern.test(summary)) return topic;
  return null;
}
