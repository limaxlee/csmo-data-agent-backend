// Response shapes for /api/threads/{threadId}/plans.

export interface Plan {
  id: string;
  /** The agent's own id for the plan within its thread — "0", "1", … — and the
   *  segment the result endpoints are keyed by. Not the same as `id`. */
  plan_id: string;
  content: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PlanListResponse {
  plans: Plan[];
  total: number;
}