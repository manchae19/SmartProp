import { useLayoutEffect, useRef, useState, useSyncExternalStore } from 'react'
import { createStateStore } from '../../shared/state/createStateStore.js'
import { hasActiveSession, sameRestrictedSession } from '../../shared/lib/restrictedSession.js'
import { session } from '../auth/api.js'
import { isForbidden } from './comparables.js'

function readAccess(snapshot) {
  return { authorized: hasActiveSession(snapshot) && ['BROKER', 'ADMIN'].includes(snapshot.user?.role) }
}

// A new snapshot invalidates the old one even if revocation and restoration are batched.
let previousSession = session.getSnapshot()
const accessStore = createStateStore(readAccess(previousSession))
const unsubscribe = session.subscribe(() => {
  const next = session.getSnapshot()
  const changed = !sameRestrictedSession(previousSession, next)
  previousSession = next
  if (changed) accessStore.set(readAccess(next))
})
import.meta.hot?.dispose(unsubscribe)

export function useComparableRequest(criteriaKey) {
  const access = useSyncExternalStore(accessStore.subscribe, accessStore.getSnapshot)
  const [state, setState] = useState(null)
  const generation = useRef(0)

  useLayoutEffect(() => {
    setState(null)
    return () => {
      generation.current += 1
    }
  }, [access, criteriaKey])

  async function run(request) {
    if (access !== accessStore.getSnapshot()) return
    const scope = { access, criteriaKey }
    if (!access.authorized) {
      setState({ ...scope, forbidden: true })
      return
    }
    const id = ++generation.current
    const isCurrent = () => id === generation.current && access === accessStore.getSnapshot()
    setState({ ...scope, loading: true })
    try {
      const result = await request()
      if (isCurrent()) setState({ ...scope, result })
    } catch (failure) {
      if (isCurrent()) {
        setState({ ...scope, ...(isForbidden(failure) ? { forbidden: true } : { failure }) })
      }
    }
  }

  return {
    authorized: access.authorized,
    state: state?.access === access && state.criteriaKey === criteriaKey ? state : null,
    run,
  }
}
