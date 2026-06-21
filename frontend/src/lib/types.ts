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

export interface QualityDimension {
  highlights: string[];
  issues: string[];
}

export interface QualityReport {
  clarity: QualityDimension;
  completeness: QualityDimension;
  consistency: QualityDimension;
  verifiability: QualityDimension;
  summary: string;
  suggestions: string[];
}

export interface QualityResult {
  is_valid: boolean;
  report: QualityReport;
}

export type Verdict = "correct" | "incorrect";

export interface UseCaseChecks {
  has_requirement: boolean;
  has_use_case_context: boolean;
  symbology_correct: boolean | null;
}

export interface UseCaseDocResult {
  name: string;
  verdict: Verdict;
  checks: UseCaseChecks;
  errors: string[];
  justification: string;
  correction: string;
  summary?: string;
  expected_verdict?: Verdict | null;
  matches_expected?: boolean | null;
}

export interface UseCaseEvalSummary {
  total: number;
  evaluated: number;
  correct: number;
  incorrect: number;
  accuracy: number | null;
}

export interface UseCaseEvalResult {
  summary: UseCaseEvalSummary;
  documents: UseCaseDocResult[];
}

export interface UseCaseDocInput {
  name: string;
  text: string;
  expected_verdict: Verdict | null;
}

export interface FullAnalysisSummary {
  use_cases_found: number;
  correct: number;
  incorrect: number;
}

export interface FullAnalysisResult {
  requirements: QualityResult;
  use_cases: UseCaseDocResult[];
  summary: FullAnalysisSummary;
}
