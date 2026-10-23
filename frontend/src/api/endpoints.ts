import { apiClient } from './client';
import {
  SystemHealth,
  TokenResponse,
  PaginatedResponse,
  ObservationSummary,
  ObservationDetail,
  QualityRule,
  QualityTestResultItem,
  RevisionItem,
  IngestionBatchRequest,
  IngestionBatchResponse,
  AnalysisCreateRequest,
  AnalysisResponse,
  AnalysisDetailResponse,
  ReplayResponse,
  AuditEventItem,
} from '../types/api';

export const api = {
  // Health
  getHealth: () => apiClient<SystemHealth>('/health'),

  // Auth
  login: (username: string, password: string) =>
    apiClient<TokenResponse>('/auth/token', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  // Ingestion
  submitBatch: (payload: IngestionBatchRequest, idempotencyKey: string) =>
    apiClient<IngestionBatchResponse>('/ingestion/batches', {
      method: 'POST',
      body: JSON.stringify(payload),
      customHeaders: {
        'Idempotency-Key': idempotencyKey,
      },
    }),

  // Observations
  getObservations: (params: {
    sensor_id?: number;
    parameter_code?: string;
    from_time?: string;
    to_time?: string;
    quality_flag?: string;
    page?: number;
    page_size?: number;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.sensor_id !== undefined) query.set('sensor_id', String(params.sensor_id));
    if (params.parameter_code) query.set('parameter_code', params.parameter_code);
    if (params.from_time) query.set('from_time', params.from_time);
    if (params.to_time) query.set('to_time', params.to_time);
    if (params.quality_flag) query.set('quality_flag', params.quality_flag);
    if (params.page) query.set('page', String(params.page));
    if (params.page_size) query.set('page_size', String(params.page_size));
    return apiClient<PaginatedResponse<ObservationSummary>>(`/observations?${query.toString()}`);
  },

  getObservationDetail: (observationId: number) =>
    apiClient<ObservationDetail>(`/observations/${observationId}`),

  // Quality Engine
  runQualityTests: (
    observationId: number,
    payload: { rule_ids?: number[]; include_temporal_checks?: boolean } = {}
  ) =>
    apiClient<{ observation_id: number; overall_flag: string; results: QualityTestResultItem[] }>(
      `/observations/${observationId}/quality-tests`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),

  getQualityRules: () => apiClient<QualityRule[]>('/quality-rules'),

  // Revisions
  getRevisions: (observationId: number) =>
    apiClient<RevisionItem[]>(`/observations/${observationId}/revisions`),

  submitRevision: (
    observationId: number,
    payload: {
      accepted_value: number;
      decision: string;
      reason: string;
      calibration_id?: number | null;
    },
    ifMatchRevision: number
  ) =>
    apiClient<RevisionItem>(`/observations/${observationId}/revisions`, {
      method: 'POST',
      body: JSON.stringify(payload),
      customHeaders: {
        'If-Match-Revision': String(ifMatchRevision),
      },
    }),

  // Analyses
  createAnalysis: (payload: AnalysisCreateRequest) =>
    apiClient<AnalysisResponse>('/analyses', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getAnalyses: (page = 1, pageSize = 50) =>
    apiClient<PaginatedResponse<AnalysisResponse>>(`/analyses?page=${page}&page_size=${pageSize}`),

  getAnalysisDetail: (analysisId: number) =>
    apiClient<AnalysisDetailResponse>(`/analyses/${analysisId}`),

  replayAnalysis: (analysisId: number) =>
    apiClient<ReplayResponse>(`/analyses/${analysisId}/replay`, {
      method: 'POST',
    }),

  // Audit Events
  getAuditEvents: (params: {
    entity_type?: string;
    entity_id?: string;
    from_time?: string;
    to_time?: string;
    page?: number;
    page_size?: number;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.entity_type) query.set('entity_type', params.entity_type);
    if (params.entity_id) query.set('entity_id', params.entity_id);
    if (params.from_time) query.set('from_time', params.from_time);
    if (params.to_time) query.set('to_time', params.to_time);
    if (params.page) query.set('page', String(params.page));
    if (params.page_size) query.set('page_size', String(params.page_size));
    return apiClient<PaginatedResponse<AuditEventItem>>(`/audit-events?${query.toString()}`);
  },
};
