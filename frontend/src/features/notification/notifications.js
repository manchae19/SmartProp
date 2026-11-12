import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import { api, session } from '../auth/api.js';
export const notifications = createStateStore({
  count: null,
  error: false
});
let sequence = 0;
(() => {
  let _previousValue = (() => session.getSnapshot().user?.id)();
  const _onChange = () => {
    const _nextValue = (() => session.getSnapshot().user?.id)();
    if (stateKey(_nextValue) === stateKey(_previousValue)) return;
    const previousValue = _previousValue;
    _previousValue = _nextValue;
    (() => {
      sequence++;
      notifications.edit(draftValue => draftValue["count"] = null);
      notifications.edit(draftValue => draftValue["error"] = false);
    })(_nextValue, previousValue, () => undefined);
  };
  session.subscribe(_onChange);
})();
export async function refreshUnread() {
  if (!session.getSnapshot().token) return;
  const run = ++sequence;
  try {
    const result = await api('/users/me/notifications/unread-count');
    if (run === sequence) {
      notifications.edit(draftValue => draftValue["count"] = result.count);
      notifications.edit(draftValue => draftValue["error"] = false);
    }
  } catch {
    if (run === sequence) {
      notifications.edit(draftValue => draftValue["error"] = true);
      notifications.edit(draftValue => draftValue["count"] = null);
    }
  }
}
