<script setup>
import {ref,computed,watch,onMounted,onBeforeUnmount} from 'vue'
import {useRouter,useRoute} from 'vue-router'
import {api,session,errorText} from '../auth/api.js'
import {useList,adapt,money,LegacyState,LegacyPager,PrivateImage,types,states,reasons as reasonLabels,date,mapUrl} from '../../lib/legacy.js'


import {isPublicProperty} from './usePublicListings.js'
import ContactPanel from './ContactPanel.vue'
import PropertyExplorer from '../map/PropertyExplorer.vue'
import {locationLabel} from '../map/locationDisplay.js'
const route=useRoute(),router=useRouter(),state=ref({busy:false,error:'',notice:'',notFound:false}),property=ref(null),isFavorite=ref(false),showGallery=ref(false),currentImageIndex=ref(0);
const listing=computed(()=>adapt(property.value)),listingId=computed(()=>route.params.id),images=computed(()=>property.value?.images?.map(i=>i.url)||[]);
const openGallery=(index=0)=>{if(!images.value.length)return;currentImageIndex.value=Math.min(index,images.value.length-1);showGallery.value=true;document.body.style.overflow='hidden'},closeGallery=()=>{showGallery.value=false;document.body.style.overflow=''},nextImage=()=>currentImageIndex.value=(currentImageIndex.value+1)%Math.max(images.value.length,1),prevImage=()=>currentImageIndex.value=(currentImageIndex.value-1+images.value.length)%Math.max(images.value.length,1),selectImage=i=>currentImageIndex.value=i;
const goHome=()=>router.push('/home'),goMap=()=>router.push({path:'/map',query:{propertyId:String(route.params.id)}}),goAccount=()=>router.push('/account');
let loadSequence=0
async function load(){
 const run=++loadSequence,id=route.params.id,own=route.query.own==='1';closeGallery();property.value=null;isFavorite.value=false;Object.assign(state.value,{busy:true,error:'',notice:'',notFound:false})
 try{
  const result=await api((own?'/users/me/properties/':'/properties/')+encodeURIComponent(id),{authenticated:own});if(run!==loadSequence)return
  const value=own?result.property:result;if(!own&&!isPublicProperty(value))throw Object.assign(Error(),{status:404})
  property.value=value
 }catch(e){if(run===loadSequence){state.value.notFound=e.status===404||e.status===400;state.value.error=state.value.notFound?'Tin đăng không tồn tại hoặc không còn được công khai.':errorText(e)}}finally{if(run===loadSequence)state.value.busy=false}
}
async function messageOwner(){if(!session.token)return router.push('/login');state.value.busy=true;state.value.error='';try{const c=await api('/conversations',{method:'POST',body:{propertyId:route.params.id}});await router.push({path:'/account/messages',query:{conversation:c.id}})}catch(e){state.value.error=errorText(e)}finally{state.value.busy=false}}
async function toggleFavorite(){if(!session.token)return router.push('/login');try{await api('/users/me/saved-properties/'+route.params.id,{method:isFavorite.value?'DELETE':'PUT'});isFavorite.value=!isFavorite.value}catch(e){state.value.error=errorText(e)}}
watch(()=>[route.params.id,route.query.own],load,{immediate:true});onBeforeUnmount(()=>{loadSequence++;closeGallery()});

</script>

<template>
  <div class="min-h-screen bg-[#ebe9e2] text-[#1E325A]">

    



    

    <div class="max-w-[1400px] mx-auto px-6 md:px-10 pt-6 pb-20">
