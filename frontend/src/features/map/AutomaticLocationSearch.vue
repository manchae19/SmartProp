<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { accuracyLabel, geocodingSignature, geocodingConfiguration, normalizeAddressQuery, searchLocations, geocodingErrorMessage } from './geocoding.js'

const props = defineProps({ address: String, city: String, district: String, ward: String, disabled: Boolean })
const emit = defineEmits(['preview', 'clear'])
const busy = ref(false), consent = ref(false), error = ref(''), status = ref(''), candidates = ref([]), selected = ref('')
const retryRemaining=ref(0)
let retryTimer
function clearRetry(){clearInterval(retryTimer);retryRemaining.value=0}
function waitBeforeRetry(seconds){clearRetry();const until=Date.now()+Math.min(86400,Math.max(1,seconds))*1000;const tick=()=>{retryRemaining.value=Math.max(0,Math.ceil((until-Date.now())/1000));if(!retryRemaining.value)clearInterval(retryTimer)};tick();retryTimer=setInterval(tick,1000)}
let revision = 0,configRevision=0
const configuration=ref(null),checking=ref(true),configurationError=ref('')
const query=computed(()=>normalizeAddressQuery(props))
const searchScope=computed(()=>[props.city==='Da Nang'?'Đà Nẵng':props.city,props.district,props.ward].filter(Boolean).join(' · '))
const providerName=computed(()=>configuration.value?.provider==='GOOGLE'?'Google Maps':'Geoapify')
async function checkConfiguration(){const run=++configRevision;checking.value=true;configurationError.value='';try{const value=await geocodingConfiguration();if(run===configRevision)configuration.value=value}catch{if(run===configRevision){configuration.value=null;configurationError.value='Chưa kiểm tra được dịch vụ tìm vị trí. Bạn vẫn có thể đặt ghim thủ công.'}}finally{if(run===configRevision)checking.value=false}}
const signature = computed(() => geocodingSignature(props))
const canSearch = computed(() => !props.disabled && !checking.value && configuration.value?.available===true && !busy.value && retryRemaining.value===0 && consent.value && !!props.address?.trim() && !!props.city?.trim())

async function search() {
  if (!canSearch.value) return
  const current = ++revision
  busy.value = true; error.value = ''; status.value = ''; candidates.value = []; selected.value = ''; emit('clear')
  try {
    const result = await searchLocations({...props,shareAddress:consent.value})
    if (current !== revision) return
    candidates.value = result.candidates
    status.value = result.candidates.length ? 'Chọn một kết quả trong khu vực đã chọn để xem ghim đề xuất; chưa lưu hoặc xác nhận vị trí.' : 'Không tìm thấy địa điểm phù hợp trong khu vực đã chọn. Bạn có thể điều chỉnh địa chỉ hoặc chọn ghim thủ công.'+(result.status==='SCOPE_UNAVAILABLE'?' Chưa có ranh giới đã kiểm chứng cho lựa chọn này; hệ thống không tự mở rộng phạm vi.':'')
    if(result.candidates.length===1){preview(result.candidates[0]);status.value='Đã đưa bản đồ đến gợi ý duy nhất. Kiểm tra vị trí và độ chính xác trước khi xác nhận.'}
  } catch (e) {
    if (current === revision){error.value=geocodingErrorMessage(e);if(e.status===429)waitBeforeRetry(e.retryAfter||2)}
  } finally { if (current === revision) busy.value = false }
}
function preview(candidate) { selected.value = candidate.id; emit('preview', candidate) }
function clearSelection() { selected.value = '' }
defineExpose({ clearSelection })
watch(signature, () => { revision++; clearRetry();busy.value = false; consent.value = false; candidates.value = []; selected.value = ''; error.value = ''; status.value = ''; emit('clear') })
onMounted(checkConfiguration)
onBeforeUnmount(() => {revision++;configRevision++;clearRetry()})
</script>

