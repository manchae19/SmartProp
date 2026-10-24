<script setup>
import { ref,reactive,computed,watch } from 'vue'
import {useRoute,useRouter} from 'vue-router'
import {api,session,errorText} from '../../services/api'
import {types,query,mapUrl,conflictText} from '../../services/property'
import AppShell from './AppShell.vue'
import ListingCard from './ListingCard.vue'
import Pager from './Pager.vue'
const route=useRoute(),router=useRouter(),busy=ref(false),acting=ref(false),error=ref(''),notice=ref(''),data=ref({items:[],page:0,totalPages:0,totalElements:0}), selected=ref(null)
const mode=computed(()=>route.path==='/favorites'?'saved':route.path==='/my-listing'?'mine':route.path==='/map'?'map':route.path==='/home'?'home':'search')
const title=computed(()=>({saved:'Bất động sản yêu thích',mine:'Tin đăng của tôi',map:'Tìm bất động sản trên bản đồ',home:'Tìm một nơi để bắt đầu',search:'Khám phá bất động sản'})[mode.value])
const filters=reactive({keyword:'',propertyType:'',transactionType:'',district:'',minPrice:'',maxPrice:'',minArea:'',maxArea:'',bedrooms:'',sort:'newest',bbox:''})
let generation=0
async function load(page=0){const run=++generation;busy.value=true;error.value='';try{const endpoint=mode.value==='saved'?'/users/me/saved-properties':mode.value==='mine'?'/users/me/properties':mode.value==='map'?'/properties/map':'/properties';const result=await api(endpoint+'?'+query({...(mode.value==='mine'||mode.value==='saved'?{}:filters),page,size:12}),{authenticated:!!session.token});if(run===generation){data.value=result;selected.value=result.items[0]?.property||result.items[0]||null}}catch(e){if(run===generation)error.value=errorText(e)}finally{if(run===generation)busy.value=false}}
async function favorite(p,remove=false){if(!session.token){await router.push('/login');return}acting.value=true;error.value='';try{await api('/users/me/saved-properties/'+p.id,{method:remove?'DELETE':'PUT'});notice.value=remove?'Đã bỏ lưu tin.':'Đã lưu vào yêu thích.';if(remove)await load(data.value.page)}catch(e){error.value=errorText(e)}finally{acting.value=false}}
async function transition(p,action){acting.value=true;error.value='';try{await api('/properties/'+p.id+(action==='delete'?'?expectedVersion='+p.contentVersion:'/'+action),{method:action==='delete'?'DELETE':'POST',...(action==='delete'?{}:{body:{expectedVersion:p.contentVersion}})});notice.value=action==='submit'?'Đã gửi duyệt.':action==='delete'?'Đã xóa tin.':'Đã đóng tin.';await load(data.value.page)}catch(e){error.value=conflictText(e)}finally{acting.value=false}}
watch(()=>route.path,()=>{data.value={items:[],page:0,totalPages:0,totalElements:0};selected.value=null;notice.value='';load()},{immediate:true})
</script>
<template><AppShell>
<section :class="mode==='home'?'sp-hero':''"><p class="sp-muted" v-if="mode!=='home'">SMARTPROP / {{mode==='mine'?'QUẢN LÝ TIN':'NHÀ ĐẤT ĐÀ NẴNG'}}</p><h1>{{title}}</h1><p>Tìm kiếm thông tin và tiện ích xung quanh từ những tin đã được duyệt.</p></section>
<form v-if="!['mine','saved'].includes(mode)" class="sp-panel sp-form" @submit.prevent="load(0)">
<label>Từ khóa<input v-model="filters.keyword" placeholder="Tên hoặc mô tả bất động sản" maxlength="100"></label><label>Loại bất động sản<select v-model="filters.propertyType"><option value="">Tất cả</option><option v-for="(label,key) in types" :key="key" :value="key">{{label}}</option></select></label>
<label>Giao dịch<select v-model="filters.transactionType"><option value="">Tất cả</option><option value="SALE">Bán</option><option value="RENT">Cho thuê</option></select></label><label>Quận / huyện<input v-model="filters.district" placeholder="Ví dụ: Hải Châu" maxlength="100"></label>
<label>Giá từ (VND)<input v-model="filters.minPrice" type="number" min="0" step="0.01"></label><label>Giá đến (VND)<input v-model="filters.maxPrice" type="number" min="0" step="0.01"></label><label>Diện tích từ (m²)<input v-model="filters.minArea" type="number" min="0" step="0.01"></label><label>Diện tích đến (m²)<input v-model="filters.maxArea" type="number" min="0" step="0.01"></label>
<label>Phòng ngủ tối thiểu<input v-model="filters.bedrooms" type="number" min="0" max="32767"></label><label>Sắp xếp<select v-model="filters.sort"><option value="newest">Mới nhất</option><option value="priceAsc">Giá tăng dần</option><option value="priceDesc">Giá giảm dần</option><option value="areaAsc">Diện tích tăng dần</option><option value="areaDesc">Diện tích giảm dần</option></select></label>
<label v-if="mode==='map'" class="sp-wide">Giới hạn bản đồ (kinh độ Tây, vĩ độ Nam, kinh độ Đông, vĩ độ Bắc)<input v-model="filters.bbox" placeholder="108,15.9,108.4,16.2"></label><div class="sp-wide"><button class="sp-primary" :disabled="busy">{{busy?'Đang tìm…':'Tìm kiếm'}}</button></div>
</form>
<div v-if="mode==='mine'" class="sp-row"><RouterLink v-if="['BROKER','ADMIN'].includes(session.user?.role)" class="sp-btn sp-primary" to="/post">+ Đăng tin mới</RouterLink><span class="sp-muted">Chỉnh sửa tin sẽ đưa tin về bản nháp để duyệt lại.</span></div>
<p v-if="error" role="alert" class="sp-error">{{error}} <button :disabled="busy" @click="load(data.page)">Tải lại</button></p><p v-if="notice" role="status" class="sp-success">{{notice}}</p><p v-if="busy" role="status">Đang tải tin…</p>
<iframe v-if="mode==='map'&&selected" class="sp-map" :src="mapUrl(selected)" title="Vị trí bất động sản được chọn trên OpenStreetMap" loading="lazy" referrerpolicy="no-referrer"></iframe>
<div v-if="!busy&&!error&&!data.items.length" class="sp-empty">{{mode==='saved'?'Bạn chưa lưu tin nào, hoặc các tin đã lưu hiện không còn công khai.':mode==='mine'?'Bạn chưa có tin đăng.':'Chưa có tin phù hợp. Hãy thử điều chỉnh bộ lọc.'}}</div>
<div class="sp-grid"><ListingCard v-for="item in data.items" :key="(item.property||item).id" :property="item.property||item" :own="mode==='mine'">
<template v-if="mode==='mine'"><RouterLink v-if="item.property.status!=='HIDDEN'" class="sp-btn" :to="{path:'/post',query:{edit:item.property.id}}">Chỉnh sửa</RouterLink><button v-if="['DRAFT','REJECTED'].includes(item.property.status)" :disabled="acting" @click="transition(item.property,'submit')">Gửi duyệt</button><button v-if="item.property.status!=='CLOSED'" :disabled="acting" @click="transition(item.property,'close')">Đóng tin</button><button :disabled="acting" class="sp-danger" @click="transition(item.property,'delete')">Xóa tin</button></template>
<template v-else><button :disabled="acting" @click="favorite(item,mode==='saved')">{{mode==='saved'?'Bỏ lưu':'Lưu yêu thích'}}</button><button v-if="mode==='map'" @click="selected=item">Xem vị trí</button></template>
</ListingCard></div><Pager v-bind="data" :busy="busy" @change="load" />
</AppShell></template>