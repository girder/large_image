import { cpus, totalmem } from 'os';

import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for the large_image Girder plugins.  This follows
 * the layout used by Girder's own web tests (girder/web/playwright.config.ts).
 * Each spec starts its own Girder server (see tests/server.ts), so the
 * server must be installed with the large_image, large_image_annotation, and
 * (optionally) dicomweb plugins, and a MongoDB instance must be reachable.
 *
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests',
  /* Test (and hook) timeout.  This is intentionally larger than the expect
   * timeout so that a slow assertion failure or a slow server startup under
   * load does not consume the entire budget. */
  timeout: 120000,
  /* Default timeout for expect() assertions and web-first assertions.  Tests
   * should rely on this value rather than passing explicit timeouts, so that
   * slower machines and CI runners do not cause flaky failures. */
  expect: {
    timeout: 20000,
  },
  /* Run tests in files in parallel */
  fullyParallel: false,
  /* Fail the build on CI if test.only is in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : (isFinite(Number(process.env.PLAYWRIGHT_RETRIES)) && parseInt(process.env.PLAYWRIGHT_RETRIES ?? '') || 0),
  workers: (() => {
    if (process.env.PLAYWRIGHT_WORKERS) {
      return parseInt(process.env.PLAYWRIGHT_WORKERS);
    }
    /* Opt out of parallel tests on CI. */
    if (process.env.CI) {
      return 1;
    }
    const physicalCores = cpus().length;
    // Limit workers based on memory; each worker runs a Girder server.
    const memoryLimiter = Math.floor(totalmem() / (4 * 1024 ** 3));
    return Math.max(1, Math.min(physicalCores, memoryLimiter));
  })(),
  /* Reporter to use.  See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['line'],
    ['html', {
      open: 'never'
    }]
  ],
  /* Collect javascript coverage of the plugin bundles; see tests/coverage.ts */
  globalSetup: './tests/playwright-setup.ts',
  globalTeardown: './tests/playwright-teardown.ts',
  /* Shared settings for all the projects below.  See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Maximum time each action such as `click()` can take. */
    actionTimeout: 30000,
    /* Collect trace when retrying the failed test.  See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    headless: process.env.HEADLESS?.toLowerCase() !== 'false',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
