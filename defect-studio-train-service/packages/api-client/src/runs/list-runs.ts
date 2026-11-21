import type { ApiClient } from '@defect-studio/api-client';
import type { RunListResponse } from './runs.dto';

// Past runs, newest first. The BFF rejects a limit above 200; `total` is how many
// runs the thread has.
export async function listRuns(
  client: ApiClient,
  threadId: string,
  limit = 200,
): Promise<RunListResponse> {
  return client.request<RunListResponse>(`/api/threads/${threadId}/runs?limit=${limit}`, {
    method: 'GET',
  });
}
