import type { ApiClient } from '@defect-studio/api-client';
import type { RunDetail } from './runs.dto';

// One run and all of its events, oldest first.
export async function getRun(
  client: ApiClient,
  threadId: string,
  runId: string,
): Promise<RunDetail> {
  return client.request<RunDetail>(`/api/threads/${threadId}/runs/${runId}`, { method: 'GET' });
}
