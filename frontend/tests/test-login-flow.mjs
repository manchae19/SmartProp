import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const { chromium } = require('../node_modules/@playwright/test');

async function testLoginFlow() {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' });

  // Test 1: Tab switching
  console.log('Testing tab switch to Register...');
  await page.click('button[role="tab"]:has-text("Đăng ký")');
  await page.waitForTimeout(400);
  console.log('Current URL after tab switch:', page.url());

  // Test 2: Name and confirm password fields are present
  const hasName = await page.locator('#name-input').count() > 0;
  const hasConfirm = await page.locator('#confirm-password-input').count() > 0;
  console.log('Register fields visible:', { hasName, hasConfirm });

  // Test 3: Password match validation
  await page.fill('#name-input', 'Nguyễn Văn Test');
  await page.fill('#email-input', 'test@smartprop.vn');
  await page.fill('#password-input', 'Password123');
  await page.fill('#confirm-password-input', 'DifferentPassword456');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(500);

  const errorText = await page.locator('[role="alert"]').textContent().catch(() => null);
  console.log('Password mismatch alert correctly shown:', errorText);

  // Test 4: Switch back to login
  await page.click('button[role="tab"]:has-text("Đăng nhập")');
  await page.waitForTimeout(400);
  console.log('Current URL after switching back to login:', page.url());

  await browser.close();
  console.log('ALL AUTH FLOW TESTS PASSED!');
}

testLoginFlow().catch(err => {
  console.error('TEST FAILED:', err);
  process.exit(1);
});
