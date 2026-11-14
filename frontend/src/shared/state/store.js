import React, { useLayoutEffect, useRef, useSyncExternalStore } from "react";
const listeners = new Set(),
  effects = new Set(),
  proxies = new WeakMap(),
  rawObjects = new WeakMap(),
  objectIds = new WeakMap();
let version = 0,
  pending = false,
  dirty = false,
  frame = null,
  serial = 0;
const identity = (o) => {
  if (!objectIds.has(o)) objectIds.set(o, ++serial);
  return objectIds.get(o);
};
const plain = (o) =>
  o &&
  typeof o === "object" &&
  (Array.isArray(o) || Object.getPrototypeOf(o) === Object.prototype);
function signature(value) {
  try {
    return JSON.stringify(value, (_, v) =>
      typeof v === "function" ? "function:" + identity(v) : v,
    );
  } catch {
    return value && typeof value === "object"
      ? "object:" + identity(value)
      : String(value);
  }
}
function changed() {
  if (frame) return;
  dirty = true;
  if (!pending) {
    pending = true;
    queueMicrotask(flush);
  }
}
function flush() {
  let runs = 0;
  while (dirty && runs++ < 30) {
    dirty = false;
    for (const e of [...effects]) e.run();
  }
  pending = false;
  version++;
  for (const notify of [...listeners]) notify();
  if (dirty) changed();
}
export const subscribe = (listener) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};
export const snapshot = () => version;
export function useStore(value) {
  useSyncExternalStore(subscribe, snapshot, snapshot);
  return value;
}
export function reactive(value) {
  if (!plain(value) || rawObjects.has(value)) return value;
  if (proxies.has(value)) return proxies.get(value);
  const p = new Proxy(value, {
    get(t, k, r) {
      return reactive(Reflect.get(t, k, r));
    },
    set(t, k, v, r) {
      const old = t[k],
        raw = rawObjects.get(v) || v,
        ok = Reflect.set(t, k, raw, r);
      if (!Object.is(old, raw)) changed();
      return ok;
    },
    deleteProperty(t, k) {
      const exists = k in t,
        ok = Reflect.deleteProperty(t, k);
      if (exists) changed();
      return ok;
    },
  });
  proxies.set(value, p);
  rawObjects.set(p, value);
  return p;
}
export function ref(value) {
  const cell = { __signal: true };
  Object.defineProperty(cell, "value", {
    enumerable: true,
    get: () => reactive(value),
    set: (next) => {
      next = rawObjects.get(next) || next;
      if (!Object.is(value, next)) {
        value = next;
        changed();
      }
    },
  });
  return cell;
}
export function computed(getter) {
  const get = typeof getter === "function" ? getter : getter.get;
  return {
    __signal: true,
    get value() {
      return get();
    },
    set value(v) {
      if (getter.set) getter.set(v);
    },
  };
}
export function watch(source, callback, options = {}) {
  const owner = frame;
  const read = () =>
    Array.isArray(source)
      ? source.map((s) =>
          typeof s === "function" ? s() : s?.__signal ? s.value : s,
        )
      : typeof source === "function"
        ? source()
        : source?.__signal
          ? source.value
          : source;
  let current = read(),
    key = signature(current),
    cleanup;
  const effect = {
    run() {
      const next = read(),
        nextKey = signature(next);
      if (nextKey === key) return;
      const old = current;
      current = next;
      key = nextKey;
      cleanup?.();
      let result;
      try {
        result = callback(next, old, (fn) => (cleanup = fn));
      } catch (error) {
        console.error(error);
      }
      result?.catch?.(console.error);
    },
  };
  effects.add(effect);
  const stop = () => {
    effects.delete(effect);
    cleanup?.();
  };
  owner?.cleanup.push(stop);
  if (options.immediate) {
    const result = callback(current, undefined, (fn) => (cleanup = fn));
    result?.catch?.(console.error);
  }
  return stop;
}
export const onMounted = (callback) => {
  if (frame) frame.mount.push(callback);
};
export const onBeforeUnmount = (callback) => {
  if (frame) frame.cleanup.push(callback);
};
export const nextTick = (callback) =>
  new Promise((resolve) =>
    queueMicrotask(() =>
      requestAnimationFrame(() => {
        callback?.();
        resolve();
      }),
    ),
  );
