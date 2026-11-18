import { beforeEach, describe, expect, it } from 'vitest';
import { renderWithUser, screen } from '@defect-studio/test-utils/react';
import { queryClient } from '@/shared/api/queryClient';
import { apiClient } from '@/shared/api/apiClient';
import { useAuthStore } from '@/features/auth/model/authStore';
import { TEST_USER } from '@/test/fixtures';
import { TabNav } from './TabNav';

describe('TabNav logout', () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession();
    queryClient.clear();
  });

  it('routes SSO logout through central auth', () => {
    apiClient.setToken('service-token');
    useAuthStore.setState({
      status: 'authenticated', mode: 'sso', token: 'service-token', user: TEST_USER,
    });
    renderWithUser(<TabNav />);

    const link = screen.getByRole('link', { name: '로그아웃' });
    expect(new URL(link.getAttribute('href')!).pathname).toBe('/auth/logout');
  });
});