<LegacyState :state="{...state,load}" />

      

      <button
        @click="router.back()"
        class="text-xs text-gray-500 hover:text-[#1E325A] mb-5"
      >
        ← Quay lại
      </button>

      <div v-if="!property&&!state.busy" class="rounded-2xl bg-white p-6 text-sm"><p>{{state.notFound?'Không tìm thấy tin đăng công khai.':'Chưa tải được tin đăng.'}}</p><button type="button" class="mt-3 underline" @click="load">Thử tải lại</button><RouterLink to="/listings" class="ml-4 underline">Xem danh sách bất động sản</RouterLink></div><template v-if="property&&!state.busy">

      <section
        class="grid grid-cols-1 gap-3 h-auto lg:h-[430px]" :class="images.length>1?'lg:grid-cols-[2fr_1fr]':''"
      >

        

        <div
          @click="openGallery(0)"
          class="relative min-h-[300px] lg:min-h-0 rounded-[24px] overflow-hidden bg-[#d9d6ce] cursor-pointer group"
        >
          <PrivateImage
            :src="images[0]"
            :alt="listing.title"
            class="absolute inset-0 w-full h-full object-cover transition duration-300 group-hover:scale-[1.02]"
          />

          

          <button
            @click.stop="toggleFavorite"
            class="absolute top-4 right-4 w-10 h-10 rounded-full bg-white shadow flex items-center justify-center text-xl transition z-20"
            :class="isFavorite ? 'text-red-500' : 'text-[#1E325A]'"
          >
            {{ isFavorite ? '♥' : '♡' }}
          </button>
        </div>

        

        <div v-if="images.length>1" class="grid grid-cols-2 lg:grid-cols-1 gap-3">

          

          <div
            @click="openGallery(1)"
            class="relative min-h-[150px] rounded-[20px] bg-[#d9d6ce] overflow-hidden cursor-pointer group"
          >
            <PrivateImage
              :src="images[1]"
              alt="Ảnh bất động sản"
              class="absolute inset-0 w-full h-full object-cover transition duration-300 group-hover:scale-105"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">

            

            <div
              v-if="images.length>2" @click="openGallery(2)"
              class="relative min-h-[150px] rounded-[20px] bg-[#d9d6ce] overflow-hidden cursor-pointer group"
            >
              <PrivateImage
                :src="images[2]"
                alt="Ảnh bất động sản"
                class="absolute inset-0 w-full h-full object-cover transition duration-300 group-hover:scale-105"
              />
            </div>

            

            <div
              v-if="images.length>3" @click="openGallery(3)"
              class="relative min-h-[150px] rounded-[20px] bg-[#1E325A] overflow-hidden cursor-pointer group"
            >
              <PrivateImage
                :src="images[3]"
                alt="Ảnh bất động sản"
                class="absolute inset-0 w-full h-full object-cover opacity-55 transition duration-300 group-hover:scale-105"
              />

              <div
                class="absolute inset-0 flex items-center justify-center bg-[#1E325A]/40"
              >
                <span class="text-white text-lg font-semibold">
                  {{images.length>3?'+'+(images.length-3)+' ảnh':images.length+' ảnh'}}
                </span>
              </div>
            </div>

          </div>
        </div>
      </section>

      

      <div
        class="grid grid-cols-1 lg:grid-cols-[1fr_330px] gap-6 mt-6 items-start"
      >

        

        <div class="space-y-5">

          

          <section
            class="bg-white rounded-[24px] p-6 md:p-8 shadow-sm"
          >
            <div
              class="flex flex-col md:flex-row md:items-start justify-between gap-5"
            >
              <div>

                <div
                  class="inline-flex px-3 py-1 rounded-full bg-[#e5f3ea] text-[#438665] text-xs mb-3"
                >
                  {{ listing.type }}
                </div>

                <h1
                  class="text-2xl md:text-3xl font-semibold tracking-tight text-[#1E325A]"
                >
                  {{ listing.title }}
                </h1>

                <p class="text-xs text-gray-400 mt-2">
                  {{ listing.location }}
                </p>
              </div>

              <div class="md:text-right">

                <p
                  class="text-2xl md:text-3xl font-semibold text-[#1E325A]"
                >
                  {{ listing.price }}
                </p>

                <p class="text-xs text-gray-400 mt-1">
                  {{ listing.pricePerM2 }}
                </p>

              </div>
            </div>

            

            <div
              class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-7 pt-6 border-t border-gray-100"
            >
              <div>
                <p class="text-xs text-gray-400">
                  Diện tích
                </p>

                <p class="text-sm font-semibold mt-1">
                  {{ listing.area }}
                </p>
              </div>

              <div>
                <p class="text-xs text-gray-400">
                  Phòng ngủ
                </p>

                <p class="text-sm font-semibold mt-1">
                  {{property.bedrooms??'Chưa cung cấp'}}
                  <span v-if="property.bedrooms!=null">
                    PN
                  </span>
                </p>
              </div>

              <div>
                <p class="text-xs text-gray-400">
                  Phòng tắm
                </p>

                <p class="text-sm font-semibold mt-1">
                  {{property.bathrooms??'Chưa cung cấp'}}
                  <span v-if="property.bathrooms!=null">
                    WC
                  </span>
                </p>
              </div>

              <div>
                <p class="text-xs text-gray-400">
                  Hướng
                </p>

                <p class="text-sm font-semibold mt-1">
                  {{ listing.direction }}
                </p>
              </div>
            </div>
          </section>

          

          <section
            class="bg-white rounded-[24px] p-6 md:p-8 shadow-sm"
          >
            <h2 class="text-base font-semibold mb-4">
              Mô tả
            </h2>

            <p class="text-xs text-gray-500 leading-6">
              {{ listing.description1 }}
            </p>

            <p class="text-xs text-gray-500 leading-6 mt-3">
              {{ listing.description2 }}
            </p>
          </section>

          

          <section
            v-if="listing.hasWarning"
            class="rounded-[24px] p-6 md:p-8 bg-[#f7e9df] border border-[#e6c9b6]"
          >
            <div
              class="flex flex-col md:flex-row md:items-center justify-between gap-5"
            >
              <div>

                <div class="flex items-center gap-2 mb-2">

                  <div
                    class="w-8 h-8 rounded-lg bg-[#c9683c] text-white flex items-center justify-center"
                  >
                    !
                  </div>

                  <h2 class="font-semibold text-[#9c4e2e]">
                    Đối chiếu hình ảnh bằng AI
                  </h2>
                </div>

                <p
                  class="text-xs text-[#a26b53] max-w-2xl leading-5"
                >
                  Hệ thống phát hiện hình ảnh trong tin đăng có mức độ
                  tương đồng cao với một số hình ảnh khác.
                  Bạn nên kiểm tra kỹ trước khi giao dịch.
                </p>
              </div>

              <div
                class="px-4 py-2 rounded-full bg-[#c9683c] text-white text-xs whitespace-nowrap"
              >
                {{ listing.statusText }}
              </div>
            </div>
          </section>

          

          <section
            v-else
            class="rounded-[24px] p-6 md:p-8 bg-[#e5f3ea] border border-[#c9e5d5]"
          >
            <div class="flex items-center justify-between gap-5">

              <div>
                <h2 class="font-semibold text-[#438665]">
                  Kiểm tra hình ảnh
                </h2>

                <p class="text-xs text-[#438665]/80 mt-2">
                  Chưa có kết quả đối chiếu hình ảnh cho tin đăng này.
                </p>
              </div>

              <div
                class="px-4 py-2 rounded-full bg-[#438665] text-white text-xs"
              >
                {{ listing.statusText }}
              </div>
            </div>
          </section>

          <section v-if="property.declaredAmenities?.length" class="bg-white rounded-[24px] p-6 md:p-8 shadow-sm"><h2 class="text-base font-semibold mb-4">Tiện ích trong bất động sản</h2><div class="flex flex-wrap gap-2"><span v-for="amenity in property.declaredAmenities" :key="amenity" class="rounded-full bg-[#f5f4ef] px-3 py-2 text-xs">{{amenity}}</span></div></section>
