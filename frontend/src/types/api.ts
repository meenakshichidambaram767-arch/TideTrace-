export type UserRole = 'researcher' | 'reviewer' | 'steward' | 'admin';

export interface UserAccount {
  user_id: number;
  username: string;
  full_name: string;
  role: UserRole;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserAccount;
}

export interface ApiErrorDetail {
  error: {
    code: string;
    message: string;
    details?: any;
    request_id?: string;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface ObservationSummary {
  observation_id: number;
  sensor_id: number;
  event_time: string;
  received_at: string;
  parameter_code: string;
  raw_value: number;
  unit: string;
  source_system: string;
  source_message_id: string;
  latest_quality_flag: string | null;
  current_accepted_value: number | null;
  current_decision: string | null;
  revision_count: number;
}

export interface QualityTestResultItem {
  test_result_id: number;
  rule_id: number;
  rule_name: string;
  rule_version: string;
  flag: 'pass' | 'suspect' | 'fail';
  details: Record<string, any>;
  tested_at: string;
}

export interface RevisionItem {
  revision_id: number;
  observation_id: number;
  revision_number: number;
  accepted_value: number;
  decision: 'accepted' | 'corrected' | 'rejected' | 'needs_review';
  reason: string;
  reviewer_id: number;
  reviewer_name?: string;
  calibration_id?: number | null;
  created_at: string;
}

export interface ObservationDetail {
  observation_id: number;
  sensor_id: number;
  event_time: string;
  received_at: string;
  parameter_code: string;
  raw_value: number;
  unit: string;
  source_system: string;
  source_message_id: string;
  latest_quality_flag: string | null;
  current_accepted_value: number | null;
  current_decision: string | null;
  revision_count: number;
  quality_tests: QualityTestResultItem[];
  revisions: RevisionItem[];
}

export interface QualityRule {
  rule_id: number;
  name: string;
  parameter_code: string;
  rule_type: string;
  thresholds: Record<string, any>;
  rule_version: string;
  is_active: boolean;
  created_at: string;
}

export interface IngestionRecordInput {
  sensor_id: number;
  event_time: string;
  parameter_code: string;
  raw_value: number;
  unit: string;
  source_message_id: string;
}

export interface IngestionBatchRequest {
  atomic?: boolean;
  records: Array<IngestionRecordInput & { source_system: string }>;
}

export interface IngestionBatchResponse {
  batch_id: string;
  status: string;
  received_count?: number;
  inserted_count?: number;
  ingested_count?: number;
  duplicate_count: number;
  rejected_count?: number;
  observation_ids?: number[];
  idempotency_replayed?: boolean;
  errors?: Array<{ index: number; source_message_id: string; error: string }>;
}

export interface AnalysisFilters {
  sensor_ids?: number[];
  parameter_code: string;
  from_time?: string;
  to_time?: string;
  revision_policy: 'latest_accepted_at_run' | 'raw_only';
}

export interface AnalysisCreateRequest {
  analysis_name: string;
  metric: 'mean' | 'min' | 'max' | 'count' | 'median' | 'standard_deviation';
  filters: AnalysisFilters;
  query_version: string;
  parameters?: Record<string, any>;
  save_input_manifest?: boolean;
}

export interface AnalysisResultItem {
  metric_name: string;
  metric_value: number;
  unit: string;
}

export interface ManifestItem {
  observation_id: number;
  revision_id: number | null;
  input_role: string;
}

export interface AnalysisResponse {
  analysis_id: number;
  analysis_name: string;
  metric: string;
  status: string;
  created_at: string;
  query_version: string;
  input_count: number;
  results: AnalysisResultItem[];
}

export interface AnalysisDetailResponse {
  analysis_id: number;
  analysis_name: string;
  metric: string;
  query_version: string;
  filters: Record<string, any>;
  parameters: Record<string, any>;
  status: string;
  creator_id: number;
  created_at: string;
  input_count: number;
  results: AnalysisResultItem[];
  manifest: ManifestItem[];
}

export interface ReplayResponse {
  analysis_id: number;
  replayed_at: string;
  original_results: AnalysisResultItem[];
  replayed_results: AnalysisResultItem[];
  matches: boolean;
  input_manifest_verified: boolean;
}

export interface AuditEventItem {
  audit_id: number;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id: number | null;
  event_time: string;
  reason: string | null;
  details: Record<string, any>;
}

export interface SystemHealth {
  status: string;
  database: string;
  timestamp: string;
}
