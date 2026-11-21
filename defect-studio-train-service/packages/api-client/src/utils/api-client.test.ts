import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { ApiClient, ApiError } from '.';

// The shared transport only. Each endpoint is tested next to its own request
// functions under ../auth, ../threads, ../runs and ../train-data.

setupMswServer();

const BASE = 'http://bff.test';
const PATH = '/api/ping';

describe('ApiClient.request', () => {
  it('attaches the Bearer token on an authenticated request', async () => {
    let sentAuth = '';
    server.use(
      http.get(`${BASE}${PATH}`, ({ request }) => {
        sentAuth = request.headers.get('authorization') ?? '';
        return HttpResponse.json({ ok: true });
      }),
    );

    const client = new ApiClient({ baseUrl: BASE, token: 'access-abc' });
    await client.request(PATH, { method: 'GET' });

    expect(sentAuth).toBe('Bearer access-abc');
  });

  it('sends no Authorization header when auth is false', async () => {
    let sentAuth: string | null = 'unset';
    server.use(
      http.get(`${BASE}${PATH}`, ({ request }) => {
        sentAuth = request.headers.get('authorization');
        return HttpResponse.json({ ok: true });
      }),
    );

    const client = new ApiClient({ baseUrl: BASE, token: 'access-abc' });
    await client.request(PATH, { method: 'GET' }, false);

    expect(sentAuth).toBeNull();
  });

  it('refuses an authenticated request with no token', async () => {
    const client = new ApiClient({ baseUrl: BASE });
    await expect(client.request(PATH, { method: 'GET' })).rejects.toThrow(/Not authenticated/);
  });

  it('sets a JSON Content-Type for a JSON body but not for FormData', async () => {
    const seen: (string | null)[] = [];
    server.use(
      http.post(`${BASE}${PATH}`, ({ request }) => {
        seen.push(request.headers.get('content-type'));
        return HttpResponse.json({ ok: true });
      }),
    );

    const client = new ApiClient({ baseUrl: BASE, token: 'access-abc' });
    await client.request(PATH, { method: 'POST', body: JSON.stringify({ a: 1 }) });
    await client.request(PATH, { method: 'POST', body: new FormData() });

    expect(seen[0]).toBe('application/json');
    expect(seen[1]).not.toBe('application/json'); // fetch sets the multipart boundary
  });

  it('returns undefined for a 204 no-content response', async () => {
    server.use(http.delete(`${BASE}${PATH}`, () => new HttpResponse(null, { status: 204 })));

    const client = new ApiClient({ baseUrl: BASE, token: 'access-abc' });
    await expect(client.request(PATH, { method: 'DELETE' })).resolves.toBeUndefined();
  });

  it('throws ApiError carrying the status on a non-ok response', async () => {
    server.use(
      http.get(`${BASE}${PATH}`, () => HttpResponse.json({ detail: 'nope' }, { status: 500 })),
    );

    const client = new ApiClient({ baseUrl: BASE, token: 'access-abc' });
    const failing = client.request(PATH, { method: 'GET' });

    await expect(failing).rejects.toBeInstanceOf(ApiError);
    await expect(failing).rejects.toMatchObject({ name: 'ApiError', status: 500 });
  });
});

