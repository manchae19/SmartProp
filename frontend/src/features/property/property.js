import {publicMapPoint} from '../map/locationDisplay.js'
export const types = { HOUSE: 'Nhà phố', APARTMENT: 'Căn hộ', LAND: 'Đất nền', VILLA: 'Biệt thự', ROOM: 'Phòng trọ', COMMERCIAL: 'Mặt bằng' }
export const states = { DRAFT: 'Bản nháp', PENDING: 'Chờ duyệt', PUBLISHED: 'Đang hiển thị', REJECTED: 'Bị từ chối', HIDDEN: 'Đã ẩn', EXPIRED: 'Hết hạn', CLOSED: 'Đã đóng', OPEN: 'Mới gửi', PROCESSING: 'Đang xử lý', RESOLVED: 'Đã giải quyết', ACTIVE: 'Hoạt động', LOCKED: 'Đã khóa' }
export const reasons = { FAKE_IMAGES: 'Ảnh không đúng thực tế', INACCURATE_INFORMATION: 'Thông tin không chính xác', SUSPECTED_SCAM: 'Nghi ngờ lừa đảo', DUPLICATE: 'Tin trùng lặp', UNAVAILABLE: 'Bất động sản không còn giao dịch', OTHER: 'Lý do khác' }
export function query(values) { return new URLSearchParams(Object.entries(values).filter(([,v]) => v !== '' && v !== null && v !== undefined)).toString() }
export function displayDecimal(value){if(value==null||!/^\d+(?:\.\d+)?$/.test(String(value)))return '—';const [integer,fraction='']=String(value).split('.');const part=fraction.replace(/0+$/,'');return BigInt(integer).toLocaleString('vi-VN')+(part?','+part:'')}
export function price(p) { return displayDecimal(p.priceExact??p.price)+' ₫'+(({PER_MONTH:'/tháng',PER_YEAR:'/năm',PER_DAY:'/ngày'})[p.priceUnit]||'') }
export function date(value) { return value ? new Date(value).toLocaleString('vi-VN') : '—' }
export function mapUrl(p) { if(!publicMapPoint(p))return ''; if(p.latitude==null||p.latitude===''||p.longitude==null||p.longitude==='')return ''; const x=Number(p.longitude),y=Number(p.latitude); if(!Number.isFinite(x)||!Number.isFinite(y))return ''; return `https://www.openstreetmap.org/export/embed.html?bbox=${x-.02},${y-.015},${x+.02},${y+.015}&layer=mapnik&marker=${y},${x}` }
export function validateFiles(files, evidence=false) {
  const allowed=evidence?['image/jpeg','image/png','application/pdf']:['image/jpeg','image/png']
  for(const file of files) { if(!allowed.includes(file.type))throw new Error(evidence?'Chỉ chọn JPEG, PNG hoặc PDF.':'Chỉ chọn ảnh JPEG hoặc PNG.'); if(file.size===0||file.size>10*1024*1024)throw new Error('Mỗi tệp phải lớn hơn 0 và tối đa 10 MB.') }
}
export function conflictText(error) { return error.status===409 ? 'Dữ liệu đã thay đổi hoặc thao tác không còn phù hợp. Tải lại dữ liệu để tiếp tục; thay đổi chưa lưu vẫn được giữ.' : error.message }
// Stored PUBLISHED can be expired; preserve the raw DTO for versioned writes.
export function listingStatus(property,now=Date.now()){return property.status==='PUBLISHED'&&property.expiresAt&&Date.parse(property.expiresAt)<=now?'EXPIRED':property.status}

// Compact listing labels only. Exact prices remain available through price() and DTO fields.
export function compactPrice(property) {
  const raw = String(property.priceExact ?? property.price ?? '')
  if (raw.length > 100 || !/^\d+(?:\.\d+)?$/.test(raw)) return '—'
  const suffix = ({ PER_MONTH: '/tháng', PER_YEAR: '/năm', PER_DAY: '/ngày' })[property.priceUnit] || ''
  const [integer, fraction = ''] = raw.split('.')
  const denominator = 10n ** BigInt(fraction.length)
  const amount = BigInt(integer + fraction)
  let unit = BigInt(integer) >= 1000000000n ? 1000000000n : BigInt(integer) >= 1000000n ? 1000000n : 1n
  if (unit === 1n) return displayDecimal(raw) + ' ₫' + suffix
  const round = value => (amount * 100n + value * denominator / 2n) / (value * denominator)
  let rounded = round(unit)
  if (unit === 1000000n && rounded >= 100000n) { unit = 1000000000n; rounded = round(unit) }
  const approximate = rounded * unit * denominator !== amount * 100n
  const decimals = (rounded % 100n).toString().padStart(2, '0').replace(/0+$/, '')
  const number = (rounded / 100n).toLocaleString('vi-VN') + (decimals ? ',' + decimals : '')
  return (approximate ? '≈ ' : '') + number + (unit === 1000000000n ? ' tỷ' : ' triệu') + suffix
}
