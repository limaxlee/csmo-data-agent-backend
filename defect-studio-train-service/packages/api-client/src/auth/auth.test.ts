import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { ApiClient, ApiError } from '@defect-studio/api-client';
import { getMe, login, type TokenResponse, type User } from '.';

setupMswServer();

const BASE = 'http://bff.test';

const makeUser = (): User => ({
  id: 'user-1',
  email: 'a@b.com',
  name: '홍길동',
  role: 'user',
  created_at: '2026-07-30T00:00:00Z',
});

const makeToken = (): TokenResponse => ({
  access_token: 'access-abc',
  refresh_token: 'refresh-xyz',
  token_type: 'bearer',
  user: makeUser(),
});

describe('login', () => {
  it('sends no Authorization header and does not replace the active token', async () => {
    let sentAuth: string | null = 'unset';
    server.use(
      http.post(`${BASE}/api/auth/login`, ({ request }) => {
        sentAuth = request.headers.get('authorization');
        return HttpResponse.json(makeToken());
      }),
    );

    const client = new ApiClient({ baseUrl: BASE, token: 'service-token' });
    const result = await login(client, { email: 'a@b.com', password: 'secret123' });

    expect(sentAuth).toBeNull();
    expect(result.access_token).toBe('access-abc');
    expect(client.getToken()).toBe('service-token');
  });

  it('throws ApiError on bad credentials and does not log the user out', async () => {
    server.use(
      http.post(`${BASE}/api/auth/login`, () =>
        HttpResponse.json({ detail: 'bad creds' }, { status: 401 }),
      ),
    );

    const client = new ApiClient({ baseUrl: BASE });
    const onUnauthorized = vi.fn();
    client.onUnauthorized = onUnauthorized;

    const failing = login(client, { email: 'a@b.com', password: 'nope' });

    await expect(failing).rejects.toBeInstanceOf(ApiError);
    await expect(failing).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});

describe('getMe', () => {
  it('returns the signed-in user for the stored token', async () => {
    let sentAuth = '';
    server.use(
      http.get(`${BASE}/api/auth/me`, ({ request }) => {
        sentAuth = request.headers.get('authorization') ?? '';
        return HttpResponse.json(makeUser());
      }),
    );

    const client = new ApiClient({ baseUrl: BASE, token: 'access-abc' });
    const user = await getMe(client);

    expect(sentAuth).toBe('Bearer access-abc');
    expect(user.email).toBe('a@b.com');
  });

  it('refuses when nobody is signed in', async () => {
    const client = new ApiClient({ baseUrl: BASE });
    await expect(getMe(client)).rejects.toThrow(/Not authenticated/);
  });
});
