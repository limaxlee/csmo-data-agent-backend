// Request and response shapes for /api/threads/{id}/runs/*.

import type { RunLogStep } from './get-run-logs';

export interface Run {
  id: string;
  agent_run_id: string;
  status: string;
  cancel_requested?: boolean;
  message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface RunListResponse {
  runs: Run[];
  total: number;
}

export interface RunEvent {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface RunDetail extends Run {
  events: RunEvent[];
  log_line_counts?: Partial<Record<RunLogStep, number>>;
}