import type { ApiClient } from '@defect-studio/api-client';
import type { PlanListResponse } from './plans.dto';

// The plans of one thread. Needed to reach results at all: those endpoints are
// keyed by `plan_id`, and nothing else the frontend fetches carries it.
export async function listPlans(client: ApiClient, threadId: string): Promise<PlanListResponse> {
  return client.request<PlanListResponse>(`/api/threads/${threadId}/plans`, { method: 'GET' });
}
