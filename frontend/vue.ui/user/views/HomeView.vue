<script setup>
import { ref, computed, watch, nextTick, defineAsyncComponent, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import HeroBackground from '../../src/components/HeroBackground.vue'
import HomeSectionNav from '../../src/components/HomeSectionNav.vue'
import ListingFilters from '../../src/components/ListingFilters.vue'
import ListingCard from '../../src/components/business/ListingCard.vue'
import HomeGIS from '../../src/components/HomeGIS.vue'
import HomeFinance from '../../src/components/HomeFinance.vue'
import ProjectDirectory from '../../src/components/ProjectDirectory.vue'
import MarketSummary from '../../src/components/MarketSummary.vue'
import TopSearchedAreas from '../../src/components/TopSearchedAreas.vue'
import { usePublicListings } from '../../src/services/usePublicListings.js'
import { useListingFilters } from '../../src/services/useListingFilters.js'
import { useComparison } from '../../src/services/useComparison.js'
import { lifestylePresets } from '../../src/services/listingFilters.js'
import { LegacyState, LegacyPager } from '../../src/services/legacy.js'
import { scrollHomeSection } from '../../src/services/siteNavigation.js'
import { usePublicProjects } from '../../src/services/usePublicProjects.js'
const MarketIntelligence = defineAsyncComponent(() => import('../../src/components/MarketIntelligence.vue'))
const route = useRoute(), search = useListingFilters(), compare = useComparison()
const state = usePublicListings(() => search.filters.value, { size: 6 })
const projectState = usePublicProjects({ size: 6 })
const selectedId = ref(null), lifestyleId = ref(''), advanced = ref(null), finance = ref(null), demoOpen = ref(false), demoLoaded = ref(false)
const projectDialog = ref(null), selectedProject = ref(null)
const lifestyle = computed(() => lifestylePresets.find(item => item.id === lifestyleId.value))
watch(() => state.items, items => { if (!state.busy && !items.some(item => item.id === selectedId.value)) selectedId.value = items[0]?.id || null })
watch(demoOpen, value => { if (value) demoLoaded.value = true })
watch(() => search.filters.value, filters => {
  if (lifestyle.value && !Object.entries(lifestyle.value.filters).every(([key, value]) => String(filters[key]) === String(value) || key === 'district' && lifestyle.value.districts?.includes(filters.district))) lifestyleId.value = ''
})
const scrollTo = scrollHomeSection
async function chooseLifestyle(item) { lifestyleId.value = item.id; await search.set(item.filters); lifestyleId.value = item.id; scrollTo('properties') }
async function showAdvanced() { scrollTo('properties'); await nextTick(); advanced.value?.expand(); document.getElementById('search')?.querySelector('input')?.focus({ preventScroll: true }) }
function showOnMap(id) { selectedId.value = id; scrollTo('gis') }
async function financialTab(tab) { finance.value?.select(tab); await nextTick(); scrollTo('finance') }
async function openProject(project) { selectedProject.value = project; await nextTick(); projectDialog.value?.showModal() }
onMounted(() => { if (['#valuation', '#investment'].includes(route.hash)) financialTab(route.hash.slice(1)) })
watch(() => route.hash, hash => { if (['#valuation', '#investment'].includes(hash)) financialTab(hash.slice(1)) })
</script>

<template>
  <div class="sp-home home-v3">
    <div>
      <section id="home" class="home-hero" aria-labelledby="home-title">
        <HeroBackground />
        <div class="hero-shade" aria-hidden="true"></div>
        <div class="hero-content home-container">

          <div class="hero-intro"><p class="hero-location">⌖ &nbsp; ĐÀ NẴNG</p><h1 id="home-title">Sống trọn Đà Nẵng.<br /><span>Tìm nơi bạn thuộc về.</span></h1><p>Khám phá bất động sản, kết nối không gian sống.<br class="desktop-break" /> Chọn ngôi nhà bằng dữ liệu và góc nhìn của riêng bạn.</p><div class="hero-ctas"><button type="button" class="gold-button" @click="scrollTo('search')">Khám phá bất động sản ↓</button><button type="button" class="ghost-button" @click="scrollTo('gis')">Khám phá bản đồ ↗</button><RouterLink to="/market" class="ghost-button" data-market-home>Dữ liệu thị trường ↗</RouterLink><RouterLink to="/advisor" class="ghost-button" data-advisor-home>Tư vấn BĐS theo nhu cầu ↗</RouterLink></div></div>
        </div>
      </section>
      <HomeSectionNav :district="search.filters.value.district" :filters="search.filters.value" />

      <section id="properties" class="home-section properties-section" aria-labelledby="properties-title"><div class="home-container">
        <div class="section-heading"><div><p class="eyebrow">TIN ĐĂNG CÔNG KHAI</p><h2 id="properties-title">Khám phá <span>bất động sản.</span></h2><p>Tin đã được duyệt và còn hiệu lực trên SmartProp.</p></div></div>
        <ListingFilters ref="advanced" :model-value="search.filters.value" @update:model-value="search.set" @search="scrollTo('properties')" />
        <div class="results-info"><p aria-live="polite">{{ state.busy ? 'Đang tìm tin phù hợp…' : state.totalElements + ' tin phù hợp' }}<span v-if="search.filters.value.district"> · {{ search.filters.value.district }}</span><span v-if="search.filters.value.transactionType"> · {{ search.filters.value.transactionType === 'SALE' ? 'Mua bán' : 'Cho thuê' }}</span></p><span class="compare-count">So sánh {{ compare.items.value.length }}/3</span></div>
        <LegacyState :state="state" />
        <div v-if="state.busy" class="listing-skeletons" aria-hidden="true"><div v-for="n in 3" :key="n"></div></div>
        <div v-else-if="state.items.length" class="home-property-grid"><ListingCard v-for="property in state.items" :key="property.id" :property="property" :class="{ 'map-selected-card': selectedId === property.id }" :data-home-property="property.id"><button type="button" class="card-map-button" :aria-pressed="selectedId === property.id" @click="showOnMap(property.id)">⌖ Bản đồ</button><button type="button" class="card-compare-button" :aria-pressed="compare.has(property.id)" @click="compare.toggle(property)">{{ compare.has(property.id) ? '✓ Đã chọn' : '+ So sánh' }}</button></ListingCard></div>
        <div v-else-if="!state.error" class="home-empty"><span aria-hidden="true">⌕</span><h3>Chưa tìm thấy bất động sản</h3><p>Thử khu vực khác hoặc mở rộng điều kiện tìm kiếm.</p><button type="button" class="navy-button" @click="search.reset(); lifestyleId = ''">Xóa bộ lọc</button></div>
        <p v-if="compare.notice.value" class="compare-notice" role="status">{{ compare.notice.value }}</p><LegacyPager :state="state" />
        <div class="view-all"><RouterLink :to="search.link('/listings')" class="navy-button">Xem tất cả bất động sản <span aria-hidden="true">→</span></RouterLink><p>Giữ nguyên bộ lọc khi mở danh sách hoặc bản đồ.</p></div>
      </div></section>

      <section id="gis" class="home-section home-container" aria-labelledby="gis-title"><div class="section-heading"><div><p class="eyebrow">GIS EXPLORER</p><h2 id="gis-title">Nhìn ngôi nhà. <span>Hiểu vị trí.</span></h2><p>Chọn ghim hoặc tin để khám phá cùng một vị trí trên bản đồ.</p></div><span class="real-data-label">● Dữ liệu tin đăng</span></div><HomeGIS v-model:selected-id="selectedId" :items="state.items" :total="state.totalElements" :busy="state.busy" :error="state.error" :map-link="search.link('/map', selectedId ? { propertyId: selectedId } : {})" @retry="state.reload" /></section>

      <section id="lifestyle" class="home-section home-container" aria-labelledby="lifestyle-title">
        <div class="section-heading"><div><p class="eyebrow">CHỌN THEO NHU CẦU</p><h2 id="lifestyle-title">Một phong cách sống. <span>Nhiều lựa chọn.</span></h2><p>Bắt đầu từ điều bạn tìm kiếm ở một ngôi nhà.</p></div><span class="section-number" aria-hidden="true">01 / EXPLORE</span></div>
        <div class="lifestyle-grid"><button v-for="item in lifestylePresets" :key="item.id" type="button" class="lifestyle-card" :aria-pressed="lifestyleId === item.id" @click="chooseLifestyle(item)"><span class="lifestyle-image"><img :src="'/media/projects/' + item.image + '.jpg'" alt="" loading="lazy" decoding="async" width="320" height="180" /><span class="lifestyle-symbol" aria-hidden="true">{{ item.icon }}</span></span><span class="lifestyle-name">{{ item.title }} <span aria-hidden="true">↗</span></span><span class="lifestyle-caption">{{ item.id === 'coast' || item.id === 'central' ? 'Gợi ý theo khu vực' : 'Bộ lọc theo thông tin tin đăng' }}</span></button></div>
        <p class="image-note">Ảnh dự án minh họa phong cách sống, không phải ảnh của các tin trong kết quả.</p>
        <div v-if="lifestyle" class="lifestyle-explanation" role="status"><strong>{{ lifestyle.title }}</strong><p>{{ lifestyle.explanation }}</p><div v-if="lifestyle.districts" class="district-suggestions"><button v-for="district in lifestyle.districts" :key="district" type="button" @click="search.patch({ district })">Gợi ý {{ district }} ↗</button></div><button type="button" @click="lifestyleId = ''; search.reset()">Xóa gợi ý và bộ lọc</button></div>
      </section>

      <section id="market" class="home-section market-section" aria-labelledby="market-title">
        <div class="home-container">
          <div class="section-heading">
            <div>
              <p class="eyebrow">MARKET INTELLIGENCE</p>
              <h2 id="market-title">Dữ liệu cho <span>quyết định của bạn.</span></h2>
              <p>Giá chào từ tin thật, trình bày riêng với biểu đồ mô phỏng.</p>
            </div>
            <div class="heading-actions flex items-center gap-3">
              <span class="real-data-label">GIÁ CHÀO · KHÔNG PHẢI GIÁ GIAO DỊCH</span>
              <RouterLink to="/market" class="gold-button inline-flex items-center gap-2" data-market-section-btn>
                <span>Chuyên trang Thị trường /market</span>
                <span aria-hidden="true">→</span>
              </RouterLink>
            </div>
          </div>
        </div>
        <MarketSummary :district="search.filters.value.district" />
        <div class="home-container my-8">
          <div class="rounded-3xl border border-[#e7e1d7] bg-white p-6 sm:p-8">
            <TopSearchedAreas eyebrow="XU HƯỚNG TÌM KIẾM · ĐÀ NẴNG" mode="market" />
          </div>
        </div>
        <div class="home-container my-6">
          <div class="market-cta-card flex flex-col md:flex-row items-center justify-between gap-6 rounded-2xl border border-[#b3915f]/30 bg-gradient-to-r from-[#10233f] via-[#162f55] to-[#1a3866] p-6 sm:p-8 text-white shadow-lg">
            <div class="space-y-2 text-center md:text-left">
              <div class="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300 border border-emerald-500/20">
                <span class="size-2 rounded-full bg-emerald-400 animate-pulse"></span>
                CHUYÊN TRANG PHÂN TÍCH THỊ TRƯỜNG BĐS ĐÀ NẴNG
              </div>
              <h3 class="text-xl sm:text-2xl font-bold tracking-tight text-white">Tra cứu biểu đồ giá, biến động 22 quận/huyện & xu hướng giao dịch</h3>
              <p class="text-sm text-slate-300 max-w-2xl leading-relaxed">Xem báo cáo thị trường chi tiết theo từng quận Sơn Trà, Hải Châu, Ngũ Hành Sơn..., biểu đồ giá m² theo quý và danh sách tin đăng nổi bật.</p>
            </div>
            <RouterLink to="/market" class="shrink-0 inline-flex items-center gap-2.5 rounded-xl bg-[#dfbe86] hover:bg-[#cca86e] px-6 py-3.5 text-sm font-bold text-[#10233f] shadow-md transition active:scale-95" data-market-banner-cta>
              <span>Mở /market ngay</span>
              <svg class="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.2"><path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
            </RouterLink>
          </div>
        </div>
        <div class="home-container demo-disclosure">
          <button type="button" class="outline-button" :aria-expanded="demoOpen" aria-controls="market-demo-panel" @click="demoOpen = !demoOpen">{{ demoOpen ? 'Thu gọn' : 'Xem' }} biểu đồ mô phỏng 3 / 6 / 12 tháng <span aria-hidden="true">⌄</span></button>
          <p>Biểu đồ minh họa giao diện, không phản ánh lịch sử thị trường thực tế.</p>
        </div>
        <div v-show="demoOpen" id="market-demo-panel">
          <MarketIntelligence v-if="demoLoaded" />
        </div>
      </section>

      <section id="projects" class="home-section home-container" aria-labelledby="projects-title"><div class="section-heading"><div><p class="eyebrow">PROJECTS · ĐÀ NẴNG</p><h2 id="projects-title">Dự án <span>định hình thành phố.</span></h2><p>Sáu dự án giới thiệu, liên kết đến website chủ đầu tư và đơn vị phát triển.</p></div><span class="section-number" aria-hidden="true">OFFICIAL DIRECTORY ↗</span></div><ProjectDirectory /><div class="backend-projects"><div class="backend-projects-heading"><h3>Dự án được công bố trên SmartProp</h3><p>Dữ liệu từ Backend, độc lập với danh mục giới thiệu phía trên.</p></div><LegacyState :state="projectState" /><p v-if="!projectState.busy && !projectState.error && !projectState.items.length" class="muted-text">Chưa có dữ liệu dự án được công bố.</p><div v-if="projectState.items.length" class="backend-project-grid"><button v-for="project in projectState.items" :key="project.id" class="backend-project-card" type="button" @click="openProject(project)"><span>{{ project.developer || 'Chưa rõ chủ đầu tư' }}</span><strong>{{ project.name }}</strong><p>{{ project.address || 'Chưa có địa chỉ' }}</p><b>Xem thông tin ↗</b></button></div><LegacyPager :state="projectState" /></div></section>

      <section id="finance" class="home-section finance-section" aria-labelledby="finance-title"><div class="home-container"><div class="section-heading"><div><p class="eyebrow">LÊN KẾ HOẠCH CỦA BẠN</p><h2 id="finance-title">Hiểu giá trị. <span>Chủ động tài chính.</span></h2><p>Hai công cụ tham khảo, giữ quyền quyết định trong tay bạn.</p></div></div><HomeFinance ref="finance" /></div></section>


    </div>

    <dialog ref="projectDialog" class="project-dialog" aria-labelledby="project-heading" @click="event => { if (event.target === projectDialog) projectDialog.close() }"><template v-if="selectedProject"><button type="button" class="close-project" aria-label="Đóng thông tin dự án" @click="projectDialog.close()">×</button><p class="eyebrow">DỰ ÁN TỪ SMARTPROP</p><h2 id="project-heading">{{ selectedProject.name }}</h2><dl><dt>Chủ đầu tư</dt><dd>{{ selectedProject.developer || 'Chưa cung cấp' }}</dd><dt>Địa chỉ</dt><dd>{{ selectedProject.address || 'Chưa cung cấp' }}</dd><dt>Quy mô</dt><dd>{{ selectedProject.scale || 'Chưa cung cấp' }}</dd><dt>Năm bàn giao</dt><dd>{{ selectedProject.handoverYear || 'Chưa cung cấp' }}</dd><dt>Tiện ích do dự án cung cấp</dt><dd>{{ selectedProject.amenities?.join(', ') || 'Chưa cung cấp' }}</dd></dl><RouterLink :to="'/projects/' + selectedProject.id" class="sp-button sp-button-primary mt-6" @click="projectDialog.close()">Mở trang dự án ↗</RouterLink></template></dialog>
  </div>
</template>

<style scoped>
.home-v3{background:#f7f5f0;color:#142b4f;min-height:100vh;font-family:'Segoe UI',sans-serif}.home-container{width:min(100% - 80px,1280px);margin-inline:auto;min-width:0}.home-section{padding-block:65px;scroll-margin-top:90px}.home-v3 :deep([id]){scroll-margin-top:90px}.home-hero{position:relative;background:#091728;color:white;isolation:isolate}.hero-shade{position:absolute;inset:0;background:linear-gradient(90deg,#061628da,#06162855 65%,#06162840),linear-gradient(0deg,#061628bb,transparent 70%);z-index:1;pointer-events:none}.hero-content{position:relative;z-index:2;padding-bottom:35px}.hero-header{display:flex;justify-content:space-between;align-items:center;padding:24px 0;gap:20px}.home-brand{font-size:23px;font-weight:700;letter-spacing:-.04em;display:flex;align-items:center;gap:10px;color:white;text-decoration:none}.home-brand>span:first-child{display:grid;place-items:center;height:35px;width:32px;background:#f6f4ee;color:#142b4f;border-radius:8px;font-size:22px}.home-brand .brand-dot{color:#dfbe86;margin-left:-10px}.hero-header-actions{display:flex;align-items:center;gap:14px}.post-link{font-size:12px;background:#dfbe86;color:#142b4f;padding:12px 20px;border-radius:9px;font-weight:650}.hero-intro{padding:58px 0 48px}.hero-location{font-size:13px;letter-spacing:.18em;color:#e3c28d;margin-bottom:20px}.hero-intro h1{font-size:clamp(38px,4.8vw,66px);font-weight:550;line-height:1.15;letter-spacing:-.045em;max-width:950px}.hero-intro h1 span{color:#dfbe86;font-family:Georgia,'Times New Roman',serif;font-weight:400}.hero-intro>p:last-of-type{font-size:15px;line-height:1.8;color:#e2e6ed;margin-top:23px}.hero-ctas{display:flex;gap:12px;margin-top:28px;flex-wrap:wrap}.gold-button,.ghost-button,.navy-button,.outline-button{display:inline-flex;align-items:center;justify-content:center;gap:14px;min-height:44px;border-radius:30px;padding:12px 23px;font-size:12px;font-weight:650;cursor:pointer;text-decoration:none}.gold-button{background:#dfbe86;color:#142b4f}.ghost-button{border:1px solid #ffffff70;color:white;backdrop-filter:blur(8px)}.navy-button{background:#142b4f;color:white;box-shadow:0 4px 12px #142b4f18}.outline-button{border:1px solid #d4cfc4;background:#fff8;color:#142b4f}.hero-search{position:relative;color:#142b4f}.project-search-link{padding:8px 20px;font-size:12px;cursor:pointer}.section-heading{display:flex;justify-content:space-between;align-items:end;gap:25px;margin-bottom:28px}.eyebrow{font-size:13px;font-weight:650;letter-spacing:.24em;color:#78572f;margin-bottom:12px}.section-heading h2,.home-account h2{font-size:clamp(28px,3vw,41px);font-weight:550;letter-spacing:-.035em;line-height:1.25}.section-heading h2 span,.home-account h2 span{color:#957344}.section-heading>div>p:last-child,.home-account>div>p:last-child{font-size:13px;line-height:1.8;color:#536178;margin-top:12px}.section-number{font-size:13px;letter-spacing:.16em;color:#8c7760;white-space:nowrap}.lifestyle-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:15px}.lifestyle-card{display:flex;flex-direction:column;min-width:0;overflow:hidden;border:1px solid #e7e1d7;border-radius:15px;background:white;text-align:left;cursor:pointer;transition:transform .2s,border-color .2s}.lifestyle-card:hover{transform:translateY(-4px)}.lifestyle-card[aria-pressed=true]{border-color:#957344;outline:2px solid #a7865540}.lifestyle-image{display:block;position:relative;width:100%;height:135px;overflow:hidden}.lifestyle-image img{width:100%;height:100%;object-fit:cover}.lifestyle-symbol{position:absolute;bottom:8px;left:10px;width:30px;height:30px;display:grid;place-items:center;background:white;border-radius:10px;color:#21775d;font-size:22px}.lifestyle-name{display:flex;align-items:center;justify-content:space-between;gap:6px;font-size:13px;font-weight:650;padding:14px 13px 0;line-height:1.5}.lifestyle-name>span{color:#957344}.lifestyle-caption{display:block;font-size:13px;line-height:1.7;color:#536178;padding:6px 13px 15px}.image-note{color:#536178;font-size:13px;margin-top:12px;line-height:1.8}.lifestyle-explanation{margin-top:18px;padding:18px 22px;border:1px solid #e7d9bd;background:#f2ebde;border-radius:14px;font-size:13px;line-height:1.8}.lifestyle-explanation>button{margin-top:9px;font-size:12px;text-decoration:underline;cursor:pointer}.district-suggestions{display:flex;flex-wrap:wrap;gap:14px;margin-top:10px}.district-suggestions button{cursor:pointer;font-weight:650}.properties-section{background:#f0ede7}.heading-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.compare-count{border:1px solid #e0dacd;padding:12px 18px;border-radius:30px;font-size:12px;color:#536178;background:white}.district-chips{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:20px}.district-chips button{border:1px solid #ddd6c8;border-radius:25px;background:white;padding:9px 14px;font-size:13px;color:#536178;cursor:pointer}.district-chips button[aria-pressed=true]{background:#142b4f;color:white;border-color:#142b4f}.results-info{display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;font-size:12px;color:#536178;margin-bottom:20px}.results-info button{color:#967242;text-decoration:underline;cursor:pointer}.home-property-grid,.listing-skeletons{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}.map-selected-card{outline:2px solid #b3915f;outline-offset:3px}.card-map-button,.card-compare-button{font-size:13px;color:#536178;cursor:pointer;padding:8px 2px}.card-compare-button{color:#78572f}.card-compare-button[aria-pressed=true]{color:#20775d;font-weight:700}.card-map-button[aria-pressed=true]{color:#142b4f;font-weight:700}.home-property-grid :deep(.property-actions){gap:7px}.home-property-grid :deep(.detail-link){padding:10px 14px}.home-empty{padding:65px 20px;text-align:center;background:white;border:1px solid #e7e1d7;border-radius:24px}.home-empty>span{font-size:40px;color:#b3915f}.home-empty h3{font-size:21px;font-weight:650;margin:10px 0}.home-empty p{font-size:13px;color:#536178;margin:10px 0 24px}.view-all{text-align:center;margin-top:30px}.view-all p{font-size:13px;color:#536178;margin-top:14px}.listing-skeletons>div{height:440px;background:linear-gradient(110deg,#e4e1d9,#eeece7,#e4e1d9);border-radius:24px}.compare-notice{font-size:12px;color:#a23e23;margin-top:15px}.real-data-label{font-size:13px;line-height:1.8;letter-spacing:.08em;color:#23765b;white-space:nowrap}.market-section{background:#f1eee8}.market-section :deep(#market-current){padding-bottom:20px}.market-section :deep(#market-current>div){width:min(100% - 80px,1280px);padding-inline:0;max-width:none}.demo-disclosure>p{font-size:12px;color:#536178;margin-top:12px}.market-section :deep(#market-demo){padding-bottom:0;padding-top:35px}.market-section :deep(#market-demo h2){font-size:30px}.backend-projects{margin-top:40px;padding-top:30px;border-top:1px solid #e0d9cd}.backend-projects-heading{margin-bottom:20px}.backend-projects h3{font-size:22px;font-weight:600}.backend-projects-heading p,.muted-text{font-size:13px;line-height:1.8;color:#536178;margin-top:10px}.backend-project-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.backend-project-card{background:white;padding:25px;border:1px solid #e7e1d7;border-radius:18px;text-align:left;display:flex;flex-direction:column;gap:12px;cursor:pointer}.backend-project-card span{font-size:13px;letter-spacing:.1em;color:#78572f}.backend-project-card strong{font-size:19px;font-weight:650}.backend-project-card p{font-size:12px;line-height:1.8;color:#536178}.backend-project-card b{font-size:12px;margin-top:auto}.finance-section{background:#eeeae3}.home-account{padding-block:65px;display:grid;grid-template-columns:1fr 1fr;gap:45px;align-items:center}.account-links{display:flex;gap:12px;flex-wrap:wrap;justify-content:flex-end}.account-links>a{border:1px solid #ddd6c8;background:white;border-radius:25px;padding:11px 17px;font-size:12px}.account-links>a.navy-button{color:white;background:#142b4f}.home-footer{background:#101f35;color:white;padding:40px 0 135px}.footer-content{display:flex;align-items:center;gap:25px;flex-wrap:wrap}.footer-brand{font-size:24px;font-weight:700}.footer-brand span{color:#dfbe86}.footer-content>p{font-size:12px;color:#b1bbca}.footer-content nav{margin-left:auto;display:flex;gap:20px;flex-wrap:wrap;font-size:12px;color:#d1d8e2}.skip-link{position:fixed;top:-100px;left:20px;z-index:100;padding:12px 20px;border-radius:12px;background:white;color:#142b4f}.skip-link:focus{top:20px}.project-dialog{width:min(650px,calc(100vw - 30px));margin:auto;border:0;border-radius:22px;padding:30px;color:#142b4f;max-height:85dvh;overflow:auto}.project-dialog::backdrop{background:#07162bbb}.close-project{float:right;font-size:28px;cursor:pointer;padding:0 10px}.project-dialog h2{font-size:28px;font-weight:650;margin:20px 0}.project-dialog dt{font-size:13px;color:#8c7760;margin-top:17px}.project-dialog dd{font-size:14px;line-height:1.8;margin-top:5px}.home-v3 :focus-visible{outline:3px solid #b3915f;outline-offset:3px}
@media(min-width:1600px){.hero-intro{padding-block:80px 65px}}@media(max-width:1050px){.home-container{width:calc(100% - 48px)}.home-section{padding-block:45px}.home-property-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.lifestyle-grid{display:flex;overflow-x:auto;padding-bottom:12px;scroll-snap-type:x proximity}.lifestyle-card{flex:0 0 210px;scroll-snap-align:start}.section-number{display:none}.section-heading{align-items:start;flex-wrap:wrap}.market-section :deep(#market-current>div){width:calc(100% - 48px)}.home-account{grid-template-columns:1fr;gap:25px}.account-links{justify-content:flex-start}.footer-content nav{margin-left:0;width:100%}.backend-project-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.home-container{width:calc(100% - 32px)}.hero-header{padding:20px 0}.home-brand{font-size:21px}.hero-header-actions{gap:8px}.post-link{padding:11px 13px;font-size:13px}.hero-intro{padding:60px 0 32px}.hero-intro h1{font-size:38px}.hero-intro>p:last-of-type{font-size:13px}.hero-ctas{gap:10px}.gold-button,.ghost-button{font-size:13px;padding:12px 17px}.hero-content{padding-bottom:25px}.section-heading h2,.home-account h2{font-size:30px}.section-heading{margin-bottom:22px}.home-section{padding-block:37px}.home-property-grid{grid-template-columns:1fr;gap:20px}.home-property-grid :deep(.property-image){height:225px}.lifestyle-card{flex-basis:190px}.lifestyle-image{height:115px}.real-data-label{white-space:normal}.heading-actions{width:100%;justify-content:space-between}.listing-skeletons{grid-template-columns:1fr}.listing-skeletons>div:not(:first-child){display:none}.market-section :deep(#market-current>div){width:calc(100% - 32px)}.backend-project-grid{grid-template-columns:1fr}.home-account{padding-block:40px}.footer-content{gap:18px}.footer-content>p{width:100%}.desktop-break{display:none}}
@media(prefers-reduced-motion:reduce){.lifestyle-card{transition:none}.lifestyle-card:hover{transform:none}}

.home-section,.home-v3 :deep([id]){scroll-margin-top:calc(var(--sp-header-height) + var(--sp-section-nav-height) + 16px)}
#properties .listing-filters{margin-bottom:22px}#properties .results-info{margin-top:18px}
.hero-intro{padding-top:48px!important;padding-bottom:22px!important}.hero-content{padding-bottom:26px!important}
@media(min-width:1051px){.lifestyle-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
</style>
