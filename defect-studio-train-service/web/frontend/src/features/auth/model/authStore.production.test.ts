import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { waitFor } from '@defect-studio/test-utils/react';
import { setupAuthStoreTest } from '@/test/authStoreTestUtils';
import { TEST_USER } from '@/test/fixtures';
import { useActiveThreadStore } from '@/features/threads/model/activeThreadStore';
import { apiClient } from '@/shared/api/apiClient';
import { useAuthStore } from './authStore';
import { markSsoRedirectAttempt, tryAutomaticSsoLogin } from './ssoRedirect';

setupMswServer();
const SERVICE = { accessToken: 'production-service', tokenType: 'Bearer', expiresAt: Date.now() / 1000 + 3600 };
describe('production SSO account preparation', () => {
  beforeEach(() => {
    setupAuthStoreTest();
    vi.stubEnv('VITE_DEPLOYMENT_ENV', 'production');
    server.use(
      http.get('*/auth/session', () => HttpResponse.json({ authenticated: true, user: { id: 'central' } })),
      http.get('*/auth/token', () => HttpResponse.json(SERVICE)),
    );
  });
  afterEach(() => vi.unstubAllEnvs());
  it('automatically provisions a verified new user without account selection', async () => {
    const provision = vi.fn(({ request }: { request: Request }) => {
      expect(request.headers.get('authorization')).toBe('Bearer production-service');
      return HttpResponse.json(TEST_USER);
    });
    server.use(
      http.get('*/api/auth/me', () => HttpResponse.json({ code: 'sso_account_unlinked' }, { status: 409 })),
      http.post('*/api/auth/sso/provision', provision),
    );
    markSsoRedirectAttempt();
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState()).toMatchObject({ status: 'authenticated', mode: 'sso', user: TEST_USER });
    expect(provision).toHaveBeenCalledTimes(1);
    expect(tryAutomaticSsoLogin(vi.fn())).toBe(true);
    expect(localStorage.getItem('defect-studio-auth')).toBeNull();
  });
  it('reuses an existing SSO account without provisioning it again', async () => {
    const provision = vi.fn();
    server.use(http.get('*/api/auth/me', () => HttpResponse.json(TEST_USER)), http.post('*/api/auth/sso/provision', provision));
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().status).toBe('authenticated');
    expect(provision).not.toHaveBeenCalled();
  });
  it('does not restore a session when logout occurs during automatic provisioning', async () => {
    let release!: () => void;
    const response = new Promise<void>((resolve) => { release = resolve; });
    const provision = vi.fn(async () => { await response; return HttpResponse.json(TEST_USER); });
    server.use(
      http.get('*/api/auth/me', () => HttpResponse.json({ code: 'sso_account_unlinked' }, { status: 409 })),
      http.post('*/api/auth/sso/provision', provision),
    );
    const pending = useAuthStore.getState().bootstrap();
    await waitFor(() => expect(provision).toHaveBeenCalledTimes(1));
    useAuthStore.getState().clearSession();
    release();
    await pending;
    expect(useAuthStore.getState()).toMatchObject({ status: 'signed-out', token: null, user: null });
  });
  it('reports provisioning conflicts without attaching an existing account', async () => {
    server.use(
      http.get('*/api/auth/me', () => HttpResponse.json({ code: 'sso_account_unlinked' }, { status: 409 })),
      http.post('*/api/auth/sso/provision', () => HttpResponse.json({ code: 'sso_account_conflict' }, { status: 409 })),
    );
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState()).toMatchObject({ status: 'error', user: null });
  });
  it('prepares a newly switched SSO identity while clearing the previous user data', async () => {
    const user = { ...TEST_USER, id: 'new-user' };
    server.use(
      http.get('*/api/auth/me', () => HttpResponse.json({ code: 'sso_account_unlinked' }, { status: 409 })),
      http.post('*/api/auth/sso/provision', () => HttpResponse.json(user)),
    );
    useAuthStore.setState({ status: 'authenticated', mode: 'sso', token: 'old', user: TEST_USER });
    useActiveThreadStore.getState().setActiveThreadId('old-thread');
    apiClient.setToken('old');
    await expect(useAuthStore.getState().getBearer(true)).rejects.toThrow('Authentication changed');
    expect(useActiveThreadStore.getState().activeThreadId).toBeNull();
    expect(useAuthStore.getState().user?.id).toBe('new-user');
  });
});
