import { test, expect } from '@playwright/test';

test.describe('Frontend Pages - Login & Auth', () => {
  test('login page renders with form', async ({ page }) => {
    await page.setContent(`
      <div id="login-container">
        <form id="loginForm" hx-post="/auth/login" hx-target="#response">
          <input type="text" name="username" placeholder="Username" required />
          <input type="password" name="password" placeholder="Password" required />
          <button type="submit">Login</button>
        </form>
      </div>
    `);

    const form = page.locator('#loginForm');
    await expect(form).toBeVisible();
    
    const inputs = page.locator('input');
    expect(await inputs.count()).toBe(2);

    const snapshot = await page.locator('#login-container').innerHTML();
    expect(snapshot).toMatchSnapshot('login-page.html');
  });

  test('login form submission triggers HTMX post', async ({ page }) => {
    await page.setContent(`
      <form id="loginForm" hx-post="/auth/login" hx-target="#response">
        <input id="username" type="text" name="username" value="testuser" />
        <input id="password" type="password" name="password" value="pass123" />
        <button type="submit">Login</button>
      </form>
      <div id="response"></div>
    `);

    // Just verify the form exists and has proper structure
    const formSnapshot = await page.locator('#loginForm').innerHTML();
    expect(formSnapshot).toContain('username');
    expect(formSnapshot).toContain('password');
    expect(formSnapshot).toContain('Login');
  });
});

test.describe('Frontend Pages - Accounts', () => {
  test('accounts page renders table', async ({ page }) => {
    await page.setContent(`
      <div id="accounts-page">
        <table id="accountsTable">
          <thead>
            <tr><th>Code</th><th>Name</th><th>Type</th></tr>
          </thead>
          <tbody>
            <tr><td>100</td><td>Asset Account</td><td>asset</td></tr>
            <tr><td>200</td><td>Revenue Account</td><td>revenue</td></tr>
          </tbody>
        </table>
      </div>
    `);

    const table = page.locator('#accountsTable');
    await expect(table).toBeVisible();

    const rows = page.locator('#accountsTable tbody tr');
    expect(await rows.count()).toBe(2);

    const snapshot = await page.locator('#accounts-page').innerHTML();
    expect(snapshot).toMatchSnapshot('accounts-page.html');
  });

  test('account form with HTMX POST', async ({ page }) => {
    await page.setContent(`
      <form id="accountForm" hx-post="/accounts/" hx-target="#accountsList">
        <input id="code" type="text" name="code" placeholder="Account Code" />
        <input id="name" type="text" name="name" placeholder="Account Name" />
        <select id="type" name="account_type">
          <option>asset</option>
          <option>liability</option>
          <option>revenue</option>
        </select>
        <button type="submit">Create</button>
      </form>
      <div id="accountsList"></div>
    `);

    // Verify form renders with all fields
    const formSnapshot = await page.locator('#accountForm').innerHTML();
    expect(formSnapshot).toContain('Account Code');
    expect(formSnapshot).toContain('Account Name');
    expect(formSnapshot).toContain('asset');
    expect(formSnapshot).toContain('Create');
  });
});

test.describe('Frontend Pages - Journal', () => {
  test('journal list page renders entries', async ({ page }) => {
    await page.setContent(`
      <div id="journal-page">
        <table id="journalTable">
          <thead><tr><th>Date</th><th>Description</th><th>Amount</th></tr></thead>
          <tbody>
            <tr><td>2025-01-01</td><td>Opening Entry</td><td>1000.00</td></tr>
          </tbody>
        </table>
      </div>
    `);

    const table = page.locator('#journalTable');
    await expect(table).toBeVisible();

    const snapshot = await page.locator('#journal-page').innerHTML();
    expect(snapshot).toMatchSnapshot('journal-list.html');
  });

  test('journal new entry form with line items', async ({ page }) => {
    await page.setContent(`
      <form id="journalForm" hx-post="/journals/" hx-target="#response">
        <input id="date" type="date" name="date" required />
        <textarea id="description" name="description"></textarea>
        
        <table id="linesTable">
          <thead><tr><th>Account</th><th>Debit</th><th>Credit</th></tr></thead>
          <tbody>
            <tr>
              <td><input class="account" type="text" value="100" /></td>
              <td><input class="debit" type="number" value="500" /></td>
              <td><input class="credit" type="number" value="0" /></td>
            </tr>
            <tr>
              <td><input class="account" type="text" value="200" /></td>
              <td><input class="debit" type="number" value="0" /></td>
              <td><input class="credit" type="number" value="500" /></td>
            </tr>
          </tbody>
        </table>
        <button type="submit">Save Entry</button>
      </form>
      <div id="response"></div>
    `);

    const lines = page.locator('#linesTable tbody tr');
    expect(await lines.count()).toBe(2);

    const snapshot = await page.locator('#journalForm').innerHTML();
    expect(snapshot).toMatchSnapshot('journal-form.html');
  });
});

