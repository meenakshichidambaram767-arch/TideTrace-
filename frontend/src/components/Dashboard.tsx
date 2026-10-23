import React, { useEffect, useState } from 'react';
import { Database, ShieldCheck, GitCommit, FileText, ArrowUpRight, Cpu, Layers, RefreshCw } from 'lucide-react';
import { api } from '../api/endpoints';

interface DashboardProps {
  onNavigate: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [stats, setStats] = useState<{
    observations: number;
    analyses: number;
    auditEvents: number;
    rules: number;
    loading: boolean;
  }>({
    observations: 0,
    analyses: 0,
    auditEvents: 0,
    rules: 0,
    loading: true,
  });

  const loadStats = async () => {
    setStats((prev) => ({ ...prev, loading: true }));
    try {
      const [obsRes, anRes, auditRes, rulesRes] = await Promise.all([
        api.getObservations({ page: 1, page_size: 1 }),
        api.getAnalyses(1, 1),
        api.getAuditEvents({ page: 1, page_size: 1 }),
        api.getQualityRules(),
      ]);

      setStats({
        observations: obsRes.total,
        analyses: anRes.total,
        auditEvents: auditRes.total,
        rules: rulesRes.length,
        loading: false,
      });
    } catch (err) {
      console.error('Failed to load dashboard statistics', err);
      setStats((prev) => ({ ...prev, loading: false }));
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Hero Banner */}
      <div className="glass-panel" style={{
        padding: '32px 36px',
        background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.12) 0%, rgba(20, 184, 166, 0.08) 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{ maxWidth: '820px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <span className="badge badge-raw">PostgreSQL 18.6 Provenance Engine</span>
            <span className="badge badge-pass">ACID Integrity Enforced</span>
          </div>
          <h1 style={{ fontSize: '2.1rem', marginBottom: '12px', lineHeight: 1.2 }}>
            Provenance-Aware Ocean Data Integrity & Anomaly Lab
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1rem', lineHeight: 1.6, marginBottom: '24px' }}>
            A database-first scientific telemetry platform. Raw observations are strictly immutable; corrections are captured as versioned, append-only revisions with optimistic concurrency locks; analysis runs freeze input manifests for bit-exact deterministic replay.
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button className="btn btn-primary" onClick={() => onNavigate('analyses')}>
              <RefreshCw size={16} /> Open Analysis & Replay Lab
            </button>
            <button className="btn btn-secondary" onClick={() => onNavigate('observations')}>
              Explore Sensor Observations <ArrowUpRight size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Live System Statistics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '18px' }}>
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontWeight: 600 }}>RAW TELEMETRY STORE</span>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8' }}>
              <Database size={20} />
            </div>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#ffffff', marginBottom: '6px' }} className="mono">
            {stats.loading ? '...' : stats.observations.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#38bdf8' }}>
            Strictly Append-Only Telemetry Rows
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontWeight: 600 }}>VERSIONED QC RULES</span>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(20, 184, 166, 0.1)', color: '#14b8a6' }}>
              <ShieldCheck size={20} />
            </div>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#ffffff', marginBottom: '6px' }} className="mono">
            {stats.loading ? '...' : stats.rules}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#14b8a6' }}>
            Active Range, Gap, Stuck, ROC Rules
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontWeight: 600 }}>REPRODUCIBLE ANALYSES</span>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(168, 85, 247, 0.1)', color: '#c084fc' }}>
              <Layers size={20} />
            </div>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#ffffff', marginBottom: '6px' }} className="mono">
            {stats.loading ? '...' : stats.analyses}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#c084fc' }}>
            Frozen Manifests & Replay Kernels
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontWeight: 600 }}>IMMUTABLE AUDIT TRAIL</span>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.1)', color: '#fbbf24' }}>
              <FileText size={20} />
            </div>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#ffffff', marginBottom: '6px' }} className="mono">
            {stats.loading ? '...' : stats.auditEvents.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#fbbf24' }}>
            Granular Actor & Action Event Records
          </div>
        </div>
      </div>

      {/* Core Architectural Pillars */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
            <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8' }}>
              <Database size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1rem', color: '#ffffff' }}>1. Raw Data Immutability</h3>
              <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>Never mutated by QC or human corrections</p>
            </div>
          </div>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Every raw reading ingested from ocean buoys is permanently preserved with source system identifiers and unique message keys. Relational foreign key and check constraints reject arbitrary mutations or deletions.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
            <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(168, 85, 247, 0.1)', color: '#c084fc' }}>
              <GitCommit size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1rem', color: '#ffffff' }}>2. Concurrency-Safe Revisions</h3>
              <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>Pessimistic row locking & If-Match-Revision</p>
            </div>
          </div>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Corrections require reviewer credentials, mandatory justification (minimum 5 characters), and monotonic revision sequencing. If an observation was modified concurrently, stale preconditions return HTTP 409 conflict.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
            <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(20, 184, 166, 0.1)', color: '#14b8a6' }}>
              <Cpu size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1rem', color: '#ffffff' }}>3. Deterministic Analysis Manifests</h3>
              <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>Exact inputs frozen at run time</p>
            </div>
          </div>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            When an analysis executes, its exact input observations and revision IDs are frozen in <code className="mono">analysis_input</code>. Replaying the analysis queries only the frozen manifest, preserving historical results even after subsequent corrections.
          </p>
        </div>
      </div>
    </div>
  );
};