describe('ApiClient onUnauthorized', () => {
  it('fires when an authenticated request is rejected with 401', async () => {
    const status = 401;
    server.use(http.get(`${BASE}${PATH}`, () => new HttpResponse(null, { status })));

    const client = new ApiClient({ baseUrl: BASE, token: 'stale' });
    const 
    client.

    await expect(client.request(PATH, { method: 'GET' })).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it('keeps the session on 403 permission errors', async () => {
    server.use(http.get(`${BASE}${PATH}`, () => new HttpResponse(null, { status: 403 })));
    const client = new ApiClient({ baseUrl: BASE, token: 'valid' });
    const onUnauthorized = vi.fn();
    client.onUnauthorized = onUnauthorized;
    await expect(client.request(PATH)).rejects.toMatchObject({ status: 403 });
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it('does NOT fire on an unauthenticated request (bad credentials, not a stale session)', async () => {
    server.use(http.get(`${BASE}${PATH}`, () => new HttpResponse(null, { status: 401 })));

    const client = new ApiClient({ baseUrl: BASE });
    const onUnauthorized = vi.fn();
    client.onUnauthorized = onUnauthorized;

    await expect(
      client.request(PATH, { method: 'GET' }, false),
    ).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});

describe('ApiClient token recovery', () => {
  it('refreshes a rejected GET once and uses the new bearer', async () => {
    const headers: string[] = [];
    server.use(http.get(`${BASE}${PATH}`, ({ request }) => {
      headers.push(request.headers.get('authorization') ?? '');
      return headers.length === 1
        ? new HttpResponse(null, { status: 401 })
        : HttpResponse.json({ ok: true });
    }));
    const client = new ApiClient({ baseUrl: BASE });
    const provider = vi.fn(async (force?: boolean) => force ? 'fresh' : 'expired');
    client.setTokenProvider(provider);
    await expect(client.request(PATH)).resolves.toEqual({ ok: true });
    expect(headers).toEqual(['Bearer expired', 'Bearer fresh']);
    expect(provider).toHaveBeenCalledWith(true);
  });

  it('stops after one failed GET retry and reports an invalid session', async () => {
    let reads = 0;
    server.use(http.get(`${BASE}${PATH}`, () => {
      reads++;
      return new HttpResponse(null, { status: 401 });
    }));
    const client = new ApiClient({ baseUrl: BASE });
    client.setTokenProvider(async (force) => force ? 'fresh' : 'expired');
    const onUnauthorized = vi.fn();
    client.onUnauthorized = onUnauthorized;
    await expect(client.request(PATH)).rejects.toMatchObject({ status: 401 });
    expect(reads).toBe(2);
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it('does not log out when a refresh request fails for a temporary network reason', async () => {
    server.use(http.get(`${BASE}${PATH}`, () => new HttpResponse(null, { status: 401 })));
    const client = new ApiClient({ baseUrl: BASE });
    client.setTokenProvider(async (force) => {
      if (force) throw new Error('Central auth unavailable');
      return 'expired';
    });
    const onUnauthorized = vi.fn();
    client.onUnauthorized = onUnauthorized;
    await expect(client.request(PATH)).rejects.toThrow('Central auth unavailable');
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it('refreshes after a rejected write without replaying it', async () => {
    let writes = 0;
    server.use(http.post(`${BASE}${PATH}`, () => {
      writes++;
      return new HttpResponse(null, { status: 401 });
    }));
    const client = new ApiClient({ baseUrl: BASE });
    const provider = vi.fn(async (force?: boolean) => force ? 'fresh' : 'expired');
    client.setTokenProvider(provider);
    await expect(client.request(PATH, { method: 'POST' })).rejects.toMatchObject({ status: 401 });
    expect(writes).toBe(1);
    expect(provider).toHaveBeenCalledWith(true);
  });
});

describe('ApiClient.requestBlob', () => {
  it('returns the raw bytes with the Bearer token attached', async () => {
    let sentAuth = '';
    server.use(
      http.get(`${BASE}${PATH}`, ({ request }) => {
        sentAuth = request.headers.get('authorization') ?? '';
        return new HttpResponse(new Uint8Array([137, 80, 78, 71]), {
          headers: { 'Content-Type': 'image/png' },
        });
      }),
    );

    const client = new ApiClient({ baseUrl: BASE, token: 'access-abc' });
    const blob = await client.requestBlob(PATH);

    expect(sentAuth).toBe('Bearer access-abc');
    expect(blob.type).toBe('image/png');
    expect(blob.size).toBe(4);
  });

  it('refuses with no token', async () => {
    const client = new ApiClient({ baseUrl: BASE });
    await expect(client.requestBlob(PATH)).rejects.toThrow(/Not authenticated/);
  });
});

