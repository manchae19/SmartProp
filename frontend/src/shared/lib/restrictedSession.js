export function hasActiveSession(snapshot) {
  return snapshot?.status === 'AUTHENTICATED' && Boolean(snapshot.token) && !snapshot.authTransition
    && (snapshot.user?.status == null || snapshot.user.status === 'ACTIVE')
}

const actor = user => user?.id ?? user?.userId ?? user?.sub ?? user?.email

export function sameRestrictedSession(previous, next) {
  // The HTTP client bumps authGeneration for external credential writes, but keeps it on renewal.
  const sameCredentialScope = previous.authGeneration != null || next.authGeneration != null
    ? previous.authGeneration === next.authGeneration
    : previous.token === next.token
  return sameCredentialScope && previous.status === next.status && Boolean(previous.token) === Boolean(next.token)
    && Boolean(previous.authTransition) === Boolean(next.authTransition)
    && actor(previous.user) === actor(next.user) && previous.user?.role === next.user?.role
    && previous.user?.status === next.user?.status
}
