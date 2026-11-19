import { createStateStore } from "../state/createStateStore.js";
import { useSyncExternalStore } from "react";
import { createComparison } from "../../features/property/comparison.js";
const selection = createComparison();
const items = createStateStore([]),
  notice = createStateStore("");
function sync() {
  items.set([...selection.items]);
}
export function useComparison() {
  useSyncExternalStore(items.subscribe, items.getSnapshot);
  useSyncExternalStore(notice.subscribe, notice.getSnapshot);
  return {
    items: items.getSnapshot(),
    notice: notice.getSnapshot(),
    has: id => items.getSnapshot().some(item => item.id === id),
    toggle(property) {
      if (!selection.toggle(property)) notice.set("Bạn có thể chọn tối đa 3 tin. Hãy bỏ một tin trước khi thêm.");else {
        notice.set("");
        sync();
      }
    },
    clear() {
      selection.clear();
      notice.set("");
      sync();
    },
    replace(values) {
      selection.replace(values);
      sync();
    },
    updateItems: items.edit,
    updateItemsValue: items.set,
    updateNotice: notice.edit,
    updateNoticeValue: notice.set
  };
}
