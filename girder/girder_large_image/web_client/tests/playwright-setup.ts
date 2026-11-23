import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { PlaywrightTestConfig } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Start each run with an empty coverage data directory.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default (_config: PlaywrightTestConfig) => {
  const coverageDir = path.join(__dirname, '..', 'coverage');
  if (fs.existsSync(coverageDir)) {
    fs.rmSync(coverageDir, { recursive: true, force: true });
  }
  fs.mkdirSync(path.join(coverageDir, 'data'), { recursive: true });
};
