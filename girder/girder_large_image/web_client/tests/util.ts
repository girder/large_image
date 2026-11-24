import path from 'path';
import { fileURLToPath } from 'url';

import { expect, Page } from '@playwright/test';

/*
 * Shared helpers for the large_image Playwright tests.  The login, dialog,
 * and upload helpers mirror those used by Girder's own Playwright tests
 * (girder/web/tests/util.ts) so that specs written for either project look
 * alike.
 */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** The repository root (four levels above this tests directory). */
export const repoRoot = path.resolve(__dirname, '..', '..', '..', '..');

/** The directory holding data files used only by these tests. */
export const dataDir = path.join(__dirname, 'data');

/**
 * Wait for all outstanding REST requests to complete.
 */
export const waitForIdlePage = async (page: Page) => {
  await expect(page.locator('#g-dialog-container')).toBeHidden();
  await expect(page.locator('.modal-backdrop')).toBeHidden();
  await page.waitForFunction(() => {
    // @ts-ignore
    return window.girder && window.girder.rest && window.girder.rest.numberOutstandingRestRequests() === 0;
  });
};

export const waitForDialog = async (page: Page) => {
  await expect(page.locator('#g-dialog-container')).toBeVisible();
  await expect(page.locator('.modal-backdrop')).toBeVisible();
  await page.waitForFunction(() => {
    // @ts-ignore
    return window.girder && window.girder.rest && window.girder.rest.numberOutstandingRestRequests() === 0;
  });
};

/**
 * Wait for the given element to become the page's active element.
 *
 * Girder dialogs focus their default field in a Bootstrap `shown.bs.modal`
 * handler, which fires only after the dialog's show transition completes.
 * Filling fields before that can corrupt the form, so wait for the dialog's
 * intended field to be focused before filling anything.
 */
export const waitForFocused = async (page: Page, selector: string) => {
  await page.waitForFunction(
    (sel) => document.activeElement === document.querySelector(sel),
    selector,
  );
};

export const logout = async (page: Page) => {
  await page.locator('.g-user-dropdown-link').click();
  await expect(page.locator('.g-logout')).toBeVisible();
  await page.locator('.g-logout').click();
  await expect(page.locator('.g-register')).toBeVisible();
  await expect(page.locator('.g-login')).toBeVisible();
  await expect(page.locator('.g-user-dropdown-link')).toBeHidden();
};

export const createUser = async (
  page: Page,
  login: string = 'firstlast',
  email: string = 'email@email.com',
  firstName: string = 'first',
  lastName: string = 'last',
  password: string = 'password',
) => {
  await expect(page.locator('.g-register')).toBeVisible();
  await page.locator('.g-register').click();
  await waitForDialog(page);
  await expect(page.locator('input#g-email')).toBeVisible();
  await waitForFocused(page, '#g-login');
  await page.locator('#g-login').fill(login);
  await page.locator('#g-email').fill(email);
  await page.locator('#g-firstName').fill(firstName);
  await page.locator('#g-lastName').fill(lastName);
  await page.locator('#g-password').fill(password);
  await page.locator('#g-password2').fill(password);
  await page.locator('#g-register-button').click();
  await waitForIdlePage(page);
  await expect(page.locator('.g-register')).toBeHidden();
  await expect(page.locator('.g-login')).toBeHidden();
  await expect(page.locator('.g-user-dropdown-link')).toBeVisible();
  await expect(page.locator('.g-user-dropdown-link')).toContainText(login);
};

export const login = async (
  page: Page,
  login: string,
  password: string = 'password',
) => {
  await expect(page.locator('.g-login')).toBeVisible();
  await page.locator('.g-login').click();
  await waitForDialog(page);
  await expect(page.locator('#g-login')).toBeVisible();
  await waitForFocused(page, '#g-login');
  await page.locator('#g-login').fill(login);
  await page.locator('#g-password').fill(password);
  await page.locator('#g-login-button').click();
  await waitForIdlePage(page);
  await expect(page.locator('.g-register')).toBeHidden();
  await expect(page.locator('.g-login')).toBeHidden();
  await expect(page.locator('.g-user-dropdown-link')).toBeVisible();
  await expect(page.locator('.g-user-dropdown-link')).toContainText(login);
};

export const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const upload = async (page: Page, file: string | string[], awaitSuccess: boolean = true) => {
  // This should be called from a folder view, where the upload button is visible.
  // At the end, the file will be uploaded and you'll be back on the folder view.
  await page.locator('.g-upload-here-button').first().click();
  await expect(page.locator('.g-drop-zone')).toBeVisible();
  await page.locator('#g-files').setInputFiles(file);
  await page.locator('.g-start-upload').click();
  if (awaitSuccess) {
    await waitForIdlePage(page);
    await expect(page.locator('.g-start-upload')).toBeHidden();
  }
};

/**
 * Upload a file from the repository's sample_data directory.
 */
export const uploadSampleFile = async (page: Page, filename: string) => {
  await upload(page, path.join(repoRoot, 'sample_data', filename));
};

