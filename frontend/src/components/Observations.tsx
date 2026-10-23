import React, { useEffect, useState } from 'react';
import { Search, Filter, ChevronLeft, ChevronRight, Eye, ShieldCheck, GitCommit, Database, RefreshCw, X } from 'lucide-react';
import { api } from '../api/endpoints';
import { ObservationSummary, ObservationDetail } from '../types/api';

export const Observations: React.FC = () => {
  const [items, setItems] = useState<ObservationSummary[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [sensorId, setSensorId] = useState<string>('');
  const [parameterCode, setParameterCode] = useState<string>('');
  const [qualityFlag, setQualityFlag] = useState<string>('');

  // Selected Detail Modal
  const [selectedObsId, setSelectedObsId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ObservationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  const fetchObservations = async () => {
    setLoading(true);
    try {
      const res = await api.getObservations({
        sensor_id: sensorId ? Number(sensorId) : undefined,
        parameter_code: parameterCode || undefined,
        quality_flag: qualityFlag || undefined,
        page,
        page_size: pageSize,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to fetch observations', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchObservations();
  }, [page, pageSize, sensorId, parameterCode, qualityFlag]);

  const handleOpenDetail = async (obsId: number) => {
    setSelectedObsId(obsId);
    setDetailLoading(true);
    try {
      const res = await api.getObservationDetail(obsId);
      setDetail(res);
    } catch (err) {
      console.error('Failed to load observation detail', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedObsId(null);
    setDetail(null);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Title & Filter Bar */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '4px' }}>Observation Telemetry Explorer</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              Query raw measurements and versioned corrections. Raw telemetry is immutable; corrections exist strictly as append-only revisions.
            </p>
          </div>
          <button className="btn btn-secondary" onClick={() => fetchObservations()}>
            <RefreshCw size={14} /> Refresh Data
          </button>
        </div>

        {/* Filter Inputs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              SENSOR ID
            </label>
            <input
              type="number"
              className="input"
              placeholder="All Sensors"
              value={sensorId}
              onChange={(e) => {
                setSensorId(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              PARAMETER
            </label>
            <select
              className="select"
              value={parameterCode}
              onChange={(e) => {
                setParameterCode(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Parameters</option>
              <option value="temperature">temperature</option>
              <option value="salinity">salinity</option>
              <option value="ph">ph</option>
              <option value="dissolved_oxygen">dissolved_oxygen</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              QUALITY FLAG
            </label>
            <select
              className="select"
              value={qualityFlag}
              onChange={(e) => {
                setQualityFlag(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Flags</option>
              <option value="pass">Pass Only</option>
              <option value="suspect">Suspect Only</option>
              <option value="fail">Fail Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Observation Table */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Sensor</th>
                <th>Event Time (UTC)</th>
                <th>Parameter</th>
                <th>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>Raw Telemetry Value</span>
                    <span className="badge badge-raw" style={{ fontSize: '0.65rem' }}>Immutable</span>
                  </div>
                </th>
                <th>Current Accepted Value</th>
                <th>Quality Flag</th>
                <th>Revisions</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                    Loading observations from PostgreSQL...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                    No observations match the current filter criteria.
                  </td>
                </tr>
              ) : (
                items.map((obs) => {
                  const hasRevision = obs.revision_count > 0 && obs.current_accepted_value !== null;
                  return (
                    <tr key={obs.observation_id}>
                      <td className="mono" style={{ fontWeight: 600, color: '#38bdf8' }}>
                        #{obs.observation_id}
                      </td>
                      <td className="mono">Sensor {obs.sensor_id}</td>
                      <td className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {new Date(obs.event_time).toISOString().replace('T', ' ').substring(0, 19)}
                      </td>
                      <td style={{ fontWeight: 600 }}>{obs.parameter_code}</td>
                      <td>
                        <span className="mono" style={{ fontWeight: 700, color: '#ffffff', fontSize: '0.9rem' }}>
                          {Number(obs.raw_value).toFixed(4)}
                        </span>{' '}
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{obs.unit}</span>
                      </td>
                      <td>
                        {hasRevision ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span className="mono" style={{ fontWeight: 700, color: '#c084fc', fontSize: '0.9rem' }}>
                              {Number(obs.current_accepted_value).toFixed(4)}
                            </span>
                            <span className="badge badge-corrected" style={{ fontSize: '0.65rem' }}>
                              Rev {obs.revision_count} ({obs.current_decision})
                            </span>
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>None (Using Raw)</span>
                        )}
                      </td>
                      <td>
                        {obs.latest_quality_flag === 'pass' && <span className="badge badge-pass">PASS</span>}
                        {obs.latest_quality_flag === 'suspect' && <span className="badge badge-suspect">SUSPECT</span>}
                        {obs.latest_quality_flag === 'fail' && <span className="badge badge-fail">FAIL</span>}
                        {!obs.latest_quality_flag && <span style={{ color: 'var(--text-dim)' }}>Untested</span>}
                      </td>
                      <td className="mono">{obs.revision_count}</td>
                      <td>
                        <button
                          className="btn btn-secondary"
                          onClick={() => handleOpenDetail(obs.observation_id)}
                          style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                        >
                          <Eye size={12} /> Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '18px' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to{' '}
            {Math.min(page * pageSize, total)} of {total.toLocaleString()} total observations
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              style={{ padding: '6px 12px' }}
            >
              <ChevronLeft size={14} /> Prev
            </button>
            <span style={{ fontSize: '0.8rem', color: '#ffffff', fontWeight: 600 }}>
              Page {page} of {Math.max(1, Math.ceil(total / pageSize))}
            </span>
            <button
              className="btn btn-secondary"
              onClick={() => setPage((p) => p + 1)}
              disabled={page * pageSize >= total}
              style={{ padding: '6px 12px' }}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Observation Detail Modal */}
      {selectedObsId !== null && (
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
            maxWidth: '850px',
            width: '100%',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '28px',
            background: 'var(--bg-deep)',
            border: '1px solid rgba(255,255,255,0.15)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', color: '#ffffff' }}>Observation #{selectedObsId} Inspection</h3>
                <span className="badge badge-raw" style={{ marginTop: '4px' }}>Immutable Telemetry Provenance</span>
              </div>
              <button
                onClick={handleCloseDetail}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {detailLoading || !detail ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                Loading full observation history...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {/* Telemetry Core Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }} className="mono">
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 14px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>RAW MEASUREMENT</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#38bdf8' }}>
                      {Number(detail.raw_value).toFixed(4)} {detail.unit}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 14px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>CURRENT ACCEPTED</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: detail.current_accepted_value ? '#c084fc' : '#ffffff' }}>
                      {detail.current_accepted_value ? `${Number(detail.current_accepted_value).toFixed(4)} ${detail.unit}` : 'None (Raw Active)'}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 14px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>SENSOR & PARAMETER</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ffffff' }}>
                      Sensor #{detail.sensor_id} ({detail.parameter_code})
                    </div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px 14px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>SOURCE MESSAGE ID</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {detail.source_message_id}
                    </div>
                  </div>
                </div>

                {/* Quality Test History */}
                <div>
                  <h4 style={{ fontSize: '0.95rem', color: '#ffffff', marginBottom: '10px' }}>Quality Test Evaluations</h4>
                  {detail.quality_tests.length === 0 ? (
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                      No automated quality tests recorded yet.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {detail.quality_tests.map((qt) => (
                        <div
                          key={qt.test_result_id}
                          style={{
                            background: 'rgba(10, 15, 26, 0.6)',
                            padding: '10px 14px',
                            borderRadius: '6px',
                            border: '1px solid var(--border-subtle)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <div>
                            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>{qt.rule_name}</div>
                            <div style={{ fontSize: '0.725rem', color: 'var(--text-dim)' }} className="mono">
                              Rule Version: {qt.rule_version} | Tested at: {qt.tested_at}
                            </div>
                          </div>
                          <div>
                            {qt.flag === 'pass' && <span className="badge badge-pass">PASS</span>}
                            {qt.flag === 'suspect' && <span className="badge badge-suspect">SUSPECT</span>}
                            {qt.flag === 'fail' && <span className="badge badge-fail">FAIL</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Revision History Timeline */}
                <div>
                  <h4 style={{ fontSize: '0.95rem', color: '#ffffff', marginBottom: '10px' }}>
                    Append-Only Revision History ({detail.revisions.length})
                  </h4>
                  {detail.revisions.length === 0 ? (
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                      No revisions submitted. Observation is operating on original raw telemetry.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {detail.revisions.map((rev) => (
                        <div
                          key={rev.revision_id}
                          style={{
                            background: 'rgba(168, 85, 247, 0.05)',
                            padding: '12px 16px',
                            borderRadius: '8px',
                            border: '1px solid rgba(168, 85, 247, 0.2)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span className="badge badge-corrected">Revision #{rev.revision_number}</span>
                              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff' }} className="mono">
                                Accepted Value: {Number(rev.accepted_value).toFixed(4)} {detail.unit}
                              </span>
                            </div>
                            <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)' }} className="mono">
                              Reviewer #{rev.reviewer_id} ({rev.created_at.substring(0, 16)})
                            </span>
                          </div>
                          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            <strong>Justification:</strong> {rev.reason}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
