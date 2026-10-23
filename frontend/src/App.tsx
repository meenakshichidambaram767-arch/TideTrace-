import React, { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { Ingestion } from './components/Ingestion';
import { Observations } from './components/Observations';
import { QualityControl } from './components/QualityControl';
import { RevisionReview } from './components/RevisionReview';
import { AnalysisWorkspace } from './components/AnalysisWorkspace';
import { AuditExplorer } from './components/AuditExplorer';
import { DatabaseSchema } from './components/DatabaseSchema';
import { LandingPage } from './components/LandingPage';

export const MainLayout: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('landing');

  if (activeTab === 'landing') {
    return <LandingPage onEnterConsole={(targetTab) => setActiveTab(targetTab || 'dashboard')} />;
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main style={{
        maxWidth: '1440px',
        width: '100%',
        margin: '0 auto',
        padding: '32px 24px 64px 24px',
        flex: 1,
      }}>
        {activeTab === 'dashboard' && <Dashboard onNavigate={setActiveTab} />}
        {activeTab === 'ingestion' && <Ingestion />}
        {activeTab === 'observations' && <Observations />}
        {activeTab === 'quality' && <QualityControl />}
        {activeTab === 'revisions' && <RevisionReview />}
        {activeTab === 'analyses' && <AnalysisWorkspace />}
        {activeTab === 'audit' && <AuditExplorer />}
        {activeTab === 'database' && <DatabaseSchema />}
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border-subtle)',
        background: 'rgba(7, 11, 20, 0.95)',
        padding: '20px 24px',
        textAlign: 'center',
        fontSize: '0.75rem',
        color: 'var(--text-dim)',
      }}>
        <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            TideTrace Provenance-Aware Ocean DBMS — PostgreSQL 18.6 | ACID Guaranteed
          </div>
          <div style={{ display: 'flex', gap: '16px' }}>
            <span>Append-Only Revisions</span>
            <span>Deterministic Manifests</span>
            <span>Immutable Telemetry</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  );
}
