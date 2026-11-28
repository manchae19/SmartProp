import React, { useState, useSyncExternalStore } from 'react'
import { session } from '../auth/api.js'
import ComparableListingsCard from './ComparableListingsCard.jsx'
import { isForbidden, loadComparables } from './comparables.js'

export default function ComparableEvidenceLookup({ body, title }) {
  const current = useSyncExternalStore(session.subscribe, session.getSnapshot)
  const [lookup, setLookup] = useState(null)
  if (!body) return null
  const token = current.token
  const key = JSON.stringify(body)
  const state = token && lookup?.token === token && lookup.key === key ? lookup : null
  if (!token || !['BROKER', 'ADMIN'].includes(current.user?.role)) {
    return <p className="cmp-muted">Đối chiếu tin đăng dành cho tài khoản môi giới hoặc quản trị viên.</p>
  }

  const load = async () => {
    setLookup({ token, key, loading: true })
    try {
      const result = await loadComparables(body)
      setLookup(previous => previous?.token === token && previous.key === key ? { token, key, result } : previous)
    } catch (failure) {
      setLookup(previous => previous?.token === token && previous.key === key ? {
        token, key, forbidden: isForbidden(failure),
        error: 'Chưa tải được tin tương đồng. Vui lòng thử lại.',
      } : previous)
    }
  }

  return state
    ? <ComparableListingsCard loading={state.loading} error={state.error} forbidden={state.forbidden}
        result={state.result} title={title} onRetry={load} />
    : <button type="button" className="cmp-link cmp-lookup" onClick={load}>{title}</button>
}
