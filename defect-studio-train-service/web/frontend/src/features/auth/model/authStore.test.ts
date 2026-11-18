import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { queryClient } from '@/shared/api/queryClient';
import { apiClient } from '@/shared/api/apiClient';
import { TEST_USER } from '@/test/fixtures';
import { SESSION, setTestSsoSession, setupAuthStoreTest, STORAGE_KEY } from '@/test/authStoreTestUtils';
import { useAuthStore } from './authStore';

describe('useAuthStore session lifecycle', () => {
  beforeEach(setupAuthStoreTest);
  afterEach(() => vi.unstubAllEnvs());

  it('keeps the SSO bearer in memory and clears it on logout', () => {
    setTestSsoSession(SESSION);
    expect(useAuthStore.getState()).toMatchObject({
      status: 'authenticated', mode: 'sso', token: 'access-abc', user: TEST_USER,
    });
    expect(apiClient.getToken()).toBe('access-abc');
    expect(localStorage.getItem('defect-studio-auth')).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();

    useAuthStore.getState().clearSession();
    expect(useAuthStore.getState().status).toBe('signed-out');
    expect(apiClient.getToken()).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('discards legacy password refresh tokens on SSO login', () => {
    sessionStorage.setItem(STORAGE_KEY, 'legacy-refresh');
    useAuthStore.getState().setSsoUser(TEST_USER);
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('removes cached user data when the identity changes', () => {
    setTestSsoSession(SESSION);
    queryClient.setQueryData(['threads'], [{ id: 'first-users-thread' }]);
    setTestSsoSession({
      ...SESSION, user: { ...TEST_USER, id: 'another-user' },
    });
    expect(queryClient.getQueryData(['threads'])).toBeUndefined();
  });
});
