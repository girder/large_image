import { spawn, ChildProcessWithoutNullStreams } from 'child_process';
import { randomBytes } from 'crypto';

import getPort from 'get-port';

import { expect, test } from '@playwright/test';

import { outputCoverageReport, startCoverage } from './coverage';

/*
 * This mirrors the test server management used by Girder's own Playwright
 * tests (girder/web/tests/server.ts).  Each describe block that calls
 * setupServer() gets a dedicated Girder server process backed by a uniquely
 * named Mongo database, which is dropped when the block finishes.
 */

const mongoUri = process.env.GIRDER_CLIENT_TESTING_MONGO_URI ?? 'mongodb://localhost:27017';
const girderExecutable = process.env.GIRDER_CLIENT_TESTING_GIRDER_EXECUTABLE ?? 'girder';

/**
 * Build a database name that is unique to this test server instance.
 *
 * Ports are recycled by the OS, so a database named after the port alone
 * could be reused by a later run if an earlier run was interrupted.
 * Combining the pid, a timestamp, and random bytes avoids that.
 */
const createDatabaseName = () =>
  `large-image-${process.pid}-${Date.now()}-${randomBytes(4).toString('hex')}`;

/**
 * The mongo shell command used for database cleanup, probed once and memoized
 * for the lifetime of this worker process.  `null` means no shell was found,
 * in which case cleanup is skipped; since database names are unique, leftover
 * databases cannot interfere with later runs.
 */
let mongoShell: Promise<string | null> | null = null;

const findMongoShell = (): Promise<string | null> => {
  if (mongoShell === null) {
    mongoShell = new Promise<string | null>((resolve) => {
      const candidates = ['mongosh', 'mongo'];
      let index = 0;
      const probe = () => {
        if (index >= candidates.length) {
          resolve(null);
          return;
        }
        const shellProcess = spawn(candidates[index], ['--version']);
        index += 1;
        shellProcess.on('error', () => probe());
        shellProcess.on('close', (code) => {
          if (code === 0) {
            resolve(candidates[index - 1]);
          } else {
            probe();
          }
        });
      };
      probe();
    });
  }
  return mongoShell;
};

/**
 * Drop a database, waiting for the mongo shell to finish.  Failures are
 * reported but never thrown, so that a cleanup problem cannot mask the actual
 * test result.
 */
const dropDatabase = async (database: string) => {
  const shell = await findMongoShell();
  if (shell === null) {
    return;
  }

  const shellProcess = spawn(shell, [`${mongoUri}/${database}`, '--eval', 'db.dropDatabase();']);

  await new Promise<void>((resolve) => {
    shellProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`mongo database ${database} cleanup failed with code`, code);
      }
      resolve();
    });

    shellProcess.on('error', (err) => {
      console.error(`mongo shell process error -- database ${database} not cleaned up`, err);
      resolve();
    });
  });
};

/**
 * Wait for a server process to exit, but do not wait forever if it hangs.
 */
const killServer = async (serverProcess?: ChildProcessWithoutNullStreams) => {
  if (!serverProcess) {
    return;
  }

  await new Promise<void>((resolve) => {
    const timeout = setTimeout(resolve, 5000);
    serverProcess.once('close', () => {
      clearTimeout(timeout);
      resolve();
    });
    serverProcess.kill();
  });
};

/**
 * The captured output of the Girder server started most recently in this
 * worker process.  It is printed when a test fails.
 */
const serverLogs: string[] = [];

/**
 * Browser console errors and uncaught page errors from the current test.
 */
const browserLogs: string[] = [];

const startServer = async (port: number, database: string) => {
  serverLogs.length = 0;
  const serverProcess = spawn(girderExecutable, [
    'serve',
    '--database', `${mongoUri}/${database}`,
    '--port', `${port}`,
    '--with-temp-assetstore',
  ], {
    env: {
      ...process.env,
      GIRDER_SETTING_CORE_CORS_ALLOW_ORIGIN: '*',
      GIRDER_EMAIL_TO_CONSOLE: 'true',
      // Run girder_worker tasks (such as processing uploaded annotations) in
      // the server process rather than requiring a message broker and a
      // celery worker.  Set this to false to test with a real worker.
      GIRDER_WORKER_TASK_ALWAYS_EAGER: process.env.GIRDER_WORKER_TASK_ALWAYS_EAGER ?? 'true',
    },
  });
  await new Promise<void>((resolve, reject) => {
    serverProcess?.stdout.on('data', (data: string) => {
      serverLogs.push(`stdout: ${data}`);
      if (data.includes('Girder server running')) {
        resolve();
      }
    });
    serverProcess?.stderr.on('data', (data: string) => {
      serverLogs.push(`stderr: ${data}`);
    });
    serverProcess?.on('error', (err) => {
      serverLogs.push(`failed to start ${girderExecutable}: ${err}`);
      reject(err);
    });
    serverProcess?.on('close', (code) => {
      serverLogs.push(`child process exited with code ${code}`);
      reject(new Error(`Girder server exited with code ${code}\n${serverLogs.join('')}`));
    });
  });
  return serverProcess;
};

export const setupServer = () => {
  let serverProcess: ChildProcessWithoutNullStreams;
  let database: string;
  let port: number;

  test.beforeAll(async () => {
    port = await getPort();
    database = createDatabaseName();
    serverProcess = await startServer(port, database);
  });

  test.afterAll(async () => {
    if (process.env.GIRDER_CLIENT_TESTING_KEEP_SERVER_ALIVE) {
      if (serverProcess) {
        console.log('WARNING: Girder server is being kept alive after test ends. Use the following to kill it:');
        console.log(`kill ${serverProcess?.pid}`);
        console.log(`Its database is: ${database}`);
      }
      return;
    }

    // Wait for the server to exit before dropping the database, so it cannot
    // recreate collections after the drop.
    await killServer(serverProcess);
    await dropDatabase(database);
  });

  test.beforeEach(async ({ page }) => {
    browserLogs.length = 0;
    page.on('console', (message) => {
      if (['error', 'warning'].includes(message.type())) {
        browserLogs.push(`console.${message.type()}: ${message.text()}`);
      }
    });
    page.on('pageerror', (error) => {
      browserLogs.push(`pageerror: ${error.message}\n${error.stack ?? ''}`);
    });
    await startCoverage(page);
    await expect(async () => {
      if (port !== null) {
        await page.goto(`http://localhost:${port}/`);
      }
      await expect(page.getByRole('link', { name: 'About' })).toBeVisible();
    }).toPass({ timeout: 60000 });
  });

  test.afterEach(async ({ page }, testInfo) => {
    if (testInfo.status !== testInfo.expectedStatus) {
      if (browserLogs.length > 0) {
        console.log('Browser errors for failed test:');
        console.log(browserLogs.join('\n'));
      }
      if (serverLogs.length > 0) {
        console.log('Server output for failed test:');
        console.log(serverLogs.join(''));
      }
    }
    serverLogs.length = 0;
    browserLogs.length = 0;
    await outputCoverageReport(page);
  });
};

export { browserLogs, serverLogs };
