import { beforeEach, describe, expect, it, vi } from 'vitest';
import { clearSsoRedirectAttempt, markSsoRedirectAttempt, tryAutomaticSsoLogin } from './ssoRedirect';

describe('automatic SSO navigation', () => {
  beforeEach(() => sessionStorage.clear());
  it('automatically enters central login once and preserves the full return URL', () => {
    const navigate = vi.fn();
    expect(tryAutomaticSsoLogin(navigate)).toBe(true);
    const url = new URL(navigate.mock.calls[0][0]);
    expect(url.pathname).toBe('/auth/login');
    expect(url.searchParams.get('callbackUrl')).toBe(window.location.href);
    expect(tryAutomaticSsoLogin(navigate)).toBe(false);
    expect(navigate).toHaveBeenCalledTimes(1);
  });
  it('does not loop when the SSO callback returns without authentication', () => {
    markSsoRedirectAttempt();
    expect(tryAutomaticSsoLogin(vi.fn())).toBe(false);
    clearSsoRedirectAttempt();
    expect(tryAutomaticSsoLogin(vi.fn())).toBe(true);
  });
  it('does not immediately sign back in during an explicit logout', () => {
    markSsoRedirectAttempt();
    const navigate = vi.fn();
    expect(tryAutomaticSsoLogin(navigate)).toBe(false);
    expect(navigate).not.toHaveBeenCalled();
  });
});

