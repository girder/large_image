import { defineConfig, devices } from '@playwright/test';

const isHeadless = () => {
  if (process.env.HEADLESS?.toLowerCase() === 'false') {
    return false;
  }
  const envVars = [ 'CI', 'CONTINUOUS_INTEGRATION', 'GITLAB_CI', 'GITHUB_ACTIONS', 'HEADLESS', 'DOCKER', 'KUBERNETES', 'LXC', 'LXD', 'SYSTEMD_IS_SYSTEMD'];
  const noDisplay = !process.env.DISPLAY;
  return envVars.some(env => process.env[env]) || noDisplay;
};

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
    headless: isHeadless(),
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
