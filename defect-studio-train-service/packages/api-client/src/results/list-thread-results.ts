import type { ApiClient } from '@defect-studio/api-client';
import type { ResultListResponse } from './results.dto';

// Every generated image of a thread, across all its plans. Preferred over
// listResults for the gallery: that one needs a plan_id, which made the listing
// depend on the plan rows existing — and those are written by different agent
// events than the artifacts themselves.
//
// `groupBy: 'plan'` fills `plans` instead of `artifacts`, each entry carrying the
// plan's settings and the times its generation ran — the gallery needs those to
// label a group, and they live in tables the artifact rows only point at.
export async function listThreadResults(
  client: ApiClient,
  threadId: string,
  options: { groupBy?: 'plan' } = {},
): Promise<ResultListResponse> {
  const query = options.groupBy ? `?group_by=${options.groupBy}` : '';
  return client.request<ResultListResponse>(`/api/threads/${threadId}/results${query}`, {
    method: 'GET',
  });
}
