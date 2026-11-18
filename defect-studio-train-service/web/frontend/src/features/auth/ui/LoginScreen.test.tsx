import { http, HttpResponse } from 'msw';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { renderWithUser, screen, waitFor } from '@defect-studio/test-utils/react';
import { Providers } from '@/app/Providers';
import { apiClient } from '@/shared/api/apiClient';
import { queryClient } from '@/shared/api/queryClient';
import { TEST_USER } from '@/test/fixtures';
import { useAuthStore } from '@/features/auth/model/authStore';
import { LoginScreen } from './LoginScreen';

setupMswServer();

const TOKEN_RESPONSE = {
  access_token: 'local-access',
  refresh_token: 'local-refresh',
  token_type: 'bearer',
  user: TEST_USER,
};

const renderLogin = () => renderWithUser(
  <Providers><LoginScreen /></Providers>,
);

describe('LoginScreen', () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    queryClient.clear();
  });

  afterEach(() => vi.unstubAllEnvs());

  it('uses central login with the full return URL and has no registration action', () => {
    renderLogin();
    const link = screen.getByRole('link', { name: 'Samsung SSO로 로그인' });
    const url = new URL(link.getAttribute('href')!);
    expect(url.pathname).toBe('/auth/login');
    expect(url.searchParams.get('callbackUrl')).toBe(window.location.href);
    expect(screen.queryByText(/회원가입|register/i)).toBeNull();
    expect(screen.queryByText(/임시 비밀번호 로그인/)).toBeNull();
  });

  it('links an existing account without replacing the SSO bearer', async () => {
    let linkAuth = '';
    let linkBody: unknown;
    server.use(
      http.post('*/api/auth/login', () => HttpResponse.json(TOKEN_RESPONSE)),
      http.post('*/api/auth/sso/link', async ({ request }) => {
        linkAuth = request.headers.get('authorization') ?? '';
        linkBody = await request.json();
        return HttpResponse.json(TEST_USER);
      }),
    );
    apiClient.setToken('service-access');
    useAuthStore.setState({
      status: 'unlinked', mode: 'sso', token: 'service-access',
      expiresAt: Math.floor(Date.now() / 1000) + 3600, user: null,
    });

    const { user } = renderLogin();
    await user.click(screen.getByRole('button', { name: '기존 계정 연결' }));
    await user.type(screen.getByLabelText('기존 계정 이메일'), 'dev@example.com');
    await user.type(screen.getByLabelText('기존 계정 비밀번호'), 'pw');
    await user.click(screen.getByRole('button', { name: '계정 연결' }));

    await waitFor(() => expect(useAuthStore.getState().status).toBe('authenticated'));
    expect(linkAuth).toBe('Bearer local-access');
    expect(linkBody).toEqual({ service_token: 'service-access' });
    expect(apiClient.getToken()).toBe('service-access');
    expect(useAuthStore.getState().user?.id).toBe(TEST_USER.id);
  });

  it('provisions a new SSO-only account', async () => {
    let auth = '';
    server.use(http.post('*/api/auth/sso/provision', ({ request }) => {
      auth = request.headers.get('authorization') ?? '';
      return HttpResponse.json(TEST_USER);
    }));
    apiClient.setToken('service-access');
    useAuthStore.setState({
      status: 'unlinked', mode: 'sso', token: 'service-access',
      expiresAt: Math.floor(Date.now() / 1000) + 3600, user: null,
    });

    const { user } = renderLogin();
    await user.click(screen.getByRole('button', { name: '새 DefectAgent 계정 만들기' }));

    await waitFor(() => expect(useAuthStore.getState().status).toBe('authenticated'));
    expect(auth).toBe('Bearer service-access');
  });

  it('explains an email mismatch and stays on the linking screen', async () => {
    server.use(
      http.post('*/api/auth/login', () => HttpResponse.json(TOKEN_RESPONSE)),
      http.post('*/api/auth/sso/link', () =>
        HttpResponse.json({ code: 'sso_email_mismatch' }, { status: 409 })),
    );
    apiClient.setToken('service-access');
    useAuthStore.setState({
      status: 'unlinked', mode: 'sso', token: 'service-access',
      expiresAt: Math.floor(Date.now() / 1000) + 3600, user: null,
    });

    const { user } = renderLogin();
    await user.click(screen.getByRole('button', { name: '기존 계정 연결' }));
    await user.type(screen.getByLabelText('기존 계정 이메일'), 'dev@example.com');
    await user.type(screen.getByLabelText('기존 계정 비밀번호'), 'pw');
    await user.click(screen.getByRole('button', { name: '계정 연결' }));

    expect((await screen.findByRole('alert')).textContent).toContain('이메일이 다릅니다');
    expect(useAuthStore.getState().status).toBe('unlinked');
  });
});

