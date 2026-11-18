import { StrictMode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@defect-studio/test-utils/react';
import { Providers } from '@/app/Providers';
import { useAuthStore } from '../model/authStore';
import * as redirect from '../model/ssoRedirect';
import { LoginScreen } from './LoginScreen';

describe('production SSO entry', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_DEPLOYMENT_ENV', 'production');
    useAuthStore.setState({ status: 'signed-out', error: null });
  });
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });
  it('starts SSO without a click and only once under StrictMode', async () => {
    const navigate = vi.spyOn(redirect, 'tryAutomaticSsoLogin').mockReturnValue(true);
    render(<StrictMode><Providers><LoginScreen /></Providers></StrictMode>);
    await screen.findByRole('status');
    expect(navigate).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('Samsung SSO로 로그인')).toBeNull();
  });
  it.each(['error', 'unlinked'] as const)('shows retry instead of legacy account choices for %s', (status) => {
    const navigate = vi.spyOn(redirect, 'tryAutomaticSsoLogin').mockReturnValue(false);
    useAuthStore.setState({ status });
    render(<Providers><LoginScreen /></Providers>);
    expect(screen.getByRole('link', { name: 'SSO 로그인 다시 시도' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: '기존 계정 연결' })).toBeNull();
    expect(screen.queryByText('새 DefectAgent 계정 만들기')).toBeNull();
    expect(navigate).not.toHaveBeenCalled();
  });
  it('allows explicit retry when automatic navigation was already attempted', async () => {
    vi.spyOn(redirect, 'tryAutomaticSsoLogin').mockReturnValue(false);
    render(<Providers><LoginScreen /></Providers>);
    await waitFor(() => expect(screen.getByRole('link', { name: 'SSO 로그인 다시 시도' })).toBeTruthy());
  });
});
