import path from 'path';

import { expect, Page, test } from '@playwright/test';

import { asyncRestRequest, createCollection, createUser, dataDir, itemLink, login, logout, navigate, uploadTestFile, waitForDialog, waitForIdlePage, waitForLargeImageViewer } from '../util';
import { setupServer } from '../server';

/**
 * Ported from girder_annotation/test_annotation/web_client_specs/annotationListSpec.js.
 *
 * This tests the annotation list widget shown on large image item pages
 * when the large_image_annotation plugin is enabled.
 */

const ADMIN = {
  login: 'admin',
  email: 'admin@email.com',
  firstName: 'Admin',
  lastName: 'Admin',
  password: 'testpassword',
};

const USER = {
  login: 'user',
  email: 'user@email.com',
  firstName: 'User',
  lastName: 'User',
  password: 'testpassword',
};

// Set once the test image is uploaded, then reused by the later tests.
let itemId = '';

/**
 * Replace the geojs viewer's annotation drawing with a record of which
 * annotations would have been drawn, then navigate to the test item.  The
 * record is kept in window.__drawnAnnotations.
 */
const openItem = async (page: Page) => {
  await page.evaluate(() => {
    const girder = (window as any).girder;
    const GeojsViewer = girder.plugins.large_image.views.imageViewerWidget.geojs;
    (window as any).__drawnAnnotations = {};
    girder.utilities.PluginUtils.wrap(GeojsViewer, 'initialize', function (this: any, initialize: any, ...args: unknown[]) {
      this.drawAnnotation = (annotation: any) => {
        (window as any).__drawnAnnotations[annotation.id] = true;
      };
      this.removeAnnotation = (annotation: any) => {
        delete (window as any).__drawnAnnotations[annotation.id];
      };
      initialize.apply(this, args);
    });
  });
  await navigate(page, `item/${itemId}`);
  await waitForLargeImageViewer(page, 'geojs');
};

const drawnAnnotations = (page: Page) =>
  page.evaluate(() => (window as any).__drawnAnnotations as Record<string, boolean>);

const rows = (page: Page) => page.locator('.g-annotation-list .g-annotation-row');

