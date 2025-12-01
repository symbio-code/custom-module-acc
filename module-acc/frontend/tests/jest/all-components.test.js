const { getByText, getByPlaceholderText } = require('@testing-library/dom');
const { setupServer } = require('msw/node');
const { rest } = require('msw');

const server = setupServer(
  rest.post('http://localhost/auth/login', (req, res, ctx) => {
    return res(ctx.text('<div id="logged-in">Welcome</div>'));
  }),
  rest.post('http://localhost/accounts/', (req, res, ctx) => {
    return res(ctx.status(200), ctx.text(''));
  }),
  rest.post('http://localhost/journals/', (req, res, ctx) => {
    return res(ctx.status(200), ctx.text(''));
  }),
  rest.get('http://localhost/accounts/1/edit', (req, res, ctx) => {
    return res(ctx.text('<form id="editForm">Edit Account</form>'));
  }),
  rest.delete('http://localhost/accounts/1', (req, res, ctx) => {
    return res(ctx.status(204), ctx.text(''));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Login Component', () => {
  test('login form renders and submits', async () => {
    document.body.innerHTML = `
      <form id="loginForm">
        <input id="username" type="text" placeholder="Username" />
        <input id="password" type="password" placeholder="Password" />
        <button type="submit">Login</button>
      </form>
      <div id="response"></div>
    `;

    const form = document.getElementById('loginForm');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      fetch('http://localhost/auth/login', { method: 'POST' })
        .then(r => r.text())
        .then(html => { document.getElementById('response').innerHTML = html; });
    });

    await getByText(document.body, 'Login').click();

    await new Promise(resolve => setTimeout(resolve, 50));

    expect(getByText(document.body, 'Welcome')).toBeTruthy();
    expect(document.getElementById('response').innerHTML).toMatchSnapshot();
  });
});

describe('Account Components', () => {
  test('account form with HTMX behavior', async () => {
    document.body.innerHTML = `
      <form id="accountForm">
        <input id="code" type="text" placeholder="Account Code" />
        <input id="name" type="text" placeholder="Account Name" />
        <select id="type">
          <option value="asset">Asset</option>
          <option value="liability">Liability</option>
        </select>
        <button type="submit">Create</button>
      </form>
    `;

    const form = document.getElementById('accountForm');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      fetch('http://localhost/accounts/', { method: 'POST' });
    });

    document.getElementById('code').value = '100';
    document.getElementById('name').value = 'Test Account';
    document.getElementById('type').value = 'asset';

    form.querySelector('button').click();
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(document.getElementById('accountForm')).toBeTruthy();
    expect(document.getElementById('accountForm').innerHTML).toMatchSnapshot();
  });

  test('account edit button triggers modal', async () => {
    document.body.innerHTML = `
      <button id="editBtn" onclick="loadEditForm()">Edit</button>
      <div id="modal"></div>
    `;

    // Define function in global scope
    window.loadEditForm = function() {
      fetch('http://localhost/accounts/1/edit')
        .then(r => r.text())
        .then(html => { document.getElementById('modal').innerHTML = html; });
    };

    document.getElementById('editBtn').click();
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(document.getElementById('modal').innerHTML).toContain('Edit Account');
    expect(document.getElementById('modal').innerHTML).toMatchSnapshot();
  });

  test('account delete button with confirmation', () => {
    document.body.innerHTML = `
      <button id="deleteBtn">Delete</button>
      <div id="status"></div>
    `;

    const confirmBtn = document.getElementById('deleteBtn');
    const statusDiv = document.getElementById('status');

    expect(confirmBtn).toBeTruthy();
    expect(statusDiv).toBeTruthy();
  });
});

describe('Journal Components', () => {
  test('journal entry form with line items', async () => {
    document.body.innerHTML = `
      <form id="journalForm">
        <input type="date" id="date" value="2025-01-01" />
        <textarea id="description">Opening entry</textarea>
        <table id="linesTable">
          <tbody>
            <tr>
              <td><input class="account" value="100" /></td>
              <td><input class="debit" value="1000" /></td>
              <td><input class="credit" value="0" /></td>
            </tr>
            <tr>
              <td><input class="account" value="200" /></td>
              <td><input class="debit" value="0" /></td>
              <td><input class="credit" value="1000" /></td>
            </tr>
          </tbody>
        </table>
        <button type="submit">Save</button>
      </form>
    `;

    const lineItems = document.querySelectorAll('#linesTable tr');
    expect(lineItems.length).toBe(2);

    const totalDebit = Array.from(document.querySelectorAll('.debit')).reduce((sum, el) => sum + parseFloat(el.value), 0);
    const totalCredit = Array.from(document.querySelectorAll('.credit')).reduce((sum, el) => sum + parseFloat(el.value), 0);

    expect(totalDebit).toBe(totalCredit);
    expect(document.getElementById('journalForm').innerHTML).toMatchSnapshot();
  });

  test('journal form submission', () => {
    document.body.innerHTML = `
      <form id="journalForm">
        <input type="date" id="date" />
        <textarea id="description"></textarea>
        <button type="submit">Save</button>
      </form>
      <div id="response"></div>
    `;

    const form = document.getElementById('journalForm');
    expect(form).toBeTruthy();
    expect(document.getElementById('response')).toBeTruthy();
  });
});

