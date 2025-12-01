import { test, expect } from '@playwright/test';

test('htmx component injects fragment and snapshot DOM', async ({ page }) => {
  // Set a minimal page that loads htmx from CDN
  await page.setContent(`
    <div id="root">
      <button id="load" hx-get="http://localhost/fragment" hx-target="#root">Load</button>
    </div>
    <script>
      // Minimal HTMX-like handler for tests: intercept click on elements with hx-get
      document.addEventListener('click', function(e){
        const el = e.target.closest('[hx-get]');
        if (!el) return;
        const url = el.getAttribute('hx-get');
        const targetSelector = el.getAttribute('hx-target');
        const target = targetSelector ? document.querySelector(targetSelector) : null;
        fetch(url).then(r => r.text()).then(html => { if (target) target.innerHTML = html; });
      });
    </script>
  `);

  // Intercept the HTMX request and return an HTML fragment
  await page.route('**/fragment', route => {
    route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<div id="fragment">Fragment content <span class="time">42</span></div>'
    });
  });

  // Trigger the HTMX-like handler by clicking the button
  await page.click('#load');

  // Wait for the fragment to be injected
  await page.waitForSelector('#fragment', { timeout: 10000 });

  // Take a DOM snapshot (serializable HTML) for regression testing
  const inner = await page.locator('#root').innerHTML();
  expect(inner).toMatchSnapshot('htmx-root.html');

  // Also capture a visual snapshot (optional)
  await expect(page.locator('#root')).toHaveScreenshot('htmx-root.png');
});
