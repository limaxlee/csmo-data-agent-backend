import type { ApiClient } from '@defect-studio/api-client';

export interface CancelRunResponse {
  status: string;
  cancel_requested?: boolean;
  cancel_error?: 'agent_cancel_rejected' | 'agent_cancel_unconfirmed';
}

export async function cancelRun(
  client: ApiClient,
  threadId: string,
  runId: string,
  reason = 'user_cancelled',
): Promise<CancelRunResponse> {
  return client.request<CancelRunResponse>(`/api/threads/${threadId}/runs/${runId}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}
