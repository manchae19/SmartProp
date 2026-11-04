import { createRequire } from 'module';
import path from 'path';

const require = createRequire(import.meta.url);
const { chromium } = require('../node_modules/@playwright/test');

const artifactDir = 'C:\\Users\\manchae\\.gemini\\antigravity\\brain\\e2842624-de61-4c71-98ec-9638abc2be75';
const realListingId = '7f4af73f-6d43-4ed3-b988-d461453e3f4d';

async function testLive() {
  console.log('Connecting to live frontend on http://127.0.0.1:5173 ...');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    deviceScaleFactor: 1.5
  });
  const page = await context.newPage();

  const consoleLogs = [];
  page.on('console', msg => consoleLogs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => consoleLogs.push(`[PAGE_ERROR] ${err.message}`));

  const url = `http://127.0.0.1:5173/listing/${realListingId}`;
  console.log(`Navigating to ${url}...`);

  const response = await page.goto(url, { waitUntil: 'networkidle' });
  console.log(`HTTP Status: ${response.status()}`);

  await page.waitForTimeout(1500);

  // Check if title is rendered
  const h1Text = await page.locator('h1').textContent().catch(() => null);
  console.log('Listing title rendered:', h1Text);

  // Capture live full page screenshot
  const screenshotPath = path.join(artifactDir, 'live_test_listing_detail.png');
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`Captured live screenshot at ${screenshotPath}`);

  // Capture top hero screenshot
  const topHeroPath = path.join(artifactDir, 'live_test_top_hero.png');
  await page.screenshot({
    path: topHeroPath,
    clip: { x: 0, y: 0, width: 1440, height: 900 }
  });
  console.log(`Captured top hero screenshot at ${topHeroPath}`);

  console.log('Console logs during run:');
  consoleLogs.slice(-10).forEach(l => console.log('  ', l));

  await browser.close();
  console.log('LIVE RUN TEST FINISHED SUCCESSFULLY!');
}

testLive().catch(err => {
  console.error('LIVE RUN TEST FAILED:', err);
  process.exit(1);
});
