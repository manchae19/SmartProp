import { createRequire } from 'module';
import path from 'path';

const require = createRequire(import.meta.url);
const { chromium } = require('../node_modules/@playwright/test');

const artifactDir = 'C:\\Users\\manchae\\.gemini\\antigravity\\brain\\e2842624-de61-4c71-98ec-9638abc2be75';

const mockListing = {
  id: 'danang-hc-001',
  title: 'Nhà phố 3 tầng mặt tiền đường Bạch Đằng, view sông Hàn tuyệt đẹp',
  description: `Chính chủ cần bán gấp căn nhà phố 3 tầng tại đường Bạch Đằng, phường Thạch Thang, quận Hải Châu, Đà Nẵng.
Vị trí đắc địa ngay trung tâm thành phố, trục đường thương mại ven sông Hàn sầm uất bậc nhất Đà Nẵng. Thích hợp vừa ở vừa làm văn phòng công ty, spa cao cấp hoặc kinh doanh dịch vụ du lịch.

- Diện tích đất: 120 m² (Ngang 6m x Dài 20m), vuông vức phong thủy tốt.
- Kết cấu: 3 tầng bê tông cốt thép kiên cố, 4 phòng ngủ khép kín, 4 toilet, phòng khách sang trọng, bếp hiện đại, sân thượng ngắm trọn pháo hoa quốc tế DIFF.
- Pháp lý: Sổ hồng chính chủ hoàn công đầy đủ, công chứng sang tên ngay trong ngày.
- Giá bán thiện chí: 18.5 tỷ (có thương lượng bớt lộc cho khách mua nhanh).`,
  price: 18500000000,
  priceExact: 18500000000,
  areaSqm: 120,
  areaSqmExact: 120,
  propertyType: 'HOUSE',
  transactionType: 'SALE',
  district: 'Quận Hải Châu',
  ward: 'Phường Thạch Thang',
  city: 'Đà Nẵng',
  address: 'Bạch Đằng, Phường Thạch Thang',
  latitude: 16.0682,
  longitude: 108.2241,
  direction: 'Đông Bắc',
  bedrooms: 4,
  bathrooms: 4,
  contactName: 'Phan Thanh Bình',
  contactPhone: '0905123456',
  contactEmail: 'thanhbinh19104@gmail.com',
  declaredAmenities: [
    'Sổ hồng hoàn công',
    'Mặt tiền kinh doanh',
    'View trực diện sông Hàn',
    'Gần cầu Rồng',
    'Ô tô đỗ cửa',
    'Khu an ninh cao cấp',
    'Thang máy gia đình',
    'Nội thất cao cấp'
  ],
  images: [
    { url: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80', cover: true },
    { url: 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=80' },
    { url: 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&q=80' },
    { url: 'https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?auto=format&fit=crop&w=800&q=80' },
    { url: 'https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=800&q=80' }
  ],
  status: 'PUBLISHED',
  createdAt: '2026-11-01T08:30:00Z',
  publishedAt: '2026-11-01T08:30:00Z'
};

async function run() {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    deviceScaleFactor: 1.5
  });
  const page = await context.newPage();

  // Route API mock for /api/v1/**
  await page.route('**/api/v1/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/auth/csrf')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ headerName: 'X-CSRF-TOKEN', token: 'mock-csrf' })
      });
    }
    if (url.includes('/auth/refresh') || url.includes('/users/me')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          accessToken: 'mock-access-token-123',
          user: { id: 'usr_test', email: 'test@smartprop.vn', role: 'USER' }
        })
      });
    }
    if (url.includes('/contact')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          available: true,
          contactName: mockListing.contactName,
          contactPhone: mockListing.contactPhone,
          contactEmail: mockListing.contactEmail
        })
      });
    }
    if (url.includes('/points-of-interest')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    }
    if (url.includes('/properties/')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockListing)
      });
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({})
    });
  });

  console.log('Navigating to listing detail page...');
  await page.goto('http://127.0.0.1:5173/listing/danang-hc-001', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // Set authenticated session in app
  await page.evaluate(() => {
    try {
      const { session } = window;
      // In case session isn't exposed, mock token
    } catch(e) {}
  });

  // Capture Top section (Hero, Nav, Header, Specs)
  await page.screenshot({
    path: path.join(artifactDir, 'detail_v2_top_hero.png'),
    clip: { x: 0, y: 0, width: 1440, height: 900 }
  });
  console.log('Saved detail_v2_top_hero.png');

  // Capture Middle section (Guarantee, Description, Amenities, Landmarks)
  await page.evaluate(() => window.scrollTo(0, 750));
  await page.waitForTimeout(500);
  await page.screenshot({
    path: path.join(artifactDir, 'detail_v2_middle_content.png'),
    clip: { x: 0, y: 0, width: 1440, height: 950 }
  });
  console.log('Saved detail_v2_middle_content.png');

  // Capture Bottom section (Map, AI Valuation)
  await page.evaluate(() => window.scrollTo(0, 1500));
  await page.waitForTimeout(500);
  await page.screenshot({
    path: path.join(artifactDir, 'detail_v2_bottom_valuation.png'),
    clip: { x: 0, y: 0, width: 1440, height: 950 }
  });
  console.log('Saved detail_v2_bottom_valuation.png');

  // Scroll back to top, capture Contact Card before click
  await page.evaluate(() => window.scrollTo(0, 200));
  await page.waitForTimeout(500);

  const brokerCard = page.locator('aside section').first();
  if (await brokerCard.count() > 0) {
    await brokerCard.screenshot({
      path: path.join(artifactDir, 'detail_v2_broker_before_reveal.png')
    });
    console.log('Saved detail_v2_broker_before_reveal.png');

    // Make sure session has a token for reveal button
    await page.evaluate(async () => {
      // Find vue instance or set session
      const apiModule = await import('/src/services/api.js');
      if (apiModule?.session) {
        apiModule.session.token = 'mock-test-token';
        apiModule.session.user = { id: 'usr_test', email: 'test@smartprop.vn' };
        apiModule.session.status = 'AUTHENTICATED';
      }
    });

    const revealBtn = page.locator('[data-testid="contact-panel"] button').first();
    if (await revealBtn.count() > 0) {
      await revealBtn.click();
      await page.waitForTimeout(1000);

      await brokerCard.screenshot({
        path: path.join(artifactDir, 'detail_v2_broker_after_reveal.png')
      });
      console.log('Saved detail_v2_broker_after_reveal.png');
    }
  }

  // Also take full page screenshot for complete review
  await page.screenshot({
    path: path.join(artifactDir, 'detail_v2_full_page.png'),
    fullPage: true
  });
  console.log('Saved detail_v2_full_page.png');

  await browser.close();
  console.log('All screenshots captured successfully!');
}

run().catch(err => {
  console.error('Error running screenshot script:', err);
  process.exit(1);
});
