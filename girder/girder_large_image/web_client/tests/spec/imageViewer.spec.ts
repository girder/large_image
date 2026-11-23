import { expect, Page, test } from '@playwright/test';

import { createCollection, createUser, goToUserFolder, itemLink, login, uploadTestFile, waitForDialog, waitForIdlePage, waitForLargeImageViewer } from '../util';
import { setupServer } from '../server';

/**
 * Ported from girder/test_girder/web_client_specs/imageViewerSpec.js.
 *
 * The original Jasmine spec ran as one long sequence in a single browser
 * session.  Each Playwright test gets a fresh page, so tests after the first
 * log in again; the server and its database are shared across the describe.
 */

const ADMIN = {
  login: 'admin',
  email: 'admin@email.com',
  firstName: 'Admin',
  lastName: 'Admin',
  password: 'testpassword',
};

const bandEnabled = (page: Page, band: string) =>
  page.locator(`.image-frame-control-box .enable-col input[value="${band}"]`);

test.describe('Test the image viewer', () => {
  setupServer();
  test.describe.configure({ mode: 'serial' });

  test('upload a multi-frame image and adjust the frame slider', async ({ page }) => {
    await createUser(page, ADMIN.login, ADMIN.email, ADMIN.firstName, ADMIN.lastName, ADMIN.password);
    await goToUserFolder(page, 'Public');
    await uploadTestFile(page, 'multi_test_source3.yml');
    await itemLink(page).click();
    await waitForIdlePage(page);
    await expect(page.locator('.g-item-image-viewer-select')).toBeVisible();
    await waitForLargeImageViewer(page, 'geojs');

    await expect(page.locator('.image-frame-control-box')).toHaveCount(1);
    const numberInput = page.locator('.image-frame-control-box input[name="numberControl"]:visible');
    const slider = page.locator('.image-frame-control-box input[name="sliderControl"]:visible');
    await expect(slider).toHaveValue('0');
    await numberInput.fill('1');
    await expect(slider).toHaveValue('1');
    await expect(page.locator('#current_image_frame')).toHaveText('1');
    await waitForIdlePage(page);
  });

  test('test layer hotkeys in band compositing', async ({ page }) => {
    await login(page, ADMIN.login, ADMIN.password);
    await goToUserFolder(page, 'Public');
    await uploadTestFile(page, 'multi_test_source_bands.yml');

    await test.step('navigate to the item and use band compositing', async () => {
      await itemLink(page, 'multi_test_source_bands').click();
      await waitForIdlePage(page);
      await waitForLargeImageViewer(page, 'geojs');
      const mode = page.locator('.image-frame-control-box select[name="mode"]');
      await expect(mode.locator('option[value="3"]')).toHaveCount(1);
      await mode.selectOption('3');
      await expect(bandEnabled(page, 'green')).toBeVisible();
      await expect(bandEnabled(page, 'red')).toBeChecked();
      await expect(bandEnabled(page, 'green')).toBeChecked();
    });

    await test.step('toggle a band with the default keys', async () => {
      // CompositeLayers listens for keydown events on the document.
      await page.keyboard.press('Control+1');
      await expect(bandEnabled(page, 'red')).not.toBeChecked();
      await page.keyboard.press('Control+1');
      await expect(bandEnabled(page, 'red')).toBeChecked();
    });

    await test.step('replace the layer hotkeys', async () => {
      await page.evaluate(() => {
        const frameSelector = (document.querySelector('.image-frame-control-box') as any).__vue__;
        frameSelector._props.layerHotkeys = {
          layerForEvent: (evt: KeyboardEvent) => (evt.key === 'q' && !evt.ctrlKey ? 1 : undefined),
          labels: [undefined, 'Q'],
        };
      });
      await page.waitForTimeout(100);
      await page.keyboard.press('Control+1');
      await page.keyboard.press('q');
      await expect(bandEnabled(page, 'green')).not.toBeChecked();
      await expect(bandEnabled(page, 'red')).toBeChecked();
    });

    await test.step('list the replaced keys in the help', async () => {
      await page.locator('.image-frame-control-box .icon-keyboard:visible').click();
      const shortcuts = page.locator('.image-frame-control-box .shortcuts:visible');
      await expect(shortcuts).toBeVisible();
      const text = ((await shortcuts.textContent()) || '').replace(/\s+/g, ' ');
      expect(text).toContain('Q Toggle visibility of green');
      expect(text).not.toContain('ctrl + number');
      await page.locator('.image-frame-control-box .icon-keyboard:visible').click();
      await page.evaluate(() => {
        const frameSelector = (document.querySelector('.image-frame-control-box') as any).__vue__;
        frameSelector._props.layerHotkeys = undefined;
      });
      // Toggling bands requests histograms; let them finish before the
      // test ends.
      await waitForIdlePage(page);
    });
  });

  test('create a large image from an uploaded file, remove it, and remake it', async ({ page }) => {
    await login(page, ADMIN.login, ADMIN.password);

    await test.step('create a collection and upload a png', async () => {
      await page.locator('a.g-nav-link[g-target="collections"]').click();
      await expect(page.locator('.g-collection-create-button:visible')).toBeVisible();
      await expect(page.locator('.g-collection-list-entry')).toHaveCount(0);
      await createCollection(page, 'test', '', 'image');
      await uploadTestFile(page, 'yb10kx5k.png');
    });

    await test.step('navigate to the item and make a large image', async () => {
      await itemLink(page).click();
      await waitForIdlePage(page);
      await expect(page.locator('.g-large-image-create')).toBeVisible();
      await page.locator('.g-large-image-create').click();
      await expect(page.locator('.g-item-image-viewer-select')).toBeVisible({ timeout: 60000 });
      await waitForIdlePage(page);
    });

    await test.step('unmake a large image', async () => {
      await page.locator('.g-large-image-remove').click();
      await expect(page.locator('.g-item-image-viewer-select')).toHaveCount(0);
      await waitForIdlePage(page);
    });

    await test.step('remake a large image and then remove the image file', async () => {
      await expect(page.locator('.g-large-image-create')).toBeVisible();
      await page.locator('.g-large-image-create').click();
      await expect(page.locator('.g-item-image-viewer-select')).toBeVisible({ timeout: 60000 });
      await waitForIdlePage(page);
      // The item now has two files; delete the generated large image file,
      // which is the one whose row has the large image remove action.
      await page.locator('.g-file-list-entry', { has: page.locator('.g-large-image-remove') }).locator('.g-delete-file').click();
      await waitForDialog(page);
      await page.locator('#g-confirm-button').click();
      await waitForIdlePage(page);
      await expect(page.locator('.g-item-image-viewer-select')).toHaveCount(0);
    });

    await test.step('delete the now-empty item and upload the file again', async () => {
      // The original spec left the empty item in place and uploaded a second
      // item with the same name; deleting it keeps the item list unambiguous.
      await page.locator('.g-item-actions-button').click();
      await page.locator('.g-delete-item').click();
      await waitForDialog(page);
      await page.locator('#g-confirm-button').click();
      await waitForIdlePage(page);
      await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
      await uploadTestFile(page, 'yb10kx5k.png');
    });

    await test.step('navigate to the item and make a large image', async () => {
      await itemLink(page).click();
      await waitForIdlePage(page);
      await expect(page.locator('.g-large-image-create')).toBeVisible();
      await page.locator('.g-large-image-create').click();
      await expect(page.locator('.g-item-image-viewer-select')).toBeVisible({ timeout: 60000 });
      await expect(page.locator('.g-large-image-remove')).toBeVisible();
      await waitForIdlePage(page);
    });
  });

  test('test metadata in item lists', async ({ page }) => {
    await login(page, ADMIN.login, ADMIN.password);
    await goToUserFolder(page, 'Public');

    await test.step('test the metadata columns are not shown', async () => {
      await expect(page.locator('.large_image_container')).toHaveCount(0);
      await expect(page.locator('.large_image_thumbnail').first()).toBeVisible();
      await expect(page.locator('.li-column-metadata')).toHaveCount(0);
    });

    await test.step('upload a config file', async () => {
      await uploadTestFile(page, '.large_image_config.yaml');
    });

    await test.step('test the metadata columns are shown', async () => {
      await expect(page.locator('.large_image_container')).toHaveCount(0);
      await expect(page.locator('.large_image_thumbnail').first()).toBeVisible();
      // Metadata cells are empty for these items, so check they exist rather
      // than that they are visible.
      await expect(page.locator('.li-column-metadata').first()).toBeAttached();
    });

    await test.step('apply a filter', async () => {
      const filter = page.locator('.li-item-list-filter-input');
      await expect(page.locator('.g-item-list-entry')).toHaveCount(3);
      await filter.fill('multi');
      await waitForIdlePage(page);
      await expect(page.locator('.g-item-list-entry')).toHaveCount(2);
      await filter.fill('ybxxx 1.2 -0.6');
      await waitForIdlePage(page);
      await expect(page.locator('.g-item-list-entry')).toHaveCount(0);
      await filter.fill('');
      await waitForIdlePage(page);
      await expect(page.locator('.g-item-list-entry')).toHaveCount(3);
    });

    await test.step('flatten the item list', async () => {
      const flatten = page.locator('.li-flatten-item-list #flattenitemlist');
      await flatten.click();
      await waitForIdlePage(page);
      await expect(flatten).toBeChecked();
      await flatten.click();
      await waitForIdlePage(page);
      await expect(flatten).not.toBeChecked();
    });

    await test.step('navigate back to an image', async () => {
      const link = itemLink(page).filter({ hasNotText: '.large_image_config.yaml' }).first();
      await expect(link).toBeVisible();
      await link.click();
      await waitForIdlePage(page);
    });

    await test.step('one viewer is loaded', async () => {
      await waitForLargeImageViewer(page, 'geojs');
      const shown = page.locator('.image-viewer:not(.hidden)');
      await expect(shown).toHaveCount(1);
      const select = page.locator('.g-item-image-viewer-select .g-item-info-header select');
      await expect(shown).toHaveId(await select.inputValue());
      await expect(select.locator('option')).toHaveCount(5);
    });
  });

  // The original spec disabled selecting each viewer in turn (xit), as some
  // viewers cannot be loaded in the test environment.
  test.skip('select each viewer in turn via change, then return to geojs', async ({ page }) => {
    await login(page, ADMIN.login, ADMIN.password);
    await goToUserFolder(page, 'Public');
    await itemLink(page).filter({ hasNotText: '.large_image_config.yaml' }).first().click();
    await waitForLargeImageViewer(page, 'geojs');
    const select = page.locator('.g-item-image-viewer-select .g-item-info-header select');
    const viewers = await select.locator('option').evaluateAll((options) => options.map((option) => (option as HTMLOptionElement).value));
    viewers.push('geojs');
    for (const vid of viewers) {
      await select.selectOption(vid);
      await waitForLargeImageViewer(page, vid);
      await expect(page.locator('.image-viewer:not(.hidden)')).toHaveCount(1);
    }
  });
});