<template>
  <div class="automatic-location" :aria-busy="busy">
    <div class="search-heading"><div><strong>Tìm vị trí từ địa chỉ</strong><p>Giữ nguyên địa chỉ bạn nhập; kết quả tìm kiếm chỉ là đề xuất cần kiểm tra.</p></div><button type="button" :disabled="!canSearch" @click="search">{{ busy ? 'Đang tìm…' : 'Tìm vị trí tự động' }}</button></div>
    <p v-if="checking" role="status">Đang kiểm tra dịch vụ tìm vị trí…</p>
    <p v-else-if="configurationError||!configuration?.available" role="status">{{configurationError||'Tìm vị trí tự động hiện chưa được bật trên hệ thống. Bạn vẫn có thể đặt ghim thủ công.'}} <button type="button" class="check-service" :disabled="disabled" @click="checkConfiguration">Kiểm tra lại</button></p>
    <label v-else class="search-consent"><input v-model="consent" type="checkbox" :disabled="disabled || busy">Tôi đồng ý gửi địa chỉ này tới {{providerName}} để tìm vị trí.</label>
    <p v-if="configuration?.available&&address?.trim()" class="search-query">Địa chỉ dùng để tìm: {{query}}</p>
    <p v-if="configuration?.available" class="search-scope">Giới hạn tìm kiếm: {{searchScope}}. Kết quả ngoài phạm vi sẽ không được hiển thị.</p>
    <p v-if="busy" role="status">Đang tìm các vị trí phù hợp…</p>
    <p v-if="error" role="alert" class="search-error">{{ error }}</p><button v-if="error" type="button" :disabled="!canSearch" @click="search">{{retryRemaining?'Thử lại sau '+retryRemaining+' giây':'Thử lại tìm vị trí'}}</button>
    <p v-if="status" role="status">{{ status }}</p>
    <fieldset v-if="candidates.length" class="search-results"><legend>Các vị trí đề xuất</legend><label v-for="candidate in candidates" :key="candidate.id" class="search-result" :class="{ chosen: selected === candidate.id }"><input type="radio" :name="'geocoding-result'" :checked="selected === candidate.id" :disabled="disabled" @change="preview(candidate)"><span><strong>{{ candidate.formattedAddress }}</strong><small>{{ accuracyLabel(candidate) }}</small><small>{{ candidate.attribution }}</small></span></label></fieldset>
    <p v-if="candidates.some(candidate => candidate.provider === 'GEOAPIFY')" class="source-links"><a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer">Powered by Geoapify</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a></p>
    <p v-if="candidates.some(candidate => candidate.provider === 'GOOGLE')" class="source-links">Google Maps · Gợi ý chỉ hiển thị trên Google; không sao chép vào bản nháp hoặc bản đồ OSM.</p>
  </div>
</template>

<style scoped>
.automatic-location .check-service{background:transparent;color:#1e325a;padding:0;text-decoration:underline;font:inherit}.search-query,.search-result span{min-width:0;overflow-wrap:anywhere}
.automatic-location{padding:18px;border:1px solid #d8dfeb;border-radius:14px;background:#f7f8fb;margin:16px 0;color:#1e325a}.search-heading{display:flex;align-items:center;justify-content:space-between;gap:16px}.search-heading strong{font-size:15px}.automatic-location p{font-size:12px;line-height:1.7;margin:7px 0;color:#59677a}.automatic-location button{flex-shrink:0;border:0;border-radius:9px;padding:12px 16px;background:#1e325a;color:white;cursor:pointer;font-size:13px;font-weight:600}.automatic-location button:disabled{opacity:.5;cursor:not-allowed}.search-consent{display:flex;align-items:flex-start;gap:9px;margin-top:12px;font-size:12px;line-height:1.7}.search-consent input,.search-result input{margin-top:4px;flex-shrink:0;accent-color:#1e325a}.automatic-location .search-error{color:#a12d2d}.search-results{margin:14px 0 0;padding:0;border:0;min-width:0}.search-results legend{font-size:12px;font-weight:600;margin-bottom:7px}.search-result{display:flex;align-items:flex-start;gap:10px;padding:12px;margin:8px 0;background:white;border:1px solid #dce2eb;border-radius:10px;cursor:pointer}.search-result.chosen{border-color:#b3915f;background:#fffaf1}.search-result strong{display:block;font-size:13px;overflow-wrap:anywhere}.search-result small{display:block;font-size:13px;color:#536178;line-height:1.7;margin-top:4px}.source-links a{text-decoration:underline;text-underline-offset:3px}:focus-visible{outline:3px solid #b3915f;outline-offset:3px}@media(max-width:600px){.search-heading{align-items:stretch;flex-direction:column}.automatic-location{padding:14px}}
</style>