export const useId = () => "smartprop-" + ++serial;
const camel = (s) =>
  String(s).replace(/[-:]([a-z])/g, (_, c) => c.toUpperCase());
export function propsForSetup(input, spec = {}) {
  const owner = frame;
  if (owner) {
    owner.spec = {
      ...owner.spec,
      ...(Array.isArray(spec)
        ? Object.fromEntries(spec.map((k) => [k, {}]))
        : spec),
    };
    return owner.props;
  }
  return input;
}
export function emitForProps(input, names = []) {
  if (frame) frame.events = names;
  return (name, ...args) => {
    const key = "on" + camel(name).replace(/^./, (c) => c.toUpperCase());
    return input[key]?.(...args);
  };
}
export function exposeForSetup(value) {
  if (frame) frame.expose = value;
}
export function defineAsyncComponent(loader) {
  const Lazy = React.lazy(loader);
  return React.forwardRef((props, ref) =>
    React.createElement(
      React.Suspense,
      {
        fallback: React.createElement("span", { role: "status" }, "Loading..."),
      },
      React.createElement(Lazy, { ...props, ref }),
    ),
  );
}
export function useSetup(setup, input, forwardedRef) {
  useSyncExternalStore(subscribe, snapshot, snapshot);
  const holder = useRef(null);
  if (!holder.current) {
    const owner = {
      input,
      spec: {},
      mount: [],
      cleanup: [],
      bindings: {},
      refs: new Map(),
      expose: null,
    };
    owner.props = new Proxy(
      {},
      {
        get(_, key) {
          const rule = owner.spec[key];
          if (key in owner.input) {
            const value = owner.input[key];
            return (rule === Boolean || rule?.type === Boolean) &&
              (value === "" || value === key)
              ? true
              : value;
          }
          if (rule === Boolean || rule?.type === Boolean)
            return rule?.default ?? false;
          if (rule && "default" in rule) {
            if (!owner.defaults) owner.defaults = {};
            if (!(key in owner.defaults))
              owner.defaults[key] =
                typeof rule.default === "function" && rule.type !== Function
                  ? rule.default()
                  : rule.default;
            return owner.defaults[key];
          }
          return undefined;
        },
        ownKeys() {
          return [
            ...new Set([
              ...Object.keys(owner.input),
              ...Object.keys(owner.spec),
            ]),
          ];
        },
        getOwnPropertyDescriptor() {
          return { enumerable: true, configurable: true };
        },
      },
    );
    owner.ctx = new Proxy(
      {},
      {
        get(_, key) {
          if (key === "$frame") return owner;
          if (key === "$children") return owner.input.children;
          if (key === "$attrs") return owner.input;
          const value = Object.prototype.hasOwnProperty.call(
            owner.bindings,
            key,
          )
            ? owner.bindings[key]
            : owner.props[key];
          return value?.__signal ? value.value : value;
        },
        set(_, key, value) {
          const current = owner.bindings[key];
          if (current?.__signal) current.value = value;
          else {
            owner.bindings[key] = value;
            changed();
          }
          return true;
        },
      },
    );
    holder.current = owner;
    const previous = frame;
    frame = owner;
    try {
      owner.bindings = setup(owner.props) || {};
    } finally {
      frame = previous;
    }
  }
  const owner = holder.current;
  owner.input = input;
  useLayoutEffect(() => {
    for (const callback of owner.mount) {
      const result = callback();
      result?.catch?.(console.error);
    }
    return () => {
      for (const cleanup of owner.cleanup) cleanup();
    };
  }, []);
  useLayoutEffect(() => {
    for (const e of [...effects]) e.run();
  });
  React.useImperativeHandle(forwardedRef, () => owner.expose || owner.ctx, []);
  return owner.ctx;
}
