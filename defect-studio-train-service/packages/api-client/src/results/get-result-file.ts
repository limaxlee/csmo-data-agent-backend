import type { ApiClient } from '@defect-studio/api-client';

// Download one generated image as a Blob. The endpoint needs the token, so an
// <img src> cannot read it, and request() only decodes JSON.
export async function getResultFile(
  client: ApiClient,
  threadId: string,
  planId: string,
  filename: string,
): Promise<Blob> {
  return client.requestBlob(
    `/api/threads/${threadId}/plans/${planId}/results/${encodeURIComponent(filename)}`,
  );
}
