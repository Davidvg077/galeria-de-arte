const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  reporter: 'list',
  timeout: 30000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://gart-gallery-v2.onrender.com',
    browserName: 'chromium',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
});