test.describe('AnnotationListWidget', () => {
  setupServer();
  test.describe.configure({ mode: 'serial' });

  test('setup: create an admin, a public collection, an image, and annotations', async ({ page }) => {
    await createUser(page, ADMIN.login, ADMIN.email, ADMIN.firstName, ADMIN.lastName, ADMIN.password);
    await page.locator('a.g-nav-link[g-target="collections"]').click();
    await expect(page.locator('.g-collection-create-button:visible')).toBeVisible();
    await expect(page.locator('.g-collection-list-entry')).toHaveCount(0);
    await createCollection(page, 'test', '', 'image');

    await test.step('make collection and folder public', async () => {
      const collections = await asyncRestRequest(page, { url: 'collection' }) as Array<Record<string, string>>;
      expect(collections.length).toBe(1);
      const collectionId = collections[0]._id;
      await asyncRestRequest(page, {
        url: `collection/${collectionId}/access`,
        method: 'PUT',
        data: { public: true, access: '{}' },
      });
      const folders = await asyncRestRequest(page, {
        url: 'folder',
        data: { parentType: 'collection', parentId: collectionId },
      }) as Array<Record<string, string>>;
      expect(folders.length).toBe(1);
      await asyncRestRequest(page, {
        url: `folder/${folders[0]._id}/access`,
        method: 'PUT',
        data: { public: true, access: '{}' },
      });
    });

    await test.step('upload test file', async () => {
      await uploadTestFile(page, 'yb10kx5k.zstd.tiff');
    });

    await test.step('navigate to item', async () => {
      await itemLink(page).click();
      await waitForIdlePage(page);
      await expect(page.locator('.g-item-image-viewer-select')).toBeVisible();
      await waitForLargeImageViewer(page, 'geojs');
      await expect(page.locator('.g-annotation-list-container .g-annotation-row')).toHaveCount(0);
      itemId = ((await page.evaluate(() => window.location.hash)) as string).split('/')[1];
      expect(itemId).toMatch(/^[0-9a-f]{24}$/);
    });

    await test.step('create annotations', async () => {
      await page.evaluate(async (itemId) => {
        const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
        const promises = [];
        for (let index = 1; index < 11; index += 1) {
          const annotation = new largeImageAnnotation.models.AnnotationModel({
            itemId,
            annotation: { name: `annotation ${index}` },
          });
          promises.push(annotation.save());
        }
        await Promise.all(promises);
      }, itemId);
    });

    await test.step('reload the item page', async () => {
      await navigate(page, '');
      await openItem(page);
      await expect(rows(page)).toHaveCount(10);
    });
  });

  test('test annotation list widget as admin', async ({ page }) => {
    await login(page, ADMIN.login, ADMIN.password);
    await openItem(page);

    await test.step('check that all annotations are displayed', async () => {
      await expect(rows(page)).toHaveCount(10);
      for (const row of await rows(page).all()) {
        await expect(row.locator('.g-annotation-entry').first()).toHaveText(/annotation [0-9]+/);
      }
    });

    await test.step('check download link', async () => {
      const row = rows(page).first();
      const id = await row.getAttribute('data-annotation-id');
      await expect(row.locator('.g-annotation-download')).toHaveAttribute('href', new RegExp(`.*annotation/${id}$`));
    });

    await test.step('test permission editor link', async () => {
      const row = rows(page).first();
      await expect(row.locator('.g-annotation-permissions')).toHaveCount(1);
      await row.locator('.g-annotation-permissions').click();
      await waitForDialog(page);
      await expect(page.locator('#g-dialog-container .modal-title')).toHaveText('Access control');
      await page.locator('#g-dialog-container .g-save-access-list').click();
      await waitForIdlePage(page);
    });

    await test.step('test delete link', async () => {
      const row = rows(page).first();
      const id = await row.getAttribute('data-annotation-id');
      await expect(row.locator('.g-annotation-delete')).toHaveCount(1);
      await row.locator('.g-annotation-delete').click();
      await waitForDialog(page);
      await page.locator('#g-dialog-container #g-confirm-button').click();
      await expect(page.locator(`.g-annotation-list .g-annotation-row[data-annotation-id="${id}"]`)).toHaveCount(0);
      await waitForIdlePage(page);
      await expect(rows(page)).toHaveCount(9);
    });
  });

  test('test annotation list widget as user', async ({ page }) => {
    await createUser(page, USER.login, USER.email, USER.firstName, USER.lastName, USER.password);
    await openItem(page);

    await test.step('check that all annotations are displayed', async () => {
      await expect(rows(page)).toHaveCount(9);
      for (const row of await rows(page).all()) {
        await expect(row.locator('.g-annotation-entry').first()).toHaveText(/annotation [0-9]+/);
      }
    });

    await test.step('check download link', async () => {
      const row = rows(page).first();
      const id = await row.getAttribute('data-annotation-id');
      await expect(row.locator('.g-annotation-download')).toHaveAttribute('href', new RegExp(`.*annotation/${id}$`));
    });

    await test.step('test delete and permission editor links are absent', async () => {
      const row = rows(page).first();
      await expect(row.locator('.g-annotation-delete')).toHaveCount(0);
      await expect(row.locator('.g-annotation-permissions')).toHaveCount(0);
    });

    await test.step('check visibility checkbox tooltip', async () => {
      await expect(page.locator('.g-annotation-list .g-annotation-row .g-annotation-toggle a').first()).toHaveAttribute('title', 'Show annotation');
    });

    await test.step('toggle annotation visibility', async () => {
      const row = rows(page).first();
      const id = await row.getAttribute('data-annotation-id') as string;
      const eye = page.locator('.g-annotation-list .g-annotation-toggle a i').first();
      await row.click();
      await expect.poll(async () => (await drawnAnnotations(page))[id]).toBe(true);
      await waitForIdlePage(page);
      await expect(eye).toHaveClass(/icon-eye$/);
      await row.click();
      await expect(eye).not.toHaveClass(/icon-eye$/);
      expect((await drawnAnnotations(page))[id]).toBeUndefined();
    });

    await test.step('toggle annotation visibility via view all button', async () => {
      const id = await rows(page).first().getAttribute('data-annotation-id') as string;
      const eye = page.locator('.g-annotation-list .g-annotation-toggle a i').first();
      await page.locator('.g-annotation-list .g-annotation-toggle-all').click();
      await expect.poll(async () => (await drawnAnnotations(page))[id]).toBe(true);
      await waitForIdlePage(page);
      await expect(eye).toHaveClass(/icon-eye$/);
      await page.locator('.g-annotation-list .g-annotation-toggle-all').click();
      await expect(eye).not.toHaveClass(/icon-eye$/);
      expect((await drawnAnnotations(page))[id]).toBeUndefined();
    });

    await test.step('test that neither the delete-all nor all-permissions icons are present', async () => {
      await expect(page.locator('.g-annotation-list-header .g-annotation-permissions')).toHaveCount(0);
      await expect(page.locator('.g-annotation-list-header .g-annotation-delete')).toHaveCount(0);
    });

    await logout(page);
  });

  test('test bulk actions as admin', async ({ page }) => {
    await login(page, ADMIN.login, ADMIN.password);
    await openItem(page);

    await test.step('test upload annotation button with cancel', async () => {
      await page.locator('.g-annotation-list-header .g-annotation-upload').click();
      await waitForDialog(page);
      await page.locator('#g-dialog-container .modal-footer a.btn').click();
      await waitForIdlePage(page);
    });

    await test.step('test upload annotation button with file', async () => {
      await page.locator('.g-annotation-list-header .g-annotation-upload').click();
      await waitForDialog(page);
      await page.locator('#g-files').setInputFiles(path.join(dataDir, 'sample_annotation.json'));
      await page.locator('.g-start-upload').click();
      await waitForIdlePage(page);
      await expect(rows(page)).toHaveCount(10);
    });

    await test.step('test header permission editor link', async () => {
      const list = page.locator('.g-annotation-list');
      await expect(list.locator('th .g-annotation-permissions')).toHaveCount(1);
      await list.locator('th.g-annotation-select input').click();
      await list.locator('th .g-annotation-permissions').click();
      await waitForDialog(page);
      await expect(page.locator('#g-dialog-container .modal-title')).toHaveText('Access control');
      await page.locator('#g-dialog-container .g-save-access-list').click();
      await waitForIdlePage(page);
    });

    await test.step('test header delete link', async () => {
      const list = page.locator('.g-annotation-list');
      await expect(list.locator('th .g-annotation-delete')).toHaveCount(1);
      await list.locator('th.g-annotation-select input').click();
      await list.locator('th .g-annotation-delete').click();
      await waitForDialog(page);
      await page.locator('#g-dialog-container #g-confirm-button').click();
      await expect(rows(page)).toHaveCount(0);
      await waitForIdlePage(page);
    });
  });
});
