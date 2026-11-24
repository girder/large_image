import { expect, Page, test } from '@playwright/test';

import { asyncRestRequest, createUser, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from sources/dicom/test_dicom/web_client_specs/dicomWebSpec.js.
 *
 * This requires a DICOMweb server with the example data used by the CI
 * configuration (see .circleci/dcm4chee).  The server URL is read from the
 * DICOMWEB_TEST_URL environment variable and an optional bearer token from
 * DICOMWEB_TEST_TOKEN; the test is skipped when no URL is set.
 */

const url = process.env.DICOMWEB_TEST_URL;
const token = process.env.DICOMWEB_TEST_TOKEN || null;

// After importing, we will verify that this item exists
const studyUID = '2.25.25644321580420796312527343668921514374';
const seriesUID = '1.3.6.1.4.1.5962.99.1.3205815762.381594633.1639588388306.2.0';
const verifyItemName = seriesUID;

/**
 * Download a URL from within the page and return the status and size in
 * bytes.  The bytes are kept in the page under the given name so that later
 * requests can be compared against them without transferring them to the
 * test process.
 */
const download = async (page: Page, url: string, name: string, headers?: Record<string, string>) => {
  return await page.evaluate(async ({ url, name, headers }) => {
    const girder = (window as any).girder;
    const resp = await fetch(`${girder.rest.getApiRoot()}/${url}`, {
      headers: {
        ...headers,
        'Girder-Token': girder.auth.getCurrentToken(),
      },
    });
    const body = new Uint8Array(await resp.arrayBuffer());
    (window as any)[name] = body;
    return { status: resp.status, length: body.length };
  }, { url, name, headers: headers || {} });
};

test.describe('DICOMWeb assetstore', () => {
  test.skip(!url, 'DICOMWEB_TEST_URL is not set');
  setupServer();

  test('Create an assetstore and import data', async ({ page }) => {
    await createUser(page, 'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!');

    await test.step('create the DICOMweb assetstore', async () => {
      await page.locator('a.g-nav-link[g-target="admin"]').click();
      await expect(page.locator('.g-assetstore-config')).toBeVisible();
      await page.locator('a.g-assetstore-config').click();
      await waitForIdlePage(page);
      await expect(page.locator('#g-create-dwas-tab')).toHaveCount(1);
      // Expand the collapsed creation panel
      await page.locator('.panel-heading[data-target="#g-create-dwas-tab"]').click();
      await expect(page.locator('#g-new-dwas-name')).toBeVisible();

      await page.locator('#g-new-dwas-name').fill('DICOMweb');
      await page.locator('#g-new-dwas-url').fill(url as string);

      // Test error for setting auth type to "token" with no token
      await page.locator('#g-new-dwas-auth-type').selectOption('token');
      await page.locator('#g-new-dwas-form input.btn-primary').click();
      await expect(page.locator('#g-new-dwas-error')).toHaveText('A token must be provided if the auth type is "token"');

      if (token === null) {
        // Change the auth type back to None
        await page.locator('#g-new-dwas-auth-type').selectOption('');
      } else {
        // Set the token
        await page.locator('#g-new-dwas-auth-token').fill(token);
      }

      // This should work now
      await page.locator('#g-new-dwas-form input.btn-primary').click();
      // The assetstore list is sorted by name, and the test server's
      // temporary assetstore is named after its directory, so the DICOMweb
      // assetstore need not be first in the list.
      await expect.poll(async () => {
        const assetstores = await asyncRestRequest(page, { url: 'assetstore' }) as Array<Record<string, string>>;
        return assetstores.length === 2 && assetstores.some((assetstore) => assetstore.type === 'dicomweb');
      }).toBe(true);
    });

    // Use the user's public folder as the destination
    const user = await asyncRestRequest(page, { url: 'user/me' }) as Record<string, string>;
    const folders = await asyncRestRequest(page, {
      url: 'folder',
      data: { parentType: 'user', parentId: user._id, name: 'Public' },
    }) as Array<Record<string, string>>;
    const destinationType = 'folder';
    const destinationId = folders[0]._id;

    await test.step('check import validation', async () => {
      // Navigate to the import page
      await page.locator('.g-dwas-import-button').first().click();
      await expect(page.locator('.g-submit-assetstore-import')).toBeVisible();
      // Scope to the import form; the hidden register dialog used to create
      // the admin user leaves its own validation message element in the DOM.
      const validationMessage = page.locator('.g-dwas-import-form .g-validation-failed-message');

      // Test error when no ID is set.  This is the only validation done in
      // the browser; the limit and filters are checked by the import task,
      // which runs in a worker and reports problems in its log rather than
      // in the response to the import request.
      await page.locator('.g-submit-assetstore-import').click();
      await expect(validationMessage).toHaveText('Invalid Destination ID');

      await page.locator('#g-dwas-import-dest-type').selectOption(destinationType);
      await page.locator('#g-dwas-import-dest-id').fill(destinationId);
      await page.locator('#g-dwas-import-limit').fill('1');
    });

    let itemId = '';
    let fileId = '';
    await test.step('import a study', async () => {
      // We will only import this specific StudyInstanceUID
      await page.locator('#g-dwas-import-filters').fill(`{"StudyInstanceUID": "${studyUID}"}`);
      await page.locator('.g-submit-assetstore-import').click();

      // Once the import has been queued, the page navigates to the
      // destination.  When tasks run eagerly in the server process, the
      // request does not return until the import is complete.
      await expect(page).toHaveURL(new RegExp(`#${destinationType}/${destinationId}$`), { timeout: 60000 });

      // Verify that the item we were looking for was imported
      await expect.poll(async () => {
        const resp = await asyncRestRequest(page, {
          url: 'resource/search',
          data: { q: `"${verifyItemName}"`, types: '["item"]' },
        }) as { item: Array<Record<string, any>> };
        const items = resp.item;
        if (items.length === 0 || items[0].largeImage === undefined) {
          return false;
        }
        itemId = items[0]._id;
        fileId = items[0].largeImage.fileId;
        return true;
      }, { timeout: 60000 }).toBe(true);
    });

    await test.step('download the item and a single file', async () => {
      // Verify that we can download the item; it should be larger than 10
      // million bytes
      const item = await download(page, `item/${itemId}/download`, '__dicomItemContent');
      expect(item.status).toBe(200);
      expect(item.length).toBeGreaterThan(10000000);

      // Verify that we can download a single file; it should be larger than
      // 500k bytes
      const file = await download(page, `file/${fileId}/download`, '__dicomFileContent');
      expect(file.status).toBe(200);
      expect(file.length).toBeGreaterThan(500000);
    });

    await test.step('make a range request', async () => {
      const resp = await download(page, `file/${fileId}/download`, '__dicomRangeContent', { Range: 'bytes=1000-1250' });
      // 206 is a partial content response
      expect(resp.status).toBe(206);
      // Should be exactly 251 bytes
      expect(resp.length).toBe(251);
      // It should be equivalent to the slice of the file content
      const matches = await page.evaluate(() => {
        const file = (window as any).__dicomFileContent as Uint8Array;
        const range = (window as any).__dicomRangeContent as Uint8Array;
        return range.every((value, idx) => value === file[1000 + idx]);
      });
      expect(matches).toBe(true);
    });
  });
});
