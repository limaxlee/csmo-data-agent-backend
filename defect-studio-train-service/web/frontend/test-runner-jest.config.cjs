const fs = require('node:fs');
const { getJestConfig } = require('@storybook/test-runner');

const testRunnerConfig = getJestConfig();
const basePlaywrightOptions = testRunnerConfig.testEnvironmentOptions?.['jest-playwright'] ?? {};

const browserPaths = [
  process.env.STORYBOOK_TEST_CHROMIUM_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].filter(Boolean);

const executablePath = browserPaths.find((path) => fs.existsSync(path));

module.exports = {
  ...testRunnerConfig,
  setupFilesAfterEnv: [
    ...(testRunnerConfig.setupFilesAfterEnv ?? []),
    require.resolve('./test-runner-setup.cjs'),
  ],
  testEnvironmentOptions: {
    ...testRunnerConfig.testEnvironmentOptions,
    'jest-playwright': {
      ...basePlaywrightOptions,
      browsers: basePlaywrightOptions.browsers ?? ['chromium'],
      launchOptions: {
        ...basePlaywrightOptions.launchOptions,
        chromium: {
          ...basePlaywrightOptions.launchOptions?.chromium,
          ...(executablePath ? { executablePath } : {}),
        },
      },
    },
  },
};