<section aria-label="Vị trí và tiện ích xung quanh"><PropertyExplorer :items="[property]" :selected-id="property.id" :allow-nearby="route.query.own!=='1'" compact /></section>

          

          <section
            class="bg-[#1E325A] text-white rounded-[24px] p-6 md:p-8 shadow-sm"
          >
            <div
              class="flex flex-col md:flex-row md:items-center justify-between gap-6"
            >
              <div>
                <p
                  class="text-xs text-white/50 uppercase tracking-widest"
                >
                  Định giá tham chiếu
                </p>

                <h2 class="text-2xl font-semibold mt-2">
                  {{ listing.valuation }}
                </h2>

                <p class="text-xs text-white/60 mt-2">
                  Chưa có dữ liệu định giá tự động cho tin này.
                </p>
              </div>

              <div class="bg-white/10 rounded-2xl px-5 py-4">

                <p class="text-xs text-white/60">
                  Giá tin đăng
                </p>

                <p class="text-lg font-semibold mt-1">
                  {{ listing.price }}
                </p>

                <p class="text-xs text-emerald-300 mt-1">
                  Chưa có kết quả so sánh giá
                </p>
              </div>
            </div>

            <div class="mt-7 border-t border-white/10 pt-5">

              <p class="text-xs font-medium mb-4">
                Các yếu tố ảnh hưởng đến giá
              </p>

              <div class="space-y-3">

                <div>
                  <div
                    class="flex justify-between text-xs text-white/60 mb-1"
                  >
                    <span>Vị trí trung tâm</span>
                    <span>—</span>
                  </div>

                  <div class="h-1.5 bg-white/10 rounded-full">
                    <div
                      class="h-full w-0 bg-white/70 rounded-full"
                    ></div>
                  </div>
                </div>

                <div>
                  <div
                    class="flex justify-between text-xs text-white/60 mb-1"
                  >
                    <span>Diện tích</span>
                    <span>—</span>
                  </div>

                  <div class="h-1.5 bg-white/10 rounded-full">
                    <div
                      class="h-full w-0 bg-white/70 rounded-full"
                    ></div>
                  </div>
                </div>

                <div>
                  <div
                    class="flex justify-between text-xs text-white/60 mb-1"
                  >
                    <span>Khoảng cách tiện ích</span>
                    <span>—</span>
                  </div>

                  <div class="h-1.5 bg-white/10 rounded-full">
                    <div
                      class="h-full w-0 bg-white/70 rounded-full"
                    ></div>
                  </div>
                </div>

              </div>
            </div>
          </section>

        </div>

        

        <aside class="space-y-4 lg:sticky lg:top-5">

          

          <section
            class="bg-white rounded-[24px] p-6 shadow-sm"
          >
            <p class="text-xs text-gray-400 mb-4">
              Người đăng
            </p>

            <div class="flex items-center gap-3">

              <div
                class="w-11 h-11 rounded-full bg-[#1E325A] text-white flex items-center justify-center text-xs font-semibold"
              >S</div>

              <div>
                <p class="text-sm font-semibold">
                  Thông tin người đăng
                </p>

                <p class="text-xs text-gray-400 mt-1">
                  Liên hệ được bảo vệ; bấm bên dưới để xem.
                </p>
              </div>

            </div>

            <RouterLink v-if="route.query.own==='1'||session.user?.role==='ADMIN'" :to="'/account/properties/'+listingId+'/legal-documents'" class="mb-3 block text-xs underline">Quản lý hồ sơ pháp lý riêng</RouterLink><ContactPanel :key="listingId" :property-id="listingId" /><button type="button" class="mt-3 w-full rounded-full border p-3 text-xs" :disabled="state.busy" @click="messageOwner">Nhắn tin</button>

            <p
              class="text-xs text-gray-400 text-center mt-4 leading-4"
            >
              Không chuyển tiền hoặc đặt cọc trước khi xác minh
              thông tin bất động sản.
            </p>
          </section>

          

          <section
            class="bg-white rounded-[24px] p-6 shadow-sm"
          >
            <h3 class="text-sm font-semibold mb-4">
              Thông tin tin đăng
            </h3>

            <div class="space-y-3 text-xs break-all">

              <div class="flex justify-between">
                <span class="text-gray-400">
                  Mã tin
                </span>

                <span>
                  {{ listingId }}
                </span>
              </div>

              <div class="flex justify-between">
                <span class="text-gray-400">
                  Ngày đăng
                </span>

                <span>
                  {{ date(property?.publishedAt || property?.createdAt) }}
                </span>
              </div>

              <div class="flex justify-between">
                <span class="text-gray-400">
                  Lượt xem
                </span>

                <span>—</span>
              </div>

              <div class="flex justify-between">
                <span class="text-gray-400">
                  Lượt lưu
                </span>

                <span>—</span>
              </div>

            </div>
          </section>

          

          <section
            class="bg-white rounded-[24px] p-5 shadow-sm"
          >
            <p class="text-xs text-gray-400 leading-5">
              Bạn thấy thông tin hoặc hình ảnh của tin đăng này
              có vấn đề?
            </p>

            <button
  @click="router.push(`/listing/${route.params.id}/report`)"
  class="mt-3 text-xs text-[#b65c3c] hover:underline cursor-pointer"
