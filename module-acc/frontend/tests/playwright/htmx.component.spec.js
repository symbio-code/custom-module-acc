import { test, expect } from '@playwright/test';

test('htmx component injects fragment and snapshot DOM', async ({ page }) => {
  // Set a minimal page that loads htmx from CDN
  await page.setContent(`
    <div id="root">
      <button id="load" hx-get="/fragment" hx-target="#root">Load</button>
    </div>
    <script src="https://unpkg.com/htmx.org@1.10.0"></script>
  `);

  // Intercept the HTMX request and return an HTML fragment
  await page.route('**/fragment', route => {
    route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<div id="fragment">Fragment content <span class="time">42</span></div>'
    });
  });

  // Trigger HTMX request
  await page.click('#load');

  // Wait for the fragment to be injected
  await page.waitForSelector('#fragment');

  // Take a DOM snapshot (serializable HTML) for regression testing
  const inner = await page.locator('#root').innerHTML();
  expect(inner).toMatchSnapshot('htmx-root.html');

  // Also capture a visual snapshot (optional)
  await expect(page.locator('#root')).toHaveScreenshot('htmx-root.png');
});
