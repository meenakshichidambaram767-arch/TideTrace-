import React, { useState, useEffect } from 'react';
import { Layers, Play, RefreshCw, CheckCircle2, AlertTriangle, ShieldCheck, ChevronRight, X, Eye } from 'lucide-react';
import { api } from '../api/endpoints';
import { AnalysisResponse, AnalysisDetailResponse, ReplayResponse } from '../types/api';

export const AnalysisWorkspace: React.FC = () => {
  const [analyses, setAnalyses] = useState<AnalysisResponse[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);

  // Creation Form State
  const [analysisName, setAnalysisName] = useState<string>('Bay Salinity Baseline Run');
  const [metric, setMetric] = useState<string>('mean');
  const [parameterCode, setParameterCode] = useState<string>('salinity');
  const [sensorId, setSensorId] = useState<string>('3');
  const [fromTime, setFromTime] = useState<string>('2026-01-01T00:00:00Z');
  const [toTime, setToTime] = useState<string>('2030-01-01T00:00:00Z');
  const [revisionPolicy, setRevisionPolicy] = useState<'latest_accepted_at_run' | 'raw_only'>('latest_accepted_at_run');
  const [queryVersion, setQueryVersion] = useState<string>('mean-v1.0');
  const [saveManifest, setSaveManifest] = useState<boolean>(true);
  const [creating, setCreating] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Selected Detail & Replay State
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<AnalysisDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [replayResult, setReplayResult] = useState<ReplayResponse | null>(null);
  const [replaying, setReplaying] = useState<boolean>(false);
  const [replayError, setReplayError] = useState<string | null>(null);

  const fetchAnalyses = async () => {
    setLoading(true);
    try {
      const res = await api.getAnalyses(page, 20);
      setAnalyses(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load analyses', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyses();
  }, [page]);

  const handleCreateAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    try {
      const payload = {
        analysis_name: analysisName,
        metric: metric as any,
        filters: {
          sensor_ids: sensorId ? [Number(sensorId)] : undefined,
          parameter_code: parameterCode,
          from_time: fromTime || undefined,
          to_time: toTime || undefined,
          revision_policy: revisionPolicy,
        },
        query_version: queryVersion,
        save_input_manifest: saveManifest,
      };

      const res = await api.createAnalysis(payload);
      await fetchAnalyses();
      handleOpenDetail(res.analysis_id);
    } catch (err: any) {
      setCreateError(err.message || 'Analysis execution failed');
    } finally {
      setCreating(false);
    }
  };

  const handleOpenDetail = async (id: number) => {
    setSelectedId(id);
    setDetailLoading(true);
    setReplayResult(null);
    setReplayError(null);

    try {
      const res = await api.getAnalysisDetail(id);
      setDetail(res);
    } catch (err) {
      console.error('Failed to load analysis detail', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleReplay = async () => {
    if (!selectedId) return;
    setReplaying(true);
    setReplayError(null);
    setReplayResult(null);

    try {
      const res = await api.replayAnalysis(selectedId);
      setReplayResult(res);
    } catch (err: any) {
      setReplayError(err.message || 'Replay execution failed');
    } finally {
      setReplaying(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ fontSize: '1.5rem', marginBottom: '6px' }}>Analysis Workspace & Deterministic Replay</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Execute reproducible statistical ocean analyses with frozen input manifests. Replay re-executes calculations using only the frozen historical inputs.
        </p>
      </div>

      {/* Create Analysis Card */}
      <form onSubmit={handleCreateAnalysis} className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: '#ffffff' }}>Execute New Reproducible Analysis</h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '16px' }}>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              ANALYSIS NAME
            </label>
            <input
              type="text"
              className="input"
              value={analysisName}
              onChange={(e) => setAnalysisName(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              STATISTICAL METRIC
            </label>
            <select className="select" value={metric} onChange={(e) => setMetric(e.target.value)}>
              <option value="mean">mean</option>
              <option value="min">min</option>
              <option value="max">max</option>
              <option value="count">count</option>
              <option value="median">median</option>
              <option value="standard_deviation">standard_deviation</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              TARGET PARAMETER
            </label>
            <select className="select" value={parameterCode} onChange={(e) => setParameterCode(e.target.value)}>
              <option value="temperature">temperature</option>
              <option value="salinity">salinity</option>
              <option value="ph">ph</option>
              <option value="dissolved_oxygen">dissolved_oxygen</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              SENSOR FILTER
            </label>
            <input
              type="number"
              className="input mono"
              value={sensorId}
              onChange={(e) => setSensorId(e.target.value)}
              placeholder="e.g. 1"
            />
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              REVISION RESOLUTION POLICY
            </label>
            <select
              className="select"
              value={revisionPolicy}
              onChange={(e) => setRevisionPolicy(e.target.value as any)}
            >
              <option value="latest_accepted_at_run">Latest Accepted Revisions</option>
              <option value="raw_only">Raw Telemetry Only</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              KERNEL VERSION
            </label>
            <input
              type="text"
              className="input mono"
              value={queryVersion}
              onChange={(e) => setQueryVersion(e.target.value)}
              required
            />
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="checkbox"
              id="chk-manifest"
              checked={saveManifest}
              onChange={(e) => setSaveManifest(e.target.checked)}
              style={{ width: '16px', height: '16px' }}
            />
            <label htmlFor="chk-manifest" style={{ fontSize: '0.85rem', color: '#ffffff', cursor: 'pointer' }}>
              Freeze Exact Observation and Revision IDs in Manifest (<code className="mono">analysis_input</code>)
            </label>
          </div>

          <button type="submit" className="btn btn-primary" disabled={creating}>
            <Play size={14} /> {creating ? 'Calculating...' : 'Run Analysis'}
          </button>
        </div>

        {createError && (
          <div style={{ marginTop: '14px', padding: '10px 14px', borderRadius: '6px', background: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', fontSize: '0.85rem' }}>
            {createError}
          </div>
        )}
      </form>

      {/* Analysis History List */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: '#ffffff' }}>Executed Analyses ({total})</h3>

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Analysis Name</th>
                <th>Metric</th>
                <th>Kernel Version</th>
                <th>Status</th>
                <th>Inputs Frozen</th>
                <th>Result Value</th>
                <th>Timestamp (UTC)</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '28px', color: 'var(--text-muted)' }}>
                    Loading analyses...
                  </td>
                </tr>
              ) : analyses.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '28px', color: 'var(--text-muted)' }}>
                    No analyses recorded yet.
                  </td>
                </tr>
              ) : (
                analyses.map((an) => (
                  <tr key={an.analysis_id}>
                    <td className="mono" style={{ color: '#38bdf8', fontWeight: 600 }}>#{an.analysis_id}</td>
                    <td style={{ fontWeight: 600 }}>{an.analysis_name}</td>
                    <td>
                      <span className="badge badge-raw">{an.metric}</span>
                    </td>
                    <td className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {an.query_version}
                    </td>
                    <td>
                      <span className="badge badge-pass">{an.status}</span>
                    </td>
                    <td className="mono">{an.input_count} rows</td>
                    <td>
                      {an.results.length > 0 ? (
                        <span className="mono" style={{ fontWeight: 700, color: '#34d399' }}>
                          {Number(an.results[0].metric_value).toFixed(4)} {an.results[0].unit}
                        </span>
                      ) : (
                        'N/A'
                      )}
                    </td>
                    <td className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {an.created_at.substring(0, 19).replace('T', ' ')}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        onClick={() => handleOpenDetail(an.analysis_id)}
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      >
                        <Eye size={12} /> Inspect & Replay
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail & Replay Drawer Modal */}
      {selectedId !== null && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '20px',
        }}>
          <div className="glass-panel" style={{
            maxWidth: '900px',
            width: '100%',
            maxHeight: '92vh',
            overflowY: 'auto',
            padding: '28px',
            background: 'var(--bg-deep)',
            border: '1px solid rgba(255,255,255,0.15)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', color: '#ffffff' }}>Analysis Snapshot #{selectedId}</h3>
                <span className="badge badge-raw" style={{ marginTop: '4px' }}>Frozen Manifest Provenance</span>
              </div>
              <button
                onClick={() => setSelectedId(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {detailLoading || !detail ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                Loading analysis snapshot...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
                {/* Metrics & Execution Bar */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }} className="mono">
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>ORIGINAL RESULT</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#34d399' }}>
                      {detail.results.length > 0
                        ? `${Number(detail.results[0].metric_value).toFixed(4)} ${detail.results[0].unit}`
                        : 'N/A'}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>FROZEN INPUTS</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#38bdf8' }}>
                      {detail.manifest.length} records
                    </div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>KERNEL VERSION</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#c084fc' }}>
                      {detail.query_version}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>CREATOR ID</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#ffffff' }}>
                      User #{detail.creator_id}
                    </div>
                  </div>
                </div>

                {/* Deterministic Replay Trigger */}
                <div style={{
                  background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(168, 85, 247, 0.08) 100%)',
                  padding: '20px',
                  borderRadius: '10px',
                  border: '1px solid rgba(6, 182, 212, 0.25)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '10px' }}>
                    <div>
                      <h4 style={{ fontSize: '1.05rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <RefreshCw size={18} color="#38bdf8" /> Deterministic Replay Engine
                      </h4>
                      <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                        Re-executes the calculation strictly from the frozen inputs in <code className="mono">analysis_input</code>. Ignores any revisions made after the analysis run.
                      </p>
                    </div>

                    <button
                      className="btn btn-teal"
                      onClick={handleReplay}
                      disabled={replaying}
                      style={{ padding: '8px 20px' }}
                    >
                      {replaying ? 'Replaying...' : 'Execute Deterministic Replay'}
                    </button>
                  </div>

                  {replayError && (
                    <div style={{ padding: '10px 14px', borderRadius: '6px', background: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', fontSize: '0.85rem', marginTop: '10px' }}>
                      {replayError}
                    </div>
                  )}

                  {replayResult && (
                    <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '14px' }}>
                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>ORIGINAL OUTPUT</div>
                          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff' }} className="mono">
                            {Number(replayResult.original_results[0].metric_value).toFixed(6)} {replayResult.original_results[0].unit}
                          </div>
                        </div>

                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>REPLAYED OUTPUT</div>
                          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#38bdf8' }} className="mono">
                            {Number(replayResult.replayed_results[0].metric_value).toFixed(6)} {replayResult.replayed_results[0].unit}
                          </div>
                        </div>

                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>MANIFEST INTEGRITY</div>
                          <div>
                            {replayResult.input_manifest_verified ? (
                              <span className="badge badge-pass">VERIFIED (100% INTACT)</span>
                            ) : (
                              <span className="badge badge-fail">MANIFEST CORRUPTED</span>
                            )}
                          </div>
                        </div>

                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>NUMERICAL EQUALITY</div>
                          <div>
                            {replayResult.matches ? (
                              <span className="badge badge-pass">MATCHES (DETERMINISTIC)</span>
                            ) : (
                              <span className="badge badge-fail">DISCREPANCY DETECTED</span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div style={{
                        padding: '10px 12px',
                        borderRadius: '6px',
                        background: 'rgba(20, 184, 166, 0.08)',
                        border: '1px solid rgba(20, 184, 166, 0.2)',
                        fontSize: '0.775rem',
                        color: 'var(--text-muted)',
                      }}>
                        <strong>Scientific Verification Notice:</strong> Manifest integrity verification and result numerical equality are distinct: manifest verification proves that every referenced input row exists in the historical database; result matching proves that re-evaluating the formula over the frozen inputs yields bit-exact equivalence.
                      </div>
                    </div>
                  )}
                </div>

                {/* Frozen Input Manifest */}
                <div>
                  <h4 style={{ fontSize: '0.95rem', color: '#ffffff', marginBottom: '10px' }}>
                    Frozen Input Manifest ({detail.manifest.length} Records)
                  </h4>
                  <div className="data-table-container" style={{ maxHeight: '240px' }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Observation ID</th>
                          <th>Revision ID Consumed</th>
                          <th>Input Role</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.manifest.map((item, idx) => (
                          <tr key={idx}>
                            <td className="mono" style={{ color: '#38bdf8' }}>#{item.observation_id}</td>
                            <td className="mono">
                              {item.revision_id !== null ? (
                                <span className="badge badge-corrected">Revision #{item.revision_id}</span>
                              ) : (
                                <span className="badge badge-raw">Raw Telemetry (None)</span>
                              )}
                            </td>
                            <td style={{ textTransform: 'capitalize' }}>{item.input_role}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
