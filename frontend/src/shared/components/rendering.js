import React from "react";
import { createPortal } from "react-dom";
const camel = (s) => s.replace(/[-:]([a-z])/g, (_, c) => c.toUpperCase());
export function cx(value) {
  if (!value) return "";
  if (Array.isArray(value)) return value.map(cx).filter(Boolean).join(" ");
  if (typeof value === "object")
    return Object.keys(value)
      .filter((k) => value[k])
      .join(" ");
  return String(value);
}
export function styleObject(value) {
  if (!value) return {};
  if (Array.isArray(value)) return Object.assign({}, ...value.map(styleObject));
  if (typeof value === "object") return value;
  return Object.fromEntries(
    String(value)
      .split(";")
      .map((part) => {
        const i = part.indexOf(":");
        return i < 0
          ? null
          : [
              part.slice(0, i).trim().startsWith("--")
                ? part.slice(0, i).trim()
                : camel(part.slice(0, i).trim()),
              part.slice(i + 1).trim(),
            ];
      })
      .filter(Boolean),
  );
}
export function mergeProps(...parts) {
  const result = {};
  for (const part of parts) {
    for (const [k, v] of Object.entries(part || {})) {
      if (k === "class" || k === "className")
        result.className = cx([result.className, v]);
      else if (k === "style")
        result.style = { ...result.style, ...styleObject(v) };
      else if (/^on[A-Z]/.test(k) && result[k] && v) {
        const before = result[k];
        result[k] = (...args) => {
          before(...args);
          v(...args);
        };
      } else result[k] = v;
    }
  }
  return result;
}
export function bindRef(ctx, name) {
  const owner = ctx.$frame;
  if (!owner.refs.has(name))
    owner.refs.set(name, (node) => {
      const value = owner.bindings[name];
      if (value?.__signal) value.value = node;
      else if (typeof value === "function") value(node);
    });
  return owner.refs.get(name);
}
export function renderList(value, render) {
  if (typeof value === "number")
    return Array.from({ length: Math.max(0, value) }, (_, i) =>
      render(i + 1, i),
    );
  if (Array.isArray(value) || typeof value === "string")
    return Array.from(value, render);
  return value && typeof value === "object"
    ? Object.entries(value).map(([key, item], i) => render(item, key, i))
    : [];
}
export function display(value) {
  if (value == null || typeof value === "boolean")
    return value == null ? "" : String(value);
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
export function modelProps(
  get,
  set,
  { kind = "text", value = "on", number = false, multiple = false } = {},
) {
  const convert = (v) =>
    number && v !== "" && !Number.isNaN(Number(v)) ? Number(v) : v;
  if (kind === "checkbox")
    return {
      checked: Array.isArray(get) ? get.includes(value) : !!get,
      onChange: (e) =>
        set(
          Array.isArray(get)
            ? e.target.checked
              ? [...get, value]
              : get.filter((v) => v !== value)
            : e.target.checked,
        ),
    };
  if (kind === "radio")
    return { checked: get === value, onChange: () => set(convert(value)) };
  return {
    value: get ?? (multiple ? [] : ""),
    onChange: (e) =>
      set(
        multiple
          ? Array.from(e.target.selectedOptions, (o) => convert(o.value))
          : convert(e.target.value),
      ),
  };
}
export function rootProps(ctx, node) {
  const owner = ctx.$frame,
    attrs = {},
    eventKey = (name) =>
      "on" +
      name
        .replace(/[-:]([a-z])/g, (_, c) => c.toUpperCase())
        .replace(/^./, (c) => c.toUpperCase());
  const declared = new Set((owner.events || []).map(eventKey));
  for (const [k, v] of Object.entries(owner.input)) {
    if (
      !(k in owner.spec) &&
      !["children", "ref", "key"].includes(k) &&
      (!k.startsWith("on") ||
        (/^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(
          k,
        ) &&
          !declared.has(k)))
    )
      attrs[k] = v;
  }
  const apply = (n) =>
    React.isValidElement(n) && n.type !== React.Fragment
      ? React.cloneElement(n, mergeProps(n.props, attrs))
      : n;
  return Array.isArray(node)
    ? React.createElement(React.Fragment, null, ...node.map(apply))
    : apply(node);
}
export function Teleport({ to = "body", disabled, children }) {
  const target =
    typeof document === "undefined" ? null : document.querySelector(to);
  return disabled || !target ? children : createPortal(children, target);
}
