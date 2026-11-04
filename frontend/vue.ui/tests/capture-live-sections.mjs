import { createRequire } from 'module';
import path from 'path';

const require = createRequire(import.meta.url);
const { chromium } = require('../node_modules/@playwright/test');

const artifactDir = 'C:\\Users\\manchae\\.gemini\\antigravity\\brain\\e2842624-de61-4c71-98ec-9638abc2be75';
const realListingId = '7f4af73f-6d43-4ed3-b988-d461453e3f4d';

async function captureSections() {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5
  });

  const url = `http://127.0.0.1:5173/listing/${realListingId}`;
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // Capture Broker Card
  const brokerCard = page.locator('aside section').first();
  if (await brokerCard.count() > 0) {
    await brokerCard.screenshot({
      path: path.join(artifactDir, 'live_broker_card_navy.png')
    });
    console.log('Saved live_broker_card_navy.png');
  }

  // Capture AI Valuation section by heading
  const aiSection = page.locator('section:has-text("ĐỊNH GIÁ THAM CHIẾU AI")');
  if (await aiSection.count() > 0) {
    await aiSection.screenshot({
      path: path.join(artifactDir, 'live_ai_valuation_navy.png')
    });
    console.log('Saved live_ai_valuation_navy.png');
  }

  // Capture Regional Landmarks section
  const landmarksSection = page.locator('section:has-text("Liên kết vùng & Tiện ích lân cận")');
  if (await landmarksSection.count() > 0) {
    await landmarksSection.screenshot({
      path: path.join(artifactDir, 'live_landmarks_navy.png')
    });
    console.log('Saved live_landmarks_navy.png');
  }

  await browser.close();
  console.log('Done capturing live sections!');
}

captureSections().catch(err => {
  console.error('Failed:', err);
  process.exit(1);
});
