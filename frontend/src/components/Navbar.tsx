import React, { useEffect, useState } from 'react';
import { Waves, Shield, Activity, User, Database, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/endpoints';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const { user, quickSwitchUser } = useAuth();
  const [healthStatus, setHealthStatus] = useState<{ status: string; database: string } | null>(null);

  useEffect(() => {
    api.getHealth()
      .then((data) => setHealthStatus({ status: data.status, database: data.database }))
      .catch(() => setHealthStatus({ status: 'offline', database: 'disconnected' }));
    const interval = setInterval(() => {
      api.getHealth()
        .then((data) => setHealthStatus({ status: data.status, database: data.database }))
        .catch(() => setHealthStatus({ status: 'offline', database: 'disconnected' }));
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'landing', label: 'Story Experience' },
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'ingestion', label: 'Batch Ingest' },
    { id: 'observations', label: 'Observations' },
    { id: 'quality', label: 'Quality Engine' },
    { id: 'revisions', label: 'Revisions' },
    { id: 'analyses', label: 'Analyses & Replay' },
    { id: 'audit', label: 'Audit Trail' },
    { id: 'database', label: 'DB & Schema' },
  ];

  return (
    <header style={{
      borderBottom: '1px solid var(--border-subtle)',
      background: 'rgba(7, 11, 20, 0.85)',
      backdropFilter: 'blur(20px)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      padding: '0 24px',
    }}>
      <div style={{
        maxWidth: '1440px',
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '68px',
      }}>
        {/* Brand */}
        <div
          onClick={() => setActiveTab('landing')}
          style={{ display: 'flex', alignItems: 'center', gap: '14px', cursor: 'pointer' }}
          title="Return to Story Experience"
        >
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(6, 182, 212, 0.35)',
          }}>
            <Waves size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.03em', color: '#ffffff' }}>
                TideTrace
              </span>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '2px 6px',
                borderRadius: '4px',
                background: 'rgba(6, 182, 212, 0.15)',
                color: '#38bdf8',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                letterSpacing: '0.06em',
              }}>
                PROVENANCE DBMS
              </span>
            </div>
            <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
              Ocean Telemetry & Anomaly Investigation
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  background: isActive ? 'rgba(14, 165, 233, 0.15)' : 'transparent',
                  color: isActive ? '#38bdf8' : 'var(--text-muted)',
                  border: isActive ? '1px solid rgba(14, 165, 233, 0.35)' : '1px solid transparent',
                  borderRadius: 'var(--radius-md)',
                  padding: '7px 14px',
                  fontSize: '0.85rem',
                  fontWeight: isActive ? 600 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Status & User Role Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Health Pill */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            padding: '5px 10px',
            borderRadius: 'var(--radius-full)',
            background: healthStatus?.database === 'connected' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
            border: healthStatus?.database === 'connected' ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(244, 63, 94, 0.25)',
            color: healthStatus?.database === 'connected' ? '#34d399' : '#fb7185',
          }}>
            {healthStatus?.database === 'connected' ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
            <span>PG18: {healthStatus?.database || 'checking'}</span>
          </div>

          {/* User Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
            }}>
              <User size={14} color="#38bdf8" />
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ffffff' }}>
                  {user?.full_name || user?.username || 'Guest'}
                </span>
                <span style={{
                  fontSize: '0.65rem',
                  color: user?.role === 'admin' ? '#f43f5e' : user?.role === 'reviewer' ? '#c084fc' : '#38bdf8',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                }}>
                  {user?.role || 'None'}
                </span>
              </div>
            </div>

            {/* Quick Switch Dropdown */}
            <select
              aria-label="Switch Role"
              value={user?.username || ''}
              onChange={(e) => quickSwitchUser(e.target.value)}
              style={{
                background: 'rgba(15, 23, 42, 0.9)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '4px 8px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                outline: 'none',
              }}
            >
              <option value="reviewer_alice">Reviewer: Alice</option>
              <option value="researcher_sam">Researcher: Sam</option>
              <option value="steward_dave">Data Steward: Dave</option>
              <option value="admin_carol">Admin: Carol</option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
