import React, { useState, useSyncExternalStore } from 'react'
import { errorText, session } from '../auth/api.js'
import ComparableListingsCard from './ComparableListingsCard.jsx'
import { COMPARABLE_DISTRICTS, buildComparableBody, isForbidden, loadComparables } from './comparables.js'
import './ComparablesView.css'

const TYPES = [
  { value: 'Nhà ở', label: 'Nhà ở / Nhà phố' },
  { value: 'Đất nền', label: 'Đất nền' },
  { value: 'Căn hộ chung cư', label: 'Căn hộ chung cư' },
  { value: 'VILLA', label: 'Biệt thự' },
]

const EMPTY_FORM = { purpose: 'SIMILAR_LISTING', propertyType: 'Nhà ở', district: 'Hải Châu', ward: '', areaSqm: '', priceVnd: '', bedrooms: '', floors: '' }

/**
 * Direct comparable lookup. Requires BROKER/ADMIN on the server; a 403 is shown
 * as a clear requirement message instead of widening access.
 */
export default function ComparablesView() {
  const [form, setForm] = useState(EMPTY_FORM)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [forbidden, setForbidden] = useState(false)
  const current = useSyncExternalStore(session.subscribe, session.getSnapshot)
  const formKey = JSON.stringify(form)

  const patch = (key, value) => setForm((current) => ({ ...current, [key]: value }))

  async function submit(event) {
    event?.preventDefault()
    // Anonymous callers get a clear notice instead of letting the global 401
    // handler bounce them to /login; the server gate is unchanged (BROKER/ADMIN).
    if (!current.token || !['BROKER', 'ADMIN'].includes(current.user?.role)) {
      setResult(null)
      setError('')
      setForbidden(true)
      return
    }
    setBusy(true)
    setError('')
    setForbidden(false)
    try {
      const body = buildComparableBody(form)
      setResult({ token: current.token, formKey, data: await loadComparables(body) })
    } catch (failure) {
      setResult(null)
      if (isForbidden(failure)) setForbidden(true)
      else setError(failure?.status ? errorText(failure) : failure?.message || 'Không thể tìm tin tương đồng.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="cmpv-section" data-comparables-view>
      <div className="cmpv-container">
        <h1 className="cmpv-title">Tìm bất động sản tương đồng</h1>
        <p className="cmpv-sub">
          Tìm tin theo địa bàn, loại hình và diện tích. Chọn mục đích để áp dụng tiêu chí giá phù hợp.
        </p>

        <form className="cmpv-form" onSubmit={submit}>
          <label>Mục đích
            <select value={form.purpose} onChange={(e) => patch('purpose', e.target.value)}>
              <option value="SIMILAR_LISTING">Tìm tin tương đồng theo giá rao</option>
              <option value="BUYER_BUDGET_SEARCH">Tìm theo ngân sách mua</option>
              <option value="VALUATION_SUPPORT">Đối chiếu định giá độc lập</option>
            </select>
          </label>
          <label>Loại BĐS
            <select value={form.propertyType} onChange={(e) => patch('propertyType', e.target.value)}>
              {TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </label>
          <label>Quận/Huyện
            <select value={form.district} onChange={(e) => patch('district', e.target.value)}>
              {COMPARABLE_DISTRICTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <label>Phường (tuỳ chọn)
            <input value={form.ward} onChange={(e) => patch('ward', e.target.value)} placeholder="vd: Thạch Thang" />
          </label>
          <label>Diện tích (m²)
            <input type="number" min="5" max="50000" step="0.1" value={form.areaSqm} onChange={(e) => patch('areaSqm', e.target.value)} placeholder="vd: 80" />
          </label>
          {form.purpose !== 'VALUATION_SUPPORT' ? <label>{form.purpose === 'BUYER_BUDGET_SEARCH' ? 'Ngân sách tối đa (VND)' : 'Giá rao tham chiếu (VND)'}
            <input type="number" min="0" step="1000000" value={form.priceVnd} onChange={(e) => patch('priceVnd', e.target.value)} placeholder="tuỳ chọn" />
          </label> : null}
          <label>Phòng ngủ
            <input type="number" min="0" step="1" value={form.bedrooms} onChange={(e) => patch('bedrooms', e.target.value)} placeholder="tuỳ chọn" />
          </label>
          <label>Số tầng
            <input type="number" min="0" step="1" value={form.floors} onChange={(e) => patch('floors', e.target.value)} placeholder="tuỳ chọn" />
          </label>
          <button type="submit" className="cmpv-submit" disabled={busy}>
            {busy ? 'Đang tìm…' : 'Tìm tin tương đồng'}
          </button>
        </form>

        <ComparableListingsCard
          loading={busy}
          error={error}
          forbidden={forbidden}
          result={current.token && current.token === result?.token && formKey === result.formKey ? result.data : null}
          onRetry={submit}
        />
      </div>
    </section>
  )
}
