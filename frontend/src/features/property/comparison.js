// A public-data snapshot by UUID, retained across pages. Revalidate via public GET before comparing.
export function createComparison() {
  let items = []
  return {
    get items() { return items },
    toggle(property) {
      if (items.some(item => item.id === property.id)) { items = items.filter(item => item.id !== property.id); return true }
      if (items.length >= 3) return false
      items = [...items, property]; return true
    },
    clear() { items = [] },
    replace(values) { items = values.filter((item, index) => values.findIndex(other => other.id === item.id) === index).slice(0, 3) },
  }
}
