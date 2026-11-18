import { describe, expect, it } from 'vitest';
import { centralLoginUrl, centralLogoutUrl } from './centralAuth';
describe('central authentication routes', () => {
  it('preserves the full return URL in the SSO callback', () => {
    const callback = 'https://example.test/defect/?thread=one';
    const url = new URL(centralLoginUrl(callback));
    expect(url.pathname).toBe('/auth/login');
    expect(url.searchParams.get('callbackUrl')).toBe(callback);
  });
  it('logs out through central auth', () => {
    expect(new URL(centralLogoutUrl()).pathname).toBe('/auth/logout');
  });
});
