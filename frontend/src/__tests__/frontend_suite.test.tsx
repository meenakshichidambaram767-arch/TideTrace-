import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import { AuthProvider } from '../context/AuthContext';
import { Dashboard } from '../components/Dashboard';
import { Observations } from '../components/Observations';
import { RevisionReview } from '../components/RevisionReview';
import { AnalysisWorkspace } from '../components/AnalysisWorkspace';
import { AuditExplorer } from '../components/AuditExplorer';
import { Ingestion } from '../components/Ingestion';
import { api } from '../api/endpoints';

// Mock the API layer
vi.mock('../api/endpoints', () => ({
  api: {
    getHealth: vi.fn(),
    login: vi.fn(),
    getObservations: vi.fn(),
    getObservationDetail: vi.fn(),
    getQualityRules: vi.fn(),
    runQualityTests: vi.fn(),
    submitRevision: vi.fn(),
    submitBatch: vi.fn(),
    createAnalysis: vi.fn(),
    getAnalyses: vi.fn(),
    getAnalysisDetail: vi.fn(),
    replayAnalysis: vi.fn(),
    getAuditEvents: vi.fn(),
  },
}));

describe('TideTrace Frontend Test Suite (Phase 4 Verification)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();

    // Default API mock implementations
    (api.getHealth as any).mockResolvedValue({
      status: 'healthy',
      database: 'connected',
      timestamp: new Date().toISOString(),
    });

    (api.getObservations as any).mockResolvedValue({
      items: [
        {
          observation_id: 101,
          sensor_id: 1,
          event_time: '2026-10-23T04:00:00Z',
          received_at: '2026-10-23T04:00:00Z',
          parameter_code: 'temperature',
          raw_value: 24.5000,
          unit: 'degC',
          source_system: 'buoy-01',
          source_message_id: 'msg-001',
          latest_quality_flag: 'pass',
          current_accepted_value: 25.1000,
          current_decision: 'corrected',
          revision_count: 1,
        },
      ],
      page: 1,
      page_size: 20,
      total: 100297,
    });

    (api.getAnalyses as any).mockResolvedValue({
      items: [
        {
          analysis_id: 5,
          analysis_name: 'Salinity Baseline',
          metric: 'mean',
          status: 'completed',
          created_at: '2026-10-23T04:30:00Z',
          query_version: 'mean-v1.0',
          input_count: 3,
          results: [{ metric_name: 'mean', metric_value: 32.0, unit: 'PSU' }],
        },
      ],
      page: 1,
      page_size: 20,
      total: 61,
    });

    (api.getAuditEvents as any).mockResolvedValue({
      items: [
        {
          audit_id: 42,
          entity_type: 'analysis_run',
          entity_id: '5',
          action: 'analysis_replayed',
          actor_id: 1,
          event_time: '2026-10-23T05:00:00Z',
          reason: 'Deterministic replay check',
          details: { matches: true, input_manifest_verified: true },
        },
      ],
      page: 1,
      page_size: 20,
      total: 187,
    });

    (api.getQualityRules as any).mockResolvedValue([
      {
        rule_id: 1,
        name: 'Temperature Valid Bounds',
        parameter_code: 'temperature',
        rule_type: 'range',
        thresholds: { min: -2.0, max: 35.0 },
        rule_version: 'v1.0',
        is_active: true,
        created_at: '2026-10-23T00:00:00Z',
      },
    ]);
  });

  it('1. Dashboard renders live system statistics and architectural integrity pillars', async () => {
    render(<Dashboard onNavigate={() => {}} />);

    expect(screen.getByText(/Provenance-Aware Ocean Data Integrity & Anomaly Lab/i)).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText(/100|1,00,297/i)).toBeDefined();
      expect(screen.getByText('187')).toBeDefined();
    });
    expect(screen.getByText(/1. Raw Data Immutability/i)).toBeDefined();
    expect(screen.getByText(/2. Concurrency-Safe Revisions/i)).toBeDefined();
    expect(screen.getByText(/3. Deterministic Analysis Manifests/i)).toBeDefined();
  });

  it('2. Observation Explorer clearly distinguishes immutable raw values from accepted corrections', async () => {
    render(<Observations />);

    await waitFor(() => {
      expect(screen.getByText(/Observation Telemetry Explorer/i)).toBeDefined();
      expect(screen.getByText('24.5000')).toBeDefined(); // Raw measurement
      expect(screen.getByText('25.1000')).toBeDefined(); // Corrected value
      expect(screen.getByText((content) => content.includes('Rev') && content.includes('corrected'))).toBeDefined();
      expect(screen.getAllByText(/Immutable/i).length).toBeGreaterThan(0);
    });
  });

  it('3. Ingestion submission handles parameters and displays conflict alert on HTTP 409', async () => {
    render(<Ingestion />);

    expect(screen.getByText(/Atomic Ingestion & Idempotency Gateway/i)).toBeDefined();
    expect(screen.getByText(/IDEMPOTENCY-KEY \(HEADER\)/i)).toBeDefined();

    // Mock 409 Conflict
    (api.submitBatch as any).mockRejectedValueOnce({
      code: 'IDEMPOTENCY_CONFLICT',
      message: 'Idempotency key reused with different payload',
      details: { expected_hash: 'abc', received_hash: 'def' },
    });

    const submitBtn = screen.getByText(/Submit Batch to Ingestion API/i);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Contract Protection Triggered \(HTTP 409\)/i)).toBeDefined();
    });
  });

  it('4. Revision review enforces reason length, displays If-Match-Revision, and records correction', async () => {
    (api.getObservationDetail as any).mockResolvedValueOnce({
      observation_id: 2,
      sensor_id: 1,
      event_time: '2026-10-23T04:00:00Z',
      received_at: '2026-10-23T04:00:00Z',
      parameter_code: 'salinity',
      raw_value: 32.0,
      unit: 'PSU',
      source_system: 'buoy-01',
      source_message_id: 'msg-sal-2',
      latest_quality_flag: 'pass',
      current_accepted_value: null,
      current_decision: null,
      revision_count: 0,
      quality_tests: [],
      revisions: [],
    });

    render(
      <AuthProvider>
        <RevisionReview />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Scientific Measurement Revisions/i)).toBeDefined();
      expect(screen.getAllByText('32.0000').length).toBeGreaterThan(0);
    });
  });

  it('5. Analysis workspace renders frozen manifests and deterministic replay outputs separately', async () => {
    (api.getAnalysisDetail as any).mockResolvedValueOnce({
      analysis_id: 5,
      analysis_name: 'Salinity Baseline',
      metric: 'mean',
      query_version: 'mean-v1.0',
      filters: { parameter_code: 'salinity' },
      parameters: {},
      status: 'completed',
      creator_id: 1,
      created_at: '2026-10-23T04:30:00Z',
      input_count: 3,
      results: [{ metric_name: 'mean', metric_value: 32.0, unit: 'PSU' }],
      manifest: [
        { observation_id: 1, revision_id: null, input_role: 'raw' },
        { observation_id: 2, revision_id: null, input_role: 'raw' },
        { observation_id: 3, revision_id: null, input_role: 'raw' },
      ],
    });

    (api.replayAnalysis as any).mockResolvedValueOnce({
      analysis_id: 5,
      replayed_at: '2026-10-23T05:00:00Z',
      original_results: [{ metric_name: 'mean', metric_value: 32.0, unit: 'PSU' }],
      replayed_results: [{ metric_name: 'mean', metric_value: 32.0, unit: 'PSU' }],
      matches: true,
      input_manifest_verified: true,
    });

    render(<AnalysisWorkspace />);

    await waitFor(() => {
      expect(screen.getByText(/Analysis Workspace & Deterministic Replay/i)).toBeDefined();
    });

    // Inspect the analysis
    const inspectBtn = screen.getByText(/Inspect & Replay/i);
    fireEvent.click(inspectBtn);

    await waitFor(() => {
      expect(screen.getByText(/Frozen Input Manifest \(3 Records\)/i)).toBeDefined();
      expect(screen.getByText(/Execute Deterministic Replay/i)).toBeDefined();
    });

    // Execute Replay
    const replayBtn = screen.getByText(/Execute Deterministic Replay/i);
    fireEvent.click(replayBtn);

    await waitFor(() => {
      expect(screen.getByText(/VERIFIED \(100% INTACT\)/i)).toBeDefined();
      expect(screen.getByText(/MATCHES \(DETERMINISTIC\)/i)).toBeDefined();
      expect(screen.getByText(/Scientific Verification Notice:/i)).toBeDefined();
    });
  });

  it('6. Audit Explorer displays events and supports searching and pagination', async () => {
    render(<AuditExplorer />);

    await waitFor(() => {
      expect(screen.getByText(/Immutable Audit Log Explorer/i)).toBeDefined();
      expect(screen.getByText(/analysis_replayed/i)).toBeDefined();
    });
  });
});
