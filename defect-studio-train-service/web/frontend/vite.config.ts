import path from 'node:path';
import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { stagingAuthProxy } from './dev/stagingAuthProxy';

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, __dirname, ''), ...process.env };
  // The browser does not send web-auth's SameSite=Lax cookie from localhost to
  // another host, so the dev server adds a session cookie copied from that host.
  const cookie = env.STUDIO_AUTH_COOKIE;
  return {
    plugins: [react()],
    define: {
      'import.meta.env.VITE_AGENT_API_URL': JSON.stringify(env.VITE_AGENT_API_URL || '/studio-backend'),
    },
    // Load proxy targets and deployment paths from the selected .env profile.
    base: env.VITE_BASE_PATH || '/',
    resolve: {
      alias: { '@': path.resolve(__dirname, './src') },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['@defect-studio/test-utils/setup'],
      css: true,
      pool: 'threads',
      maxWorkers: 1,
      coverage: {
        provider: 'v8',
        include: ['src/**/*.{ts,tsx}'],
        exclude: ['src/**/*.stories.tsx', 'src/**/*.test.{ts,tsx}', 'src/mocks/**'],
      },
    },
    server: {
      port: Number(env.STUDIO_DEV_PORT || 3000),
      strictPort: true,
      host: '127.0.0.1',
      // Opt-in local Compose routing; static production builds are unaffected.
      proxy: env.STUDIO_API_PROXY_TARGET ? {
        '^/studio-backend/api/threads/[^/]+/runs/[^/]+/events(?:\\?|$)': {
          target: env.STUDIO_API_PROXY_TARGET,
          changeOrigin: true,
          rewrite: (url) => url.replace(/^\/studio-backend/, ''),
          proxyTimeout: 120_000,
          timeout: 120_000,
        },
        ...(env.STUDIO_AUTH_PROXY_TARGET ? env.STUDIO_LOCAL_AUTH_PROXY === 'true'
          ? stagingAuthProxy(env.STUDIO_AUTH_PROXY_TARGET) : {
          '/auth': {
            target: env.STUDIO_AUTH_PROXY_TARGET,
            changeOrigin: true,
            rewrite: (url: string) => url.replace(/^\/auth/, ''),
            headers: cookie ? { cookie } : undefined,
          },
        } : {}),
        '/studio-backend': {
          target: env.STUDIO_API_PROXY_TARGET,
          changeOrigin: true,
          rewrite: (url) => url.replace(/^\/studio-backend/, ''),
          proxyTimeout: 15000,
          timeout: 15000,
        },
      } : undefined,
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
    },
  };
});

