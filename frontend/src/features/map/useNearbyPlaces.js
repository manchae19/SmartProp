import { ref, watch, onBeforeUnmount } from 'vue'
import { requestNearby } from './nearbyRequest.js'
import { nearbyPath } from './nearbyExplorer.js'
export function useNearbyPlaces(getProperty, getRadius, getGroups, enabled = () => true) {
  const data = ref(null), busy = ref(false), error = ref(''), retryAt = ref(0)
  let sequence = 0, timer, controller
  async function load() {
    const run = ++sequence
    clearTimeout(timer); controller?.abort(); controller = new AbortController()
    data.value = null; error.value = ''; busy.value = false
    const path = enabled() && nearbyPath(getProperty()?.id, getRadius(), getGroups())
    if (!path) return
    if (Date.now() < retryAt.value) { error.value = 'Vui lòng chờ một lát trước khi thử lại.'; return }
    busy.value = true
    try {
      const result = await requestNearby(path, { base: import.meta.env?.VITE_API_BASE_URL || '/api/v1', signal: controller.signal })
      if (run === sequence && result.propertyId === getProperty()?.id) data.value = result
    } catch (e) {
      if (run !== sequence || e.name === 'AbortError') return
      error.value = ({
        NEARBY_TIMEOUT: 'Tìm tiện ích quá thời gian. Bạn có thể thử lại.',
        NEARBY_NOT_CONFIGURED: 'Nguồn tiện ích chưa được cấu hình trên máy chủ.',
        NEARBY_QUOTA_EXCEEDED: 'Nguồn tiện ích đang giới hạn truy cập. Vui lòng thử lại sau.',
        NEARBY_PROVIDER_AUTH: 'Máy chủ chưa có quyền truy cập nguồn tiện ích.',
        RATE_LIMITED: 'Bạn đang thao tác quá nhanh. Vui lòng chờ rồi thử lại.'
      })[e.code] || (e.status === 404 ? 'Tin đăng không còn công khai.' : 'Chưa tải được tiện ích. Vui lòng thử lại.')
      if (e.status === 429) retryAt.value = Date.now() + Math.min(3600, Math.max(1, e.retryAfter || 10)) * 1000
    } finally { if (run === sequence) busy.value = false }
  }
  watch(() => [getProperty()?.id, getProperty()?.latitude, getProperty()?.longitude, getRadius(), [...getGroups()].sort().join(','), enabled()], () => {
    ++sequence; controller?.abort(); clearTimeout(timer); data.value = null; error.value = ''; busy.value = false
    timer = setTimeout(load, 650)
  }, { immediate: true })
  onBeforeUnmount(() => { ++sequence; clearTimeout(timer); controller?.abort() })
  return { data, busy, error, retry: load }
}
