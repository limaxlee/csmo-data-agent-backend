import type { ApiClient } from '@defect-studio/api-client';
import type { ThreadListResponse } from './threads.dto';

// The BFF returns only the threads belonging to the token's user.
export async function listThreads(client: ApiClient): Promise<ThreadListResponse> {
  return client.request<ThreadListResponse>('/api/threads', { method: 'GET' });
}