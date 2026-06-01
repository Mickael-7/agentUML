export interface DiagramInfo {
  diagram_id: string;
  diagram_type: string;
  name: string;
  status: "generating" | "completed" | "failed";
  error?: string;
  puml_text?: string | null;
  image_url?: string | null;
  sub_status?: string;
  attempt?: number;
  attempt_max?: number;
  critic_score?: number;
  critic_round?: number;
  critic_round_max?: number;
}

export interface JobStatus {
  job_id: string;
  status: "idle" | "queued" | "quality_gate" | "extracting_rules" | "partitioning" | "generating" | "completed" | "completed_with_errors" | "failed";
  diagrams: DiagramInfo[];
  created_at?: string;
  completed_at?: string | null;
  quality_report?: string | null;
  cross_validation_report?: string | null;
  error?: string;
}

export interface ConfigResponse {
  provider: string;
  model: string;
  temperature: number;
  available_providers: string[];
  provider_models: Record<string, string[]>;
}

export interface HistoryJob {
  job_id: string;
  status: string;
  created_at: string;
  diagrams: DiagramInfo[];
}
