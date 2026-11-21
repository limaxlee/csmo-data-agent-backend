import type { AgentEvent, ApiClient } from '@defect-studio/api-client';

// Read a run's events as they happen. Not `async`: the callers use
// `for await (...)`, which needs an AsyncGenerator, not a Promise of one.
export function streamRunEvents(
  client: ApiClient,
  threadId: string,
  runId: string,
  signal?: AbortSignal,
  after?: string,
): AsyncGenerator<AgentEvent> {
  const cursor = after ? '?after=' + encodeURIComponent(after) : '';
  return client.openStream(`/api/threads/${threadId}/runs/${runId}/events${cursor}`, signal);
}