/**
 * Upload a file from the repository's test/test_files directory.
 */
export const uploadTestFile = async (page: Page, filename: string) => {
  await upload(page, path.join(repoRoot, 'test', 'test_files', filename));
};

/**
 * Make a REST request from within the page context and await its result.
 */
export const asyncRestRequest = async (page: Page, opts: Record<string, unknown>) => {
  return await page.evaluate((opts) => {
    return new Promise((resolve, reject) => {
      // @ts-ignore - window.girder is available at runtime
      window.girder.rest.restRequest(opts).done((resp: unknown) => {
        resolve(resp);
      }).fail((resp: unknown) => {
        reject(resp);
      });
    });
  }, opts);
};

/**
 * Navigate the Girder single-page application to a route without reloading
 * the page, then wait for the resulting REST requests to finish.
 */
export const navigate = async (page: Page, route: string) => {
  await page.evaluate((route) => {
    // @ts-ignore - window.girder is available at runtime
    window.girder.router.navigate(route, { trigger: true });
  }, route);
  await waitForIdlePage(page);
};

/**
 * From anywhere in the app, open the logged-in user's folder with the given
 * name (for instance "Public" or "Private").
 */
export const goToUserFolder = async (page: Page, folderName: string) => {
  await page.locator('.g-user-dropdown-link').click();
  await page.locator('a.g-my-folders').click();
  await expect(page.locator('.g-user-header')).toBeVisible();
  await expect(page.locator('a.g-folder-list-link', { hasText: folderName })).toBeVisible();
  await page.locator('a.g-folder-list-link', { hasText: folderName }).click();
  await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
  await waitForIdlePage(page);
};

/**
 * Create a collection through the UI and, optionally, a folder within it.
 * This mirrors girderTest.createCollection from the Jasmine test utilities.
 * When a folder is created, the browser is left viewing that folder.
 */
export const createCollection = async (
  page: Page, name: string, description: string = '', folderName?: string,
) => {
  await navigate(page, 'collections');
  await expect(page.locator('.g-collection-create-button:visible')).toBeVisible();
  await page.locator('.g-collection-create-button').click();
  await waitForDialog(page);
  await waitForFocused(page, '#g-name');
  await page.locator('#g-name').fill(name);
  if (description) {
    await page.locator('#collection-description-write .g-markdown-text').fill(description);
  }
  await page.locator('.g-save-collection').click();
  await expect(page.locator('.g-collection-header .g-collection-name')).toHaveText(name);
  await waitForIdlePage(page);
  if (folderName) {
    await page.locator('.g-folder-actions-button:visible').click();
    await page.locator('.g-create-subfolder:visible').click();
    await waitForDialog(page);
    await waitForFocused(page, '#g-name');
    await page.locator('#g-name').fill(folderName);
    await page.locator('#g-dialog-container .g-save-folder').click();
    await waitForIdlePage(page);
    await expect(page.locator('a.g-folder-list-link', { hasText: folderName })).toBeVisible();
    await page.locator('a.g-folder-list-link', { hasText: folderName }).click();
    await expect(page.locator('.g-folder-actions-button:visible')).toHaveCount(1);
    await waitForIdlePage(page);
  }
};

/**
 * Locate the name link of an item in a folder's item list.  The large_image
 * item list renders every column as a link, so this restricts the match to
 * the name column; if `name` is given, only items with that text match.
 */
export const itemLink = (page: Page, name?: string) =>
  page.locator('a.g-item-list-link.li-column-record-name', name ? { hasText: name } : {});

/**
 * Wait for the large_image viewer named `viewerName` to be the one visible
 * viewer on the item page.
 */
export const waitForLargeImageViewer = async (page: Page, viewerName: string) => {
  await page.waitForFunction((viewerName) => {
    const viewers = Array.from(document.querySelectorAll('.image-viewer'));
    const shown = viewers.filter((el) => !el.classList.contains('hidden'));
    const hidden = viewers.filter((el) => el.classList.contains('hidden'));
    return shown.length === 1 &&
      shown[0].id === viewerName &&
      shown[0].children.length > 0 &&
      hidden.every((el) => el.children.length === 0);
  }, viewerName);
};

/**
 * Run `fn` in the page with the window object, forwarding `arg` and
 * resolving with its return value.  This is a convenience over
 * page.evaluate for tests that exercise the plugin's javascript modules
 * directly; `fn` may be async.
 */
export const inPage = async <T, A>(page: Page, fn: (win: any, arg: A) => T | Promise<T>, arg?: A): Promise<T> => {
  return await page.evaluate(
    async ({ fnBody, arg: innerArg }) => {
      // eslint-disable-next-line no-new-func
      const fn = new Function('win', 'arg', `return (${fnBody})(win, arg);`) as (win: unknown, arg: unknown) => unknown;
      return await fn(window, innerArg);
    },
    { fnBody: fn.toString(), arg },
  ) as T;
};
