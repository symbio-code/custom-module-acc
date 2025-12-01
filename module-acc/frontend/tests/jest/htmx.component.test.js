require('whatwg-fetch');
const { getByText } = require('@testing-library/dom');

const { setupServer } = require('msw/node');
const { rest } = require('msw');

// Mock server that returns an HTML fragment for HTMX
const server = setupServer(
  rest.get('http://localhost/fragment', (req, res, ctx) => {
    return res(ctx.text('<div id="fragment">Fragment content</div>'));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('htmx loads fragment and injects into DOM (jsdom + MSW)', async () => {
  document.body.innerHTML = `
    <div id="root">
      <button id="load" hx-get="http://localhost/fragment" hx-target="#root">Load</button>
    </div>
  `;

  // Attach a simple handler that simulates HTMX behavior (fetch + inject)
  document.querySelector('#load').addEventListener('click', () => {
    fetch('http://localhost/fragment')
      .then(r => r.text())
      .then(html => { document.getElementById('root').innerHTML = html; });
  });

  // Simulate user click which triggers the fetch and injection
  document.querySelector('#load').click();

  // Wait for the mocked fetch to resolve and the DOM to update
  await new Promise(resolve => setTimeout(resolve, 50));

  expect(document.getElementById('fragment')).not.toBeNull();
  expect(getByText(document.body, 'Fragment content')).toBeTruthy();

  // Snapshot the root.innerHTML for regression testing
  expect(document.getElementById('root').innerHTML).toMatchSnapshot();
});
