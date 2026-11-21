import type { ApiClient } from '@defect-studio/api-client';
import type { Run } from './runs.dto';

// Start a run. The returned `id` goes in the events, input and cancel URLs.
// It is not `agent_run_id`.
export async function startRun(
  client: ApiClient,
  threadId: string,
  message: string,
  requestKey?: string,
): Promise<Run> {
  return client.request<Run>(`/api/threads/${threadId}/runs`, {
    method: 'POST',
    body: JSON.stringify({ message, ...(requestKey ? { request_key: requestKey } : {}) }),
  });
}
