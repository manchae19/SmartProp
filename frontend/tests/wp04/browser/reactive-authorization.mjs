import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, realpathSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { advisorPath, deferred, login, prepareAdvisor, waitResponse } from "./workflows.mjs";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || "playwright");
const app = process.env.WP04_APP;
const admin = process.env.WP04_ADMIN_EMAIL;
const buyer = process.env.WP04_BUYER_EMAIL;
const password = process.env.WP04_FIXTURE_PASSWORD;
const authApi = "/src/features/auth/api.js";
const researchButton = /Bật dữ liệu nghiên cứu TiniX/;
const syntheticTitle = "WP04 synthetic restricted result";

function guardedSql() {
  const manifest = JSON.parse(readFileSync(process.env.WP04_RUNTIME_FILE, "utf8"));
  assert.equal(manifest.state, "ready");
  assert.equal(manifest.stack.react, app);
  const configPath = resolve(manifest.db_file);
  const root = realpathSync(manifest.root);
  assert.match(root, /[\\/]wp04-owned-[^\\/]+$/);
  assert.equal(realpathSync(dirname(configPath)), root);
  const fixture = JSON.parse(readFileSync(configPath, "utf8"));
  const { port, schema, user, mysql, datadir } = fixture;
  assert.equal(port, manifest.ports.mysql);
  assert.ok(Number.isInteger(port) && port >= 49152 && port <= 65535);
  assert.equal(schema, "wp04_final_fixture");
  assert.equal(user, "wp04_fixture");
  assert.equal(realpathSync(dirname(datadir)), root);
  assert.match(fixture.uuid, /^[a-f0-9-]{36}$/);
  assert.match(fixture.marker, /^[a-f0-9]{32}$/);
  assert.match(admin, /^[a-z0-9-]+-wp04@example\.invalid$/);
  const run = (statement) => {
    try {
      return execFileSync(mysql, ["--no-defaults", "--protocol=TCP", "--host=127.0.0.1",
        "--port=" + port, "--user=" + user, "--database=" + schema,
        "--batch", "--skip-column-names", "--connect-timeout=3"], {
        env: { ...process.env, MYSQL_PWD: fixture.password }, input: statement,
        encoding: "utf8", stdio: ["pipe", "pipe", "pipe"], timeout: 8000,
      }).trim();
    } catch (error) {
      throw Error("Restricted fixture SQL failed (" + (error.status ?? error.code) + ")");
    }
  };
  function check() {
    const [server, dir, listenPort, database, account, marker] = run(
      "SELECT @@server_uuid,@@datadir,@@port,DATABASE(),CURRENT_USER(),(SELECT marker FROM wp04_isolation_marker);",
    ).split("\t");
    assert.equal(server, fixture.uuid);
    assert.equal(realpathSync(dir), realpathSync(datadir));
    assert.equal(Number(listenPort), port);
    assert.equal(database, schema);
    assert.equal(account, user + "@127.0.0.1");
    assert.equal(marker, fixture.marker);
    const grants = run("SHOW GRANTS FOR CURRENT_USER();").split(/\r?\n/);
    assert.equal(grants.length, 2);
    assert.ok(grants.some((grant) => grant.startsWith("GRANT USAGE ON *.* TO ")));
    assert.ok(grants.some((grant) => grant.startsWith("GRANT ALL PRIVILEGES ON `" + schema + "`.* TO ")));
  }
  return (sql) => { check(); return run(sql); };
}

async function profile(page) {
  return page.evaluate(async (url) => {
    const { api, session } = await import(url);
    const snapshot = session.getSnapshot();
    try {
      const data = await api("/users/me", { authenticated: true });
      return { status: 200, role: data.role, id: data.id, active: snapshot.status === "AUTHENTICATED" };
    } catch (error) {
      return { status: error.status, active: snapshot.status === "AUTHENTICATED" };
    }
  }, authApi);
}

async function lockActiveSession(browser) {
  const sql = guardedSql();
  const page = await browser.newPage();
  const query = "SELECT id,status,role,token_version,IFNULL(locked_at,''),IFNULL(lock_reason,'') FROM users WHERE email='" + admin + "';";
  const raw = sql(query);
  const [id, originalStatus, role] = raw.split("\t");
  assert.match(id, /^\d+$/);
  assert.equal(originalStatus, "ACTIVE");
  assert.equal(role, "ADMIN");
  const setStatus = (status) => assert.equal(sql("UPDATE users SET status='" + status
    + "' WHERE id=" + id + "; SELECT ROW_COUNT();"), "1");
  let locked = false;
  try {
    await login(page, app, admin, password);
    await page.getByText(admin, { exact: true }).first().waitFor();
    const active = await profile(page);
    assert.deepEqual(active, { status: 200, role: "ADMIN", id: Number(id), active: true });
    setStatus("LOCKED");
    locked = true;
    assert.equal(sql(query).split("\t")[1], "LOCKED");
    const response = waitResponse(page, "/api/v1/users/me", "GET");
    const rejected = await profile(page);
    const denied = await response;
    assert.ok((await denied.request().allHeaders()).authorization?.startsWith("Bearer "));
    assert.ok([401, 403].includes(denied.status()));
    assert.ok([401, 403].includes(rejected.status));
    await page.waitForURL((url) => url.pathname === "/login");
    assert.equal(await page.getByText(admin, { exact: true }).count(), 0);
  } finally {
    if (locked || sql(query).split("\t")[1] === "LOCKED") setStatus(originalStatus);
    assert.equal(sql(query), raw, "Fixture account state restoration did not match");
    await page.close();
  }
  const restored = await browser.newPage();
  try {
    await login(restored, app, admin, password);
    assert.equal((await profile(restored)).role, "ADMIN");
  } finally {
    await restored.close();
  }
}

