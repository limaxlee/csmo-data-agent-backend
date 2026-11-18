import type { IncomingMessage } from 'node:http';
import type { ProxyOptions } from 'vite';

function localOrigin(request: Pick<IncomingMessage, 'headers'>): URL | undefined {
  try {
    const origin = new URL(`http://${request.headers.host}`);
    return ['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname) ? origin : undefined;
  } catch { return undefined; }
}

// Only adapts staging's explicitly enabled dev-login flow. Real ADFS callbacks
// still belong to the registered staging URL and are not made localhost-safe.
export function adaptDevLoginResponse(
  headers: { location?: string; 'set-cookie'?: string[] },
  status: number | undefined,
  request: Pick<IncomingMessage, 'headers' | 'url'>,
): void {
  const origin = localOrigin(request);
  if (!origin || !request.url) return;
  const url = new URL(request.url, origin);
  if (url.pathname !== '/dev-login' || status !== 302 && status !== 307) return;
  // The actual staging server must first authorize the identity and issue cookies.
  if (!headers['set-cookie']?.some(cookie => cookie.startsWith('dice.dev-loginid='))) return;
  const redirect = url.searchParams.get('redirect');
  if (!redirect) return;
  let target: URL;
  try { target = new URL(redirect, origin); } catch { return; }
  if (target.origin !== origin.origin) return;
  headers.location = target.href;
  headers['set-cookie'] = headers['set-cookie'].map(cookie =>
    /^(dice\.dev-loginid|dice\.dev-role)=/.test(cookie)
      ? cookie.replace(/;\s*Secure(?=;|$)/gi, '').replace(/;\s*Domain=[^;]*/gi, '')
      : cookie);
}

export function stagingAuthProxy(target: string): Record<string, ProxyOptions> {
  const proxy = (stripAuth = false): ProxyOptions => ({
    target,
    changeOrigin: true,
    ...(stripAuth ? { rewrite: (url: string) => url.replace(/^\/auth/, '') } : {}),
    configure(server) {
      server.on('proxyRes', (response, request) => {
        adaptDevLoginResponse(response.headers, response.statusCode, request);
      });
    },
  });
  return {
    '/auth': proxy(true),
    '/_next': proxy(),
    '/api/auth': proxy(),
    '/dev-login': proxy(),
    '/error': proxy(),
    '/logout-success': proxy(),
  };
}

