import type { ApiClient } from '@defect-studio/api-client';
import type { MessageListResponse } from './threads.dto';

// The messages saved for a thread, used when rebuilding a past conversation.
// Messages of a run in progress come from streamRunEvents instead.
export async function getMessages(
  client: ApiClient,
  threadId: string,
): Promise<MessageListResponse> {
  return client.request<MessageListResponse>(`/api/threads/${threadId}/messages`, {
    method: 'GET',
  });
}