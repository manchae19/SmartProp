// Concept illustrations are separate from the geographically constrained photo
// catalogue. They never represent a real location, building or legal document.
import {newsTopic} from './newsTopics.js';
import {newsIllustration,stableNewsImage} from './newsIllustrations.js';
import {permittedNewsImage} from './newsImagePolicy.js';
const terms='https://openai.com/policies/terms-of-use/';
const descriptions={
 villa:['Nhà ở cao cấp minh họa','Kiến trúc nhà ở sân vườn hư cấu, ánh sáng ban ngày.'],
 apartments:['Căn hộ minh họa','Không gian căn hộ và sân trong hư cấu với cây xanh.'],
 legal:['Thủ tục bất động sản minh họa','Mô hình nhà, chìa khóa và hồ sơ trống; không phải giấy chứng nhận hoặc bằng chứng pháp lý.'],
 planning:['Quy hoạch đô thị minh họa','Không gian khu dân cư hư cấu với đường đi bộ và cây xanh; không phải bản đồ hay quy hoạch đã phê duyệt.'],
 infrastructure:['Hạ tầng minh họa','Cầu và công trình hạ tầng hư cấu; không mô tả công trình hoặc tiến độ thực tế.'],
 market:['Thị trường bất động sản minh họa','Cảnh quan kiến trúc đô thị hư cấu; không biểu thị số liệu, giá trị hay lợi nhuận đầu tư.'],
 projects:['Dự án kiến trúc minh họa','Tổ hợp kiến trúc sân vườn hư cấu; không phải phối cảnh của dự án trong bài.'],
 commercial:['Bất động sản thương mại minh họa','Tòa nhà văn phòng và khối thương mại hư cấu, không có thương hiệu hoặc dự án xác định.'],
};
export const NEWS_EDITORIAL_COVERS=Object.freeze(Object.fromEntries(Object.entries(descriptions).map(([topic,[title,description]])=>[topic,Object.freeze({
 id:'editorial-'+topic,topic,src:'/images/news/editorial-'+topic+'.webp',title,
 kind:'AI_CONCEPT',tool:'OpenAI image_gen',createdAt:'2026-11-23',checkedAt:'2026-11-23',
 author:'OpenAI image_gen — tạo theo định hướng SmartProp',source:'Minh họa AI tạo mới',sourceUrl:terms,
 license:'Theo điều khoản dịch vụ OpenAI; không gán giấy phép CC',licenseUrl:terms,
 rights:'Sử dụng theo điều khoản OpenAI áp dụng; không tuyên bố độc quyền hoặc bảo đảm bản quyền đối với mọi yếu tố đầu ra.',
 label:'Ảnh minh họa',description,
 caption:'Minh họa khái niệm tạo bằng AI. '+description+' Không phải ảnh chụp địa điểm hoặc dự án được đề cập.',
 changes:'Cắt giữa khung 16:9, thu nhỏ 960 × 540 và chuyển WebP; không chèn chữ hoặc logo.',
 usageRestrictions:'Chỉ minh họa khái niệm; không dùng như bằng chứng về địa điểm, pháp lý, quy hoạch, giá hoặc tình trạng dự án.',
})])));
export function newsCoverTopic(article){
 if(!article)return null;
 const title=String(article.title||'').normalize('NFC').toLocaleLowerCase('vi');
 const existing=newsTopic({...article,summary:article.summary||article.description});
 if(existing==='legal')return 'legal';
 if(/biệt thự|nhà phố|bất động sản cao cấp/u.test(title))return 'villa';
 if(/văn phòng|bất động sản thương mại|trung tâm thương mại|mặt bằng bán lẻ/u.test(title))return 'commercial';
 if(existing==='construction'||/(?:xây dựng|thi công|khởi công|cải tạo)\s+(?:cầu|đường|hầm)/u.test(title)||(existing==='planning'&&/cầu|cao tốc|vành đai|đường sắt|giao thông|hạ tầng/u.test(title)))return 'infrastructure';
 return existing;
}
export function usableEditorialCover(image){
 return !!image&&image.kind==='AI_CONCEPT'&&image.tool==='OpenAI image_gen'
   &&/^\/images\/news\/editorial-[a-z-]+\.webp$/.test(image.src)
   &&['caption','rights','usageRestrictions','changes','author','createdAt'].every(key=>typeof image[key]==='string'&&image[key].trim())
   &&image.sourceUrl===terms&&image.licenseUrl===terms;
}
export function newsEditorialCover(article,catalog=NEWS_EDITORIAL_COVERS){
 const topic=newsCoverTopic(article)||'market';
 // Stable ranking also supports additional reviewed variants of a topic later.
 return stableNewsImage(article||{},Object.values(catalog).filter(image=>image.topic===topic&&usableEditorialCover(image)));
}
export function newsCardMedia(article){
 const publisherUrl=permittedNewsImage(article);
 if(publisherUrl)return {url:publisherUrl,illustration:null};
 const illustration=newsIllustration(article)||newsEditorialCover(article);
 return {url:illustration?.src||null,illustration};
}
