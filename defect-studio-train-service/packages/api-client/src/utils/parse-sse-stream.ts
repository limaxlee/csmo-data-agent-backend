// Parses the `data:` frames of a text/event-stream by hand. The BFF requires an
// `Authorization: Bearer` header, which the native EventSource API cannot send,
// so openAgentStream fetches the stream and this file reads its body.

import type { AgentEvent } from './events.dto';

// One SSE frame → one typed event. Comments (`:` keep-alives), non-data frames,
// the `[DONE]` sentinel, and malformed JSON all return null so a single bad
// frame never kills the stream.
const parseFrame = (frame: string): AgentEvent | null => {
  const dataLines: string[] = [];
  for (const line of frame.split(/\r?\n/)) {
    if (line.startsWith(':')) continue; // keep-alive comment
    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''));
    }
    // event:/id:/retry: fields are ignored — the real type lives in the JSON payload
  }
  if (dataLines.length === 0) return null;
  const data = dataLines.join('\n');
  if (data === '[DONE]') return null;
  try {
    return JSON.parse(data) as AgentEvent;
  } catch {
    return null; // skip a malformed frame, keep reading
  }
};

// Turn a raw byte stream into typed events. Frames are separated by a blank
// line; a frame split across two chunks is held in `buffer` until complete.
export async function* parseSseStream(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
  idleTimeoutMs = 90_000,
): AsyncGenerator<AgentEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  // Cancelling the reader both unblocks a pending read() and aborts the underlying
  // fetch body — so cancellation works without handing the signal to fetch itself
  // (which fails across realms, e.g. jsdom AbortSignal vs a Node fetch).
  const onAbort = () => void reader.cancel().catch(() => {});
  if (signal?.aborted) onAbort();
  signal?.addEventListener('abort', onAbort);
  try {
    while (true) {
      if (signal?.aborted) return;
      let timer: ReturnType<typeof setTimeout> | undefined;
      const timeout = new Promise<never>((_, reject) => {
        timer = setTimeout(() => {
          reject(new Error('SSE connection idle'));
          void reader.cancel().catch(() => {});
        }, idleTimeoutMs);
      });
      const { done, value } = await Promise.race([reader.read(), timeout]).finally(() => clearTimeout(timer));
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? ''; // last piece may be an incomplete frame
      for (const frame of frames) {
        const event = parseFrame(frame);
        if (event) yield event;
      }
    }
    const tail = parseFrame(buffer); // flush any final frame with no trailing blank line
    if (tail) yield tail;
  } finally {
    signal?.removeEventListener('abort', onAbort);
    void reader.cancel().catch(() => {});
    try {
      reader.releaseLock();
    } catch {
      // reader may already be released after cancel() — ignore
    }
  }
}
