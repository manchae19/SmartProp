const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PR40_BROWSER_PLAYWRIGHT || 'playwright-core');

const { PR48_BACKEND_PORT, PR48_FRONTEND_PORT, PR48_TLS_CERT, PR48_TLS_KEY,
  PR48_EXPECTED_EMAIL, PR48_FIXTURE_PASSWORD } = process.env;
const secure = Boolean(PR48_TLS_CERT);
const origin = (secure ? 'https' : 'http') + '://127.0.0.1:' + PR48_FRONTEND_PORT;
const root = path.resolve(__dirname, '../..');
let step = 'startup';

(async () => {
  assert.ok(Number(PR48_BACKEND_PORT) >= 49152 && Number(PR48_FRONTEND_PORT) >= 49152);
  const target = 'http://127.0.0.1:' + PR48_BACKEND_PORT;
  const { createServer } = await import(pathToFileURL(path.join(root, 'node_modules/vite/dist/node/index.js')).href);
  process.env.VITE_ENABLE_REFRESH = 'true';
  process.env.VITE_API_BASE_URL = '/api/v1';
  process.env.SMARTPROP_DEV_API_TARGET = target;
  const vite = await createServer({ root, server: {
    host: '127.0.0.1', port: Number(PR48_FRONTEND_PORT), strictPort: true,
    proxy: {
      '/api': { target, changeOrigin: false, configure: proxy => {
        proxy.on('proxyReq', request => {
          request.setHeader('X-Forwarded-Proto', secure ? 'https' : 'http');
          request.setHeader('X-Forwarded-Port', PR48_FRONTEND_PORT);
        });
      } }
    },
    ...(secure ? { https: { cert: fs.readFileSync(PR48_TLS_CERT), key: fs.readFileSync(PR48_TLS_KEY) } } : {})
  } });
  let browser;
  try {
    await vite.listen();
    browser = await chromium.launch({ executablePath: process.env.PR40_BROWSER_EXECUTABLE, headless: true });
    const ctx = await browser.newContext({ ignoreHTTPSErrors: secure, serviceWorkers: 'block', viewport: { width: 1280, height: 820 } });
    const page = await ctx.newPage();
    page.setDefaultTimeout(12000);
    page.on('response', response => {
      const url = new URL(response.url());
      if (url.origin === origin && (url.pathname.startsWith('/api/v1/auth') || url.pathname.startsWith('/api/v1/users/me'))) {
        console.log('fixture HTTP ' + response.request().method() + ' ' + url.pathname + ' ' + response.status());
      }
    });
    page.on('pageerror', error => console.error('fixture page error: ' + error.name));
    page.on('requestfailed', request => {
      const url = new URL(request.url());
      if (url.origin === origin && url.pathname.startsWith('/api/v1/auth')) {
        console.error('fixture request failed ' + url.pathname + ' ' + request.failure()?.errorText);
      }
    });
    await ctx.route('**/*', route => {
      const { hostname } = new URL(route.request().url());
      return ['127.0.0.1', 'localhost'].includes(hostname) ? route.continue() : route.abort();
    });
    const completionPath = '/api/v1/auth/google/link/complete';
    const flowCookie = 'SMARTPROP_GOOGLE_LINK';
    const ticketCookie = 'SMARTPROP_GOOGLE_LINK_TICKET';
    const waitApi = (path, method = 'POST') =>
      page.waitForResponse(response => new URL(response.url()).pathname === path && response.request().method() === method);
    const cookieOnResponse = async (response, name, maxAge) => {
      const value = (await response.headerValues('set-cookie')).find(header => header.startsWith(name + '='));
      assert.ok(value, 'Missing expected cookie');
      const attrs = value.split(';').slice(1).map(field => field.trim().toLowerCase());
      assert.ok(attrs.includes('path=/api/v1/auth') && attrs.includes('httponly'));
      assert.ok(attrs.includes('samesite=lax') && attrs.includes('max-age=' + maxAge));
      assert.equal(attrs.includes('secure'), secure);
    };

    step = 'password sign-in';
    const initial = await page.goto(origin + '/login?redirect=%2Faccount');
    assert.equal(initial.status(), 200);

    step = 'password form rendered';
    await page.locator('#email-input').fill(PR48_EXPECTED_EMAIL);
    await page.locator('#password-input').fill(PR48_FIXTURE_PASSWORD);
    step = 'submit password form';
    const signIn = waitApi('/api/v1/auth/login');
    await page.locator('form').getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    const signInResponse = await signIn;
    assert.equal(signInResponse.status(), 200);
    step = 'password response navigation';
    await page.waitForURL(url => url.pathname !== '/login');
    await page.goto(origin + '/account');
    const form = page.locator('form').filter({ has: page.getByRole('button', { name: 'Liên kết Google', exact: true }) });

    const sessionIdOf = async request => {
      const bearer = (await request.allHeaders()).authorization;
      if (!bearer) return null;
      return JSON.parse(Buffer.from(bearer.split('.')[1], 'base64url').toString('utf8')).jti;
    };
    step = 'wrong password';
    await form.locator('input[type=password]').fill('incorrect-fixture');
    const wrong = waitApi('/api/v1/auth/google/link/start');
    await form.getByRole('button', { name: 'Liên kết Google' }).click();
    assert.equal((await wrong).status(), 400);
    await page.getByText('Mật khẩu hiện tại không chính xác', { exact: true }).waitFor();
    assert.equal(await form.locator('input[type=password]').inputValue(), '');
    assert.equal((await ctx.cookies()).some(cookie => cookie.name === flowCookie), false);

    step = 'correct password, controlled provider callback and session restore';
    await form.locator('input[type=password]').fill(PR48_FIXTURE_PASSWORD);
    const start = waitApi('/api/v1/auth/google/link/start');
    const callback = waitApi('/api/v1/auth/oauth2/callback/google', 'GET');
    const complete = waitApi(completionPath);
    const refresh = waitApi('/api/v1/auth/refresh');
    await form.getByRole('button', { name: 'Liên kết Google' }).click();
    const started = await start;
    assert.equal(started.status(), 200);
    assert.ok((await started.request().allHeaders())['x-csrf-token']);
    assert.ok((await started.request().allHeaders()).cookie?.includes('XSRF-TOKEN='));
    await cookieOnResponse(started, flowCookie, 300);
    const received = await callback;
    assert.equal(new URL(received.url()).origin, origin);
    assert.equal(await received.headerValue('location'), origin + '/auth/google/link/complete');
    assert.ok((await received.request().allHeaders()).cookie?.includes(flowCookie + '='));
    await cookieOnResponse(received, ticketCookie, 60);
    assert.equal((await refresh).status(), 200);
    const completed = await complete;
    assert.equal(completed.status(), 200);
    const startingSession = await sessionIdOf(started.request());
    assert.ok(startingSession && startingSession === await sessionIdOf(completed.request()),
      'Binding changed during browser session restoration');
    assert.ok((await completed.request().allHeaders()).cookie?.includes(ticketCookie + '='));
    assert.ok((await completed.request().allHeaders())['x-csrf-token']);
    await cookieOnResponse(completed, flowCookie, 0);
    await cookieOnResponse(completed, ticketCookie, 0);
    await page.getByText(/Google đã được liên kết với tài khoản SmartProp của bạn/).waitFor();
    assert.equal((await ctx.cookies()).some(cookie => [flowCookie, ticketCookie].includes(cookie.name)), false);
    assert.equal(await page.evaluate(() => document.cookie.includes('SMARTPROP_GOOGLE_')), false);
    const duplicate = await page.evaluate(async () => {
      const { completeGoogleLink, getGoogleLinkScope } = await import('/src/features/auth/api.js');
      try { await completeGoogleLink(getGoogleLinkScope()); return 200; }
      catch (error) { return error.status; }
    });
    assert.equal(duplicate, 410);

    step = 'reload and sign-in by linked subject';
    await page.getByRole('button', { name: /Quay lại Hồ sơ/ }).click();
    await page.getByText('Đã liên kết Google với tài khoản SmartProp này.', { exact: true }).waitFor();
    await page.evaluate(async () => (await import('/src/features/auth/api.js')).logout());
    await page.goto(origin + '/login');
    await page.getByRole('button', { name: 'Tiếp tục với Google', exact: true }).click();
    await page.waitForURL(url => !['/login', '/auth/google/complete'].includes(url.pathname));
    await page.goto(origin + '/account');
    await page.getByText(PR48_EXPECTED_EMAIL, { exact: true }).waitFor();
    await page.getByText('Đã liên kết Google với tài khoản SmartProp này.', { exact: true }).waitFor();
    step = 'callback after revocation';
    await page.evaluate(async () => (await import('/src/features/auth/api.js')).logout());
    await page.goto(origin + '/login?redirect=%2Faccount');
    await page.locator('#email-input').fill(process.env.PR48_REVOKE_EMAIL);
    await page.locator('#password-input').fill(process.env.PR48_REVOKE_PASSWORD);
    const secondLogin = waitApi('/api/v1/auth/login');
    await page.locator('form').getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    assert.equal((await secondLogin).status(), 200);
    await page.waitForURL(url => url.pathname !== '/login');
    await page.goto(origin + '/account');
    await form.locator('input[type=password]').fill(process.env.PR48_REVOKE_PASSWORD);
    let revoked = false;
    let completionRequests = 0;
    page.on('request', request => {
      if (new URL(request.url()).pathname === completionPath) completionRequests++;
    });
    await ctx.route(url => url.pathname === '/api/v1/auth/oauth2/callback/google', async route => {
      // Revoke through the ordinary cookie-authenticated logout endpoint before forwarding the callback.
      const challenge = await ctx.request.get(origin + '/api/v1/auth/csrf', { headers: { Origin: origin } });
      assert.equal(challenge.status(), 200);
      const csrf = await challenge.json();
      const loggedOut = await ctx.request.post(origin + '/api/v1/auth/logout', {
        headers: { Origin: origin, [csrf.headerName]: csrf.token }
      });
      assert.equal(loggedOut.status(), 204);
      revoked = true;
      await route.fallback();
    }, { times: 1 });
    await form.getByRole('button', { name: 'Liên kết Google' }).click();
    await page.getByRole('alert').filter({ hasText: 'Phiên đăng nhập đã thay đổi' }).waitFor();
    assert.ok(revoked);
    assert.equal(completionRequests, 0);

    console.log('PASS actual browser, Spring OAuth/Tomcat, MySQL and controlled signed OIDC, Secure=' + secure);
  } finally {
    await browser?.close();
    await vite.close();
  }
})().catch(error => {
  console.error('OAuth fixture failed at ' + step + ' (' + error.name + '): ' +
    (error.name === 'AssertionError' ? error.message : 'check the failing step'));
  process.exitCode = 1;
});
