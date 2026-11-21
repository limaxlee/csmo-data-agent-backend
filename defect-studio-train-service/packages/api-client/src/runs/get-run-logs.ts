import type { ApiClient } from '../utils/api-client';

export type RunLogStep = 'train/mask' | 'train/defect' | 'infer/mask' | 'infer/defect';

export interface RunLogPage {
  events: { id: string; sequence: number; event_type: string; lines: string[]; step?: RunLogStep | null }[];
  next_sequence: number;
  has_more: boolean;
}

export function getRunLogs(client: ApiClient, threadId: string, runId: string,
  afterSequence = 0, signal?: AbortSignal): Promise<RunLogPage> {
  return client.request(`/api/threads/${threadId}/runs/${runId}/logs?after_sequence=${afterSequence}&limit=200`, { signal });
}