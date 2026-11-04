import { createRequire } from 'module';
import path from 'path';

const require = createRequire(import.meta.url);
const { chromium } = require('../node_modules/@playwright/test');

const artifactDir = 'C:\\Users\\manchae\\.gemini\\antigravity\\brain\\e2842624-de61-4c71-98ec-9638abc2be75';

async function captureAuth() {
  console.log('Capturing Login & Register pages...');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });

  // Desktop 1440x900
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5
  });
  const page = await context.newPage();

  // 1. Login View
  console.log('Navigating to /login ...');
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await page.screenshot({
    path: path.join(artifactDir, 'auth_v2_login_desktop.png')
  });
  console.log('Saved auth_v2_login_desktop.png');

  // Focus on login card only
  const card = page.locator('section[aria-labelledby="auth-heading"]');
  if (await card.count() > 0) {
    await card.screenshot({
      path: path.join(artifactDir, 'auth_v2_login_card.png')
    });
    console.log('Saved auth_v2_login_card.png');
  }

  // 2. Register View
  console.log('Navigating to /register ...');
  await page.goto('http://127.0.0.1:5173/register', { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await page.screenshot({
    path: path.join(artifactDir, 'auth_v2_register_desktop.png')
  });
  console.log('Saved auth_v2_register_desktop.png');

  if (await card.count() > 0) {
    await card.screenshot({
      path: path.join(artifactDir, 'auth_v2_register_card.png')
    });
    console.log('Saved auth_v2_register_card.png');
  }

  // 3. Mobile View 390x844 (iPhone 14)
  const mobileContext = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2
  });
  const mobilePage = await mobileContext.newPage();
  await mobilePage.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' });
  await mobilePage.waitForTimeout(600);
  await mobilePage.screenshot({
    path: path.join(artifactDir, 'auth_v2_login_mobile.png')
  });
  console.log('Saved auth_v2_login_mobile.png');

  await browser.close();
  console.log('Auth screenshot capture finished successfully!');
}

captureAuth().catch(err => {
  console.error('Error capturing auth screenshots:', err);
  process.exit(1);
});
