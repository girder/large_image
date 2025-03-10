import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 2,
  reporter: [['html', { host: '0.0.0.0'}]],

  use: {
    actionTimeout: 30000,
    trace: 'on-first-retry',
    headless: !!process.env.HEADLESS,
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'npx vite dev --port 5173',
    port: 5173,
    reuseExistingServer: false
  },
});
