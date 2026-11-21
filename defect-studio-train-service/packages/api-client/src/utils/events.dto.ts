// SSE AgentEvent contract — mirrors the REAL events emitted by agent_service
// (remote_defectstudio/DefectAgent/src), verified against emit sites and against
// the run_events the BFF has actually stored.
//
// plan.created / plan.updated / artifact.created were once left out of this file
// as "declared backend-side but NEVER emitted". They are emitted: the agent sends
// the plan pair from commit_plan_node and artifact.created from
// defect_agent_service_adapter, and the BFF's run_events holds 15 / 23 / 2 of them
// respectively. The chat still shows none of them — see eventReducer — but they
// are typed here so that stays a choice rather than an accident.

export type AgentEventType =
  | 'run.started'
  | 'run.completed'
  | 'run.failed'
  | 'run.cancelled'
  | 'run.cancel_requested'
  | 'run.cancel_request_failed'
  | 'run.requires_input'
  | 'node.started'
  | 'node.completed'
  | 'assistant.delta'
  | 'assistant.completed'
  | 'system.message'
  | 'agent.status'
  | 'observation.status'
  | 'plan.created'
  | 'plan.updated'
  | 'plan.validation_failed'
  | 'artifact.created'
  | 'train.started'
  | 'train.log'
  | 'train.progress'
  | 'train.completed'
  | 'train.failed'
  | 'infer.started'
  | 'infer.log'
  | 'infer.progress'
  | 'infer.completed'
  | 'infer.failed';

// train/infer progress is a best-effort parsed bag: any field can be absent.
export interface ProgressPayload {
  /** Which half of the run this is. With `target`, it names one of the five steps. */
  service?: 'train' | 'infer';
  /** `regen` runs only after a defect `done` event with `regen_scheduled: true`. */
  target?: 'mask' | 'defect' | 'regen';
  stage?: string;
  status?: string;
  /** On infer events, a finished Korean sentence that already includes the counts. */
  message?: string;
  current?: number;
  total?: number;
  /**
   * How far the sub-task in `stage` has got — "Loading weights: 38%". Resets on
   * every new sub-task, so it belongs in the detail line, not on the step's bar.
   */
  percent?: number;
  /**
   * How far the whole step has got, 0-100. Train sends it on selected events
   * only: 2 (model_loading) → 4 (dataset) → 7…100 (training). Infer sends it on
   * every event, from 0 to 100 for each target. The step's progress bar reads it.
   */
  progress?: number;
  stage_current?: number;
  stage_total?: number;
  attempt_number?: number;
  /** Regen round, starting at 1. Only regen events have it. */
  round_index?: number;
  requested_count?: number;
  accepted_count?: number;
  placement_success_count?: number;
  /** Only on the defect `done` event. True when a regen step follows. */
  regen_scheduled?: boolean;
  unit?: string;
  task?: string;
  lr?: number;
  loss?: number;
  speed?: number;
  speed_unit?: string;
  component?: string;
  label?: string;
  image_count?: number;
  augmented?: boolean;
  checkpoint_path?: string;
  weights_path?: string;
}

// The plan the agent saved, as DefectPlan.model_dump(mode="json") sends it.
export interface DefectPlanPayload {
  size: 'small' | 'medium' | 'large';
  position: 'random' | 'center' | 'top' | 'left' | 'right' | 'bottom';
  generation_count: number;
  /** null while the agent is still collecting information. */
  is_full_image_defect_region: boolean | null;
  /**
   * Absent on plans written before the agent sent it — 8 of the 15 recorded ones
   * — and a restored conversation replays those, so this cannot be required.
   */
  execution?: {
    train_action: 'reuse' | 'train_if_missing' | 'retrain';
    generation_action: 'generation' | 'no_generation';
  };
  updated_at: string;
}

export interface LogPayload {
  level: string;
  lines: string[];
}

// Per-type payloads. Empty-payload events use Record<string, never> ({}).
export interface AgentEventPayloads {
  'run.started': Record<string, never>;
  'run.completed': Record<string, never>;
  'run.cancelled': Record<string, never>;
  'run.cancel_requested': { source: 'studio'; reason?: string };
  'run.cancel_request_failed': { source: 'studio'; code: string };
  'run.failed': { error: string };
  'run.requires_input': { message: string };
  'node.started': { node: string };
  'node.completed': { node: string };
  'assistant.delta': { text: string };
  'assistant.completed': Record<string, never>;
  'system.message': { text: string };
  'agent.status': { message: string };
  'observation.status': {
    status: 'live' | 'stale'; message: string;
    reason?: string; phase?: string; last_event_type?: string | null;
    last_event_at?: string; timeout_seconds?: number; elapsed_seconds?: number;
  };
  'plan.created': { plan_id: string; plan: DefectPlanPayload };
  'plan.updated': { plan_id: string; plan: DefectPlanPayload };
  'plan.validation_failed': { message: string };
  // Carries a message and nothing else — no plan_id, no file list. That is why
  // the BFF indexes generated images off infer.completed instead.
  'artifact.created': { message: string };
  'train.started': { message: string };
  'train.log': LogPayload;
  'train.progress': ProgressPayload;
  // plan_id is present, same as on train.failed — the agent sends
  // {"plan_id": ..., "message": ...} from defect_agent_service_adapter.
  'train.completed': { plan_id: string; message: string };
  'train.failed': { plan_id: string; message: string };
  'infer.started': { message: string };
  'infer.log': LogPayload;
  'infer.progress': ProgressPayload;
  'infer.completed': { plan_id: string; message: string };
  'infer.failed': { plan_id: string; message: string };
}

// Frame shape the FRONTEND receives. The internal agent_service emits a fuller
// envelope (event_id/thread_id/run_id/timestamp), but the BFF relay re-wraps each
// event as {id, type, payload} before forwarding — see run_controller.stream_events.
// `id` is the BFF's own run_events row, not the agent's event_id, and timestamp is
// NOT available to the client; thread_id/run_id are known from the request context,
// not the frame. Modelled against the BFF, not the agent.
interface AgentEventBase<T extends AgentEventType> {
  // The run_events row this event was read from. Every frame off the wire carries
  // one — agentStore.drive resumes a reconnected stream by it. Optional because the
  // store also folds events it makes up locally, such as the run.cancelled it raises
  // after a cancel request; those come from no row.
  id?: string;
  type: T;
  payload: AgentEventPayloads[T];
}

// Discriminated union over `type` — narrows payload automatically.
export type AgentEvent = {
  [T in AgentEventType]: AgentEventBase<T>;
}[AgentEventType];

