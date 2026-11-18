import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { reloadAuth, setupAuthStoreTest, STORAGE_KEY } from '@/test/authStoreTestUtils';
import { useAuthStore } from './authStore';
setupMswServer();
describe('retired local password sessions', () => {
  beforeEach(setupAuthStoreTest);
  it.each(['invalid json', '{}', '{"refreshToken":"old-password-token"}'])('discards old tab tokens: %s', async (saved) => {
    let refreshCalls = 0;
    sessionStorage.setItem(STORAGE_KEY, saved);
    localStorage.setItem(STORAGE_KEY, saved);
    server.use(
      http.get('*/auth/session', () => HttpResponse.json({ authenticated: false, user: null })),
      http.post('*/api/auth/refresh', () => { refreshCalls++; return new HttpResponse(null, { status: 401 }); }),
    );
    await reloadAuth();
    expect(useAuthStore.getState().status).toBe('signed-out');
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(refreshCalls).toBe(0);
  });
});
