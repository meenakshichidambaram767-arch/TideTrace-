import React, { useEffect, useState } from 'react';
import { Shield, ShieldAlert, CheckCircle2, Play, Info, AlertTriangle, Layers } from 'lucide-react';
import { api } from '../api/endpoints';
import { QualityRule, QualityTestResultItem } from '../types/api';

export const QualityControl: React.FC = () => {
  const [rules, setRules] = useState<QualityRule[]>([]);
  const [loadingRules, setLoadingRules] = useState<boolean>(true);

  // Run Test State
  const [targetObsId, setTargetObsId] = useState<string>('1');
  const [includeTemporal, setIncludeTemporal] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{
    observation_id: number;
    overall_flag: string;
    results: QualityTestResultItem[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getQualityRules()
      .then((data) => setRules(data))
      .catch((err) => console.error('Failed to load quality rules', err))
      .finally(() => setLoadingRules(false));
  }, []);

  const handleRunQualityTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetObsId) return;
    setRunning(true);
    setError(null);
    setTestResult(null);

    try {
      const res = await api.runQualityTests(Number(targetObsId), {
        include_temporal_checks: includeTemporal,
      });
      setTestResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to execute quality assessment');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ fontSize: '1.5rem', marginBottom: '6px' }}>Versioned Quality-Control Engine</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Evaluate sensor readings against versioned oceanographic rules (Range, Temporal Gap, Rate of Change, Stuck Sensor, Duplicate). Raw measurements are strictly preserved; quality flags are saved with the exact rule version.
        </p>
      </div>

      {/* Manual Quality Evaluation Trigger */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '14px', color: '#ffffff' }}>Run Automated Quality Assessment</h3>
        <form onSubmit={handleRunQualityTest} style={{ display: 'flex', gap: '14px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ minWidth: '220px' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              TARGET OBSERVATION ID
            </label>
            <input
              type="number"
              className="input mono"
              value={targetObsId}
              onChange={(e) => setTargetObsId(e.target.value)}
              placeholder="e.g. 1"
              required
              min={1}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingTop: '22px' }}>
            <input
              type="checkbox"
              id="chk-temporal"
              checked={includeTemporal}
              onChange={(e) => setIncludeTemporal(e.target.checked)}
              style={{ width: '16px', height: '16px' }}
            />
            <label htmlFor="chk-temporal" style={{ fontSize: '0.825rem', color: '#ffffff', cursor: 'pointer' }}>
              Include Temporal Checks (Gap, Rate of Change, Stuck)
            </label>
          </div>

          <div style={{ paddingTop: '20px' }}>
            <button type="submit" className="btn btn-teal" disabled={running}>
              <Play size={14} /> {running ? 'Evaluating Rules...' : 'Execute Quality Tests'}
            </button>
          </div>
        </form>

        {error && (
          <div style={{ marginTop: '16px', padding: '12px 16px', borderRadius: '6px', background: 'rgba(244,63,94,0.1)', color: '#fb7185', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}

        {/* Test Result Display */}
        {testResult && (
          <div style={{ marginTop: '20px', padding: '20px', borderRadius: '8px', background: 'rgba(10, 15, 26, 0.7)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>
                  Evaluation Results for Observation #{testResult.observation_id}
                </span>
                {testResult.overall_flag === 'pass' && <span className="badge badge-pass">OVERALL: PASS</span>}
                {testResult.overall_flag === 'suspect' && <span className="badge badge-suspect">OVERALL: SUSPECT</span>}
                {testResult.overall_flag === 'fail' && <span className="badge badge-fail">OVERALL: FAIL</span>}
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                {testResult.results.length} rules executed
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {testResult.results.map((r) => (
                <div
                  key={r.test_result_id}
                  style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    padding: '12px 16px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff' }}>{r.rule_name}</span>
                      <span className="badge badge-raw mono" style={{ fontSize: '0.65rem' }}>{r.rule_version}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }} className="mono">
                      Details: {JSON.stringify(r.details)}
                    </div>
                  </div>
                  <div>
                    {r.flag === 'pass' && <span className="badge badge-pass">PASS</span>}
                    {r.flag === 'suspect' && <span className="badge badge-suspect">SUSPECT</span>}
                    {r.flag === 'fail' && <span className="badge badge-fail">FAIL</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Active Rules Registry */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '14px', color: '#ffffff' }}>
          Registered Ocean Quality Rules ({rules.length})
        </h3>
        {loadingRules ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>Loading rules...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            {rules.map((rule) => (
              <div
                key={rule.rule_id}
                style={{
                  background: 'rgba(10, 15, 26, 0.6)',
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#ffffff' }}>{rule.name}</div>
                  <span className="badge badge-pass" style={{ fontSize: '0.65rem' }}>{rule.rule_type}</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Parameter: <strong style={{ color: '#38bdf8' }}>{rule.parameter_code}</strong> | Version: <code className="mono">{rule.rule_version}</code>
                </div>
                <div style={{
                  background: 'rgba(0,0,0,0.3)',
                  padding: '8px 10px',
                  borderRadius: '4px',
                  fontSize: '0.7rem',
                  color: 'var(--text-dim)',
                }} className="mono">
                  {JSON.stringify(rule.thresholds)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
