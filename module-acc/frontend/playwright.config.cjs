module.exports = {
  testDir: './tests/playwright',
  timeout: 30000,
  use: {
    headless: true,
    viewport: { width: 1280, height: 720 }
  }
};
