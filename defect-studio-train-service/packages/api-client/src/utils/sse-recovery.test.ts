import { afterEach, expect, it, vi } from 'vitest';
import { parseSseStream } from './parse-sse-stream';
import { openAgentStream } from './open-agent-stream';

const encode = (text: string) => new TextEncoder().encode(text);
async function collect(stream: ReturnType<typeof parseSseStream>) {
  const result = [];
  for await (const item of stream) result.push(item);
  return result;
}
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

it('keeps a two-hour stream alive through heartbeat comments without training progress', async () => {
  vi.useFakeTimers();
  const stream = new ReadableStream<Uint8Array>({ start(controller) {
    const tick = setInterval(() => controller.enqueue(encode(': heartbeat\n\n')), 10_000);
    setTimeout(() => {
      clearInterval(tick);
      controller.enqueue(encode('data: {"id":"end","type":"run.completed","payload":{}}\n\n'));
      controller.close();
    }, 2 * 60 * 60 * 1000);
  } });
  const result = collect(parseSseStream(stream));
  await vi.advanceTimersByTimeAsync(2 * 60 * 60 * 1000);
  expect((await result).map((e) => e.type)).toEqual(['run.completed']);
});

it('detects a silent transport rather than manufacturing a run.failed event', async () => {
  vi.useFakeTimers();
  const cancelled = vi.fn();
  const stream = new ReadableStream<Uint8Array>({ cancel: cancelled });
  const failed = expect(collect(parseSseStream(stream, undefined, 100))).rejects.toThrow('SSE connection idle');
  await vi.advanceTimersByTimeAsync(101);
  await failed;
  expect(cancelled).toHaveBeenCalled();
});

it('supports old Backends that ignore the cursor and replay all rows', async () => {
  const body = ['a', 'b', 'c'].map((id) => 'data: ' + JSON.stringify({ id, type: 'agent.status', payload: {} }) + '\n\n').join('');
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)));
  const result = await collect(openAgentStream({ url: 'http://fixture/events?after=b', token: 'fixture' }));
  expect(result.map((e) => e.id)).toEqual(['c']);
});

it('does not wait for an already skipped cursor when the Backend acknowledges incremental replay', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
    'data: {"id":"c","type":"agent.status","payload":{}}\n\n',
    { headers: { 'X-Event-Replay': 'cursor-v1' } },
  )));
  const result = await collect(openAgentStream({ url: 'http://fixture/events?after=b', token: 'fixture' }));
  expect(result.map((e) => e.id)).toEqual(['c']);
});

