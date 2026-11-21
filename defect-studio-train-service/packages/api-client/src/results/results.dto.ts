// Response shapes for the BFF result endpoints.

export interface ResultArtifact {
  id: string;
  plan_id: string;
  filename: string;
  file_type: string;
  file_size: number | null;
  created_at: string;
  // True when the BFF has a mask for this image. Older BFF builds leave it out; treat that as false.
  has_mask?: boolean;
}

// What the plan asked the agent for. The agent decides the keys, so every one
// is optional — an older plan may carry fewer of them.
export interface PlanContent {
  generation_count?: number;
  position?: string;
  size?: string;
  is_full_image_defect_region?: boolean;
  [key: string]: unknown;
}

// One generation: the plan's settings, when it ran, and the images it produced.
export interface PlanResults {
  plan_id: string;
  content: PlanContent | null;
  status: string | null;
  // Null when the run that produced these images is gone; the images remain.
  started_at: string | null;
  completed_at: string | null;
  artifacts: ResultArtifact[];
  total: number;
}

export interface ResultListResponse {
  // Filled unless the request asked for grouping.
  artifacts: ResultArtifact[];
  total: number;
  // Filled only when the request asked for grouping.
  plans: PlanResults[];
}
