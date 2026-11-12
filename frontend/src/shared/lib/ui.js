export function classNames(value) {
  if (!value) return '';
  if (Array.isArray(value)) return value.map(classNames).filter(Boolean).join(' ');
  if (typeof value === 'object') return Object.keys(value).filter(key => value[key]).join(' ');
  return String(value);
}
export function inlineStyle(value) {
  if (!value) return {};
  if (Array.isArray(value)) return Object.assign({}, ...value.map(inlineStyle));
  if (typeof value === 'object') return value;
  return Object.fromEntries(String(value).split(';').map(part => {
    const index = part.indexOf(':');
    if (index < 0) return null;
    const key = part.slice(0, index).trim();
    return [key.startsWith('--') ? key : key.replace(/[-:]([a-z])/g, (_, c) => c.toUpperCase()), part.slice(index + 1).trim()];
  }).filter(Boolean));
}
export const chainHandlers = (first, second) => (...args) => {
  first?.(...args);
  second?.(...args);
};
export const numericInput = value => value !== '' && !Number.isNaN(Number(value)) ? Number(value) : value;
export const afterPaint = callback => new Promise(resolve => requestAnimationFrame(() => {
  callback?.();
  resolve();
}));