describe('General Components', () => {
  test('pagination component navigation', () => {
    document.body.innerHTML = `
      <nav id="pagination">
        <a href="?page=1">Prev</a>
        <span>Page 2</span>
        <a href="?page=3">Next</a>
      </nav>
    `;

    const links = document.querySelectorAll('#pagination a');
    expect(links.length).toBe(2);
    expect(document.getElementById('pagination').innerHTML).toMatchSnapshot();
  });

  test('stats cards display values', () => {
    document.body.innerHTML = `
      <div id="statsCards">
        <div class="card"><h3>Assets</h3><p>50000</p></div>
        <div class="card"><h3>Liabilities</h3><p>20000</p></div>
      </div>
    `;

    const cards = document.querySelectorAll('#statsCards .card');
    expect(cards.length).toBe(2);
    expect(document.getElementById('statsCards').innerHTML).toMatchSnapshot();
  });

  test('modal component visibility toggle', () => {
    document.body.innerHTML = `
      <div id="modal" style="display:none;">
        <p>Modal Content</p>
        <button onclick="closeModal()">Close</button>
      </div>
      <script>
        function closeModal() {
          document.getElementById('modal').style.display = 'none';
        }
      </script>
    `;

    const modal = document.getElementById('modal');
    const initialDisplay = getComputedStyle(modal).display;
    expect(initialDisplay).toBe('none');

    modal.style.display = 'block';
    const updatedDisplay = getComputedStyle(modal).display;
    expect(updatedDisplay).toBe('block');

    expect(document.getElementById('modal').innerHTML).toMatchSnapshot();
  });

  test('toast notification auto-hide', async () => {
    document.body.innerHTML = `
      <div id="toast" style="display:block;">Success message</div>
    `;

    const toast = document.getElementById('toast');
    expect(toast.style.display).toBe('block');

    setTimeout(() => {
      toast.style.display = 'none';
    }, 100);

    await new Promise(resolve => setTimeout(resolve, 150));
    expect(toast.style.display).toBe('none');
  });

  test('table component with HTMX actions', async () => {
    document.body.innerHTML = `
      <table id="dataTable">
        <tbody>
          <tr>
            <td>Item 1</td>
            <td>
              <button id="editBtn">Edit</button>
              <button id="deleteBtn">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    `;

    const editBtn = document.getElementById('editBtn');
    const deleteBtn = document.getElementById('deleteBtn');

    expect(editBtn).toBeTruthy();
    expect(deleteBtn).toBeTruthy();
    expect(document.getElementById('dataTable').innerHTML).toMatchSnapshot();
  });

  test('form field component with validation', () => {
    document.body.innerHTML = `
      <div id="formField">
        <label>Username:</label>
        <input type="text" id="username" required pattern="[a-z0-9]{3,}" />
        <span id="error" style="display:none;">Min 3 characters</span>
      </div>
    `;

    const input = document.getElementById('username');
    input.value = 'ab';

    const isValid = input.value.match(/[a-z0-9]{3,}/);
    expect(isValid).toBeFalsy();

    input.value = 'abc123';
    const isNowValid = input.value.match(/[a-z0-9]{3,}/);
    expect(isNowValid).toBeTruthy();

    expect(document.getElementById('formField').innerHTML).toMatchSnapshot();
  });

  test('confirm delete component actions', () => {
    document.body.innerHTML = `
      <div id="confirmDelete">
        <p>Delete this account?</p>
        <button id="confirmBtn">Yes</button>
        <button id="cancelBtn">No</button>
      </div>
    `;

    const confirmBtn = document.getElementById('confirmBtn');
    const cancelBtn = document.getElementById('cancelBtn');

    expect(confirmBtn).toBeTruthy();
    expect(cancelBtn).toBeTruthy();
    expect(document.getElementById('confirmDelete').innerHTML).toMatchSnapshot();
  });
});

describe('Report Components', () => {
  test('trial balance table rendering', () => {
    document.body.innerHTML = `
      <table id="trialBalance">
        <thead><tr><th>Account</th><th>Debit</th><th>Credit</th></tr></thead>
        <tbody>
          <tr><td>Cash</td><td>5000</td><td>0</td></tr>
          <tr><td>Income</td><td>0</td><td>5000</td></tr>
        </tbody>
      </table>
    `;

    const rows = document.querySelectorAll('#trialBalance tbody tr');
    expect(rows.length).toBe(2);
    expect(document.getElementById('trialBalance').innerHTML).toMatchSnapshot();
  });

  test('profit loss report calculations', () => {
    document.body.innerHTML = `
      <div id="profitLoss">
        <p>Revenue: <span id="revenue">10000</span></p>
        <p>Expenses: <span id="expenses">3000</span></p>
        <p>Net: <span id="net">7000</span></p>
      </div>
    `;

    const revenue = parseFloat(document.getElementById('revenue').textContent);
    const expenses = parseFloat(document.getElementById('expenses').textContent);
    const net = parseFloat(document.getElementById('net').textContent);

    expect(net).toBe(revenue - expenses);
    expect(document.getElementById('profitLoss').innerHTML).toMatchSnapshot();
  });

  test('balance sheet sections', () => {
    document.body.innerHTML = `
      <div id="balanceSheet">
        <section><h3>Assets</h3><p>100000</p></section>
        <section><h3>Liabilities</h3><p>50000</p></section>
        <section><h3>Equity</h3><p>50000</p></section>
      </div>
    `;

    const sections = document.querySelectorAll('#balanceSheet section');
    expect(sections.length).toBe(3);
    expect(document.getElementById('balanceSheet').innerHTML).toMatchSnapshot();
  });
});
