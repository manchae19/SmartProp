// Explicit immutable snapshots consumed by React.useSyncExternalStore.
export function copyState(value, seen = new WeakMap()) {
  if (!value || typeof value !== 'object' || value.$$typeof) return value;
  if (seen.has(value)) return seen.get(value);
  if (value instanceof Set) return new Set(value);
  if (value instanceof Map) return new Map(value);
  if (!Array.isArray(value) && Object.getPrototypeOf(value) !== Object.prototype) return value;
  const next = Array.isArray(value) ? [] : {};
  seen.set(value, next);
  for (const key of Object.keys(value)) next[key] = copyState(value[key], seen);
  return next;
}
export function createStateStore(initial) {
  let snapshot = initial;
  const listeners = new Set();
  const store = {
    getSnapshot: () => snapshot,
    subscribe: listener => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    set: value => {
      if (!Object.is(snapshot, value)) {
        snapshot = value;
        for (const listener of [...listeners]) listener();
      }
      return value;
    },
    edit: recipe => {
      const next = copyState(snapshot),
        result = recipe(next);
      store.set(next);
      return result;
    }
  };
  return store;
}
export function combineStateStores(stores, read) {
  let snapshot = read();
  const listeners = new Set();
  const changed = () => {
    snapshot = read();
    for (const listener of [...listeners]) listener();
  };
  for (const store of stores) store.subscribe(changed);
  return {
    getSnapshot: () => snapshot,
    subscribe: listener => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    }
  };
}
export function stateKey(value) {
  const seen = new WeakSet();
  return JSON.stringify(value, (_, item) => {
    if (item && typeof item === 'object') {
      if (seen.has(item)) return '[circular]';
      seen.add(item);
    }
    return item;
  });
}