async function replaceAccountDuringResearch(browser) {
  const page = await browser.newPage();
  const delayed = deferred();
  const arrived = deferred();
  const drained = deferred();
  const loginRelease = deferred();
  const loginArrived = deferred();
  let holdResearch = false;
  let safePayload;
  let researchCalls = 0;
  try {
    await login(page, app, admin, password);
    assert.equal((await profile(page)).role, "ADMIN");
    await page.route("**/api/v1/admin/advisor/research-config", async (route) => {
      assert.ok((await route.request().allHeaders()).authorization?.startsWith("Bearer "));
      await route.fulfill({ json: { enabled: true } });
    });
    await page.route("**" + advisorPath, async (route) => {
      const body = route.request().postDataJSON();
      if (!body.includeResearch) {
        const response = await route.fetch();
        safePayload = await response.json();
        await route.fulfill({ response });
        return;
      }
      assert.ok((await route.request().allHeaders()).authorization?.startsWith("Bearer "));
      researchCalls += 1;
      const response = structuredClone(safePayload);
      response.mode = "INTERNAL_RESEARCH";
      response.recommendedProperties[0].title = syntheticTitle;
      if (!holdResearch) return route.fulfill({ json: response });
      arrived.resolve();
      try {
        await delayed.promise;
        await route.fulfill({ json: response });
      } catch (error) {
        assert.match(String(error), /abort|handled|closed|request/i);
      } finally {
        drained.resolve();
      }
    });

    const submit = await prepareAdvisor(page, app);
    const safe = waitResponse(page, advisorPath);
    await submit.click();
    assert.equal((await (await safe).json()).mode, "SAFE");
    await page.locator('[data-advisor-mode="SAFE"]').waitFor();
    await page.getByRole("button", { name: researchButton }).click();
    await prepareAdvisor(page, app, { navigate: false });
    const shown = waitResponse(page, advisorPath);
    await submit.click();
    assert.equal((await (await shown).json()).mode, "INTERNAL_RESEARCH");
    await page.getByText(syntheticTitle, { exact: true }).first().waitFor();

    holdResearch = true;
    const intercepted = page.waitForRequest((request) => new URL(request.url()).pathname === advisorPath
      && request.postDataJSON().includeResearch === true);
    await submit.click();
    await intercepted;
    await arrived.promise;
    await page.route("**/api/v1/auth/login", async (route) => {
      loginArrived.resolve();
      await loginRelease.promise;
      await route.continue();
    });
    const loginRequest = page.waitForRequest((request) => new URL(request.url()).pathname === "/api/v1/auth/login");
    const replacement = page.evaluate(async ({ url, buyer, password }) => {
      const { login } = await import(url);
      const user = await login(buyer, password);
      return { role: user.role };
    }, { url: authApi, buyer, password });
    await loginRequest;
    await loginArrived.promise;
    assert.equal(await page.evaluate(async (url) => {
      const { session } = await import(url);
      return session.getSnapshot().authTransition;
    }, authApi), true);
    await page.getByRole("button", { name: researchButton }).waitFor({ state: "hidden" });
    await page.getByText(syntheticTitle, { exact: true }).first().waitFor({ state: "hidden" });
    await page.getByText("Chế độ công khai an toàn (SAFE)", { exact: true }).waitFor();
    loginRelease.resolve();
    assert.deepEqual(await replacement, { role: "BUYER" });
    assert.equal((await profile(page)).role, "BUYER");
    delayed.resolve();
    await drained.promise;
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.equal(await page.getByText(syntheticTitle, { exact: true }).count(), 0);
    assert.equal(await page.locator('[data-advisor-mode="INTERNAL_RESEARCH"]').count(), 0);
    await page.unroute("**/api/v1/admin/advisor/research-config");
    const denied = await page.evaluate(async (url) => {
      const { api } = await import(url);
      try { await api("/admin/advisor/research-config", { authenticated: true }); return 200; }
      catch (error) { return error.status; }
    }, authApi);
    // The test config fixture is removed before checking the real policy.
    assert.equal(denied, 403);
    await prepareAdvisor(page, app, { navigate: false });
    const fallback = waitResponse(page, advisorPath);
    await submit.click();
    const reply = await fallback;
    assert.equal(reply.request().postDataJSON().includeResearch, false);
    assert.equal((await reply.json()).mode, "SAFE");
    await page.locator('[data-advisor-mode="SAFE"]').waitFor();
    assert.equal(researchCalls, 2);
  } finally {
    delayed.resolve();
    loginRelease.resolve();
    await page.close();
  }
}

const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME });
const outcomes = [];
try {
  for (const [name, evidence, scenario] of [
    ["active admin locks, shared client denies credential, account restored", "REAL_HTTP_AND_MYSQL", lockActiveSession],
    ["authTransition, account replacement, late research response rejected, SAFE fallback",
      "REAL_SESSION_AND_SAFE_API_WITH_SYNTHETIC_RESEARCH_RESPONSE", replaceAccountDuringResearch],
  ]) {
    try {
      await scenario(browser);
      outcomes.push({ name, evidence, ok: true });
      console.log("PASS " + name);
    } catch (error) {
      outcomes.push({ name, evidence, ok: false, error: String(error.message).split("\n")[0] });
      console.log("FAIL " + name + " — " + String(error.message).split("\n")[0]);
    }
  }
} finally {
  await browser.close();
  writeFileSync(process.env.WP04_AUTH_REPORT, JSON.stringify(outcomes, null, 2) + "\n");
  process.exitCode = outcomes.length === 2 && outcomes.every((item) => item.ok) ? 0 : 1;
}
