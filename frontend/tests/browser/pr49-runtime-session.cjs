const assert = require('node:assert/strict');

const authModule = '/src/features/auth/api.js';

async function browserSession(page) {
  return page.evaluate(async authModule => {
    const { session, getGoogleLinkScope } = await import(authModule);
    const { token, user, status } = session.getSnapshot();
    if (!token || status !== 'AUTHENTICATED') return null;
    const decode = part => JSON.parse(atob(part.replace(/-/g, '+').replace(/_/g, '/')));
    const [header, payload, signature] = token.split('.');
    const { iss, sub, jti, ver } = decode(payload);
    return { iss, sub, jti, ver, userId: String(user.id), scope: getGoogleLinkScope(),
      signed: Boolean(signature) && decode(header).alg === 'HS256' };
  }, authModule);
}

async function waitForBoundSession(page, previous) {
  await page.evaluate(async authModule => {
    const { session, getGoogleLinkScope } = await import(authModule);
    window.pr49SessionMatches = previous => {
      const { token } = session.getSnapshot();
      if (!token || getGoogleLinkScope() == null) return false;
      const claims = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      return !previous || claims.jti !== previous;
    };
    window.pr49SignedOut = () => session.getSnapshot().status === 'UNAUTHENTICATED' && getGoogleLinkScope() == null;
  }, authModule);
  await page.waitForFunction(previous => window.pr49SessionMatches(previous), previous);
}

async function verifySharedBrowserSession({ ctx, page, origin, email, password }) {
  await waitForBoundSession(page);
  const first = await browserSession(page);
  assert.ok(first, 'Expected active session on the first tab');
  assert.ok(first.signed, 'Expected a server-issued HS256 credential');
  assert.ok(first.iss === 'smartprop', 'Expected SmartProp issuer');
  assert.ok(String(first.sub) === first.userId, 'Expected authenticated account subject');
  assert.ok(first.jti && Number.isSafeInteger(first.ver), 'Expected session and integer version claims');
  const peer = await ctx.newPage();
  peer.setDefaultTimeout(12000);
  let releaseResponse;
  try {
    await page.evaluate(() => new Promise(acquired => {
      void navigator.locks.request('smartprop-refresh', () => new Promise(release => {
        window.pr49ReleaseLock = release;
        acquired();
      }));
    }));
    try {
      await peer.goto(origin + '/account');
      const queued = await page.evaluate(async () => {
        const deadline = performance.now() + 8000;
        while (performance.now() < deadline) {
          if ((await navigator.locks.query()).pending.some(request => request.name === 'smartprop-refresh')) return true;
          await new Promise(resolve => setTimeout(resolve, 25));
        }
        return false;
      });
      assert.ok(queued, 'Peer initialization queued behind the held Web Lock');
      assert.equal(await browserSession(peer), null, 'Real browser lock holds cookie-based initialization');
    } finally {
      await page.evaluate(() => window.pr49ReleaseLock?.());
    }
    await waitForBoundSession(peer);
    const peerFirst = await browserSession(peer);
    assert.ok(peerFirst.signed && peerFirst.iss === first.iss && peerFirst.sub === first.sub
      && peerFirst.jti === first.jti && peerFirst.ver === first.ver, 'Peer refresh must preserve the signed session');
    // Force one expired-access response, then use the real Spring refresh and profile endpoints.
    await peer.route(url => url.pathname === '/api/v1/users/me' && url.searchParams.has('pr49_refresh'), route => route.fulfill({
      status: 401, json: { code: 'UNAUTHENTICATED' },
    }), { times: 1 });
    const refresh = peer.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/refresh');
    const validProfile = await peer.evaluate(async authModule => {
      const { api, session } = await import(authModule);
      return String((await api('/users/me?pr49_refresh=1')).id) === String(session.getSnapshot().user.id);
    }, authModule);
    assert.ok(validProfile && (await refresh).ok(), 'The backend must authorize the reissued credential');
    const renewed = await browserSession(peer);
    assert.ok(renewed.jti === peerFirst.jti && renewed.scope === peerFirst.scope, 'Renewal must preserve linking scope');

    await peer.evaluate(() => {
      window.pr49Messages = [];
      const channel = new BroadcastChannel('smartprop-session');
      channel.onmessage = event => window.pr49Messages.push(event.data);
      window.pr49Channel = channel;
    });
    const barrier = new Promise(resolve => { releaseResponse = resolve; });
    let received;
    const observed = new Promise(resolve => { received = resolve; });
    await peer.route('**/api/v1/auth/google/link/status', async route => {
      try {
        const response = await route.fetch();
        received(response.status());
        await barrier;
        await route.fulfill({ response });
      } catch {
        received(0);
        await route.abort().catch(() => {});
      }
    }, { times: 1 });
    await peer.evaluate(async authModule => {
      const { googleLinkStatus, getGoogleLinkScope } = await import(authModule);
      window.pr49Pending = googleLinkStatus(getGoogleLinkScope()).then(() => 'accepted', error => error.code);
    }, authModule);
    const waitLimit = AbortSignal.timeout(10000);
    const deadline = new Promise((_, reject) => waitLimit.addEventListener('abort', () => {
      reject(Error('Expected a real linking status request'));
    }, { once: true }));
    assert.equal(await Promise.race([observed, deadline]), 200);
    await page.evaluate(async ({ authModule, email, password }) => {
      const { login } = await import(authModule);
      await login(email, password);
    }, { authModule, email, password });
    await waitForBoundSession(peer, peerFirst.jti);
    const next = await browserSession(peer);
    assert.ok(next.signed && next.sub === first.sub && next.jti !== first.jti && next.scope !== peerFirst.scope,
      'A login in the other tab must replace the same-account session');
    releaseResponse();
    assert.equal(await peer.evaluate(() => window.pr49Pending), 'SESSION_CHANGED');

    await page.evaluate(async authModule => (await import(authModule)).logout(), authModule);
    await peer.waitForFunction(() => window.pr49SignedOut());
    assert.ok(await peer.evaluate(() => window.pr49Messages.length === 2
      && window.pr49Messages[0] === 'login' && window.pr49Messages[1] === 'logout'),
      'BroadcastChannel must transmit only the login/logout actions');
    console.log('PASS signed claims, Web Locks, same-account replacement and cross-tab logout');
  } finally {
    releaseResponse?.();
    await page.evaluate(() => window.pr49ReleaseLock?.()).catch(() => {});
    await peer.close();
  }
}

module.exports = { verifySharedBrowserSession };
