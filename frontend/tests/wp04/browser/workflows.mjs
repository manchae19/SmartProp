import assert from "node:assert/strict";

export const predictPath = "/api/ai/predict";
export const previewPath = "/api/v1/properties/valuation-preview";
export const advisorPath = "/api/v1/advisor/consult";
export const matches = (url, path) => new URL(url).pathname === path;
export const waitResponse = (page, path, method = "POST") => page.waitForResponse(
  (response) => matches(response.url(), path) && response.request().method() === method,
  { timeout: 45000 },
);

export function deferred() {
  let resolve;
  const promise = new Promise((complete) => { resolve = complete; });
  return { promise, resolve };
}

export async function prepareStandalone(page, app) {
  const options = waitResponse(page, "/api/ai/model/options", "GET");
  await page.goto(app + "/valuation", { waitUntil: "domcontentloaded" });
  assert.ok((await options).ok(), "Valuation model options must load");
  await page.locator("select").first().selectOption({ label: "Nhà ở" });
  const location = page.locator("select").nth(1);
  await location.locator("option").filter({ hasText: /^Cẩm Lệ$/ }).waitFor({ state: "attached" });
  await location.selectOption({ label: "Cẩm Lệ" });
  await page.getByPlaceholder("Ví dụ: 80").first().fill("100");
  return page.getByRole("button", { name: /Ước tính giá rao/ }).first();
}

export async function login(page, app, email, password, next = "/account") {
  assert.ok(email && password, "Disposable fixture credentials are required");
  await page.goto(app + "/login?next=" + encodeURIComponent(next), { waitUntil: "domcontentloaded" });
  await page.locator("#email-input").fill(email);
  await page.locator("#password-input").fill(password);
  const response = waitResponse(page, "/api/v1/auth/login");
  await page.locator("form").getByRole("button", { name: "Đăng nhập", exact: true }).click();
  assert.equal((await response).status(), 200, "Fixture login failed");
  await page.waitForURL((url) => url.pathname === next);
}

export async function preparePosting(page, app, email, password) {
  await login(page, app, email, password, "/post");
  await page.getByRole("heading", { name: "Tạo tin đăng mới" }).first().waitFor();
  for (const name of ["Đã hiểu", "Đóng bảng so sánh"]) {
    const button = page.getByRole("button", { name, exact: true }).first();
    if (await button.isVisible()) await button.click();
  }
  await page.locator("#post-transactionType").getByRole("button", { name: /Đăng bán/ }).click();
  await page.locator("#post-propertyType").selectOption({ label: "Nhà phố" });
  await page.locator("#post-title").fill("WP04 runtime fixture");
  await page.locator("#post-area").fill("80");
  await page.locator("#post-price").fill("5000000000");
  await page.locator(".valuation-optional summary").first().click();
  const location = page.getByTestId("valuation-location");
  await location.locator("option").filter({ hasText: /^Cẩm Lệ$/ }).waitFor({ state: "attached" });
  await location.selectOption({ label: "Cẩm Lệ" });
  return page.getByTestId("valuation-preview");
}

export async function prepareAdvisor(page, app, { navigate = true } = {}) {
  if (navigate) await page.goto(app + "/advisor/analysis", { waitUntil: "domcontentloaded" });
  const form = page.locator(".advisor-page form");
  await form.locator('input[aria-describedby="budget-hint"]').fill("7000000000");
  await form.getByLabel(/Biên ngân sách linh hoạt/).selectOption("0");
  await form.getByLabel(/Mục đích mua/).selectOption("LIVING");
  await form.getByLabel(/Loại bất động sản/).selectOption("HOUSE");
  await form.locator('input[list="advisor-districts"]').fill("Cẩm Lệ");
  await form.getByPlaceholder("Không giới hạn").fill("60");
  await form.getByLabel(/Số lượng đề xuất/).selectOption("5");
  await form.getByLabel(/Định giá tham chiếu/).check();
  await form.getByLabel(/Đối chiếu bất động sản tương đồng/).check();
  return page.locator("[data-advisor-submit]");
}
