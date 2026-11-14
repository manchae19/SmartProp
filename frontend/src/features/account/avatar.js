import {reactive,watch} from '../../shared/state/store.js'
import {api,session} from '../auth/api.js'
export const avatar=reactive({owner:null,enabled:false,available:false,url:null,revision:null,loading:false,error:''})
let generation=0,flight=null
function clear(){generation++;flight=null;Object.assign(avatar,{owner:session.user?.id??null,enabled:false,available:false,url:null,revision:null,loading:false,error:''})}
export async function loadAvatar(){
 if(!session.token||!session.user?.id)return
 if(flight)return flight
 const current=generation,owner=session.user.id;avatar.loading=true;avatar.error=''
 flight=(async()=>{try{const data=await api('/users/me/avatar');if(current===generation&&owner===session.user?.id)Object.assign(avatar,data,{owner})}catch{if(current===generation)avatar.error='Ảnh đại diện chưa sẵn sàng. Vui lòng thử lại sau.'}finally{if(current===generation){avatar.loading=false;flight=null}}})();return flight
}
export async function uploadAvatar(file){const owner=session.user?.id,current=generation,body=new FormData();body.append('file',file);const data=await api('/users/me/avatar',{method:'POST',body});if(owner!==session.user?.id||current!==generation)return;Object.assign(avatar,data,{owner,error:''});return data}
export async function removeAvatar(){const current=generation,owner=session.user?.id;await api('/users/me/avatar',{method:'DELETE'});if(current===generation&&owner===session.user?.id)Object.assign(avatar,{available:false,url:null,revision:null,error:''})}
watch(()=>session.user?.id,()=>{clear();if(session.user?.id)loadAvatar()},{immediate:true})

export async function validateAvatar(file){
 if(!file||!['image/jpeg','image/png','image/webp'].includes(file.type))throw Error('Chọn ảnh JPG, PNG hoặc WebP.')
 if(file.size>5*1024*1024)throw Error('Ảnh đại diện tối đa 5 MB.')
 const bytes=new Uint8Array(await file.slice(0,12).arrayBuffer())
 const png=bytes[0]===137&&bytes[1]===80&&bytes[2]===78&&bytes[3]===71
 const jpeg=bytes[0]===255&&bytes[1]===216&&bytes[2]===255
 const webp=String.fromCharCode(...bytes.slice(0,4))==='RIFF'&&String.fromCharCode(...bytes.slice(8,12))==='WEBP'
 if(!(file.type==='image/png'&&png||file.type==='image/jpeg'&&jpeg||file.type==='image/webp'&&webp))throw Error('Nội dung tệp không đúng định dạng ảnh.')
 let bitmap;try{bitmap=await createImageBitmap(file);if(bitmap.width<64||bitmap.height<64||bitmap.width>4096||bitmap.height>4096||bitmap.width*bitmap.height>16000000)throw Error('Ảnh cần có kích thước từ 64 đến 4096 pixel mỗi chiều, tối đa 16 triệu pixel.')}catch(e){throw Error(e.message||'Ảnh bị hỏng hoặc không đọc được.')}finally{bitmap?.close()}
}
