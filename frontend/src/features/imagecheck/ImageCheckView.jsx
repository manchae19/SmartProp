import React, { useEffect, useRef, useState } from 'react'
import { RouterLink } from '../../shared/routing/router.jsx'

const MAX_BYTES = 8 * 1024 * 1024
const TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
const labels = {
  EXACT_DUPLICATE: 'Ảnh trùng',
  NEAR_DUPLICATE: 'Ảnh gần trùng',
  SIMILAR: 'Tương tự, chưa đủ bằng chứng',
  NO_MATCH: 'Không tìm thấy ảnh tương ứng',
  CHECKING: 'Đang kiểm tra',
}

function safeImage(value) {
  return typeof value === 'string' &&
    (value.startsWith('/api/v1/properties/') || value.startsWith('https://res.cloudinary.com/')) &&
    !value.includes('..')
}

export default function ImageCheckView() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [state, setState] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const input = useRef(null)

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  function choose(event) {
    const selected = event.target.files?.[0]
    setResult(null)
    setError('')
    if (!selected) { setFile(null); setPreview(''); return }
    if (!TYPES.includes(selected.type)) { setError('Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.'); return }
    if (selected.size > MAX_BYTES) { setError('Ảnh vượt quá 8 MB.'); return }
    if (preview) URL.revokeObjectURL(preview)
    setFile(selected)
    setPreview(URL.createObjectURL(selected))
    setState('idle')
  }

  async function check() {
    if (!file || state === 'checking') return
    setState('checking')
    setError('')
    setResult(null)
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 60000)
    try {
      const response = await fetch('/api/image-duplicates/check', {
        method: 'POST',
        headers: { 'Content-Type': file.type },
        body: file,
        signal: controller.signal,
        credentials: 'omit',
        cache: 'no-store',
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || 'Không kiểm tra được ảnh.')
      setResult(payload)
      setState('done')
    } catch (err) {
      setError(err?.name === 'AbortError' ? 'Kiểm tra quá 60 giây. Vui lòng thử ảnh nhỏ hơn.' : (err.message || 'Không kiểm tra được ảnh.'))
      setState('idle')
    } finally {
      clearTimeout(timer)
    }
  }

  const matches = Array.isArray(result?.matches) ? result.matches : []
  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-6 max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-gold">SmartProp / Kiểm tra hình ảnh</p>
        <h1 className="mt-2 text-3xl font-semibold text-brand-navy">Ảnh này đã xuất hiện trong tin đăng nào?</h1>
        <p className="mt-3 text-sm leading-6 text-brand-muted">So khớp ảnh với kho ảnh công khai của SmartProp bằng SHA-256, dHash/pHash và đặc trưng màu/bố cục. Đây là bằng chứng tương đồng, không phải kết luận ảnh bị đánh cắp.</p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]">
        <div className="rounded-3xl border border-brand-line bg-white p-5 shadow-sm">
          <label htmlFor="duplicate-image" className="block text-sm font-semibold text-brand-navy">Chọn một ảnh</label>
          <input ref={input} id="duplicate-image" type="file" accept="image/jpeg,image/jpg,image/png,image/webp" onChange={choose} className="mt-3 block w-full rounded-xl border border-brand-line bg-brand-cream px-3 py-3 text-sm text-brand-navy file:mr-3 file:rounded-lg file:border-0 file:bg-brand-navy file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white" />
          <p className="mt-2 text-xs text-brand-muted">JPEG, PNG hoặc WebP · tối đa 8 MB · ảnh chỉ xử lý trong bộ nhớ, không lưu.</p>
          {preview ? <img src={preview} alt="Ảnh đang kiểm tra" className="mt-4 max-h-72 w-full rounded-2xl object-contain bg-brand-cream" /> : null}
          <button type="button" onClick={check} disabled={!file || state === 'checking'} className="mt-4 w-full rounded-xl bg-brand-navy px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
            {state === 'checking' ? 'Đang so khớp…' : 'Kiểm tra ảnh'}
          </button>
          {error ? <p role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
          <p className="mt-4 text-xs leading-5 text-brand-muted">Kết quả chỉ so với ảnh công khai trong SmartProp. Chưa có reverse image search Internet.</p>
        </div>

        <div className="min-w-0">
          <div aria-live="polite" className="mb-4 rounded-2xl border border-brand-line bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold text-brand-navy">Kết quả</h2>
              <span className="rounded-full bg-brand-cream px-3 py-1 text-xs font-semibold text-brand-navy">{labels[result?.status] || labels[state] || 'Chưa kiểm tra'}</span>
            </div>
            {state === 'checking' ? <p className="mt-2 text-sm text-brand-muted">Đang tải index ảnh công khai và so khớp…</p> : null}
            {result ? <p className="mt-2 text-sm leading-6 text-brand-muted">{result.status === 'NO_MATCH' ? 'Chưa tìm thấy ảnh tương tự trong dữ liệu công khai hiện có.' : `Tìm thấy ${matches.length} ảnh cần đối chiếu. Hãy mở tin đăng và xác minh thủ công.`}</p> : null}
            {Array.isArray(result?.limitations) ? <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-brand-muted">{result.limitations.map((item) => <li key={item}>{item}</li>)}</ul> : null}
          </div>

          {matches.length ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {matches.map((match) => (
                <article key={`${match.propertyId}-${match.imageId}`} className="overflow-hidden rounded-2xl border border-brand-line bg-white shadow-sm">
                  {safeImage(match.imageUrl) ? <img src={match.imageUrl} alt="" loading="lazy" className="h-40 w-full object-cover" /> : null}
                  <div className="p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-brand-gold">{labels[match.classification] || match.classification}</p>
                    <h3 className="mt-1 line-clamp-2 text-sm font-semibold text-brand-navy">{match.title || match.listingCode || match.propertyId}</h3>
                    <p className="mt-1 text-xs text-brand-muted">{match.listingCode || '—'}{match.location ? ` · ${match.location}` : ''}</p>
                    <p className="mt-2 text-sm font-semibold text-brand-navy">Tương đồng {Math.round(Number(match.similarity || 0) * 100)}%</p>
                    <p className="text-xs text-brand-muted">Phương pháp: {match.method}</p>
                    <RouterLink to={match.listingUrl || `/listing/${match.propertyId}`} className="mt-3 inline-flex text-sm font-semibold text-brand-gold hover:underline">Mở tin đăng →</RouterLink>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
