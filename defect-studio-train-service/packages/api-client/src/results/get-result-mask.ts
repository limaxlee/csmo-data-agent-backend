import type { ApiClient } from '@defect-studio/api-client';

// Download the mask of one generated image as a Blob. The mask is a PNG: white
// where the defect is, black elsewhere. The BFF answers 404 when the image has no mask.
export async function getResultMask(
  client: ApiClient,
  threadId: string,
  planId: string,
  filename: string,
): Promise<Blob> {
  return client.requestBlob(
    `/api/threads/${threadId}/plans/${planId}/results/${encodeURIComponent(filename)}/mask`,
  );
}