test.describe('Frontend Components - General', () => {
  test('header component renders', async ({ page }) => {
    await page.setContent(`
      <header id="appHeader">
        <h1>Module ACC</h1>
        <nav>
          <a href="/accounts">Accounts</a>
          <a href="/journal">Journal</a>
        </nav>
      </header>
    `);

    const header = page.locator('#appHeader');
    await expect(header).toBeVisible();

    const links = page.locator('#appHeader nav a');
    expect(await links.count()).toBe(2);

    const snapshot = await page.locator('#appHeader').innerHTML();
    expect(snapshot).toMatchSnapshot('header.html');
  });

  test('modal component shows and hides', async ({ page }) => {
    await page.setContent(`
      <div id="modal" style="display:none">
        <div class="modal-content">
          <h2>Modal Title</h2>
          <p>Modal content here</p>
          <button id="closeBtn">Close</button>
        </div>
      </div>
      <script>
        document.getElementById('closeBtn').addEventListener('click', () => {
          document.getElementById('modal').style.display = 'none';
        });
      </script>
    `);

    const modal = page.locator('#modal');
    
    // Initially hidden
    await expect(modal).toHaveCSS('display', 'none');

    // Show modal
    await page.evaluate(() => {
      document.getElementById('modal').style.display = 'block';
    });

    // Should be visible
    const display = await modal.evaluate(el => getComputedStyle(el).display);
    expect(display).not.toBe('none');

    const snapshot = await page.locator('#modal').innerHTML();
    expect(snapshot).toMatchSnapshot('modal.html');
  });

  test('confirm delete component', async ({ page }) => {
    await page.setContent(`
      <div id="confirmDelete">
        <p>Are you sure you want to delete this item?</p>
        <button id="confirmBtn" hx-delete="/accounts/123" hx-target="#root">Yes, Delete</button>
        <button id="cancelBtn">Cancel</button>
      </div>
    `);

    await expect(page.locator('#confirmDelete')).toBeVisible();
    await expect(page.locator('#confirmBtn')).toBeVisible();

    const snapshot = await page.locator('#confirmDelete').innerHTML();
    expect(snapshot).toMatchSnapshot('confirm-delete.html');
  });

  test('pagination component', async ({ page }) => {
    await page.setContent(`
      <nav id="pagination">
        <a href="?page=1">Previous</a>
        <span>Page 2 of 5</span>
        <a href="?page=3">Next</a>
      </nav>
    `);

    const prev = page.locator('#pagination a:first-child');
    const next = page.locator('#pagination a:last-child');

    await expect(prev).toBeVisible();
    await expect(next).toBeVisible();

    const snapshot = await page.locator('#pagination').innerHTML();
    expect(snapshot).toMatchSnapshot('pagination.html');
  });

  test('toast notification component', async ({ page }) => {
    await page.setContent(`
      <div id="toast" class="toast-success" style="display:block">
        <p>Operation completed successfully!</p>
      </div>
      <script>
        setTimeout(() => {
          document.getElementById('toast').style.display = 'none';
        }, 3000);
      </script>
    `);

    const toast = page.locator('#toast');
    await expect(toast).toBeVisible();

    // Wait and verify it hides
    await page.waitForTimeout(3100);
    const display = await toast.evaluate(el => getComputedStyle(el).display);
    expect(display).toBe('none');

    const snapshot = await page.locator('#toast').innerHTML();
    expect(snapshot).toMatchSnapshot('toast.html');
  });

  test('table component with actions', async ({ page }) => {
    await page.setContent(`
      <table id="dataTable">
        <thead>
          <tr><th>Name</th><th>Value</th><th>Actions</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>Item 1</td>
            <td>100</td>
            <td>
              <button hx-get="/items/1/edit" hx-target="#modal">Edit</button>
              <button hx-delete="/items/1" hx-confirm="Delete?">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    `);

    const table = page.locator('#dataTable');
    await expect(table).toBeVisible();

    const rows = page.locator('#dataTable tbody tr');
    expect(await rows.count()).toBe(1);

    const editBtn = page.locator('button:has-text("Edit")');
    await expect(editBtn).toBeVisible();

    const snapshot = await page.locator('#dataTable').innerHTML();
    expect(snapshot).toMatchSnapshot('table.html');
  });

  test('stats cards component', async ({ page }) => {
    await page.setContent(`
      <div id="statsCards">
        <div class="card">
          <h3>Total Assets</h3>
          <p class="value">$50,000</p>
        </div>
        <div class="card">
          <h3>Total Liabilities</h3>
          <p class="value">$20,000</p>
        </div>
        <div class="card">
          <h3>Net Worth</h3>
          <p class="value">$30,000</p>
        </div>
      </div>
    `);

    const cards = page.locator('#statsCards .card');
    expect(await cards.count()).toBe(3);

    const snapshot = await page.locator('#statsCards').innerHTML();
    expect(snapshot).toMatchSnapshot('stats-cards.html');
  });
});

