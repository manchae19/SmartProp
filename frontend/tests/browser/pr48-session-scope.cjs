const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PR40_BROWSER_PLAYWRIGHT || 'playwright-core');

const root = path.resolve(__dirname, '../..');
const profile = (id, name) => ({ id, email: 'user' + id + '@example.invalid', fullName: name, role: 'BUYER', status: 'ACTIVE' });
function token(id, sid, serial) {
  const encode = data => Buffer.from(JSON.stringify(data)).toString('base64url');
  return encode({ alg: 'fixture' }) + '.' + encode({ iss: 'smartprop', sub: String(id), jti: sid, ver: 0, iat: serial }) + '.fixture';
}

(async () => {
  process.env.VITE_ENABLE_REFRESH = 'true';
  const { createServer } = await import(pathToFileURL(path.join(root, 'node_modules/vite/dist/node/index.js')).href);
  const vite = await createServer({ root, server: { host: '127.0.0.1', port: 0 } });
  let browser;
  let step = 'startup';
  try {
    await vite.listen();
    const origin = 'http://127.0.0.1:' + vite.httpServer.address().port;
    browser = await chromium.launch({ executablePath: process.env.PR40_BROWSER_EXECUTABLE, headless: true });
    for (const scenario of ['account-switch', 'same-user-new-session', 'logout-completion', 'same-user-completion', 'ordinary-refresh']) {
      step = scenario;
      let entered, release, authRequests = 0, login = false, serial = 0;
      let user = profile(41, 'Account Before');
      let sid = 'original-browser-fixture';
      const oldRequest = new Promise(resolve => { entered = resolve; });
      const waitForRelease = new Promise(resolve => { release = resolve; });
      const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
      try {
        const page = await ctx.newPage();
        page.setDefaultTimeout(8000);
        let delayed = false;
        await ctx.route('**/api/**', async route => {
          const p = new URL(route.request().url());
          const send = (body, status = 200) => route.fulfill({ json: body, status });
          if (p.pathname.endsWith('/auth/csrf')) return send({ headerName: 'X-CSRF-TOKEN', token: 'fixture' });
          if (p.pathname.endsWith('/auth/refresh')) return send({ user, accessToken: token(user.id, sid, ++serial) });
          if (p.pathname.endsWith('/auth/login')) {
            login = true;
            sid = 'new-browser-fixture';
            user = profile(scenario === 'account-switch' ? 42 : 41, 'Account After');
            return send({ user, accessToken: token(user.id, sid, ++serial) });
          }
          if (p.pathname.endsWith('/auth/logout')) return send({});
          if (p.pathname.endsWith('/users/me') && p.searchParams.has('rotate') && serial === 1) {
            return send({ code: 'UNAUTHENTICATED' }, 401);
          }
          if (p.pathname.endsWith('/users/me')) return send(user);
          if (p.pathname.endsWith('/users/me/valuation-history')) return send({ items: [], totalPages: 0 });
          if (p.pathname.endsWith('/auth/google/link/status')) {
            if (scenario === 'account-switch' && !login && !delayed) {
              delayed = true; entered(); await waitForRelease;
              return send({ available: true, linked: true });
            }
            return send({ available: true, linked: false });
          }
          if (p.pathname.endsWith('/auth/google/link/start')) {
            entered(); await waitForRelease;
            return send({ authorizationPath: '/auth/oauth2/link/authorize/google' });
          }
          if (p.pathname.endsWith('/auth/google/link/complete')) {
            entered(); await waitForRelease;
            return send({ linked: true });
          }
          if (p.pathname.endsWith('/auth/oauth2/link/authorize/google')) {
            authRequests++;
            return route.fulfill({ status: 200, body: 'controlled redirect reached' });
          }
          return send({});
        });
        const complete = scenario.endsWith('completion');
        await page.goto(origin + (complete ? '/auth/google/link/complete' : '/account'));
        if (!complete && scenario !== 'account-switch') {
          const form = page.locator('form').filter({ has: page.getByRole('button', { name: 'Liên kết Google', exact: true }) });
          await form.locator('input[type=password]').fill('fixture-password');
          await form.getByRole('button', { name: 'Liên kết Google' }).click();
        }
        await Promise.race([oldRequest, new Promise((_, reject) => {
          const timer = setTimeout(() => reject(Error('expected pending request')), 8000);
          timer.unref();
        })]);
        await page.evaluate(async name => {
          const auth = await import('/src/features/auth/api.js');
          if (name === 'logout-completion') await auth.logout();
          else if (name === 'ordinary-refresh') await auth.api('/users/me?rotate=1');
          else await auth.login('fixture@example.invalid', 'fixture-only');
        }, scenario);

        const suffix = complete ? '/complete' : scenario === 'account-switch' ? '/status' : '/start';
        const oldResponse = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/auth/google/link' + suffix));
        release();
        await (await oldResponse).finished();
        if (scenario === 'ordinary-refresh') {
          await page.waitForURL('**/auth/oauth2/link/authorize/google');
          assert.equal(authRequests, 1);
          assert.ok(serial >= 2);
        } else if (complete) {
          await page.getByRole('alert').filter({ hasText: 'Phiên đăng nhập đã thay đổi' }).waitFor();
          assert.equal(await page.getByText(/Google đã được liên kết với tài khoản SmartProp của bạn/).count(), 0);
        } else {
          await page.getByText('Account After', { exact: true }).first().waitFor();
          await page.getByText('Chưa liên kết Google với tài khoản SmartProp này.', { exact: true }).waitFor();
          assert.equal(await page.getByText('Đã liên kết Google với tài khoản SmartProp này.', { exact: true }).count(), 0);
          assert.equal(authRequests, 0);
        }
        console.log(scenario + ' PASS');
      } finally {
        release();
        await ctx.close();
      }
    }
  } catch (error) {
    console.error(step + ' failed (' + error.name + '): ' + (error.name === 'AssertionError' ? error.message : 'check the failing step'));
    process.exitCode = 1;
  } finally {
    await browser?.close();
    await vite.close();
  }
})().catch(error => { console.error(error.name); process.exitCode = 1; });
