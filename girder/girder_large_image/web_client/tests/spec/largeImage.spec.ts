import { expect, test } from '@playwright/test';

import { asyncRestRequest, createUser, waitForDialog, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from girder/test_girder/web_client_specs/largeImageSpec.js.
 *
 * This exercises the large_image plugin configuration page.
 */
test.describe('Test the large image plugin', () => {
  setupServer();

  test('change the large_image settings and the config folder', async ({ page }) => {
    await createUser(page, 'admin', 'admin@email.com', 'Admin', 'Admin', 'testpassword');

    await test.step('change the large_image settings', async () => {
      await page.locator('a.g-nav-link[g-target="admin"]').click();
      await expect(page.locator('.g-plugins-config')).toBeVisible();
      await page.locator('.g-plugins-config').click();
      await waitForIdlePage(page);
      await expect(page.locator('.g-plugin-config-link[g-route="plugins/large_image/config"]')).toBeVisible();
      await page.locator('.g-plugin-config-link[g-route="plugins/large_image/config"]').click();
      await waitForIdlePage(page);
      await expect(page.locator('#g-large-image-form input').first()).toBeVisible();

      await page.locator('.g-large-image-thumbnails-hide').check();
      await page.locator('.g-large-image-viewer-hide').check();
      await page.locator('.g-large-image-default-viewer').selectOption('geojs');
      await page.locator('.g-large-image-auto-set-off').check();
      await page.locator('.g-large-image-max-thumbnail-files').fill('5');
      await page.locator('.g-large-image-max-small-image-size').fill('1024');
      await page.locator('.g-large-image-show-extra-public').fill('{}');
      await page.locator('.g-large-image-show-extra').fill('{}');
      await page.locator('.g-large-image-show-extra-admin').fill('{"images": ["label", "macro"]}');
      await page.locator('.g-large-image-show-item-extra-public').fill('{}');
      await page.locator('.g-large-image-show-item-extra').fill('{}');
      await page.locator('.g-large-image-show-item-extra-admin').fill('{"metadata": ["tile", "internal"], "images": ["label", "macro", "*"]}');
      await page.locator('.g-large-image-icc-correction-off').check();
      await page.locator('#g-large-image-form input.btn-primary').click();
      await waitForIdlePage(page);

      await expect.poll(async () => {
        const settings = await asyncRestRequest(page, { url: 'large_image/settings' }) as Record<string, unknown>;
        return settings['large_image.max_thumbnail_files'];
      }).toBe(5);
      const settings = await asyncRestRequest(page, { url: 'large_image/settings' }) as Record<string, unknown>;
      expect(settings['large_image.show_thumbnails']).toBe(false);
      expect(settings['large_image.show_viewer']).toBe(false);
      expect(settings['large_image.auto_set']).toBe(false);
      expect(settings['large_image.default_viewer']).toBe('geojs');
      expect(settings['large_image.max_thumbnail_files']).toBe(5);
      expect(settings['large_image.max_small_image_size']).toBe(1024);
      expect(settings['large_image.show_extra_public']).toBe('{}');
      expect(settings['large_image.show_extra']).toBe('{}');
      expect(settings['large_image.show_extra_admin']).toBe('{"images": ["label", "macro"]}');
      expect(settings['large_image.show_item_extra_public']).toBe('{}');
      expect(settings['large_image.show_item_extra']).toBe('{}');
      expect(JSON.parse(settings['large_image.show_item_extra_admin'] as string)).toEqual({ metadata: ['tile', 'internal'], images: ['label', 'macro', '*'] });
      expect(settings['large_image.icc_correction']).toBe(false);

      await page.locator('.g-large-image-icc-correction').check();
      await page.locator('#g-large-image-form input.btn-primary').click();
      await waitForIdlePage(page);
      await expect.poll(async () => {
        const settings = await asyncRestRequest(page, { url: 'large_image/settings' }) as Record<string, unknown>;
        return settings['large_image.icc_correction'];
      }).toBe(true);
    });

    await test.step('change the config folder', async () => {
      await page.locator('.g-open-browser').click();
      await waitForDialog(page);
      const rootSelector = page.locator('#g-root-selector');
      await expect(rootSelector.locator('option')).not.toHaveCount(0);
      const rootValue = await rootSelector.locator('option').nth(1).getAttribute('value');
      await rootSelector.selectOption(rootValue as string);
      await expect(page.locator('#g-dialog-container .g-folder-list-link').nth(1)).toBeVisible();
      await page.locator('#g-dialog-container .g-folder-list-link').first().click();
      await expect(page.locator('#g-selected-model')).not.toHaveValue('');
      await page.locator('.g-submit-button').click();
      await waitForIdlePage(page);
      await expect(page.locator('#g-large-image-config-folder')).not.toHaveValue('');
    });
  });
});
