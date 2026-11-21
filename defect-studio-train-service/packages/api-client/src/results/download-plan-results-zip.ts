import type { ApiClient } from '@defect-studio/api-client';

// Download every image artifact of a plan as a single ZIP file. The endpoint
// streams the zip server-side, so the client receives one blob regardless of
// how many images the plan produced.
export async function downloadPlanResultsZip(
  client: ApiClient,
  threadId: string,
  planId: string,
): Promise<Blob> {
  return client.requestBlob(
    `/api/threads/${threadId}/plans/${planId}/results/download`,
  );
}