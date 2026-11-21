import type { AgentEvent } from './events.dto';
import { parseSseStream } from './parse-sse-stream';
import { ApiError } from './api-error';

export interface OpenAgentStreamOptions {
  url: string;
  token: string;
  body?: unknown; // JSON body → POST; omit → GET
  signal?: AbortSignal;
}

// Open an authenticated agent stream and yield each event as it arrives.
export async function* openAgentStream({
  url,
  token,
  body,
  signal,
}: OpenAgentStreamOptions): AsyncGenerator<AgentEvent> {
  // NOTE: `signal` is intentionally NOT passed to fetch — cancellation is driven
  // through the body reader in parseSseStream (see there). This avoids the
  // cross-realm "signal is not an AbortSignal" failure under jsdom + Node fetch.
  const response = await fetch(url, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(response.status, response.statusText, await response.text(), response.headers.get('Retry-After'));
  }
  if (!response.body) {
    throw new Error('Agent stream response has no body');
  }
  // Rolling upgrade: old Backends replay everything and ignore ?after=.
  // New Backends explicitly acknowledge incremental replay.
  const after = new URL(url, 'http://localhost').searchParams.get('after');
  let skip = !!after && response.headers.get('X-Event-Replay') !== 'cursor-v1';
  for await (const event of parseSseStream(response.body, signal)) {
    if (skip) {
      if (event.id === after) skip = false;
      continue;
    }
    yield event;
  }
}
