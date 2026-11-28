import React from 'react'
import ComparableListingsCard from './ComparableListingsCard.jsx'
import { loadComparables } from './comparables.js'
import { useComparableRequest } from './useComparableRequest.js'

export default function ComparableEvidenceLookup({ body, title }) {
  const { authorized, state, run } = useComparableRequest(JSON.stringify(body))
  if (!body) return null
  if (!authorized) {
    return <p className="cmp-muted">Đối chiếu tin đăng dành cho tài khoản môi giới hoặc quản trị viên.</p>
  }

  const load = () => run(() => loadComparables(body))

  return state
    ? <ComparableListingsCard loading={state.loading} forbidden={state.forbidden}
        error={state.failure ? 'Chưa tải được tin tương đồng. Vui lòng thử lại.' : null}
        result={state.result} title={title} onRetry={load} />
    : <button type="button" className="cmp-link cmp-lookup" onClick={load}>{title}</button>
}
