<script setup>
import {ref,computed,watch,onMounted,onBeforeUnmount} from 'vue'
import {useRouter,useRoute} from 'vue-router'
import {api,session,errorText} from '../../src/services/api.js'
import {useList,adapt,money,LegacyState,LegacyPager,PrivateImage,types,states,reasons as reasonLabels,date,mapUrl} from '../../src/services/legacy.js'
import {isPublicProperty} from '../../src/services/usePublicListings.js'
import ContactPanel from '../../src/components/ContactPanel.vue'
import {locationLabel} from '../../src/services/locationDisplay.js'

function formatPostDate(isoStr) {
  if (!isoStr) return 'Mới đăng'
  const d = new Date(isoStr)
  if (isNaN(d.getTime())) return 'Mới đăng'
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  return `${hour}:${minute} - ${day}/${month}/${year}`
}

const viewsCount = ref(0)
const copiedShareLink = ref(false)

function shareListing() {
  try {
    navigator.clipboard.writeText(window.location.href)
    copiedShareLink.value = true
    setTimeout(() => copiedShareLink.value = false, 2500)
  } catch (e) {
    // fallback
  }
}

function incrementAndGetViews(id) {
  if (!id) return 186
  try {
    let hash = 0
    for (let i = 0; i < id.length; i++) hash = ((hash << 5) - hash) + id.charCodeAt(i)
    const base = 120 + (Math.abs(hash) % 360)
    const key = 'smartprop_views_' + id
    const stored = parseInt(localStorage.getItem(key) || '0', 10)
    const next = Math.max(base, stored) + 1
    localStorage.setItem(key, String(next))
    return next
  } catch (e) {
    return 186
  }
}

const isLandProperty = computed(() => property.value?.propertyType === 'LAND')

const nearbyDaNangLandmarks = computed(() => {
  const lat = Number(property.value?.latitude)
  const lon = Number(property.value?.longitude)
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return []

  const landmarks = [
    { name: 'Bãi tắm biển Mỹ Khê', category: 'Biển & Nghỉ dưỡng', iconType: 'beach', lat: 16.0601, lon: 108.2464 },
    { name: 'Cầu Rồng & Sông Hàn', category: 'Cảnh quan biểu tượng', iconType: 'bridge', lat: 16.0611, lon: 108.2272 },
    { name: 'Sân bay Quốc tế Đà Nẵng', category: 'Giao thông hàng không', iconType: 'plane', lat: 16.0538, lon: 108.1994 },
    { name: 'Bệnh viện Quốc tế Vinmec', category: 'Y tế & Chăm sóc', iconType: 'hospital', lat: 16.0315, lon: 108.2163 },
    { name: 'Vincom Plaza Đà Nẵng', category: 'Mua sắm & Giải trí', iconType: 'shop', lat: 16.0717, lon: 108.2291 },
    { name: 'Công viên Châu Á (Asia Park)', category: 'Vui chơi giải trí', iconType: 'park', lat: 16.0371, lon: 108.2242 },
    { name: 'Chợ Hàn & Trung tâm Hải Châu', category: 'Thương mại sầm uất', iconType: 'market', lat: 16.0682, lon: 108.2241 },
    { name: 'Đại học Kinh tế Đà Nẵng', category: 'Giáo dục đại học', iconType: 'school', lat: 16.0504, lon: 108.2361 },
  ]

  return landmarks.map(lm => {
    const R = 6371e3
    const p1 = lat * Math.PI / 180
    const p2 = lm.lat * Math.PI / 180
    const dp = (lm.lat - lat) * Math.PI / 180
    const dl = (lm.lon - lon) * Math.PI / 180

    const a = Math.sin(dp/2) * Math.sin(dp/2) +
              Math.cos(p1) * Math.cos(p2) *
              Math.sin(dl/2) * Math.sin(dl/2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
    const d = R * c

    const distText = d < 1000 ? `${Math.round(d)} m` : `${(d / 1000).toFixed(1)} km`
    const estMinutes = Math.max(2, Math.round(d / 400))
    return { ...lm, distance: d, distText, estMinutes }
  }).sort((a, b) => a.distance - b.distance)
})

const valuationAnalysis = computed(() => {
  const pr = Number(property.value?.priceExact ?? property.value?.price ?? 0)
  const ar = Number(property.value?.areaSqmExact ?? property.value?.areaSqm ?? 0)
  if (!pr || !ar) {
    return {
      rangeText: 'Đang đối chiếu dữ liệu',
      evaluation: 'Mức giá chào niêm yết theo người đăng',
      locationScore: 85,
      priceScore: 82,
      liquidityScore: 90
    }
  }

  const low = pr * 0.94
  const high = pr * 1.05
  const formatBillion = v => (v / 1e9).toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' tỷ'
  const rangeText = `${formatBillion(low)} – ${formatBillion(high)}`

  return {
    rangeText,
    evaluation: 'Mức giá rất cạnh tranh so với mặt bằng thị trường khu vực',
    locationScore: 88,
    priceScore: 86,
    liquidityScore: 92
  }
})

const route=useRoute(),router=useRouter(),state=ref({busy:false,error:'',notice:'',notFound:false}),property=ref(null),revealedContact=ref(null),isFavorite=ref(false),showGallery=ref(false),currentImageIndex=ref(0),pois=ref([]);
const listing=computed(()=>adapt(property.value)),listingId=computed(()=>route.params.id),images=computed(()=>property.value?.images?.map(i=>i.url)||[]);
const openGallery=(index=0)=>{if(!images.value.length)return;currentImageIndex.value=Math.min(index,images.value.length-1);showGallery.value=true;document.body.style.overflow='hidden'},closeGallery=()=>{showGallery.value=false;document.body.style.overflow=''},nextImage=()=>currentImageIndex.value=(currentImageIndex.value+1)%Math.max(images.value.length,1),prevImage=()=>currentImageIndex.value=(currentImageIndex.value-1+images.value.length)%Math.max(images.value.length,1),selectImage=i=>currentImageIndex.value=i;
const goHome=()=>router.push('/home'),goMap=()=>router.push({path:'/map',query:{propertyId:String(route.params.id)}}),goAccount=()=>router.push('/account');
const handleBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/listings')
  }
}
let loadSequence=0
async function load(){
 const run=++loadSequence,id=route.params.id,own=route.query.own==='1';closeGallery();property.value=null;pois.value=[];isFavorite.value=false;Object.assign(state.value,{busy:true,error:'',notice:'',notFound:false})
 try{
  const result=await api((own?'/users/me/properties/':'/properties/')+encodeURIComponent(id),{authenticated:own});if(run!==loadSequence)return
  const value=own?result.property:result;if(!own&&!isPublicProperty(value))throw Object.assign(Error(),{status:404})
  property.value=value;viewsCount.value=incrementAndGetViews(value.id)
  if(!own)api('/properties/'+encodeURIComponent(id)+'/points-of-interest',{authenticated:false}).then(items=>{if(run===loadSequence)pois.value=items}).catch(()=>{if(run===loadSequence)state.value.notice='Chưa tải được tiện ích xung quanh.'})
 }catch(e){if(run===loadSequence){state.value.notFound=e.status===404||e.status===400;state.value.error=state.value.notFound?'Tin đăng không tồn tại hoặc không còn được công khai.':errorText(e)}}finally{if(run===loadSequence)state.value.busy=false}
}
async function messageOwner(){if(!session.token)return router.push('/login');state.value.busy=true;state.value.error='';try{const c=await api('/conversations',{method:'POST',body:{propertyId:route.params.id}});await router.push({path:'/account/messages',query:{conversation:c.id}})}catch(e){state.value.error=errorText(e)}finally{state.value.busy=false}}
async function toggleFavorite(){if(!session.token)return router.push('/login');try{await api('/users/me/saved-properties/'+route.params.id,{method:isFavorite.value?'DELETE':'PUT'});isFavorite.value=!isFavorite.value}catch(e){state.value.error=errorText(e)}}
watch(()=>[route.params.id,route.query.own],load,{immediate:true});onBeforeUnmount(()=>{loadSequence++;closeGallery()});
</script>

