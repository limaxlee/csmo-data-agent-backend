import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server, setupMswServer } from '@defect-studio/test-utils/msw-server';
import { collect, frame, makeSseEvent, streamOf } from '@defect-studio/test-utils/sse';
import { ApiClient, openAgentStream, parseSseStream, type AgentEvent } from '.';

setupMswServer();

const STREAM_URL = 'http://bff.test/api/runs/stream';

// The BFF forwards each event as just {type, payload} — no envelope.
const makeEvent = makeSseEvent<AgentEvent>();

describe('parseSseStream', () => {
  it('yields typed events and reassembles a frame split across chunks', async () => {
    const started = makeEvent('run.started', {});
    const delta = makeEvent('assistant.delta', { text: 'hello' });
    const raw = frame(started) + frame(delta);
    // Split mid-frame so the parser must buffer across reads.
    const events = await collect(parseSseStream(streamOf([raw.slice(0, 30), raw.slice(30)])));

    expect(events).toHaveLength(2);
    expect(events[0]).toMatchObject({ type: 'run.started' });
    expect(events[1]).toMatchObject({ type: 'assistant.delta', payload: { text: 'hello' } });
  });

  it('skips keep-alive comments and the [DONE] sentinel', async () => {
    const chunk = `: keep-alive\n\n${frame(makeEvent('run.completed', {}))}data: [DONE]\n\n`;
    const events = await collect(parseSseStream(streamOf([chunk])));

    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('run.completed');
  });

  it('drops a malformed frame without ending the stream', async () => {
    const chunk = `data: {not json}\n\n${frame(makeEvent('run.completed', {}))}`;
    const events = await collect(parseSseStream(streamOf([chunk])));

    expect(events.map((event) => event.type)).toEqual(['run.completed']);
  });
});

describe('openAgentStream', () => {
  it('sends the Bearer token and streams typed events', async () => {
    let authHeader = '';
    server.use(
      http.post(STREAM_URL, ({ request }) => {
        authHeader = request.headers.get('authorization') ?? '';
        const body =
          frame(makeEvent('train.started', { message: '학습 시작' })) +
          frame(makeEvent('train.completed', { plan_id: '0', message: '학습 완료' }));
        return new HttpResponse(streamOf([body]), {
          headers: { 'Content-Type': 'text/event-stream' },
        });
      }),
    );

    const events = await collect(
      openAgentStream({ url: STREAM_URL, token: 'tok-123', body: { thread_id: 'thread-1' } }),
    );

    expect(authHeader).toBe('Bearer tok-123');
    expect(events.map((event) => event.type)).toEqual(['train.started', 'train.completed']);
  });

  it('throws on a non-ok response', async () => {
    server.use(http.get(STREAM_URL, () => new HttpResponse(null, { status: 401 })));

    await expect(collect(openAgentStream({ url: STREAM_URL, token: 'bad' }))).rejects.toThrow(/401/);
  });
});

describe('ApiClient stream recovery', () => {
  it('refreshes the bearer before consuming a stream rejected with 401', async () => {
    const headers: string[] = [];
    server.use(http.get(STREAM_URL, ({ request }) => {
      headers.push(request.headers.get('authorization') ?? '');
      if (headers.length === 1) return new HttpResponse(null, { status: 401 });
      return new HttpResponse(streamOf([frame(makeEvent('run.started', {}))]), {
        headers: { 'Content-Type': 'text/event-stream' },
      });
    }));
    const client = new ApiClient({ baseUrl: 'http://bff.test' });
    client.setTokenProvider(async (force) => force ? 'fresh' : 'expired');

    const events = await collect(client.openStream('/api/runs/stream'));
    expect(events).toHaveLength(1);
    expect(headers).toEqual(['Bearer expired', 'Bearer fresh']);
  });
});
