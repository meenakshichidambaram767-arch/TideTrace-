import React, { useState, useEffect } from 'react';
import { GitCommit, Shield, AlertTriangle, CheckCircle2, History, Send, Lock } from 'lucide-react';
import { api } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { ObservationDetail, RevisionItem } from '../types/api';

export const RevisionReview: React.FC = () => {
  const { user, canReview } = useAuth();
  const [obsId, setObsId] = useState<string>('2');
  const [loading, setLoading] = useState<boolean>(false);
  const [obsDetail, setObsDetail] = useState<ObservationDetail | null>(null);

  // Correction Form
  const [acceptedValue, setAcceptedValue] = useState<string>('25.5');
  const [decision, setDecision] = useState<string>('corrected');
  const [reason, setReason] = useState<string>('Bench calibration test confirmed temperature offset of +0.5 degC.');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string; details?: any } | null>(null);

  const loadObservation = async (id: number) => {
    setLoading(true);
    setFeedback(null);
    try {
      const res = await api.getObservationDetail(id);
      setObsDetail(res);
      if (res.current_accepted_value !== null) {
        setAcceptedValue(String(res.current_accepted_value));
      } else {
        setAcceptedValue(String(res.raw_value));
      }
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Observation not found' });
      setObsDetail(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (obsId) {
      loadObservation(Number(obsId));
    }
  }, []);

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault();
    if (obsId) {
      loadObservation(Number(obsId));
    }
  };

  const handleApplyCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!obsDetail) return;

    if (reason.trim().length < 5) {
      setFeedback({
        type: 'error',
        message: 'A detailed scientific reason of at least 5 characters is mandatory for auditing.',
      });
      return;
    }

    setSubmitting(true);
    setFeedback(null);

    const currentRevNumber = obsDetail.revisions.length > 0
      ? obsDetail.revisions[obsDetail.revisions.length - 1].revision_number
      : 0;

    try {
      const res = await api.submitRevision(
        obsDetail.observation_id,
        {
          accepted_value: Number(acceptedValue),
          decision,
          reason,
        },
        currentRevNumber
      );

      setFeedback({
        type: 'success',
        message: `Revision #${res.revision_number} successfully recorded with decision '${res.decision}'. Raw observation telemetry remains strictly unchanged.`,
      });

      // Reload updated observation
      await loadObservation(obsDetail.observation_id);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to submit correction',
        details: err.details,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ fontSize: '1.5rem', marginBottom: '6px' }}>Scientific Measurement Revisions</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Human-in-the-loop scientific correction workflow protected by optimistic concurrency (<code className="mono">If-Match-Revision</code>) and pessimistic row locks.
        </p>
      </div>

      {/* Observation Selector Bar */}
      <div className="glass-panel" style={{ padding: '20px 24px' }}>
        <form onSubmit={handleLookup} style={{ display: 'flex', gap: '14px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: '220px' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              LOOKUP OBSERVATION ID
            </label>
            <input
              type="number"
              className="input mono"
              value={obsId}
              onChange={(e) => setObsId(e.target.value)}
              min={1}
              required
            />
          </div>
          <button type="submit" className="btn btn-secondary" disabled={loading} style={{ height: '38px' }}>
            {loading ? 'Fetching...' : 'Load Observation'}
          </button>

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Active Reviewer:</span>
            <span className="badge badge-corrected">
              {user?.username} ({user?.role})
            </span>
            {!canReview && (
              <span className="badge badge-fail" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Lock size={12} /> Read-Only Role
              </span>
            )}
          </div>
        </form>
      </div>

      {/* Observation Review Workspace */}
      {obsDetail && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
          {/* Left Column: Side-by-Side Comparison & Correction Form */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: '#ffffff' }}>
              Proposed Correction vs Immutable Raw Telemetry
            </h3>

            {/* Side by side cards */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '20px' }}>
              <div style={{
                background: 'rgba(56, 189, 248, 0.06)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                borderRadius: '8px',
                padding: '16px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.7rem', color: '#38bdf8', fontWeight: 700 }}>RAW TELEMETRY</span>
                  <span className="badge badge-raw" style={{ fontSize: '0.6rem' }}>Immutable</span>
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#ffffff' }} className="mono">
                  {Number(obsDetail.raw_value).toFixed(4)}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {obsDetail.unit} | Sensor {obsDetail.sensor_id}
                </div>
              </div>

              <div style={{
                background: 'rgba(168, 85, 247, 0.06)',
                border: '1px solid rgba(168, 85, 247, 0.25)',
                borderRadius: '8px',
                padding: '16px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.7rem', color: '#c084fc', fontWeight: 700 }}>CURRENT ACCEPTED</span>
                  <span className="badge badge-corrected" style={{ fontSize: '0.6rem' }}>
                    Rev {obsDetail.revisions.length}
                  </span>
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#ffffff' }} className="mono">
                  {obsDetail.current_accepted_value !== null
                    ? Number(obsDetail.current_accepted_value).toFixed(4)
                    : Number(obsDetail.raw_value).toFixed(4)}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Decision: {obsDetail.current_decision || 'raw_telemetry'}
                </div>
              </div>
            </div>

            {/* Correction Form */}
            <form onSubmit={handleApplyCorrection} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                    NEW ACCEPTED VALUE
                  </label>
                  <input
                    type="number"
                    step="0.0001"
                    className="input mono"
                    value={acceptedValue}
                    onChange={(e) => setAcceptedValue(e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                    DECISION
                  </label>
                  <select
                    className="select"
                    value={decision}
                    onChange={(e) => setDecision(e.target.value)}
                  >
                    <option value="corrected">corrected</option>
                    <option value="accepted">accepted</option>
                    <option value="rejected">rejected</option>
                    <option value="needs_review">needs_review</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                  MANDATORY AUDIT REASON (MINIMUM 5 CHARACTERS)
                </label>
                <textarea
                  className="textarea"
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Explain the scientific, calibration, or operational basis for this modification..."
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '6px' }}>
                <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)' }} className="mono">
                  Optimistic Lock Header: If-Match-Revision: {obsDetail.revisions.length}
                </span>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submitting || !canReview}
                >
                  <Send size={14} /> {submitting ? 'Applying...' : 'Commit Revision'}
                </button>
              </div>
            </form>

            {/* Notification Banner */}
            {feedback && (
              <div
                style={{
                  marginTop: '16px',
                  padding: '14px',
                  borderRadius: '6px',
                  background: feedback.type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                  border: feedback.type === 'success' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(244, 63, 94, 0.3)',
                  color: feedback.type === 'success' ? '#34d399' : '#fb7185',
                  fontSize: '0.85rem',
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: feedback.details ? '6px' : '0' }}>{feedback.message}</div>
                {feedback.details && (
                  <pre style={{ fontSize: '0.75rem', background: 'rgba(0,0,0,0.3)', padding: '6px', borderRadius: '4px' }} className="mono">
                    {JSON.stringify(feedback.details, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>

          {/* Right Column: Revision Timeline */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.1rem', color: '#ffffff' }}>Append-Only Revision Timeline</h3>
              <span className="badge badge-raw">Observation #{obsDetail.observation_id}</span>
            </div>

            {obsDetail.revisions.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '48px 24px',
                color: 'var(--text-dim)',
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '8px',
              }}>
                <History size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
                <div style={{ fontWeight: 600, color: 'var(--text-muted)' }}>No Revisions Appended</div>
                <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                  This reading is currently evaluated using its immutable raw telemetry value.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {obsDetail.revisions.map((rev) => (
                  <div
                    key={rev.revision_id}
                    style={{
                      background: 'rgba(10, 15, 26, 0.6)',
                      padding: '14px 18px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      position: 'relative',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="badge badge-corrected">Revision #{rev.revision_number}</span>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#ffffff' }}>
                          Decision: <span style={{ color: '#c084fc' }}>{rev.decision}</span>
                        </span>
                      </div>
                      <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)' }} className="mono">
                        {rev.created_at.substring(0, 19).replace('T', ' ')} UTC
                      </span>
                    </div>

                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#38bdf8', marginBottom: '6px' }} className="mono">
                      Accepted: {Number(rev.accepted_value).toFixed(4)} {obsDetail.unit}
                    </div>

                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.4, marginBottom: '6px' }}>
                      <strong>Audit Reason:</strong> {rev.reason}
                    </p>

                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }} className="mono">
                      Reviewer ID: #{rev.reviewer_id} | Calibration ID: {rev.calibration_id ?? 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