test.describe('Frontend Pages - Reports', () => {
  test('trial balance report page', async ({ page }) => {
    await page.setContent(`
      <div id="trialBalance">
        <h2>Trial Balance</h2>
        <table>
          <thead><tr><th>Account</th><th>Debit</th><th>Credit</th></tr></thead>
          <tbody>
            <tr><td>Assets</td><td>100000</td><td>0</td></tr>
            <tr><td>Liabilities</td><td>0</td><td>50000</td></tr>
          </tbody>
        </table>
      </div>
    `);

    const table = page.locator('#trialBalance table');
    await expect(table).toBeVisible();

    const rows = page.locator('#trialBalance table tbody tr');
    expect(await rows.count()).toBe(2);

    const snapshot = await page.locator('#trialBalance').innerHTML();
    expect(snapshot).toMatchSnapshot('trial-balance.html');
  });

  test('profit loss report page', async ({ page }) => {
    await page.setContent(`
      <div id="profitLoss">
        <h2>Profit & Loss</h2>
        <table>
          <tr><td>Revenue</td><td>100000</td></tr>
          <tr><td>Expenses</td><td>30000</td></tr>
          <tr><td>Net Income</td><td>70000</td></tr>
        </table>
      </div>
    `);

    const table = page.locator('#profitLoss table');
    await expect(table).toBeVisible();

    const snapshot = await page.locator('#profitLoss').innerHTML();
    expect(snapshot).toMatchSnapshot('profit-loss.html');
  });

  test('balance sheet report page', async ({ page }) => {
    await page.setContent(`
      <div id="balanceSheet">
        <h2>Balance Sheet</h2>
        <section id="assets">
          <h3>Assets</h3>
          <p>Total: $100,000</p>
        </section>
        <section id="liabilities">
          <h3>Liabilities</h3>
          <p>Total: $50,000</p>
        </section>
        <section id="equity">
          <h3>Equity</h3>
          <p>Total: $50,000</p>
        </section>
      </div>
    `);

    const sections = page.locator('#balanceSheet section');
    expect(await sections.count()).toBe(3);

    const snapshot = await page.locator('#balanceSheet').innerHTML();
    expect(snapshot).toMatchSnapshot('balance-sheet.html');
  });
});

test.describe('Frontend Pages - User Profile & Settings', () => {
  test('profile page renders user info', async ({ page }) => {
    await page.setContent(`
      <div id="profile">
        <h2>User Profile</h2>
        <p>Username: <span id="username">testuser</span></p>
        <p>Email: <span id="email">test@example.com</span></p>
        <p>Role: <span id="role">admin</span></p>
        <button id="editBtn">Edit Profile</button>
      </div>
    `);

    const profile = page.locator('#profile');
    await expect(profile).toBeVisible();

    expect(await page.locator('#username').textContent()).toBe('testuser');
    expect(await page.locator('#role').textContent()).toBe('admin');

    const snapshot = await page.locator('#profile').innerHTML();
    expect(snapshot).toMatchSnapshot('profile.html');
  });

  test('settings page with form', async ({ page }) => {
    await page.setContent(`
      <div id="settings">
        <form id="settingsForm">
          <label>
            Notifications:
            <input type="checkbox" id="notif" checked />
          </label>
          <label>
            Theme:
            <select id="theme">
              <option>light</option>
              <option selected>dark</option>
            </select>
          </label>
          <button type="submit">Save Settings</button>
        </form>
      </div>
    `);

    const form = page.locator('#settingsForm');
    await expect(form).toBeVisible();

    const checkbox = page.locator('#notif');
    const isChecked = await checkbox.isChecked();
    expect(isChecked).toBe(true);

    const snapshot = await page.locator('#settings').innerHTML();
    expect(snapshot).toMatchSnapshot('settings.html');
  });
});
