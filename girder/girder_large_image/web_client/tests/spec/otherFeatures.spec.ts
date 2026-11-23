import { expect, test } from '@playwright/test';

import { createUser, goToUserFolder, itemLink, uploadTestFile, waitForDialog, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from girder/test_girder/web_client_specs/otherFeatures.js.
 *
 * Test features added by the large image plugin but not directly related to
 * large images: the codemirror editor shown for yaml, json, and girder
 * configuration files.
 */
test.describe('Test features added by the large image plugin but not directly related to large images', () => {
  setupServer();

  test('edit yaml and girder config files with the codemirror item view', async ({ page }) => {
    await createUser(page, 'admin', 'admin@email.com', 'Admin', 'Admin', 'testpassword');

    await test.step('upload a yaml file and check the editor is present', async () => {
      await goToUserFolder(page, 'Public');
      await uploadTestFile(page, 'multi_test_source3.yml');
      await itemLink(page, 'multi_test_source3.yml').click();
      await waitForIdlePage(page);
      await expect(page.locator('.li-item-view-codemirror>.editor')).toHaveCount(1);
    });

    await test.step('test buttons', async () => {
      await page.locator('.g-view-codemirror-format-button').click();
      await page.locator('.g-view-codemirror-save-button').click();
      await waitForIdlePage(page);
      await page.locator('.g-view-codemirror-revert-button').click();
      await page.locator('.g-view-codemirror-save-button').click();
      await waitForIdlePage(page);
      await page.locator('.g-view-codemirror-save-button').click();
      await waitForIdlePage(page);
      await expect(page.locator('.li-item-view-codemirror>.editor')).toHaveCount(1);
    });

    await test.step('go up a folder and upload a girder config file', async () => {
      await page.locator('a.g-item-breadcrumb-link').last().click();
      await waitForIdlePage(page);
      await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
      await uploadTestFile(page, 'sample.girder.cfg');
    });

    await test.step('navigate to the item and change the mime type', async () => {
      await itemLink(page, 'sample.girder.cfg').click();
      await waitForIdlePage(page);
      await page.locator('.g-file-actions-container .g-update-info').click();
      await waitForDialog(page);
      await page.locator('#g-mimetype').fill('application/x-girder-ini');
      await page.locator('button.g-save-file').click();
      await waitForIdlePage(page);
    });

    await test.step('navigate away and back', async () => {
      await page.locator('a.g-item-breadcrumb-link').last().click();
      await waitForIdlePage(page);
      await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
      await itemLink(page, 'sample.girder.cfg').click();
      await waitForIdlePage(page);
      await expect(page.locator('.li-item-view-codemirror>.editor')).toHaveCount(1);
    });

    await test.step('test buttons', async () => {
      await page.locator('.g-view-codemirror-format-button').click();
      await page.locator('.g-view-codemirror-save-button').click();
      await waitForIdlePage(page);
      await page.locator('.g-view-codemirror-revert-button').click();
      await page.locator('.g-view-codemirror-save-button').click();
      await waitForIdlePage(page);
      await page.locator('.g-view-codemirror-format-button').click();
      await waitForIdlePage(page);
    });

    await test.step('test replace button', async () => {
      await page.locator('.g-view-codemirror-general-button[button-key="replace"]').click();
      await waitForDialog(page);
      await expect(page.locator('#g-confirm-button')).toHaveText('Save, Replace, and Restart');
      await page.locator('#g-dialog-container a.btn-default').click();
      await waitForIdlePage(page);
    });
  });
});
