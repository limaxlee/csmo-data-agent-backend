import type { ApiClient } from '@defect-studio/api-client';
import type { Thread } from './threads.dto';

export async function createThread(client: ApiClient, title?: string | null): Promise<Thread> {
  return client.request<Thread>('/api/threads', {
    method: 'POST',
    body: JSON.stringify({ title: title ?? null }),
  });
}
