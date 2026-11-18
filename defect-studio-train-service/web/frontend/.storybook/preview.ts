import { createElement } from 'react';
import type { Preview } from '@storybook/react';
import { themes } from '@storybook/theming';
import { initialize, mswLoader } from 'msw-storybook-addon';
import { handlers } from '../src/mocks/handlers';
import { Providers } from '../src/app/Providers';
import { queryClient } from '../src/shared/api/queryClient';
import '../src/app/index.css';
import tailwindConfig from '../tailwind.config';

const darkPalette = tailwindConfig.theme.extend.colors.dark as Record<string, string>;
const lightPalette = tailwindConfig.theme.extend.colors.light as Record<string, string>;

const backendRoutePatterns = [/^\/api(?:\/|$)/, /^\/mock(?:\/|$)/];

const isBackendRequest = (request: Request) => {
  const url = new URL(request.url);
  return backendRoutePatterns.some((pattern) => pattern.test(url.pathname));
};

initialize({
  onUnhandledRequest: (request, print) => {
    if (isBackendRequest(request)) {
      print.warning();
    }
  },
});

const preview: Preview = {
  // Providers passes the one queryClient built at module level, so data fetched by
  // one story is still cached when the next one renders. Empty it between stories.
  async beforeEach() {
    queryClient.clear();
  },
  loaders: [mswLoader],
  decorators: [(Story) => createElement(Providers, null, createElement(Story))],
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    msw: {
      handlers,
    },
    darkMode: {
      dark: { ...themes.dark, appBg: darkPalette['300'] },
      light: { ...themes.normal, appBg: lightPalette['50'] },
      darkClass: 'dark',
      classTarget: 'html',
      stylePreview: true,
    },
  },
};

export default preview;
