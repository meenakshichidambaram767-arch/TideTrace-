import React, { useState } from 'react';
import { UploadCloud, Plus, Trash2, RefreshCw, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';
import { api } from '../api/endpoints';
import { IngestionRecordInput, IngestionBatchResponse } from '../types/api';

export const Ingestion: React.FC = () => {
  const [sourceSystem, setSourceSystem] = useState<string>('buoy-mooring-01');
  const [idempotencyKey, setIdempotencyKey] = useState<string>(
    () => `idemp-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`
  );
  const [atomic, setAtomic] = useState<boolean>(true);
  const [records, setRecords] = useState<IngestionRecordInput[]>([
    {
      sensor_id: 1,
      parameter_code: 'temperature',
      event_time: new Date().toISOString(),
      raw_value: 24.5,
      unit: 'degC',
      source_message_id: `msg-${Date.now()}-1`,
    },
  ]);

  const [loading, setLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<IngestionBatchResponse | null>(null);
  const [error, setError] = useState<{ code: string; message: string; details?: any } | null>(null);

  const handleAddRow = () => {
    setRecords((prev) => [
      ...prev,
      {
        sensor_id: 1,
        parameter_code: 'temperature',
        event_time: new Date().toISOString(),
        raw_value: 25.0,
        unit: 'degC',
        source_message_id: `msg-${Date.now()}-${prev.length + 1}`,
      },
    ]);
  };

  const handleRemoveRow = (index: number) => {
    setRecords((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateRecord = (index: number, field: keyof IngestionRecordInput, val: any) => {
    setRecords((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: val };
      return copy;
    });
  };

  const handleGenerateKey = () => {
    setIdempotencyKey(`idemp-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idempotencyKey.trim()) {
      alert('An Idempotency-Key is required by the API contract.');
      return;
    }
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const payload = {
        atomic,
        records: records.map((r) => ({
          ...r,
          source_system: sourceSystem,
          raw_value: Number(r.raw_value),
        })),
      };

      const res = await api.submitBatch(payload, idempotencyKey);
      setResponse(res);
    } catch (err: any) {
      setError({
        code: err.code || 'SUBMISSION_FAILED',
        message: err.message || 'Failed to submit batch',
        details: err.details,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ fontSize: '1.5rem', marginBottom: '6px' }}>Atomic Ingestion & Idempotency Gateway</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Batch intake of ocean sensor observations with cryptographic idempotency protection and atomic rollback guarantees.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="glass-panel" style={{ padding: '28px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '20px', marginBottom: '24px' }}>
          {/* Source System */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
              SOURCE SYSTEM IDENTIFIER
            </label>
            <input
              type="text"
              className="input"
              value={sourceSystem}
              onChange={(e) => setSourceSystem(e.target.value)}
              required
            />
          </div>

          {/* Idempotency Key */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                IDEMPOTENCY-KEY (HEADER)
              </label>
              <button
                type="button"
                onClick={handleGenerateKey}
                style={{ background: 'none', border: 'none', color: '#38bdf8', fontSize: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                <RefreshCw size={12} /> Regenerate
              </button>
            </div>
            <input
              type="text"
              className="input mono"
              value={idempotencyKey}
              onChange={(e) => setIdempotencyKey(e.target.value)}
              required
            />
          </div>

          {/* Atomic Rollback Option */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingTop: '28px' }}>
            <input
              type="checkbox"
              id="chk-atomic"
              checked={atomic}
              onChange={(e) => setAtomic(e.target.checked)}
              style={{ width: '16px', height: '16px', cursor: 'pointer' }}
            />
            <label htmlFor="chk-atomic" style={{ fontSize: '0.85rem', cursor: 'pointer', color: '#ffffff' }}>
              Enforce Atomic Batch Rollback (ACID)
            </label>
          </div>
        </div>

        {/* Observation Rows */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 style={{ fontSize: '1.05rem', color: '#ffffff' }}>Telemetry Records ({records.length})</h3>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleAddRow}
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            >
              <Plus size={14} /> Add Telemetry Row
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {records.map((rec, idx) => (
              <div
                key={idx}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '90px 150px 220px 130px 100px 1fr 40px',
                  gap: '12px',
                  alignItems: 'center',
                  background: 'rgba(10, 15, 26, 0.6)',
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'block' }}>SENSOR ID</label>
                  <input
                    type="number"
                    className="input"
                    value={rec.sensor_id}
                    onChange={(e) => handleUpdateRecord(idx, 'sensor_id', Number(e.target.value))}
                    min={1}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'block' }}>PARAMETER</label>
                  <select
                    className="select"
                    value={rec.parameter_code}
                    onChange={(e) => handleUpdateRecord(idx, 'parameter_code', e.target.value)}
                  >
                    <option value="temperature">temperature</option>
                    <option value="salinity">salinity</option>
                    <option value="ph">ph</option>
                    <option value="dissolved_oxygen">dissolved_oxygen</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'block' }}>EVENT TIME (UTC)</label>
                  <input
                    type="text"
                    className="input mono"
                    value={rec.event_time}
                    onChange={(e) => handleUpdateRecord(idx, 'event_time', e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'block' }}>RAW VALUE</label>
                  <input
                    type="number"
                    step="0.0001"
                    className="input mono"
                    value={rec.raw_value}
                    onChange={(e) => handleUpdateRecord(idx, 'raw_value', e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'block' }}>UNIT</label>
                  <input
                    type="text"
                    className="input"
                    value={rec.unit}
                    onChange={(e) => handleUpdateRecord(idx, 'unit', e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'block' }}>SOURCE MSG ID</label>
                  <input
                    type="text"
                    className="input mono"
                    value={rec.source_message_id}
                    onChange={(e) => handleUpdateRecord(idx, 'source_message_id', e.target.value)}
                    required
                  />
                </div>

                <div>
                  <button
                    type="button"
                    onClick={() => handleRemoveRow(idx)}
                    disabled={records.length === 1}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: records.length === 1 ? 'var(--text-dim)' : '#fb7185',
                      cursor: records.length === 1 ? 'not-allowed' : 'pointer',
                      padding: '4px',
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Submit Action */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '14px' }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ padding: '10px 24px' }}
          >
            {loading ? <RefreshCw size={16} className="spin" /> : <UploadCloud size={16} />}
            {loading ? 'Submitting Batch...' : 'Submit Batch to Ingestion API'}
          </button>
        </div>
      </form>

      {/* Response Panel */}
      {response && (
        <div className="glass-panel" style={{ padding: '24px', borderLeft: '4px solid #10b981' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <CheckCircle2 size={24} color="#10b981" />
            <div>
              <h3 style={{ fontSize: '1.1rem', color: '#10b981' }}>Batch Processed Successfully</h3>
              <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                {response.idempotency_replayed
                  ? 'Replayed cached response from identical prior Idempotency-Key submission.'
                  : 'New observation records committed to PostgreSQL raw telemetry store.'}
              </p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }} className="mono">
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>BATCH ID</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#38bdf8' }}>{response.batch_id}</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>INSERTED COUNT</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#10b981' }}>{response.inserted_count}</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>DUPLICATES SKIPPED</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f59e0b' }}>{response.duplicate_count}</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>STATUS</div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>{response.status}</div>
            </div>
          </div>
        </div>
      )}

      {/* Error / Conflict Alert */}
      {error && (
        <div className="glass-panel" style={{ padding: '24px', borderLeft: '4px solid #f43f5e' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <ShieldAlert size={26} color="#f43f5e" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span className="badge badge-fail">{error.code}</span>
                <span style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff' }}>{error.message}</span>
              </div>
              {error.code === 'IDEMPOTENCY_CONFLICT' && (
                <p style={{ fontSize: '0.825rem', color: '#fb7185', lineHeight: 1.5, marginTop: '8px' }}>
                  <strong>Contract Protection Triggered (HTTP 409):</strong> This <code className="mono">Idempotency-Key</code> was previously submitted with a different payload. The API strictly refuses to execute conflicting mutations under the same key. Click <em>Regenerate</em> to create a fresh key or submit the identical payload.
                </p>
              )}
              {error.details && (
                <pre style={{
                  background: 'rgba(0,0,0,0.4)',
                  padding: '10px 14px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  marginTop: '10px',
                  overflowX: 'auto',
                }} className="mono">
                  {JSON.stringify(error.details, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
