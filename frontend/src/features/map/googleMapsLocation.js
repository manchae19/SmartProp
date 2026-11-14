import {validCoordinates} from '../property/postForm.js'
export function googleSearchUrl(address){return 'https://www.google.com/maps/search/?'+new URLSearchParams({api:'1',query:String(address||'Đà Nẵng')})}
export function googlePointUrl(latitude,longitude){return validCoordinates(latitude,longitude)?googleSearchUrl(latitude+','+longitude):''}
export function coordinatesFromGoogleLink(raw){
  let url;try{url=new URL(String(raw).trim())}catch{throw Error('Dán liên kết vị trí Google Maps đầy đủ, bắt đầu bằng https://.')}
  if(url.protocol!=='https:'||url.username||url.password)throw Error('Chỉ nhận liên kết HTTPS Google Maps hợp lệ.')
  if(['maps.app.goo.gl','goo.gl'].includes(url.hostname))throw Error('Hãy mở liên kết rút gọn trên Google Maps rồi sao chép đường dẫn đầy đủ từ thanh địa chỉ.')
  if(!['google.com','www.google.com','maps.google.com','google.com.vn','www.google.com.vn','maps.google.com.vn'].includes(url.hostname)||(!url.pathname.startsWith('/maps')&&!url.hostname.startsWith('maps.')))throw Error('Đây không phải liên kết Google Maps được hỗ trợ.')
  let decoded;try{decoded=decodeURIComponent(url.pathname+url.search+url.hash)}catch{throw Error('Liên kết Google Maps không hợp lệ.')}
  let match=decoded.match(/!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/)
  if(!match)for(const name of ['query','q']){match=(url.searchParams.get(name)||'').trim().match(/^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$/);if(match)break}
  if(!match)throw Error('Liên kết chưa chứa ghim vị trí cụ thể. Hãy chọn địa điểm trên Google Maps rồi sao chép đường dẫn đầy đủ; vị trí tâm bản đồ không được coi là địa chỉ đã chọn.')
  const latitude=Number(match[1]),longitude=Number(match[2]);if(!validCoordinates(latitude,longitude))throw Error('Tọa độ trong liên kết không hợp lệ.')
  return {latitude,longitude}
}
export function coordinatesFromPlace(place){
  const location=place?.location;const latitude=typeof location?.lat==='function'?location.lat():location?.lat;const longitude=typeof location?.lng==='function'?location.lng():location?.lng
  if(!validCoordinates(latitude,longitude)||!place?.formattedAddress)throw Error('Địa chỉ này chưa có vị trí hợp lệ. Vui lòng chọn một gợi ý khác.')
  return {address:place.formattedAddress,latitude:Number(latitude),longitude:Number(longitude),placeId:place.id||''}
}