import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

import v8toIstanbul from 'v8-to-istanbul';
import { Page } from '@playwright/test';

/*
 * Collect javascript coverage of the large_image plugin bundles from the
 * browser's V8 coverage, converting it to istanbul format.  This follows
 * girder/web/tests/coverage.ts in Girder.  Each test writes a coverage file
 * to coverage/data; the global teardown (playwright-teardown.ts) merges them
 * into HTML and cobertura reports.
 */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..', '..', '..');

/**
 * The directories holding the built bundles of each plugin in this
 * repository, keyed by the plugin name used in the plugin_static URL.
 */
const pluginDistDirs: Record<string, string> = {
  large_image: path.join(repoRoot, 'girder', 'girder_large_image', 'web_client', 'dist'),
  large_image_annotation: path.join(repoRoot, 'girder_annotation', 'girder_large_image_annotation', 'web_client', 'dist'),
  dicomweb: path.join(repoRoot, 'sources', 'dicom', 'large_image_source_dicom', 'web_client', 'dist'),
};

const createId = (length: number) => {
  let result = '';
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let counter = 0; counter < length; counter += 1) {
    result += characters.charAt(Math.floor(Math.random() * characters.length));
  }
  return result;
};

export const startCoverage = async (page: Page) => {
  try {
    await page.coverage.startJSCoverage({ resetOnNavigation: false });
  } catch (e) {
    // Coverage is only available on chromium.
  }
};

export const outputCoverageReport = async (page: Page) => {
  let coverage;
  try {
    coverage = await page.coverage.stopJSCoverage();
  } catch (e) {
    return;
  }
  for (const entry of coverage) {
    const match = /\/plugin_static\/([^/]+)\/(.*?)(\?.*)?$/.exec(entry.url);
    if (!match || !pluginDistDirs[match[1]]) {
      // Only the plugins in this repository are reported.
      continue;
    }
    const filename = match[2];
    if (filename.startsWith('extra/')) {
      // Third-party libraries (geojs) are copied into the extra directory.
      continue;
    }
    const distPath = path.join(pluginDistDirs[match[1]], filename);
    try {
      await fs.access(distPath);
    } catch (e) {
      continue;
    }
    try {
      const converter = v8toIstanbul(
        distPath,
        0,
        { source: entry.source ?? '' },
        (sourcePath) => sourcePath.includes('node_modules'),
      );
      await converter.load();
      converter.applyCoverage(entry.functions);
      await fs.writeFile(
        path.join(__dirname, '..', 'coverage', 'data', `istanbul-${createId(8)}.json`),
        JSON.stringify(converter.toIstanbul()),
      );
    } catch (e) {
      console.error(`Failed to process coverage for ${entry.url}:`, e);
    }
  }
};
