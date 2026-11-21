import type { ApiClient } from '@defect-studio/api-client';
import type { Thread } from './threads.dto';

// Title is the only editable field on a thread. The server requires 1-255 characters
// and does not trim, so callers must trim before calling.
//
// The returned thread always carries message_count: 0 — the rename handler does not
// count messages. Merging the whole response into a cached thread resets that count.
export async function renameThread(
  client: ApiClient,
  threadId: string,
  title: string,
): Promise<Thread> {
  return client.request<Thread>(`/api/threads/${threadId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
}
