import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

import { PlaywrightTestConfig } from '@playwright/test';
import libCoverage from 'istanbul-lib-coverage';
import libReport from 'istanbul-lib-report';
import reports from 'istanbul-reports';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Merge the per-test coverage data into an HTML report in coverage/report
 * and a cobertura report in the repository's build/test/coverage directory
 * (or GIRDER_TEST_COVERAGE_DIR), alongside the Python coverage output.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default async (_config: PlaywrightTestConfig) => {
  const coverageDir = path.join(__dirname, '..', 'coverage');
  const dataDir = path.join(coverageDir, 'data');
  const coverageMap = libCoverage.createCoverageMap({});
  let files: string[] = [];
  try {
    files = await fs.readdir(dataDir);
  } catch (e) {
    return;
  }
  console.log(`Found coverage files: ${files.length}`);
  for (const file of files) {
    coverageMap.merge(JSON.parse((await fs.readFile(path.join(dataDir, file))).toString()));
  }

  const watermarks = {
    statements: [50, 80] as [number, number],
    functions: [50, 80] as [number, number],
    branches: [50, 80] as [number, number],
    lines: [50, 80] as [number, number],
  };
  const htmlContext = libReport.createContext({
    dir: path.join(coverageDir, 'report'),
    defaultSummarizer: 'nested',
    watermarks,
    coverageMap,
  });
  reports.create('html', { skipEmpty: false }).execute(htmlContext);

  const outputDir = process.env.GIRDER_TEST_COVERAGE_DIR || path.join(__dirname, '..', '..', '..', '..', 'build', 'test', 'coverage');
  await fs.mkdir(outputDir, { recursive: true });
  const xmlContext = libReport.createContext({
    dir: outputDir,
    defaultSummarizer: 'nested',
    coverageMap,
  });
  reports.create('cobertura', {
    file: process.env.GIRDER_TEST_COVERAGE_FILE || 'cobertura-coverage.xml',
  }).execute(xmlContext);
};
