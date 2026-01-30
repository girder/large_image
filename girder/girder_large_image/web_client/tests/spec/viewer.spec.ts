import { test } from '@playwright/test';

import { createUser, uploadSampleFile } from '../util';
import { setupServer } from '../server';

test.describe('Test image viewer', () => {
  setupServer();

  test('Upload SVS large image and ensure thumbnail renders', async ({ page }) => {
    await createUser(page);
    await page.locator('#g-app-header-container').getByText('firstlast').click();
    await page.getByRole('link', { name: ' My folders' }).click();
    await page.getByRole('link', { name: ' Private ' }).click();
    await uploadSampleFile(page, 'sample_svs_image.TCGA-DU-6399-01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs');

    const locator = page.locator('.large_image_thumbnail>img.loaded');
    await locator.waitFor({ state: 'visible' });
  });
});
