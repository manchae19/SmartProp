import React, { useEffect, useMemo, useRef, useState } from 'react'

const MAX_BYTES = 8 * 1024 * 1024
const TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
const ENDPOINT = '/api/image-analysis/analyze'

// One colour per object group so the overlay reads at a glance.
const GROUP_COLORS = {
  bedroom: '#7c3aed',
  living: '#0f766e',
  kitchen: '#b45309',
  bathroom: '#0369a1',
  decor: '#be123c',
  other: '#475569',
}

function groupColor(group) {
  return GROUP_COLORS[group] || GROUP_COLORS.other
}

export default function ImageAnalysisView() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [state, setState] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [showBoxes, setShowBoxes] = useState(true)
  const [activeId, setActiveId] = useState(null)
  const input = useRef(null)
  const imageRef = useRef(null)

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  function choose(event) {
    const selected = event.target.files?.[0]
    setResult(null)
    setError('')
    setActiveId(null)
    if (!selected) { setFile(null); setPreview(''); return }
    if (!TYPES.includes(selected.type)) { setError('Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.'); return }
    if (selected.size > MAX_BYTES) { setError('Ảnh vượt quá 8 MB.'); return }
    if (preview) URL.revokeObjectURL(preview)
    setFile(selected)
    setPreview(URL.createObjectURL(selected))
    setState('idle')
  }

  async function analyze() {
    if (!file || state === 'analyzing') return
    setState('analyzing')
    setError('')
    setResult(null)
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 60000)
    try {
      const response = await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': file.type },
        body: file,
        signal: controller.signal,
        credentials: 'omit',
        cache: 'no-store',
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || 'Không phân tích được ảnh.')
      setResult(payload)
      setState('done')
    } catch (err) {
      setError(err?.name === 'AbortError'
        ? 'Phân tích quá 60 giây. Vui lòng thử ảnh nhỏ hơn.'
        : (err.message || 'Không phân tích được ảnh.'))
      setState('idle')
    } finally {
      clearTimeout(timer)
    }
  }

  const detections = Array.isArray(result?.detections) ? result.detections : []
  const counts = result?.countsByLabel || {}
  const summary = useMemo(() => Object.entries(counts).sort((a, b) => b[1] - a[1]), [counts])

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-6 max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-gold">
          SmartProp / Phân tích hình ảnh
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-brand-navy">
          Ảnh này có những đồ vật gì?
        </h1>
        <p className="mt-3 text-sm leading-6 text-brand-muted">
          Nhận diện đối tượng nội thất bằng YOLOv8n (COCO pretrained) và vẽ khung lên ảnh.
          Đây là nhận diện đối tượng, không phải thẩm định chất lượng hay pháp lý bất động sản.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <div className="rounded-3xl border border-brand-line bg-white p-5 shadow-sm">
          <label htmlFor="analysis-image" className="block text-sm font-semibold text-brand-navy">
            Chọn một ảnh
          </label>
          <input
            ref={input}
            id="analysis-image"
            type="file"
            accept="image/jpeg,image/jpg,image/png,image/webp"
            onChange={choose}
            className="mt-3 block w-full rounded-xl border border-brand-line bg-brand-cream px-3 py-3 text-sm text-brand-navy file:mr-3 file:rounded-lg file:border-0 file:bg-brand-navy file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white"
          />
          <p className="mt-2 text-xs text-brand-muted">
            JPEG, PNG hoặc WebP · tối đa 8 MB · ảnh chỉ xử lý trong bộ nhớ, không lưu.
          </p>

          <button
            type="button"
            onClick={analyze}
            disabled={!file || state === 'analyzing'}
            className="mt-4 w-full rounded-xl bg-brand-navy px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {state === 'analyzing' ? 'Đang phân tích…' : 'Phân tích ảnh'}
          </button>

          {error ? (
            <p role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</p>
          ) : null}

          <div className="mt-4 rounded-2xl bg-brand-cream p-3 text-xs leading-5 text-brand-muted">
            <p className="font-semibold text-brand-navy">Mô hình chỉ nhận diện được:</p>
            <p className="mt-1">
              Giường, ghế sofa, ghế, bàn ăn, tivi, tủ lạnh, lò vi sóng, lò nướng, bồn rửa,
              bồn cầu, cây cảnh, đồng hồ, bình hoa.
            </p>
            <p className="mt-2">
              Không nhận diện được: bồn tắm, vòi sen, tủ quần áo, điều hoà, ban công, cầu thang.
            </p>
          </div>
        </div>

        <div className="min-w-0">
          <div aria-live="polite" className="mb-4 rounded-2xl border border-brand-line bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold text-brand-navy">Kết quả</h2>
              <span className="rounded-full bg-brand-cream px-3 py-1 text-xs font-semibold text-brand-navy">
                {state === 'analyzing'
                  ? 'Đang phân tích'
                  : result
                    ? `${result.detectionCount} đối tượng`
                    : 'Chưa phân tích'}
              </span>
            </div>

            {result ? (
              <div className="mt-2 space-y-1 text-sm text-brand-muted">
                <p>
                  Thời gian suy luận <strong className="text-brand-navy">{Math.round(result.timing?.inferenceMs || 0)} ms</strong>
                  {' · '}tổng <strong className="text-brand-navy">{Math.round(result.timing?.totalMs || 0)} ms</strong>
                  {' · '}thiết bị <strong className="text-brand-navy">{result.device}</strong>
                </p>
                <p className="text-xs">
                  Model {result.modelVersion} · {result.image?.width}×{result.image?.height} {result.image?.format}
                </p>
              </div>
            ) : null}

            {result && detections.length === 0 ? (
              <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
                Không phát hiện đối tượng nào thuộc danh sách hỗ trợ. Ảnh có thể là ngoại thất,
                giấy tờ, hoặc chỉ chứa đồ vật mô hình không nhận diện được.
              </p>
            ) : null}

            {summary.length ? (
              <ul className="mt-3 flex flex-wrap gap-2">
                {summary.map(([label, count]) => (
                  <li key={label} className="rounded-full bg-brand-cream px-3 py-1 text-xs font-semibold text-brand-navy">
                    {label} × {count}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>

          {preview ? (
            <div className="relative overflow-hidden rounded-2xl border border-brand-line bg-brand-cream">
              <div className="flex items-center justify-between gap-2 border-b border-brand-line bg-white px-3 py-2">
                <span className="text-xs font-semibold text-brand-navy">Ảnh và khung nhận diện</span>
                <label className="flex items-center gap-2 text-xs text-brand-muted">
                  <input
                    type="checkbox"
                    data-overlay-toggle
                    checked={showBoxes}
                    onChange={(event) => setShowBoxes(event.target.checked)}
                  />
                  Hiện khung
                </label>
              </div>
              <div className="relative">
                <img
                  ref={imageRef}
                  src={preview}
                  alt="Ảnh đang phân tích"
                  className="block max-h-[520px] w-full object-contain"
                />
                {showBoxes && detections.map((item, index) => {
                  const [x1, y1, x2, y2] = item.box || []
                  if ([x1, y1, x2, y2].some((value) => typeof value !== 'number')) return null
                  const id = `${item.cocoName}-${index}`
                  const active = activeId === id
                  return (
                    <div
                      key={id}
                      onMouseEnter={() => setActiveId(id)}
                      onMouseLeave={() => setActiveId(null)}
                      className="pointer-events-auto absolute"
                      style={{
                        left: `${x1 * 100}%`,
                        top: `${y1 * 100}%`,
                        width: `${(x2 - x1) * 100}%`,
                        height: `${(y2 - y1) * 100}%`,
                        border: `2px solid ${groupColor(item.group)}`,
                        boxShadow: active ? `0 0 0 3px ${groupColor(item.group)}55` : 'none',
                        borderRadius: '4px',
                      }}
                    >
                      <span
                        className="absolute left-0 top-0 -translate-y-full whitespace-nowrap rounded-t px-1.5 py-0.5 text-[10px] font-bold text-white"
                        style={{ backgroundColor: groupColor(item.group) }}
                      >
                        {item.label} {Math.round(item.confidence * 100)}%
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : null}

          {detections.length ? (
            <div className="mt-4 overflow-hidden rounded-2xl border border-brand-line bg-white">
              <table data-detection-table className="w-full text-left text-sm">
                <thead className="bg-brand-cream text-xs uppercase tracking-wide text-brand-muted">
                  <tr>
                    <th className="px-3 py-2">Đối tượng</th>
                    <th className="px-3 py-2">Nhóm</th>
                    <th className="px-3 py-2 text-right">Độ tin cậy</th>
                  </tr>
                </thead>
                <tbody>
                  {detections.map((item, index) => {
                    const id = `${item.cocoName}-${index}`
                    return (
                      <tr
                        key={id}
                        onMouseEnter={() => setActiveId(id)}
                        onMouseLeave={() => setActiveId(null)}
                        className={activeId === id ? 'bg-brand-cream' : ''}
                      >
                        <td className="px-3 py-2 font-semibold text-brand-navy">{item.label}</td>
                        <td className="px-3 py-2 text-xs text-brand-muted">{item.group}</td>
                        <td className="px-3 py-2 text-right font-semibold text-brand-navy">
                          {Math.round(item.confidence * 100)}%
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : null}

          {Array.isArray(result?.limitations) ? (
            <ul className="mt-4 list-disc space-y-1 pl-5 text-xs leading-5 text-brand-muted">
              {result.limitations.map((item) => <li key={item}>{item}</li>)}
            </ul>
          ) : null}
        </div>
      </div>
    </section>
  )
}