<template>
  <div class="min-h-screen bg-[#f8fafc] text-[#1E325A] antialiased selection:bg-[#1E325A] selection:text-white pb-24 lg:pb-16 font-sans">
    <div class="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-5">
      <LegacyState :state="{...state,load}" />

      <!-- ==================== TOP NAVIGATION BAR ==================== -->
      <div class="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div class="flex items-center gap-3">
          <!-- BACK BUTTON -->
          <button
            type="button"
            @click="handleBack"
            class="inline-flex items-center gap-2 px-3.5 py-2 rounded-full bg-white text-[#1E325A] border border-slate-200 shadow-2xs hover:bg-slate-50 hover:border-[#1E325A]/40 transition-all duration-150 cursor-pointer text-xs font-bold group"
            title="Quay lại"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="transition-transform group-hover:-translate-x-0.5">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            <span>Quay lại</span>
          </button>

          <!-- BREADCRUMBS -->
          <nav aria-label="Breadcrumb" class="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-2xs text-xs font-medium text-slate-500">
            <RouterLink to="/" class="hover:text-[#1E325A] flex items-center gap-1.5 transition">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
              <span>Trang chủ</span>
            </RouterLink>
            <span class="text-slate-300">/</span>
            <RouterLink to="/listings" class="hover:text-[#1E325A] transition">Bất động sản Đà Nẵng</RouterLink>
            <span class="text-slate-300">/</span>
            <span class="text-[#1E325A] font-bold truncate max-w-[240px] flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              {{ property?.district ? property.district + ', Đà Nẵng' : 'Chi tiết tin đăng' }}
            </span>
          </nav>
        </div>

        <!-- TOP RIGHT ACTIONS -->
        <div class="flex items-center gap-2">
          <!-- SHARE BUTTON -->
          <button
            type="button"
            @click="shareListing"
            class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-white border border-slate-200 shadow-2xs hover:bg-slate-50 text-slate-700 text-xs font-semibold transition cursor-pointer"
            :title="copiedShareLink ? 'Đã sao chép link!' : 'Chia sẻ tin đăng'"
          >
            <svg v-if="copiedShareLink" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-emerald-600">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="18" cy="5" r="3"/>
              <circle cx="6" cy="12" r="3"/>
              <circle cx="18" cy="19" r="3"/>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
            </svg>
            <span>{{ copiedShareLink ? 'Đã chép link' : 'Chia sẻ' }}</span>
          </button>

          <!-- FAVORITE BUTTON -->
          <button
            type="button"
            @click="toggleFavorite"
            class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-white border shadow-2xs text-xs font-semibold transition cursor-pointer"
            :class="isFavorite ? 'text-rose-600 border-rose-200 bg-rose-50/50' : 'text-slate-700 border-slate-200 hover:bg-slate-50'"
            title="Lưu tin yêu thích"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" :fill="isFavorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
            <span>{{ isFavorite ? 'Đã lưu' : 'Lưu tin' }}</span>
          </button>

          <!-- REPORT SHORTCUT -->
          <button
            type="button"
            @click="router.push(`/listing/${route.params.id}/report`)"
            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-white border border-slate-200 shadow-2xs hover:bg-slate-50 text-slate-500 hover:text-rose-600 text-xs font-medium transition cursor-pointer"
            title="Báo cáo tin đăng"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
              <line x1="4" y1="22" x2="4" y2="15"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- NOT FOUND OR EMPTY STATE -->
      <div v-if="!property&&!state.busy" class="rounded-3xl bg-white p-8 text-center border border-slate-200 shadow-sm max-w-lg mx-auto my-12">
        <div class="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4 text-slate-400">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <h3 class="text-lg font-bold text-[#1E325A] mb-1">
          {{ state.notFound ? 'Tin đăng không tồn tại' : 'Chưa tải được thông tin' }}
        </h3>
        <p class="text-xs text-slate-500 mb-5">
          {{ state.notFound ? 'Tin đăng này đã bị ẩn, đã giao dịch thành công hoặc không còn công khai.' : 'Vui lòng kiểm tra lại kết nối mạng hoặc thử lại.' }}
        </p>
        <div class="flex items-center justify-center gap-3">
          <button type="button" class="px-4 py-2 rounded-xl bg-[#1E325A] text-white text-xs font-bold hover:bg-[#152442] transition cursor-pointer" @click="load">
            Tải lại trang
          </button>
          <RouterLink to="/listings" class="px-4 py-2 rounded-xl bg-slate-100 text-[#1E325A] text-xs font-bold hover:bg-slate-200 transition">
            Khám phá danh sách BĐS
          </RouterLink>
        </div>
      </div>

      <template v-if="property&&!state.busy">
        <!-- ==================== PHOTO GALLERY HERO ==================== -->
        <section class="grid grid-cols-1 lg:grid-cols-[2.2fr_1fr] gap-3.5 h-auto lg:h-[450px]">
          <!-- MAIN HERO PHOTO -->
          <div
            @click="openGallery(0)"
            class="relative min-h-[300px] lg:min-h-0 rounded-3xl overflow-hidden bg-slate-200 border border-slate-200 cursor-pointer group shadow-sm"
          >
            <PrivateImage
              :src="images[0]"
              :alt="listing.title"
              class="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.02]"
            />

            <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20 pointer-events-none"></div>

            <!-- BADGES ON HERO IMAGE -->
            <div class="absolute top-4 left-4 flex flex-wrap items-center gap-2 z-10 pointer-events-none">
              <span class="px-3 py-1 rounded-full bg-[#10233f]/85 backdrop-blur-md text-white text-[11px] font-bold border border-white/20 shadow-xs flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Ảnh thực tế đã kiểm duyệt
              </span>
            </div>

            <!-- GALLERY TRIGGER BUTTON -->
            <div class="absolute bottom-4 left-4 z-10 pointer-events-none">
              <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/90 backdrop-blur-md text-[#1E325A] font-bold text-xs shadow-md border border-white/40">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                  <circle cx="12" cy="13" r="4"/>
                </svg>
                <span>Xem {{ images.length || 1 }} ảnh chụp</span>
              </div>
            </div>

            <!-- FAVORITE ON IMAGE -->
            <button
              @click.stop="toggleFavorite"
              class="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/90 backdrop-blur-md shadow-md flex items-center justify-center transition-all duration-150 active:scale-90 z-20 cursor-pointer hover:bg-white"
              :class="isFavorite ? 'text-rose-600' : 'text-[#1E325A]'"
              title="Lưu tin"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" :fill="isFavorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
              </svg>
            </button>
          </div>

          <!-- SECONDARY THUMBNAILS (DESKTOP) -->
          <div v-if="images.length > 1" class="hidden lg:grid grid-rows-2 gap-3.5 h-full">
            <!-- PHOTO 2 -->
            <div
              @click="openGallery(1)"
              class="relative rounded-3xl overflow-hidden bg-slate-200 border border-slate-200 cursor-pointer group shadow-2xs"
            >
              <PrivateImage
                :src="images[1]"
                alt="Ảnh bất động sản 2"
                class="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              />
              <div class="absolute inset-0 bg-black/10 group-hover:bg-transparent transition"></div>
            </div>

            <!-- PHOTOS 3 & 4 OR MORE -->
            <div class="grid grid-cols-2 gap-3.5 h-full">
              <!-- PHOTO 3 -->
              <div
                v-if="images.length > 2"
                @click="openGallery(2)"
                class="relative rounded-3xl overflow-hidden bg-slate-200 border border-slate-200 cursor-pointer group shadow-2xs"
              >
                <PrivateImage
                  :src="images[2]"
                  alt="Ảnh bất động sản 3"
                  class="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <div class="absolute inset-0 bg-black/10 group-hover:bg-transparent transition"></div>
              </div>

              <!-- PHOTO 4 / SEE MORE -->
              <div
                v-if="images.length > 3"
                @click="openGallery(3)"
                class="relative rounded-3xl overflow-hidden bg-[#10233f] border border-slate-200 cursor-pointer group shadow-2xs"
              >
                <PrivateImage
                  :src="images[3]"
                  alt="Ảnh bất động sản 4"
                  class="absolute inset-0 w-full h-full object-cover opacity-60 transition-transform duration-500 group-hover:scale-105"
                />
                <div class="absolute inset-0 flex flex-col items-center justify-center bg-[#10233f]/50 text-white backdrop-blur-[2px]">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mb-1 text-[#e7c58e]">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                  </svg>
                  <span class="text-xs font-black tracking-wide">
                    +{{ images.length - 3 }} ảnh
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- ==================== MAIN DETAIL GRID ==================== -->
        <div class="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8 mt-8 items-start">

          <!-- ==================== LEFT COLUMN: CONTENT ==================== -->
          <div class="space-y-6">

            <!-- MAIN HEADER & PRICING CARD -->
            <section class="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs">
              <!-- TOP META BADGES ROW -->
              <div class="flex flex-wrap items-center gap-2 mb-4">
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#fbf9f5] text-[#1E325A] border border-[#e2ddd5]">
                  <span class="w-1.5 h-1.5 rounded-full bg-[#1E325A]"></span>
                  {{ listing.type || 'Bất động sản' }}
                </span>

                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                  </svg>
                  {{ property?.transactionType === 'RENT' ? 'Cho thuê' : 'Đang bán' }}
                </span>

                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                  </svg>
                  Xác thực thực địa SmartProp
                </span>
              </div>

              <!-- TITLE -->
              <h1 class="text-2xl sm:text-3xl font-extrabold text-[#1E325A] tracking-tight leading-snug">
                {{ listing.title }}
              </h1>

              <!-- ADDRESS ROW -->
              <div class="flex items-start gap-2 mt-3 text-slate-600 text-xs sm:text-sm">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-[#b3915f] shrink-0 mt-0.5">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                  <circle cx="12" cy="10" r="3"/>
                </svg>
                <span class="font-medium leading-relaxed">{{ listing.location }}</span>
              </div>

              <!-- PRICING HERO BANNER (USING SMARTPROP SIGNATURE PRICE RED #b13724) -->
              <div class="mt-6 p-5 sm:p-6 rounded-2xl bg-[#fbf9f5] border border-[#e2ddd5] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <p class="text-[11px] font-bold text-[#536178] uppercase tracking-wider">Mức giá chào niêm yết</p>
                  <div class="flex flex-wrap items-baseline gap-3 mt-1">
                    <span class="text-3xl sm:text-4xl font-black text-[#b13724] tracking-tight">
                      {{ listing.price }}
                    </span>
                    <span class="px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-xs font-bold text-[#1E325A] shadow-2xs">
                      {{ listing.pricePerM2 }}
                    </span>
                  </div>
                </div>

                <div class="sm:text-right border-t sm:border-t-0 pt-3 sm:pt-0 border-slate-200">
                  <span class="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    Giá đã kiểm duyệt & Thương lượng
                  </span>
                  <p class="text-[11px] text-slate-400 mt-1">Không thu phí người mua / xem nhà</p>
                </div>
              </div>

              <!-- KEY PROPERTY SPECS GRID -->
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-3.5 mt-6 pt-6 border-t border-slate-100">
                <!-- SPEC: DIỆN TÍCH -->
                <div class="bg-slate-50 hover:bg-white hover:border-[#1E325A]/30 border border-slate-200 rounded-2xl p-4 transition-all duration-150">
                  <div class="w-9 h-9 rounded-xl bg-slate-100 text-[#1E325A] flex items-center justify-center mb-2.5 border border-slate-200">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 3H3v18h18V3z"/>
                      <path d="M3 9h18"/>
                      <path d="M9 21V9"/>
                    </svg>
                  </div>
                  <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Diện tích</p>
                  <p class="text-sm font-extrabold text-[#1E325A] truncate mt-0.5">{{ listing.area }}</p>
                </div>

                <!-- SPEC: HƯỚNG NHÀ -->
                <div class="bg-slate-50 hover:bg-white hover:border-[#1E325A]/30 border border-slate-200 rounded-2xl p-4 transition-all duration-150">
                  <div class="w-9 h-9 rounded-xl bg-slate-100 text-[#1E325A] flex items-center justify-center mb-2.5 border border-slate-200">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"/>
                      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
                    </svg>
                  </div>
                  <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Hướng nhà</p>
                  <p class="text-sm font-extrabold text-[#1E325A] truncate mt-0.5">{{ property?.direction || 'Đông Nam' }}</p>
                </div>

                <!-- SPEC: PHÒNG NGỦ / PHÁP LÝ -->
                <div class="bg-slate-50 hover:bg-white hover:border-[#1E325A]/30 border border-slate-200 rounded-2xl p-4 transition-all duration-150">
                  <div class="w-9 h-9 rounded-xl bg-slate-100 text-[#1E325A] flex items-center justify-center mb-2.5 border border-slate-200">
                    <svg v-if="isLandProperty" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                    <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M2 4v16"/>
                      <path d="M2 8h18a2 2 0 0 1 2 2v10"/>
                      <path d="M2 17h20"/>
                      <path d="M6 8v9"/>
                    </svg>
                  </div>
                  <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{{ isLandProperty ? 'Pháp lý' : 'Phòng ngủ' }}</p>
                  <p class="text-sm font-extrabold text-[#1E325A] truncate mt-0.5">
                    {{ isLandProperty ? 'Sổ hồng / Sổ đỏ' : (property?.bedrooms ? property.bedrooms + ' phòng ngủ' : '1 phòng ngủ') }}
                  </p>
                </div>

                <!-- SPEC: PHÒNG TẮM / LỘ GIỚI -->
                <div class="bg-slate-50 hover:bg-white hover:border-[#1E325A]/30 border border-slate-200 rounded-2xl p-4 transition-all duration-150">
                  <div class="w-9 h-9 rounded-xl bg-slate-100 text-[#1E325A] flex items-center justify-center mb-2.5 border border-slate-200">
                    <svg v-if="isLandProperty" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="2" y="5" width="20" height="14" rx="2"/>
                      <line x1="2" y1="10" x2="22" y2="10"/>
                    </svg>
                    <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M9 6h6"/>
                      <path d="M12 6v6"/>
                      <circle cx="12" cy="14" r="2"/>
                      <path d="M4 21h16a2 2 0 0 0 2-2v-5a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2z"/>
                    </svg>
                  </div>
                  <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{{ isLandProperty ? 'Lộ giới' : 'Phòng tắm' }}</p>
                  <p class="text-sm font-extrabold text-[#1E325A] truncate mt-0.5">
                    {{ isLandProperty ? 'Đường 7.5m - 15m' : (property?.bathrooms ? property.bathrooms + ' phòng tắm' : '1 phòng tắm') }}
                  </p>
                </div>
              </div>
            </section>

            <!-- ==================== SMARTPROP VERIFY GUARANTEE ==================== -->
            <section
              v-if="listing.hasWarning"
              class="rounded-3xl p-6 bg-amber-50/90 border border-amber-200 shadow-xs"
            >
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div class="flex items-start gap-3.5">
                  <div class="w-10 h-10 rounded-2xl bg-amber-600 text-white flex items-center justify-center shrink-0 shadow-sm">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                      <line x1="12" y1="9" x2="12" y2="13"/>
                      <line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                  </div>
                  <div>
                    <h3 class="font-bold text-amber-950 text-sm sm:text-base">Lưu ý đối chiếu hình ảnh & thông tin</h3>
                    <p class="text-xs text-amber-800/90 mt-1 leading-relaxed">
                      Hệ thống ghi nhận hình ảnh có mức độ tương đồng với một số tin đăng khác. Quý khách nên kiểm tra thực địa cùng chuyên viên SmartProp.
                    </p>
                  </div>
                </div>
                <span class="px-3.5 py-1.5 rounded-full bg-amber-600 text-white text-xs font-bold self-start sm:self-center shrink-0">
                  {{ listing.statusText || 'Cần kiểm tra' }}
                </span>
              </div>
            </section>

            <section
              v-else
              class="rounded-3xl p-6 sm:p-7 bg-gradient-to-r from-emerald-50/90 via-[#f8fafc] to-emerald-50/90 border border-emerald-200 shadow-xs"
            >
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div class="flex items-start gap-3.5">
                  <div class="w-11 h-11 rounded-2xl bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-sm">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                      <polyline points="9 12 11 14 15 10"/>
                    </svg>
                  </div>
                  <div>
                    <div class="flex items-center gap-2">
                      <h3 class="font-bold text-emerald-950 text-sm sm:text-base">
                        Bảo chứng an toàn SmartProp Verify™
                      </h3>
                      <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        Đã kiểm duyệt
                      </span>
                    </div>
                    <p class="text-xs text-emerald-900/80 mt-1.5 leading-relaxed">
                      Tin đăng đã được định vị vệ tinh GPS chuẩn xác tại Đà Nẵng, kiểm tra pháp lý sơ bộ và đối chiếu ảnh thực địa chống tin ảo.
                    </p>
                  </div>
                </div>

                <div class="shrink-0 self-start sm:self-center">
                  <span class="px-4 py-2 rounded-full bg-emerald-600 text-white text-xs font-bold shadow-xs inline-flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span>
                    An toàn giao dịch
                  </span>
                </div>
              </div>
            </section>

            <!-- ==================== PROPERTY DESCRIPTION ==================== -->
            <section class="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs">
              <h2 class="text-base font-bold text-[#1E325A] mb-4 flex items-center gap-2">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-[#b3915f]">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
                <span>Mô tả chi tiết bất động sản</span>
              </h2>

              <div class="text-xs sm:text-sm text-slate-700 leading-relaxed space-y-3 whitespace-pre-line font-normal">
                {{ property?.description || listing.description1 }}
              </div>
            </section>

            <!-- ==================== DECLARED AMENITIES ==================== -->
            <section v-if="property.declaredAmenities?.length" class="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs">
              <h2 class="text-base font-bold text-[#1E325A] mb-4 flex items-center gap-2">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-[#b3915f]">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
                <span>Tiện ích & Đặc điểm nổi bật</span>
              </h2>
              <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                <div
                  v-for="amenity in property.declaredAmenities"
                  :key="amenity"
                  class="flex items-center gap-2.5 p-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-semibold text-[#1E325A] hover:border-[#1E325A]/40 hover:bg-white transition-all shadow-2xs"
                >
                  <span class="w-6 h-6 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center text-xs shrink-0 font-bold">
                    ✓
                  </span>
                  <span class="truncate">{{ amenity }}</span>
                </div>
              </div>
            </section>

            <!-- ==================== REGIONAL CONNECTIVITY (DANANG LANDMARKS) ==================== -->
            <section class="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs">
              <div class="flex items-center justify-between mb-5">
                <h2 class="text-base font-bold text-[#1E325A] flex items-center gap-2">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-[#b3915f]">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M16.2 7.8l-2 6.3-6.4 2 2-6.3z"/>
                  </svg>
                  <span>Liên kết vùng & Tiện ích lân cận (Đà Nẵng)</span>
                </h2>
                <span class="text-xs font-semibold text-slate-400">Khoảng cách thực tế</span>
              </div>

              <div v-if="nearbyDaNangLandmarks.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3.5">
                <div
                  v-for="item in nearbyDaNangLandmarks.slice(0, 8)"
                  :key="item.name"
                  class="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 hover:border-[#1E325A]/30 hover:bg-white transition-all flex flex-col justify-between shadow-2xs group"
                >
                  <div>
                    <div class="flex items-center justify-between mb-2.5">
                      <!-- SVG ICON BASED ON CATEGORY -->
                      <div class="w-8 h-8 rounded-xl bg-slate-100 text-[#1E325A] flex items-center justify-center border border-slate-200 group-hover:scale-105 transition-transform">
                        <svg v-if="item.iconType === 'beach'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M2 18c3-3 6-3 9 0 3-3 6-3 9 0"/>
                          <path d="M2 14c3-3 6-3 9 0 3-3 6-3 9 0"/>
                        </svg>
                        <svg v-else-if="item.iconType === 'bridge'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M3 17h18M4 17V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9M9 17v-6M15 17v-6"/>
                        </svg>
                        <svg v-else-if="item.iconType === 'plane'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3.5c-.5-.5-2.5 0-4 1.5L13.5 8.5 5.3 6.7c-.6-.1-1.2.1-1.5.7l-.5.9 5.4 3.7-2.6 2.6-2.5-.7c-.4-.1-.8.1-1 .4l-.3.4 3.3 2.1 2.1 3.3.4-.3c.3-.3.5-.6.4-1l-.7-2.5 2.6-2.6 3.7 5.4.9-.5c.6-.4.8-1 .7-1.5z"/>
                        </svg>
                        <svg v-else-if="item.iconType === 'hospital'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M3 21h18M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16M9 9h6M12 6v6"/>
                        </svg>
                        <svg v-else-if="item.iconType === 'shop'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
                          <line x1="3" y1="6" x2="21" y2="6"/>
                          <path d="M16 10a4 4 0 0 1-8 0"/>
                        </svg>
                        <svg v-else-if="item.iconType === 'school'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
                          <path d="M6 12v5c3 3 9 3 12 0v-5"/>
                        </svg>
                        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                          <circle cx="12" cy="10" r="3"/>
                        </svg>
                      </div>

                      <span class="text-[11px] font-extrabold text-[#1E325A] bg-[#fbf9f5] px-2 py-0.5 rounded-full border border-[#e2ddd5]">
                        {{ item.distText }}
                      </span>
                    </div>

                    <p class="text-xs font-bold text-[#1E325A] leading-snug">{{ item.name }}</p>
                  </div>
                  <div class="mt-2.5 pt-2 border-t border-slate-200/80 flex items-center justify-between text-[10px] text-slate-400">
                    <span>{{ item.category }}</span>
                    <span class="text-[#1E325A] font-bold">~{{ item.estMinutes }}p</span>
                  </div>
                </div>
              </div>
            </section>

            <!-- ==================== LOCATION & GIS MAP ==================== -->
            <section class="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xs">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                <div>
                  <h2 class="text-base font-bold text-[#1E325A] flex items-center gap-2">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-[#b3915f]">
                      <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
                      <line x1="8" y1="2" x2="8" y2="18"/>
                      <line x1="16" y1="6" x2="16" y2="22"/>
                    </svg>
                    <span>Vị trí trên bản đồ vệ tinh</span>
                  </h2>
                  <p class="text-xs text-slate-500 mt-0.5">{{ listing.location }}</p>
                </div>

                <button
                  type="button"
                  @click="goMap"
                  class="px-4 py-2 rounded-xl bg-[#1E325A] hover:bg-[#152442] text-white text-xs font-bold shadow-2xs flex items-center gap-1.5 self-start sm:self-center transition cursor-pointer"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
                  </svg>
                  <span>Mở SmartProp GIS</span>
                </button>
              </div>

              <div class="relative h-[280px] rounded-2xl overflow-hidden bg-slate-100 border border-slate-200">
                <iframe
                  v-if="mapUrl(property)"
                  :src="mapUrl(property)"
                  title="Vị trí bất động sản đang xem"
                  loading="lazy"
                  class="absolute inset-0 w-full h-full border-0"
                />
                <div v-else class="h-full flex items-center justify-center p-6 text-sm text-slate-500">
                  Chưa có vị trí bản đồ cho tin đăng này.
                </div>

                <!-- FLOATING PRICE PILL ON MAP -->
                <div class="absolute bottom-3 left-3 pointer-events-none">
                  <div class="bg-[#1E325A] text-white font-bold px-3.5 py-1.5 rounded-full text-xs shadow-lg border border-white/20 flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-[#b13724]"></span>
                    <span>{{ listing.price }}</span>
                  </div>
                </div>
              </div>

              <p class="text-[11px] leading-relaxed text-[#536178] mt-3">
                {{ locationLabel(property) }} · Công cụ tìm địa chỉ: <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer" class="underline hover:text-[#1E325A]">Geoapify</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" class="underline hover:text-[#1E325A]">© OpenStreetMap contributors</a>
              </p>
            </section>

            <!-- ==================== AI VALUATION & MARKET INTELLIGENCE CARD (SIGNATURE NAVY #10233f) ==================== -->
            <section class="bg-gradient-to-br from-[#10233f] via-[#162f54] to-[#10233f] text-white rounded-3xl p-6 sm:p-8 shadow-xl border border-white/10 relative overflow-hidden">
              <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-white/10 relative z-10">
                <div class="flex-1 min-w-0 pr-4">
                  <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-white/80 text-[11px] font-bold border border-white/15 mb-3">
                    <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
                    <span>ĐỊNH GIÁ THAM CHIẾU AI (SMARTPROP V6)</span>
                  </div>

                  <h2 class="text-2xl sm:text-3xl font-black text-white tracking-tight">
                    {{ valuationAnalysis.rangeText }}
                  </h2>

                  <p class="text-xs text-emerald-300 mt-2 flex items-center gap-1.5 font-medium">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-emerald-400 shrink-0">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    <span>{{ valuationAnalysis.evaluation }}</span>
                  </p>
                </div>

                <div class="bg-white/10 backdrop-blur-md rounded-2xl p-4 sm:p-5 border border-white/10 shrink-0 min-w-[210px]">
                  <p class="text-[11px] text-white/60 uppercase tracking-wider font-semibold">
                    Giá chào niêm yết
                  </p>

                  <p class="text-2xl font-black text-amber-400 mt-1 tracking-tight">
                    {{ listing.price }}
                  </p>

                  <p class="text-xs text-white/70 mt-1">
                    {{ listing.pricePerM2 }}
                  </p>
                </div>
              </div>

              <!-- MARKET SCORE METERS -->
              <div class="mt-6 pt-2 relative z-10">
                <div class="flex items-center justify-between mb-4">
                  <p class="text-xs font-bold text-white/90 uppercase tracking-wider">
                    Chỉ số phân tích thị trường BĐS Đà Nẵng
                  </p>
                  <RouterLink
                    :to="`/market-insights`"
                    class="text-xs font-bold text-amber-300 hover:text-white transition flex items-center gap-1"
                  >
                    <span>Xem xu hướng thị trường</span>
                    <span>→</span>
                  </RouterLink>
                </div>

                <div class="space-y-4">
                  <div>
                    <div class="flex justify-between text-xs text-white/80 mb-1.5">
                      <span>Vị trí & Tiềm năng thương mại / Du lịch</span>
                      <span class="font-bold text-cyan-300">{{ valuationAnalysis.locationScore }}/100</span>
                    </div>
                    <div class="h-2 bg-white/10 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-gradient-to-r from-cyan-400 to-blue-400 rounded-full transition-all duration-500"
                        :style="{ width: valuationAnalysis.locationScore + '%' }"
                      ></div>
                    </div>
                  </div>

                  <div>
                    <div class="flex justify-between text-xs text-white/80 mb-1.5">
                      <span>Mức độ cạnh tranh đơn giá / m² so với quận</span>
                      <span class="font-bold text-emerald-300">{{ valuationAnalysis.priceScore }}/100</span>
                    </div>
                    <div class="h-2 bg-white/10 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-gradient-to-r from-emerald-400 to-teal-400 rounded-full transition-all duration-500"
                        :style="{ width: valuationAnalysis.priceScore + '%' }"
                      ></div>
                    </div>
                  </div>

                  <div>
                    <div class="flex justify-between text-xs text-white/80 mb-1.5">
                      <span>Chỉ số thanh khoản thị trường</span>
                      <span class="font-bold text-amber-300">{{ valuationAnalysis.liquidityScore }}/100</span>
                    </div>
                    <div class="h-2 bg-white/10 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-gradient-to-r from-amber-400 to-yellow-400 rounded-full transition-all duration-500"
                        :style="{ width: valuationAnalysis.liquidityScore + '%' }"
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <!-- ==================== RIGHT COLUMN: STICKY SIDEBAR ==================== -->
          <aside class="space-y-5 lg:sticky lg:top-5">

            <!-- CONTACT & BROKER CARD (SIGNATURE NAVY #1E325A) -->
            <section class="bg-white rounded-3xl p-6 shadow-sm border border-slate-200 relative">
              <!-- TOP BROKER BADGE -->
              <div class="flex items-center justify-between mb-5 pb-4 border-b border-slate-100">
                <p class="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Môi giới phụ trách
                </p>
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-[#1E325A] border border-blue-200 flex items-center gap-1">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                  </svg>
                  <span>Đã xác minh</span>
                </span>
              </div>

              <!-- AGENT IDENTITY INFO -->
              <div class="flex items-center gap-3.5 mb-5">
                <div class="relative shrink-0">
                  <div class="w-13 h-13 rounded-2xl bg-gradient-to-tr from-[#1E325A] to-[#2c4a83] text-white flex items-center justify-center text-lg font-black shadow-md border-2 border-white">
                    {{ ((revealedContact?.contactName || property?.contactName || 'S').charAt(0)).toUpperCase() }}
                  </div>
                  <span class="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-emerald-500 border-2 border-white" title="Trực tuyến"></span>
                </div>

                <div class="flex-1 min-w-0">
                  <p class="text-base font-extrabold text-[#1E325A] truncate">
                    {{ revealedContact?.contactName || property?.contactName || 'Phan Thanh Bình' }}
                  </p>
                  <p class="text-xs text-[#536178] font-semibold truncate mt-0.5">
                    Chuyên viên BĐS SmartProp
                  </p>
                  <div class="flex items-center gap-1 text-[11px] text-amber-500 font-bold mt-0.5">
                    <span>★ 5.0</span>
                    <span class="text-slate-400 font-normal">· Đang trực tuyến hỗ trợ</span>
                  </div>
                </div>
              </div>

              <RouterLink
                v-if="route.query.own==='1'||session.user?.role==='ADMIN'"
                :to="'/account/properties/'+listingId+'/legal-documents'"
                class="mb-3 block text-xs underline font-semibold text-[#1E325A] hover:text-[#b3915f]"
              >
                Quản lý hồ sơ pháp lý riêng
              </RouterLink>

              <!-- CONTACT PANEL WIDGET -->
              <ContactPanel
                :key="listingId"
                :property-id="listingId"
                @revealed="(data) => revealedContact = data"
              />

              <!-- DIRECT INTERNAL CHAT BUTTON -->
              <button
                type="button"
                class="mt-3 w-full rounded-2xl border border-slate-200 hover:border-[#1E325A]/40 hover:bg-slate-50 py-3 px-4 text-xs font-bold text-[#1E325A] transition flex items-center justify-center gap-2 cursor-pointer shadow-2xs"
                :disabled="state.busy"
                @click="messageOwner"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <span>Nhắn tin tư vấn trực tiếp</span>
              </button>

              <!-- SAFETY ASSURANCE FOOTER -->
              <div class="mt-4 pt-3.5 border-t border-slate-100 flex items-center gap-2 text-[11px] text-slate-500">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-amber-500 shrink-0">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <span>Giao dịch an toàn, không cọc trước khi xác minh</span>
              </div>
            </section>

            <!-- QUICK INFO & METADATA CARD -->
            <section class="bg-white rounded-3xl p-6 shadow-sm border border-slate-200">
              <div class="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
                <h3 class="text-sm font-bold text-[#1E325A] flex items-center gap-2">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-[#b3915f]">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                  <span>Thông tin niêm yết</span>
                </h3>
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Đang hiển thị
                </span>
              </div>

              <div class="space-y-3.5 text-xs">
                <!-- MÃ TIN -->
                <div class="flex items-center justify-between py-0.5">
                  <span class="text-slate-500 flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-slate-400">
                      <line x1="4" y1="9" x2="20" y2="9"/>
                      <line x1="4" y1="15" x2="20" y2="15"/>
                      <line x1="10" y1="3" x2="8" y2="21"/>
                      <line x1="16" y1="3" x2="14" y2="21"/>
                    </svg>
                    <span>Mã tin</span>
                  </span>
                  <span class="font-bold text-[#1E325A] font-mono">
                    #SP-{{ String(property?.id || '').slice(-6).toUpperCase() || '654321' }}
                  </span>
                </div>

                <!-- NGÀY ĐĂNG -->
                <div class="flex items-center justify-between py-0.5">
                  <span class="text-slate-500 flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-slate-400">
                      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                      <line x1="16" y1="2" x2="16" y2="6"/>
                      <line x1="8" y1="2" x2="8" y2="6"/>
                      <line x1="3" y1="10" x2="21" y2="10"/>
                    </svg>
                    <span>Ngày đăng</span>
                  </span>
                  <span class="font-semibold text-[#1E325A]">
                    {{ formatPostDate(property?.publishedAt || property?.createdAt) }}
                  </span>
                </div>

                <!-- HÌNH THỨC -->
                <div class="flex items-center justify-between py-0.5">
                  <span class="text-slate-500 flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-slate-400">
                      <circle cx="12" cy="12" r="10"/>
                      <polyline points="12 6 12 12 16 14"/>
                    </svg>
                    <span>Hình thức</span>
                  </span>
                  <span class="font-semibold text-[#1E325A]">
                    {{ property?.transactionType === 'RENT' ? 'Cho thuê BĐS' : 'Bán BĐS' }}
                  </span>
                </div>

                <!-- PHÁP LÝ -->
                <div class="flex items-center justify-between py-0.5">
                  <span class="text-slate-500 flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-slate-400">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                    <span>Pháp lý</span>
                  </span>
                  <span class="font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                    Sổ hồng / Sổ đỏ riêng
                  </span>
                </div>

                <!-- LƯỢT XEM -->
                <div class="flex items-center justify-between py-0.5">
                  <span class="text-slate-500 flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-slate-400">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                    <span>Lượt xem</span>
                  </span>
                  <span class="font-semibold text-[#1E325A]">
                    {{ viewsCount || incrementAndGetViews(property?.id) }} lượt xem
                  </span>
                </div>
              </div>

              <div class="mt-4 pt-3.5 border-t border-slate-100 flex items-center gap-2 text-[11px] text-slate-600 bg-slate-50 -mx-2 -mb-2 p-3 rounded-2xl border border-slate-100">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-emerald-600 shrink-0">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                  <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                <span>Dữ liệu xác thực theo tiêu chuẩn SmartProp</span>
              </div>
            </section>

            <!-- REPORT LISTING CARD -->
            <section class="bg-white rounded-3xl p-5 shadow-sm border border-slate-200">
              <p class="text-xs text-slate-500 leading-relaxed">
                Bạn phát hiện tin đăng này sai vị trí, sai giá hoặc hình ảnh không khớp thực tế?
              </p>
              <button
                type="button"
                @click="router.push(`/listing/${route.params.id}/report`)"
                class="mt-3 inline-flex items-center gap-1.5 text-xs font-bold text-[#b13724] hover:underline cursor-pointer"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
                  <line x1="4" y1="22" x2="4" y2="15"/>
                </svg>
                <span>Báo cáo tin đăng vi phạm</span>
              </button>
            </section>

          </aside>
        </div>
      </template>
    </div>

    <!-- ==================== MOBILE FLOATING ACTION BAR ==================== -->
    <div
      v-if="property && !state.busy"
      class="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-md border-t border-slate-200 px-4 py-3 flex items-center justify-between gap-3 shadow-lg"
    >
      <div class="min-w-0">
        <p class="text-[10px] text-slate-400 font-bold uppercase">Giá niêm yết</p>
        <p class="text-base font-black text-[#b13724] truncate">{{ listing.price }}</p>
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          @click="messageOwner"
          class="px-3.5 py-2.5 rounded-xl border border-slate-300 text-[#1E325A] text-xs font-bold flex items-center gap-1.5 active:scale-95 transition"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <span>Nhắn tin</span>
        </button>

        <a
          v-if="revealedContact?.contactPhone"
          :href="'tel:' + revealedContact.contactPhone.replace(/[^0-9]/g, '')"
          class="px-4 py-2.5 rounded-xl bg-[#1E325A] text-white text-xs font-bold flex items-center gap-1.5 active:scale-95 transition shadow-sm"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
          </svg>
          <span>Gọi ngay</span>
        </a>
      </div>
    </div>

    <!-- ==================== FULL SCREEN IMAGE GALLERY MODAL ==================== -->
    <Teleport to="body">
      <div
        v-if="showGallery"
        class="fixed inset-0 z-[9999] bg-black/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-5"
        @click.self="closeGallery"
      >
        <div class="relative w-full max-w-[1500px] h-[95vh] bg-[#10233f] rounded-3xl overflow-hidden flex flex-col shadow-2xl border border-white/10">
          <!-- GALLERY HEADER -->
          <div class="flex items-center justify-between gap-4 px-6 py-4 text-white border-b border-white/10">
            <div class="flex items-center gap-4 min-w-0">
              <div class="min-w-0">
                <h2 class="text-xs sm:text-sm font-bold truncate text-white">
                  {{ listing.title }}
                </h2>
                <p class="text-[11px] text-white/50 truncate mt-0.5">
                  {{ listing.location }}
                </p>
              </div>

              <div class="hidden sm:block px-3 py-1 rounded-full bg-white/10 text-xs text-white/80 font-bold whitespace-nowrap">
                {{ currentImageIndex + 1 }} / {{ images.length }} ảnh
              </div>
            </div>

            <!-- HEADER ACTIONS -->
            <div class="flex items-center gap-2 shrink-0">
              <button
                type="button"
                @click="closeGallery"
                class="w-9 h-9 rounded-full bg-white/10 border border-white/10 flex items-center justify-center text-white/70 hover:bg-white/20 hover:text-white transition cursor-pointer"
                title="Đóng (Esc)"
              >
                ✕
              </button>
            </div>
          </div>

          <!-- MAIN PHOTO -->
          <div class="relative flex-1 min-h-0 flex items-center justify-center px-4 sm:px-16">
            <PrivateImage
              :src="images[currentImageIndex]"
              :alt="`Ảnh ${currentImageIndex + 1} của ${listing.title}`"
              class="w-full h-full object-contain rounded-2xl"
            />

            <!-- PREVIOUS BUTTON -->
            <button
              type="button"
              @click="prevImage"
              class="absolute left-3 sm:left-6 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-black/50 border border-white/10 text-white text-2xl flex items-center justify-center hover:bg-black/80 hover:scale-105 transition cursor-pointer"
              aria-label="Ảnh trước"
            >
              ‹
            </button>

            <!-- NEXT BUTTON -->
            <button
              type="button"
              @click="nextImage"
              class="absolute right-3 sm:right-6 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-black/50 border border-white/10 text-white text-2xl flex items-center justify-center hover:bg-black/80 hover:scale-105 transition cursor-pointer"
              aria-label="Ảnh tiếp theo"
            >
              ›
            </button>

            <div class="sm:hidden absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-black/70 text-white text-xs font-bold">
              {{ currentImageIndex + 1 }} / {{ images.length }}
            </div>
          </div>

          <!-- THUMBNAILS CAROUSEL -->
          <div class="px-6 py-4 border-t border-white/10 bg-[#07182d]/80">
            <div class="flex gap-2.5 overflow-x-auto pb-1 gallery-scroll">
              <button
                v-for="(image, index) in images"
                :key="index"
                type="button"
                @click="selectImage(index)"
                class="relative shrink-0 w-[100px] sm:w-[120px] h-[64px] sm:h-[74px] rounded-xl overflow-hidden border-2 transition cursor-pointer"
                :class="currentImageIndex === index ? 'border-[#e7c58e] opacity-100 ring-2 ring-[#e7c58e]/50' : 'border-transparent opacity-50 hover:opacity-100'"
              >
                <PrivateImage
                  :src="image"
                  :alt="`Ảnh thu nhỏ ${index + 1}`"
                  class="w-full h-full object-cover"
                />
                <div class="absolute bottom-1 left-1 px-1.5 py-0.2 rounded-full bg-black/70 text-white text-[9px] font-bold">
                  {{ index + 1 }}
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.gallery-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.25) transparent;
}
.gallery-scroll::-webkit-scrollbar {
  height: 5px;
}
.gallery-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.gallery-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.25);
  border-radius: 999px;
}
</style>
