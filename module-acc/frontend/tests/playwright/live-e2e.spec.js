import { test, expect } from '@playwright/test';

const base = 'http://127.0.0.1:8000';

test.describe('Live E2E (login -> accounts -> journal -> reports)', () => {
  test('full workflow with real backend', async ({ page, request }) => {
    // Login
    await page.goto(`${base}/login`);
    await page.fill('#username', 'admin');
    await page.fill('input[name="password"]', 'admin_pass');
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle' }),
      page.click('#loginButton')
    ]);

    await expect(page).toHaveURL(/dashboard|\/dashboard/);
    await expect(page.locator('text=Dashboard')).toBeVisible();

    // Accounts page
    await page.goto(`${base}/accounts`);
    await expect(page.locator('text=Chart of Accounts')).toBeVisible();

    // Journal new entry
    await page.goto(`${base}/journal/new`);
    await expect(page.locator('#journal-form')).toBeVisible();

    // Reports: check export link and fetch PDF via API request
    await page.goto(`${base}/reports/trial-balance`);
    const exportEl = page.locator('#export-tb');
    await expect(exportEl).toBeVisible();
    const href = await exportEl.getAttribute('href');
    const pdfUrl = href.startsWith('http') ? href : `${base}${href.startsWith('/')? href : '/'+href}`;

    // Use Playwright request to fetch PDF (server must return application/pdf)
    const resp = await request.get(pdfUrl);
    expect(resp.ok()).toBeTruthy();
    const ct = resp.headers()['content-type'] || '';
    expect(ct).toContain('pdf');
  });
});
