// Curated photographs, separate from publisher imageUrl and RSS permissions.
// Reviewed 2026-11-21 against each Commons file's Licensing section.
const commons = 'https://commons.wikimedia.org/wiki/File:';
const cc0 = 'https://creativecommons.org/publicdomain/zero/1.0/';
const by4 = 'https://creativecommons.org/licenses/by/4.0/';
const entry = (id, file, author, license, licenseUrl, location, photographedAt, caption, automatic) => Object.freeze({
  id, src:`/images/news/${id}.webp`, title:file.replaceAll('_',' '), author,
  source:'Wikimedia Commons', sourceUrl:commons+encodeURIComponent(file),
  license, licenseUrl, location, photographedAt, checkedAt:'2026-11-21',
  changes:'Cắt giữa khung 16:9, đổi kích thước 960 × 540 và chuyển WebP.',
  caption, automatic,
  topics: Object.freeze(id==='construction'?['construction']:id==='dragon-bridge'?['planning']:id==='danang-street'?['housing']:id==='cantho-urban'||id==='camau-urban'?['urban','planning']:['market','urban']),
  applicableLocations: Object.freeze(id==='construction'?[]:[location.split(',')[0]]),
  description:caption, label:'Ảnh minh họa', licenseEvidence:commons+encodeURIComponent(file)+'#Licensing',
  attributionRequirements:license==='CC0 1.0'?'Ghi nguồn để minh bạch.':'Ghi tác giả, nguồn, giấy phép và thay đổi; giữ ShareAlike nếu áp dụng.',
  usageRestrictions:'Chỉ minh họa bối cảnh đúng địa phương; không mô tả tài sản, dự án hay pháp lý cụ thể.',
});
export const NEWS_ILLUSTRATIONS = Object.freeze({
  // Conditional approvals: kept out of automatic selection. An exact article
  // mapping requires a separate context review; no matching current article.
  'hanoi-denlu':Object.freeze({...entry('hanoi-denlu','Công_viên_hồ_Đền_Lừ_vào_buổi_tối.jpg','Vmosnokia31','CC BY 4.0',by4,'Hà Nội, Việt Nam','2026-03-27','Công viên hồ Đền Lừ, Hà Nội (2026), có các tòa nhà Đền Lừ 2/3 phía xa; không phải ảnh dự án được đề cập.',false),checkedAt:'2026-11-23',topics:Object.freeze(['housing','urban']),changes:'Giữ khung gần 16:9 của bản xem trước 960 × 540, chuyển WebP; không chỉnh màu.',usageRestrictions:'Chỉ bối cảnh nhà ở/cảnh quan đô thị Hà Nội đã duyệt theo bài; có người trong cảnh công cộng, không dùng để hàm ý họ bảo chứng SmartProp. Không xác nhận pháp lý, chất lượng hay tiến độ nhà ở.'}),
  'hanoi-times-city':Object.freeze({...entry('hanoi-times-city','Times_City_Apartment_entrance.jpg','Amenoc','CC0 1.0',cc0,'Hà Nội, Việt Nam','2017-09-18','Sảnh khu căn hộ Times City, Hà Nội (2017); không phải ảnh sảnh của dự án khác.',false),checkedAt:'2026-11-23',topics:Object.freeze(['apartments']),changes:'Cắt giữa bản xem trước 960 × 720 thành khung 960 × 540, chuyển WebP; không chỉnh màu.',usageRestrictions:'Chỉ bài đúng Times City hoặc bối cảnh căn hộ Hà Nội được duyệt riêng; có người và tên thương mại trong ảnh, không hàm ý bảo chứng hoặc quyền sử dụng hình ảnh cá nhân cho quảng cáo. Không dùng cho dự án/địa phương khác.'}),
  'cantho-cairang-2010':Object.freeze({...entry('cantho-cairang-2010','Construction_of_new_Cai_Rang_Bridge_2010.jpg','FOSSASIA Team','CC BY 2.0','https://creativecommons.org/licenses/by/2.0/','Cần Thơ, Việt Nam','2010-11-21','Công trường xây dựng cầu Cái Răng, Cần Thơ (2010); ảnh tư liệu, không phải hiện trạng công trường hiện nay.',false),checkedAt:'2026-11-23',topics:Object.freeze(['construction','planning']),changes:'Cắt giữa bản xem trước 960 × 640 thành khung 960 × 540, chuyển WebP; không chỉnh màu.',originalSourceUrl:'https://www.flickr.com/photos/fossasia/15778317919/',licenseReview:'FlickreviewR 2 xác nhận CC BY 2.0 trên Commons ngày 2023-07-22.',usageRestrictions:'Chỉ bài phù hợp hoạt động xây dựng cầu Cái Răng, Cần Thơ năm 2010 đã duyệt riêng. Không dùng minh họa tiến độ hiện tại hoặc công trình khác.'}),
  'hanoi-office':Object.freeze({...entry('hanoi-office','Hanoi_Skyline.jpg','Minhvuong308hn','CC BY-SA 4.0','https://creativecommons.org/licenses/by-sa/4.0/','Hà Nội, Việt Nam','2015-05-05','Hà Nội (2015); ảnh bối cảnh đô thị, không đại diện nguồn cung văn phòng trong bài.',false),changes:'Cắt giữa khung 16:9 từ bản xem trước 960 × 720, chuyển WebP 960 × 540.',derivativeLicense:'CC BY-SA 4.0',derivativeLicenseUrl:'https://creativecommons.org/licenses/by-sa/4.0/'}),
  'cantho-urban':Object.freeze({...entry('cantho-urban','Can_tho.jpg','Gnguyen5','CC BY-SA 4.0','https://creativecommons.org/licenses/by-sa/4.0/','Cần Thơ, Việt Nam','2015-08-02','Cảnh quan Cần Thơ (2015); không phải hình ảnh quy hoạch hay hiện trạng năm 2026.',false),changes:'Cắt khung 16:9 về phía dưới để giữ sông và cầu từ bản xem trước 960 × 720, chuyển WebP 960 × 540.',derivativeLicense:'CC BY-SA 4.0',derivativeLicenseUrl:'https://creativecommons.org/licenses/by-sa/4.0/'}),
  'camau-urban':Object.freeze({...entry('camau-urban','Cà_Mau_city_center.jpg','[Tycho] / Shansov.net','CC BY-SA 3.0','https://creativecommons.org/licenses/by-sa/3.0/','Cà Mau, Việt Nam','2015-12-25','Trung tâm Cà Mau (2015); không phải phối cảnh hoặc kết quả thực hiện quy hoạch.',false),changes:'Giữ khung 16:9, chuyển bản xem trước thành WebP 960 × 540.',derivativeLicense:'CC BY-SA 3.0',derivativeLicenseUrl:'https://creativecommons.org/licenses/by-sa/3.0/'}),
  'danang-street':entry('danang-street','Street_scene_-_Da_Nang,_Vietnam_-_DSC02417.JPG','Daderot','CC0 1.0',cc0,'Đà Nẵng, Việt Nam','2014-08-02','Đường phố Đà Nẵng (2014); không phải ảnh tài sản được đề cập.',true),
  'dragon-bridge':entry('dragon-bridge','Dragon_Bridge_at_night_(Danang)_-_DSC02093.JPG','Daderot','CC0 1.0',cc0,'Đà Nẵng, Việt Nam','2014-07-30','Cầu Rồng, Đà Nẵng (2014); ảnh minh họa hạ tầng đô thị.',true),
  'danang-skyline':entry('danang-skyline','2024-12-01_Da_Nang_3.jpg','Alexkom000','CC BY 4.0',by4,'Đà Nẵng, Việt Nam','2024-12-01','Toàn cảnh Đà Nẵng (2024); không phải ảnh dự án được đề cập.',true),
  // License verified, but location unknown and identifiable people are present.
  // Prepared locally, NOT selected automatically or mapped to any article.
  construction:entry('construction','Construction_site_work.jpg','Varshith2024','CC BY 4.0',by4,'Chưa xác định','2024-06-10','Hoạt động xây nhà (2024), địa điểm chưa xác định.',false),
});
// Reviewed against the actual RSS title + URL, not ID alone (protect ID reuse).
export const NEWS_ILLUSTRATION_MAPPINGS = Object.freeze({
  "ebf9a2b9-d368-3527-af21-9aad9eeec856":Object.freeze({"illustration": "hanoi-office", "title": "Hà Nội: Nguồn cung văn phòng tăng mạnh, cuộc đua giữ khách thuê ngày càng khốc liệt", "articleUrl": "https://batdongsan.baoxaydung.vn/ha-noi-nguon-cung-van-phong-tang-manh-cuoc-dua-giu-khach-thue-ngay-cang-khoc-liet-192261117200431867.htm", "reviewedAt": "2026-11-21"}),
  "47823dfe-10fa-351f-8578-a20f38d410e2":Object.freeze({"illustration": "hanoi-office", "title": "Nguồn cung mới gia tăng, bất động sản văn phòng tạo lợi thế để hút khách", "articleUrl": "https://bnews.vn/nguon-cung-moi-gia-tang-bat-dong-san-van-phong-tao-loi-the-de-hut-khach/444383.html", "reviewedAt": "2026-11-21"}),
  "ad9b989e-dc06-39b6-a135-3776996eb7ee":Object.freeze({"illustration": "cantho-urban", "title": "Cần Thơ phát triển đô thị bền vững đến năm 2030, tầm nhìn đến năm 2045", "articleUrl": "https://bnews.vn/can-tho-phat-trien-do-thi-ben-vung-den-nam-2030-tam-nhin-den-nam-2045/444276.html", "reviewedAt": "2026-11-21"}),
  "02547b6b-7573-3785-9ed5-4a68c3319027":Object.freeze({"illustration": "camau-urban", "title": "Xây dựng Cà Mau thành đô thị xanh, thông minh và bền vững", "articleUrl": "https://batdongsan.baoxaydung.vn/xay-dung-ca-mau-thanh-do-thi-xanh-thong-minh-va-ben-vung-192261018152445338.htm", "reviewedAt": "2026-11-21"}),
  '9f5ea04d-ab55-3f25-a6aa-9e6c03920391':Object.freeze({
    illustration:'danang-street',
    title:'Đà Nẵng chuyển đổi công năng, xử lý nhiều cơ sở nhà đất dôi dư',
    articleUrl:'https://bnews.vn/da-nang-chuyen-doi-cong-nang-xu-ly-nhieu-co-so-nha-dat-doi-du/444659.html',
    reviewedAt:'2026-11-21',
  }),
});
const normalize = value => String(value || '').normalize('NFC').replace(/\s+/g,' ').trim().toLocaleLowerCase('vi');
export function usableNewsIllustration(image) {
  return !!image && ['id','src','author','sourceUrl','license','licenseUrl','licenseEvidence','caption','changes','checkedAt','usageRestrictions'].every(key=>typeof image[key]==='string'&&image[key].trim())
    && /^\/images\/news\/[a-z0-9-]+\.webp$/.test(image.src)
    && /^https:\/\/commons\.wikimedia\.org\/wiki\/File:/.test(image.sourceUrl)
    && /^https:\/\/creativecommons\.org\/(?:licenses\/(?:by|by-sa)\/\d\.\d|publicdomain\/zero\/1\.0)\/$/.test(image.licenseUrl)
    && ({'CC0 1.0':cc0,'CC BY 4.0':by4,'CC BY 2.0':'https://creativecommons.org/licenses/by/2.0/','CC BY-SA 4.0':'https://creativecommons.org/licenses/by-sa/4.0/','CC BY-SA 3.0':'https://creativecommons.org/licenses/by-sa/3.0/'}[image.license]===image.licenseUrl)
    && (!image.license.includes('BY-SA') || (image.derivativeLicense===image.license&&image.derivativeLicenseUrl===image.licenseUrl));
}
// Stable article/asset ranking: never depends on page, render order or neighbours.
export function stableNewsImage(article, candidates) {
  const key=String(article.id||article.articleUrl||normalize(article.title));
  const score=id=>{let hash=2166136261;for(const character of key+'|'+id)hash=Math.imul(hash^character.charCodeAt(0),16777619);return hash>>>0;};
  return [...candidates].sort((a,b)=>score(b.id)-score(a.id)||a.id.localeCompare(b.id))[0]||null;
}
export function newsIllustration(article, catalog=NEWS_ILLUSTRATIONS) {
  // Array.filter/map supply an index as the second callback argument.
  if(!catalog||typeof catalog!=='object')catalog=NEWS_ILLUSTRATIONS;
  if (!article) return null;
  const mapped=NEWS_ILLUSTRATION_MAPPINGS[article.id];
  if(mapped) return normalize(article.title)===normalize(mapped.title)&&article.articleUrl===mapped.articleUrl&&usableNewsIllustration(catalog[mapped.illustration])?catalog[mapped.illustration]:null;
  const title=normalize(article.title), summary=normalize(article.summary||article.description);
  // Only explicit city-wide overview titles; locationTags alone are insufficient.
  if(!/đà nẵng/u.test(title)||!/(?:tổng quan|toàn cảnh|bức tranh|diễn biến|xu hướng)/u.test(title))return null;
  const text=title+' '+summary;
  if(/khu đô thị|khu dân cư|khu biệt thự|tại phường|tại xã|triệu đồng|tỷ đồng|tỉ đồng/iu.test(text))return null;
  if(/cần thơ|cà mau|bình dương|đồng nai|hưng yên|bắc ninh|nha trang|vũng tàu|huế|hải châu|sơn trà|liên chiểu|ngũ hành sơn|cẩm lệ|redstar|thủ thiêm/iu.test(text))return null;
  if(!/đà nẵng/u.test(summary) || /hà nội|tp\.?\s*hcm|hồ chí minh|hải phòng|khánh hòa|quảng nam|hòa vang|bà nà|chu lai|phía nam|phía bắc|dự án|phân khu|khởi công|pháp lý|sổ hồng|sổ đỏ|đấu giá|đấu thầu|residence|alphanam|vsip/iu.test(text))return null;
  if(article.category==='Chính sách & pháp lý'||article.category==='Dự án')return null;
  // City scenery is not a substitute for a villa, apartment or legal document.
  if(/biệt thự|chung cư|căn hộ|sổ hồng|sổ đỏ/u.test(title))return null;
  const topic=/hạ tầng giao thông/u.test(title)?'planning':/nhà phố|nhà đất/u.test(title)?'housing':/thị trường bất động sản|thị trường bđs|đô thị/u.test(title)?'market':null;
  if(!topic)return null;
  return stableNewsImage(article,Object.values(catalog).filter(image=>image.automatic&&usableNewsIllustration(image)&&image.topics?.includes(topic)&&image.applicableLocations?.some(location=>normalize(location)==='đà nẵng')));
}
