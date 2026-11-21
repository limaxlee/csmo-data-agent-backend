import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { ApiClient } from '@defect-studio/api-client';
import {
  createThread,
  deleteThread,
  getMessages,
  listThreads,
  renameThread,
  type Message,
  type Thread,
} from '.';

setupMswServer();

const BASE = 'http://bff.test';
const authedClient = () => new ApiClient({ baseUrl: BASE, token: 'access-abc' });

const makeThread = (): Thread => ({
  id: 'thread-1',
  agent_thread_id: 'agent-thread-1',
  title: '결함 학습',
  status: 'active',
  created_at: '2026-07-31T00:00:00Z',
  updated_at: '2026-07-31T00:00:00Z',
  message_count: 2,
});

const makeMessage = (): Message => ({
  id: 'msg-1',
  role: 'user',
  content: '안녕',
  metadata: null,
  created_at: '2026-07-31T00:00:00Z',
});

describe('listThreads', () => {
  it('returns the thread list and the total', async () => {
    server.use(
      http.get(`${BASE}/api/threads`, () =>
        HttpResponse.json({ threads: [makeThread()], total: 1 }),
      ),
    );

    const result = await listThreads(authedClient());

    expect(result.threads[0].id).toBe('thread-1');
    expect(result.total).toBe(1);
  });
});

describe('createThread', () => {
  it('sends the title in the JSON body', async () => {
    let body: unknown;
    server.use(
      http.post(`${BASE}/api/threads`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(makeThread());
      }),
    );

    const thread = await createThread(authedClient(), '결함 학습');

    expect(body).toEqual({ title: '결함 학습' });
    expect(thread.id).toBe('thread-1');
  });

  it('sends a null title when none is given', async () => {
    let body: unknown;
    server.use(
      http.post(`${BASE}/api/threads`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(makeThread());
      }),
    );

    await createThread(authedClient());

    expect(body).toEqual({ title: null });
  });
});

describe('renameThread', () => {
  it('PATCHes the new title and returns the updated thread', async () => {
    let method: string | undefined;
    let body: unknown;
    server.use(
      http.patch(`${BASE}/api/threads/thread-1`, async ({ request }) => {
        method = request.method;
        body = await request.json();
        return HttpResponse.json({ ...makeThread(), title: '새 제목' });
      }),
    );

    const thread = await renameThread(authedClient(), 'thread-1', '새 제목');

    expect(method).toBe('PATCH');
    expect(body).toEqual({ title: '새 제목' });
    expect(thread.title).toBe('새 제목');
  });

  it('throws ApiError with the status when the server rejects the title', async () => {
    server.use(
      http.patch(`${BASE}/api/threads/thread-1`, () =>
        HttpResponse.json({ detail: [{ type: 'string_too_short' }] }, { status: 422 }),
      ),
    );

    await expect(renameThread(authedClient(), 'thread-1', '')).rejects.toMatchObject({
      name: 'ApiError',
      status: 422,
    });
  });
});

describe('deleteThread', () => {
  it('tolerates a 204 no-content response', async () => {
    server.use(
      http.delete(`${BASE}/api/threads/thread-1`, () => new HttpResponse(null, { status: 204 })),
    );

    await expect(deleteThread(authedClient(), 'thread-1')).resolves.toBeUndefined();
  });
});

describe('getMessages', () => {
  it("returns a thread's saved messages", async () => {
    server.use(
      http.get(`${BASE}/api/threads/thread-1/messages`, () =>
        HttpResponse.json({ messages: [makeMessage()], total: 1 }),
      ),
    );

    const result = await getMessages(authedClient(), 'thread-1');

    expect(result.messages[0].content).toBe('안녕');
  });
});