>
  ⚑ Báo cáo tin đăng
</button>
          </section>

        </aside>
      </div>
    </template></div>

    
    
    

    <Teleport to="body">
      <div
        v-if="showGallery"
        class="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center p-2 md:p-5"
        @click.self="closeGallery"
      >
        <div
          class="relative w-full max-w-[1500px] h-[95vh] bg-[#11182a] rounded-[28px] overflow-hidden flex flex-col shadow-2xl"
        >

          

          <div
            class="flex items-center justify-between gap-4 px-5 md:px-8 py-4 text-white"
          >

            

            <div class="flex items-center gap-4 min-w-0">

              <div class="min-w-0">

                <h2
                  class="text-xs md:text-sm font-medium truncate"
                >
                  {{ listing.title }}
                </h2>

                <p
                  class="text-xs md:text-xs text-white/40 mt-1 truncate"
                >
                  {{ listing.location }}
                </p>

              </div>

              

              <div
                class="hidden sm:block px-3 py-1 rounded-full bg-white/10 text-xs text-white/70 whitespace-nowrap"
              >
                {{ currentImageIndex + 1 }} / {{ images.length }} ảnh
              </div>

            </div>

            

            <div class="flex items-center gap-2 shrink-0">

              <button
                class="hidden sm:block px-4 py-2 rounded-full border border-white/10 bg-white/5 text-xs text-white/70 hover:bg-white/10 transition"
              >
                Tải ảnh
              </button>

              <button
                class="hidden md:block px-4 py-2 rounded-full border border-white/10 bg-white/5 text-xs text-white/70 hover:bg-white/10 transition"
              >
                Báo cáo ảnh sai
              </button>

              

              <button
                @click="closeGallery"
                class="w-9 h-9 rounded-full border border-white/10 bg-white/5 flex items-center justify-center text-white/70 hover:bg-white/10 hover:text-white transition"
              >
                ✕
              </button>

            </div>
          </div>

          

          <div
            class="relative flex-1 min-h-0 flex items-center justify-center px-5 md:px-16"
          >

            <PrivateImage
              :src="images[currentImageIndex]"
              :alt="`Ảnh ${currentImageIndex + 1} của ${listing.title}`"
              class="w-full h-full object-contain rounded-[18px]"
            />

            

            <button
              @click="prevImage"
              class="absolute left-3 md:left-5 top-1/2 -translate-y-1/2 w-11 h-11 md:w-12 md:h-12 rounded-full bg-white/10 border border-white/10 text-white text-3xl flex items-center justify-center hover:bg-white/20 transition"
              aria-label="Ảnh trước"
            >
              ‹
            </button>

            

            <button
              @click="nextImage"
              class="absolute right-3 md:right-5 top-1/2 -translate-y-1/2 w-11 h-11 md:w-12 md:h-12 rounded-full bg-white/10 border border-white/10 text-white text-3xl flex items-center justify-center hover:bg-white/20 transition"
              aria-label="Ảnh tiếp theo"
            >
              ›
            </button>

            

            <div
              class="sm:hidden absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-black/50 text-white text-xs"
            >
              {{ currentImageIndex + 1 }} / {{ images.length }}
            </div>

          </div>

          

          <div class="px-5 md:px-8 py-4">

            <div
              class="flex gap-2 overflow-x-auto pb-1 gallery-scroll"
            >

              <button
                v-for="(image, index) in images"
                :key="index"
                @click="selectImage(index)"
                class="relative shrink-0 w-[105px] md:w-[130px] h-[65px] md:h-[78px] rounded-xl overflow-hidden border-2 transition"
                :class="
                  currentImageIndex === index
                    ? 'border-white opacity-100'
                    : 'border-transparent opacity-50 hover:opacity-100'
                "
              >
                <PrivateImage
                  :src="image"
                  :alt="`Ảnh thu nhỏ ${index + 1}`"
                  class="w-full h-full object-cover"
                />

                <div
                  class="absolute bottom-1 left-1 px-1.5 py-0.5 rounded-full bg-black/60 text-white text-[8px]"
                >
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
.map-pattern {
  background-color: #dedbd2;

  background-image: repeating-linear-gradient(
    120deg,
    rgba(255, 255, 255, 0.45) 0,
    rgba(255, 255, 255, 0.45) 12px,
    rgba(205, 202, 194, 0.35) 12px,
    rgba(205, 202, 194, 0.35) 24px
  );
}

/* Gallery thumbnail scrollbar */
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