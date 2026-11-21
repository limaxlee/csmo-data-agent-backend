import type { ApiClient } from '@defect-studio/api-client';

// Send the user's answer to a run that stopped to ask a question.
export async function submitInput(
  client: ApiClient,
  threadId: string,
  runId: string,
  message: string,
): Promise<void> {
  await client.request<unknown>(`/api/threads/${threadId}/runs/${runId}/input`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}