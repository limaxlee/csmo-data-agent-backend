import type { ApiClient } from '@defect-studio/api-client';
import type { ResultListResponse } from './results.dto';

// The images a plan's generation produced. The BFF indexes them when the agent
// reports infer.completed, so a plan whose generation has not finished answers
// with an empty list rather than an error.
export async function listResults(
  client: ApiClient,
  threadId: string,
  planId: string,
): Promise<ResultListResponse> {
  return client.request<ResultListResponse>(
    `/api/threads/${threadId}/plans/${planId}/results`,
    { method: 'GET' },
  );
}
