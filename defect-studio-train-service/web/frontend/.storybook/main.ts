import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  stories: [
    '../src/**/*.stories.@(ts|tsx)',
    // Component packages keep their stories beside the component, so the shared UI is
    // browsable here rather than needing a Storybook per package. Tailwind already
    // scans packages/*/src through tailwind.config.js, so their classes are built.
    '../../../packages/*/src/**/*.stories.@(ts|tsx)',
  ],
  staticDirs: ['../public'],
  addons: ['@storybook/addon-essentials', 'storybook-dark-mode'],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
};

export default config;