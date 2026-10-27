import { ref } from 'vue'
import { createComparison } from './comparison.js'
const selection = createComparison()
const items = ref([]), notice = ref('')
function sync() { items.value = [...selection.items] }
export function useComparison() {
  return { items, notice, has: id => items.value.some(item => item.id === id),
    toggle(property) { if (!selection.toggle(property)) notice.value = 'Bạn có thể chọn tối đa 3 tin. Hãy bỏ một tin trước khi thêm.'; else { notice.value = ''; sync() } },
    clear() { selection.clear(); notice.value = ''; sync() },
    replace(values) { selection.replace(values); sync() },
  }
}
