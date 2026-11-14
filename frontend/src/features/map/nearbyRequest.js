// Public, read-only request: no account token, cookies or automatic write retries.
export async function requestNearby(path, { signal, fetcher = fetch, base = '/api/v1', timeoutMs = 12000 } = {}) {
  const controller = new AbortController(), cancel = () => controller.abort()
  if (signal?.aborted) controller.abort()
  signal?.addEventListener('abort', cancel, { once: true })
  const timer = setTimeout(cancel, timeoutMs)
  try {
    const response = await fetcher(base.replace(/\/$/, '') + path, { headers: { Accept: 'application/json' }, credentials: 'omit', signal: controller.signal })
    const value = await response.json()
    if (!response.ok) throw Object.assign(Error(value?.message || 'Không tải được tiện ích.'), { status: response.status, code: value?.code, retryAfter: Number(response.headers.get('Retry-After')) || 10 })
    return value
  } catch (e) {
    if (controller.signal.aborted && !signal?.aborted) throw Object.assign(Error('Tìm tiện ích quá thời gian.'), { code: 'NEARBY_TIMEOUT' })
    throw e
  } finally { clearTimeout(timer); signal?.removeEventListener('abort', cancel) }
}
