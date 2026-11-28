import '../src/app/main.jsx'
import router from '../src/app/router.js'
import { session } from '../src/features/auth/api.js'

// This entry is compiled only into the isolated regression build.
window.pr37Fixture = {
  navigate: path => router.navigate(path),
  set({ role, revision = 1, actor = 1, accountStatus = 'ACTIVE', status = 'AUTHENTICATED' }) {
    session.set(role ? {
      token: `fixture-${revision}`,
      user: { id: actor, role, status: accountStatus, displayName: 'Tài khoản fixture' },
      status, error: null,
    } : { token: null, user: null, status: 'UNAUTHENTICATED', error: null })
  },
}
