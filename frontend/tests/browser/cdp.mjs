export async function connect(base = 'http://127.0.0.1:49374') {
  const target = await fetch(base + '/json/new?about:blank', { method: 'PUT' }).then(response => response.json());
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let counter = 0;
  const pending = new Map();
  const listeners = new Map();
  const errors = [];
  function send(method, params = {}) {
    const id = ++counter;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)); }, 25000);
      pending.set(id, { resolve, reject, timer });
      socket.send(JSON.stringify({ id, method, params }));
    });
  }
  socket.onmessage = ({ data }) => {
    const message = JSON.parse(data);
    if (message.id) {
      const item = pending.get(message.id);
      if (!item) return;
      clearTimeout(item.timer);
      pending.delete(message.id);
      if (message.error) item.reject(new Error(message.error.message)); else item.resolve(message.result);
    } else for (const callback of listeners.get(message.method) || []) Promise.resolve(callback(message.params)).catch(error => errors.push(error.message));
  };
  function on(name, fn) { listeners.set(name, [...(listeners.get(name) || []), fn]); }
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
  }
  async function waitFor(expression, timeout = 12000) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      if (await evaluate(expression)) return;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error('Condition not reached: ' + expression);
  }
  await send('Page.enable');
  await send('Runtime.enable');
  on('Runtime.exceptionThrown', event => errors.push(event.exceptionDetails.exception?.description || event.exceptionDetails.text));
  return { send, evaluate, on, waitFor, errors, close: async () => { await send('Page.close').catch(() => {}); socket.close(); } };
}
