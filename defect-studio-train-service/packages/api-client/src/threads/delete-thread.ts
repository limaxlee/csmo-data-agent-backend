import type { ApiClient } from '@defect-studio/api-client';

export async function deleteThread(client: ApiClient, threadId: string): Promise<void> {
  await client.request<void>(`/api/threads/${threadId}`, { method: 'DELETE' });
}
