import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { queryClient } from '@/shared/api/queryClient';
import { apiClient } from '@/shared/api/apiClient';
import { getMe } from '@defect-studio/api-client';
import { TEST_USER } from '@/test/fixtures';
import { reloadAuth, setupAuthStoreTest, STORAGE_KEY } from '@/test/authStoreTestUtils';
import { useAuthStore } from './authStore';
import { useActiveThreadStore } from '@/features/threads/model/activeThreadStore';

setupMswServer();

const SERVICE = { accessToken: 'service-abc', tokenType: 'Bearer', expiresAt: Math.floor(Date.now() / 1000) + 3600 };

describe('useAuthStore SSO sessions', () => {
  beforeEach(setupAuthStoreTest);
  afterEach(() => vi.unstubAllEnvs());

  it.each([true, false])('restores Thread navigation only for the verified previous owner: %s', async (sameOwner) => {
    localStorage.setItem('defect-studio-sso-owner', sameOwner ? TEST_USER.id : 'other-user');
    useActiveThreadStore.getState().setActiveThreadId('saved-thread');
    server.use(
      http.get('*/auth/session', () => HttpResponse.json({ authenticated: true, user: { id: 'central' } })),
      http.get('*/auth/token', () => HttpResponse.json(SERVICE)),
      http.get('*/api/auth/me', () => HttpResponse.json(TEST_USER)),
    );
    await useAuthStore.getState().bootstrap();
    expect(useActiveThreadStore.getState().activeThreadId).toBe(sameOwner ? 'saved-thread' : null);
    expect(localStorage.getItem('defect-studio-sso-owner')).toBe(TEST_USER.id);
  });

  it('bootstraps a linked central user with the service bearer', async () => {
    server.use(
      http.get('*/auth/session', () => HttpResponse.json({ authenticated: true, user: { id: 'miche-kim' } })),
      http.get('*/auth/token', () => HttpResponse.json(SERVICE)),
      http.get('*/api/auth/me', ({ request }) => {
        expect(request.headers.get('authorization')).toBe('Bearer service-abc');
        return HttpResponse.json(TEST_USER);
      }),
    );

    await useAuthStore.getState().bootstrap();

    expect(useAuthStore.getState()).toMatchObject({
      status: 'authenticated', mode: 'sso', user: TEST_USER, token: 'service-abc',
    });
    expect(localStorage.getItem('defect-studio-auth')).toBeNull();
  });

  it('restores SSO from its cookie across reloads and renews a rejected bearer', async () => {
    let tokenCalls = 0;
    server.use(
      http.get('*/auth/session', ({ request }) => {
        expect(request.credentials).toBe('include');
        return HttpResponse.json({ authenticated: true, user: { id: 'miche-kim' } });
      }),
      http.get('*/auth/token', ({ request }) => {
        expect(request.credentials).toBe('include');
        tokenCalls++;
        return HttpResponse.json({ ...SERVICE, accessToken: tokenCalls === 1 ? 'expired' : SERVICE.accessToken });
      }),
      http.get('*/api/auth/me', ({ request }) => request.headers.get('authorization') === 'Bearer expired'
        ? new HttpResponse(null, { status: 401 }) : HttpResponse.json(TEST_USER)),
    );

    await reloadAuth();
    await reloadAuth();

    expect(tokenCalls).toBe(3);
    expect(useAuthStore.getState()).toMatchObject({ status: 'authenticated', mode: 'sso', user: TEST_USER });
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('shows account linking when the backend recognizes an unlinked SSO identity', async () => {
    server.use(
      http.get('*/auth/session', () => HttpResponse.json({ authenticated: true, user: { id: 'miche-kim' } })),
      http.get('*/auth/token', () => HttpResponse.json(SERVICE)),
      http.get('*/api/auth/me', () =>
        HttpResponse.json({ code: 'sso_account_unlinked' }, { status: 409 })),
    );

    await useAuthStore.getState().bootstrap();

    expect(useAuthStore.getState()).toMatchObject({ status: 'unlinked', mode: 'sso', user: null });
  });

  it('deduplicates central token refresh before expiry', async () => {
    let calls = 0;
    server.use(
      http.get('*/auth/token', () => {
        calls++;
        return HttpResponse.json(SERVICE);
      }),
      http.get('*/api/auth/me', () => HttpResponse.json(TEST_USER)),
    );
    apiClient.setToken('old-service');
    useAuthStore.setState({
      status: 'authenticated', mode: 'sso', token: 'old-service',
      expiresAt: Math.floor(Date.now() / 1000) + 10, user: TEST_USER,
    });

    const [first, second] = await Promise.all([
      useAuthStore.getState().getBearer(),
      useAuthStore.getState().getBearer(),
    ]);
    expect([first, second]).toEqual(['service-abc', 'service-abc']);
    expect(calls).toBe(1);
  });

  it('clears prior-user data when a refreshed SSO token belongs to another account', async () => {
    const nextUser = { ...TEST_USER, id: 'second-user' };
    server.use(
      http.get('*/auth/token', () => HttpResponse.json(SERVICE)),
      http.get('*/api/auth/me', () => HttpResponse.json(nextUser)),
    );
    useAuthStore.setState({
      status: 'authenticated', mode: 'sso', token: 'old-service',
      expiresAt: Math.floor(Date.now() / 1000) + 10, user: TEST_USER,
    });
    queryClient.setQueryData(['threads'], [{ id: 'first-users-thread' }]);

    await expect(useAuthStore.getState().getBearer()).rejects.toThrow('Authentication changed');
    expect(useAuthStore.getState().user?.id).toBe('second-user');
    expect(queryClient.getQueryData(['threads'])).toBeUndefined();
  });

  it('moves to account setup if refreshed SSO belongs to an unlinked person', async () => {
    server.use(
      http.get('*/auth/token', () => HttpResponse.json(SERVICE)),
      http.get('*/api/auth/me', () =>
        HttpResponse.json({ code: 'sso_account_unlinked' }, { status: 409 })),
    );
    useAuthStore.setState({
      status: 'authenticated', mode: 'sso', token: 'old-service',
      expiresAt: Math.floor(Date.now() / 1000) + 10, user: TEST_USER,
    });
    queryClient.setQueryData(['threads'], [{ id: 'first-users-thread' }]);

    await expect(useAuthStore.getState().getBearer()).rejects.toMatchObject({ status: 409 });
    expect(useAuthStore.getState()).toMatchObject({ status: 'unlinked', user: null });
    expect(queryClient.getQueryData(['threads'])).toBeUndefined();
  });

  it('does not log out the new account when a rejected read discovers an SSO switch', async () => {
    const nextUser = { ...TEST_USER, id: 'second-user' };
    server.use(
      http.get('*/auth/token', () => HttpResponse.json(SERVICE)),
      http.get('*/api/auth/me', ({ request }) =>
        request.headers.get('authorization') === 'Bearer old-service'
          ? new HttpResponse(null, { status: 401 })
          : HttpResponse.json(nextUser)),
    );
    useAuthStore.setState({
      status: 'authenticated', mode: 'sso', token: 'old-service',
      expiresAt: Math.floor(Date.now() / 1000) + 3600, user: TEST_USER,
    });
    apiClient.setToken('old-service');
    apiClient.setTokenProvider((force) => useAuthStore.getState().getBearer(force));
    queryClient.setQueryData(['threads'], [{ id: 'first-users-thread' }]);

    await expect(getMe(apiClient)).rejects.toThrow('Authentication changed');
    expect(useAuthStore.getState()).toMatchObject({ status: 'authenticated', user: nextUser });
    expect(queryClient.getQueryData(['threads'])).toBeUndefined();
  });

  it('does not restore a token from a refresh that finishes after logout', async () => {
    let respond = () => {};
    let started = () => {};
    const gate = new Promise<void>((resolve) => { respond = resolve; });
    const requestStarted = new Promise<void>((resolve) => { started = resolve; });
    server.use(http.get('*/auth/token', async () => {
      started();
      await gate;
      return HttpResponse.json(SERVICE);
    }));
    apiClient.setToken('old-service');
    useAuthStore.setState({
      status: 'authenticated', mode: 'sso', token: 'old-service',
      expiresAt: Math.floor(Date.now() / 1000) + 10, user: TEST_USER,
    });
    const pending = useAuthStore.getState().getBearer();
    await requestStarted;
    useAuthStore.getState().clearSession();
    respond();

    await expect(pending).rejects.toThrow('Authentication changed');
    expect(useAuthStore.getState().status).toBe('signed-out');
    expect(apiClient.getToken()).toBeNull();
  });
});

