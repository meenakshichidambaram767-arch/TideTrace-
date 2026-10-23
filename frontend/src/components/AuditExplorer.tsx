import React, { useState, useEffect } from 'react';
import { FileText, Search, ChevronLeft, ChevronRight, Eye, RefreshCw, X, Shield } from 'lucide-react';
import { api } from '../api/endpoints';
import { AuditEventItem } from '../types/api';

export const AuditExplorer: React.FC = () => {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [entityType, setEntityType] = useState<string>('');
  const [entityId, setEntityId] = useState<string>('');
  const [actionFilter, setActionFilter] = useState<string>('');

  // Selected Detail Modal
  const [selectedEvent, setSelectedEvent] = useState<AuditEventItem | null>(null);

  const fetchAuditEvents = async () => {
    setLoading(true);
    try {
      const res = await api.getAuditEvents({
        entity_type: entityType || undefined,
        entity_id: entityId || undefined,
        page,
        page_size: pageSize,
      });
      setEvents(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load audit events', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditEvents();
  }, [page, pageSize, entityType, entityId]);

  const filteredEvents = actionFilter
    ? events.filter((e) => e.action.toLowerCase().includes(actionFilter.toLowerCase()))
    : events;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ fontSize: '1.5rem', marginBottom: '6px' }}>Immutable Audit Log Explorer</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Chronological, append-only security ledger capturing all ingestions, corrections, analysis snapshots, and deterministic replays.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <h3 style={{ fontSize: '1.1rem', color: '#ffffff' }}>Search Security Events</h3>
          <button className="btn btn-secondary" onClick={() => fetchAuditEvents()}>
            <RefreshCw size={14} /> Refresh Log
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              ENTITY TYPE
            </label>
            <select
              className="select"
              value={entityType}
              onChange={(e) => {
                setEntityType(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Entities</option>
              <option value="ingestion_batch">ingestion_batch</option>
              <option value="observation">observation</option>
              <option value="analysis_run">analysis_run</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              ENTITY IDENTIFIER
            </label>
            <input
              type="text"
              className="input mono"
              placeholder="e.g. 1 or batch_..."
              value={entityId}
              onChange={(e) => {
                setEntityId(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              ACTION QUICK-FILTER
            </label>
            <input
              type="text"
              className="input"
              placeholder="e.g. replay, revision..."
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Audit Events Table */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Audit ID</th>
                <th>Action</th>
                <th>Entity Type</th>
                <th>Entity ID</th>
                <th>Actor</th>
                <th>Timestamp (UTC)</th>
                <th>Reason / Summary</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    Loading audit events...
                  </td>
                </tr>
              ) : filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No audit records match the selected criteria.
                  </td>
                </tr>
              ) : (
                filteredEvents.map((evt) => (
                  <tr key={evt.audit_id}>
                    <td className="mono" style={{ color: '#38bdf8', fontWeight: 600 }}>#{evt.audit_id}</td>
                    <td>
                      <span className={`badge ${
                        evt.action.includes('replay')
                          ? 'badge-pass'
                          : evt.action.includes('revision')
                          ? 'badge-corrected'
                          : evt.action.includes('ingest')
                          ? 'badge-raw'
                          : 'badge-suspect'
                      }`}>
                        {evt.action}
                      </span>
                    </td>
                    <td className="mono" style={{ fontSize: '0.8rem' }}>{evt.entity_type}</td>
                    <td className="mono" style={{ fontSize: '0.8rem', fontWeight: 600 }}>{evt.entity_id}</td>
                    <td className="mono" style={{ fontSize: '0.8rem' }}>
                      {evt.actor_id !== null ? `User #${evt.actor_id}` : 'System'}
                    </td>
                    <td className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {evt.event_time.substring(0, 19).replace('T', ' ')}
                    </td>
                    <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {evt.reason || 'N/A'}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        onClick={() => setSelectedEvent(evt)}
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      >
                        <Eye size={12} /> Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '18px' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Showing {filteredEvents.length > 0 ? (page - 1) * pageSize + 1 : 0} to{' '}
            {Math.min(page * pageSize, total)} of {total.toLocaleString()} total audit entries
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

      {/* JSON Inspector Modal */}
      {selectedEvent && (
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
            maxWidth: '680px',
            width: '100%',
            padding: '24px',
            background: 'var(--bg-deep)',
            border: '1px solid rgba(255,255,255,0.15)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#ffffff' }}>Audit Record #{selectedEvent.audit_id}</h3>
                <span className="badge badge-pass" style={{ marginTop: '4px' }}>
                  {selectedEvent.action}
                </span>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }} className="mono">
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-dim)' }}>ENTITY:</span> {selectedEvent.entity_type} ({selectedEvent.entity_id})
              </div>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-dim)' }}>ACTOR:</span> {selectedEvent.actor_id !== null ? `User #${selectedEvent.actor_id}` : 'System'}
              </div>
            </div>

            {selectedEvent.reason && (
              <div style={{ marginBottom: '14px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                <strong>Reason:</strong> {selectedEvent.reason}
              </div>
            )}

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-dim)', display: 'block', marginBottom: '6px' }}>
                STRUCTURED PAYLOAD DETAILS (JSON)
              </label>
              <pre style={{
                background: 'rgba(0, 0, 0, 0.5)',
                padding: '14px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                maxHeight: '320px',
                overflowY: 'auto',
                color: '#38bdf8',
              }} className="mono">
                {JSON.stringify(selectedEvent.details, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
