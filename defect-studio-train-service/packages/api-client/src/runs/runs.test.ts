import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { ApiClient } from '@defect-studio/api-client';
import { cancelRun, getRun, getRunLogs, listRuns, startRun, submitInput, type Run } from '.';

setupMswServer();

const BASE = 'http://bff.test';
const authedClient = () => new ApiClient({ baseUrl: BASE, token: 'access-abc' });

const makeRun = (): Run => ({
  id: 'run-1',
  agent_run_id: 'agent-run-1',
  status: 'running',
  message: '안녕',
  started_at: '2026-07-31T00:00:00Z',
  completed_at: null,
});

describe('startRun', () => {
  it('preserves an explicit request key for idempotent retries', async () => {
    let body: unknown;
    server.use(http.post(`${BASE}/api/threads/thread-1/runs`, async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(makeRun(), { status: 201 });
    }));
    await startRun(authedClient(), 'thread-1', '생성', 'request-key');
    expect(body).toEqual({ message: '생성', request_key: 'request-key' });
  });
  it('posts the message and returns the run id used by the events URL', async () => {
    let body: unknown;
    server.use(
      http.post(`${BASE}/api/threads/thread-1/runs`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(makeRun(), { status: 201 });
      }),
    );

    const run = await startRun(authedClient(), 'thread-1', '안녕');

    expect(body).toEqual({ message: '안녕' });
    expect(run.id).toBe('run-1'); // not agent_run_id
  });
});

describe('listRuns', () => {
  it('defaults the limit to 200, the highest the BFF accepts', async () => {
    let url = '';
    server.use(
      http.get(`${BASE}/api/threads/thread-1/runs`, ({ request }) => {
        url = request.url;
        return HttpResponse.json({ runs: [makeRun()], total: 1 });
      }),
    );

    const result = await listRuns(authedClient(), 'thread-1');

    expect(url).toContain('limit=200');
    expect(result.total).toBe(1);
  });
});

describe('getRun', () => {
  it('gets a bounded log page using the independent durable cursor', async () => {
    server.use(http.get(`${BASE}/api/threads/thread-1/runs/run-1/logs`, ({ request }) => {
      const url = new URL(request.url);
      expect(url.searchParams.get('after_sequence')).toBe('650');
      expect(url.searchParams.get('limit')).toBe('200');
      expect(request.headers.get('Authorization')).toBe('Bearer access-abc');
      return HttpResponse.json({ events: [], next_sequence: 650, has_more: false });
    }));
    expect(await getRunLogs(authedClient(), 'thread-1', 'run-1', 650)).toEqual({ events: [], next_sequence: 650, has_more: false });
  });
  it('returns the run together with its events', async () => {
    server.use(
      http.get(`${BASE}/api/threads/thread-1/runs/run-1`, () =>
        HttpResponse.json({
          ...makeRun(),
          events: [
            {
              id: 'ev-1',
              event_type: 'assistant.delta',
              payload: { text: '안녕' },
              created_at: '2026-07-31T00:00:01Z',
            },
          ],
        }),
      ),
    );

    const detail = await getRun(authedClient(), 'thread-1', 'run-1');

    expect(detail.events[0].event_type).toBe('assistant.delta');
  });
});

describe('submitInput', () => {
  it('posts the answer that resumes an interrupted run', async () => {
    let body: unknown;
    server.use(
      http.post(`${BASE}/api/threads/thread-1/runs/run-1/input`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ status: 'resumed' });
      }),
    );

    await submitInput(authedClient(), 'thread-1', 'run-1', '네');

    expect(body).toEqual({ message: '네' });
  });
});

describe('cancelRun', () => {
  it('defaults the reason to user_cancelled', async () => {
    let body: unknown;
    server.use(
      http.post(`${BASE}/api/threads/thread-1/runs/run-1/cancel`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ status: 'cancelled' });
      }),
    );

    await cancelRun(authedClient(), 'thread-1', 'run-1');

    expect(body).toEqual({ reason: 'user_cancelled' });
  });
});

