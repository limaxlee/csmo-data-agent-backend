const fs = require('node:fs');
const path = require('node:path');

const testRunnerPackagePath = require.resolve('@storybook/test-runner/package.json');
const testRunnerPackage = require(testRunnerPackagePath);
const setupScriptPath = path.join(path.dirname(testRunnerPackagePath), 'dist', 'setup-page-script.mjs');
const setupScript = fs.readFileSync(setupScriptPath, 'utf8');
const workerScriptPath = path.join(__dirname, 'public', 'mockServiceWorker.js');
const workerScript = fs.readFileSync(workerScriptPath, 'utf8');

let workerRouteInstalled = false;

beforeEach(async () => {
  if (!globalThis.page || !process.env.TARGET_URL) {
    return;
  }

  if (globalThis.context && !workerRouteInstalled) {
    await globalThis.context.route('**/mockServiceWorker.js', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/javascript',
        body: workerScript,
      }),
    );
    workerRouteInstalled = true;
  }

  const iframeUrl = new URL('iframe.html', process.env.TARGET_URL).toString();
  const renderedEvent =
    'globalThis.__STORYBOOK_MODULE_CORE_EVENTS__.STORY_FINISHED ?? globalThis.__STORYBOOK_MODULE_CORE_EVENTS__.STORY_RENDERED';
  const content = setupScript
    .replaceAll('{{storybookUrl}}', process.env.TARGET_URL)
    .replaceAll('{{failOnConsole}}', process.env.TEST_CHECK_CONSOLE ?? 'false')
    .replaceAll('"{{renderedEvent}}"', renderedEvent)
    .replaceAll('{{testRunnerVersion}}', testRunnerPackage.version)
    .replaceAll('{{viewMode}}', process.env.VIEW_MODE ?? 'story')
    .replaceAll('{{logLevel}}', 'info')
    .replaceAll('{{debugPrintLimit}}', process.env.DEBUG_PRINT_LIMIT ?? '1000');

  await globalThis.page.goto(iframeUrl, { waitUntil: 'load' });
  await globalThis.page.addScriptTag({ content });
});

