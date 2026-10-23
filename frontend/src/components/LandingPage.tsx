import React, { useEffect, useState, useRef } from 'react';
import './LandingPage.css';

interface LandingPageProps {
  onEnterConsole: (targetTab?: string) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onEnterConsole }) => {
  const [scrollDepth, setScrollDepth] = useState<number>(0);
  const [isAudioPlaying, setIsAudioPlaying] = useState<boolean>(false);
  const [dbStats, setDbStats] = useState<{ total_observations: number; table_count: number; database_size: string } | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);

  // Depth calculation based on scroll position
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const progress = maxScroll > 0 ? Math.min(Math.max(scrollY / maxScroll, 0), 1) : 0;
      // Map 0 -> 6,400 meters depth (Mariana Benthic Trench level)
      const calculatedDepth = Math.round(progress * 6400);
      setScrollDepth(calculatedDepth);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Fetch live PostgreSQL database statistics
  useEffect(() => {
    fetch('/api/v1/database/stats')
      .then(res => res.json())
      .then(data => {
        if (data && data.total_observations) {
          setDbStats({
            total_observations: data.total_observations,
            table_count: data.table_count || 14,
            database_size: data.database_size || '41 MB'
          });
        }
      })
      .catch(() => {
        setDbStats({
          total_observations: 100297,
          table_count: 14,
          database_size: '41 MB'
        });
      });
  }, []);

  // Ambient Ocean Synthesizer using Web Audio API
  const toggleAudio = () => {
    if (!audioContextRef.current) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;

      const bufferSize = ctx.sampleRate * 2;
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        b0 = 0.99886 * b0 + white * 0.0555179;
        b1 = 0.99332 * b1 + white * 0.0750759;
        b2 = 0.96900 * b2 + white * 0.1538520;
        b3 = 0.86650 * b3 + white * 0.3104856;
        b4 = 0.55000 * b4 + white * 0.5329522;
        b5 = -0.7616 * b5 - white * 0.0168980;
        data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.04;
        b6 = white * 0.115926;
      }

      const noise = ctx.createBufferSource();
      noise.buffer = buffer;
      noise.loop = true;

      const filter = ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(260, ctx.currentTime);

      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.35, ctx.currentTime);
      gainNodeRef.current = gain;

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      noise.start();
      setIsAudioPlaying(true);
    } else {
      if (audioContextRef.current.state === 'running') {
        audioContextRef.current.suspend();
        setIsAudioPlaying(false);
      } else {
        audioContextRef.current.resume();
        setIsAudioPlaying(true);
      }
    }
  };

  const getDepthZone = (depth: number) => {
    if (depth < 200) return 'Epipelagic (Sunlight Zone)';
    if (depth < 1000) return 'Mesopelagic (Twilight Zone)';
    if (depth < 4000) return 'Bathypelagic (Midnight Zone)';
    return 'Abyssopelagic (Benthic Trench)';
  };

  // Generate ambient rising bubbles
  const bubbles = Array.from({ length: 12 }, (_, i) => ({
    id: i,
    left: `${(i * 8.3 + 4).toFixed(1)}%`,
    size: `${(10 + (i % 5) * 6)}px`,
    delay: `${(i * 1.5).toFixed(1)}s`,
    duration: `${(14 + (i % 4) * 3)}s`
  }));

  return (
    <div className="bbc-landing">
      {/* SVG Water Ripple & Turbulence Distortion Filter (BBC replica) */}
      <svg width="0" height="0" style={{ position: 'absolute', pointerEvents: 'none' }}>
        <defs>
          <filter id="bbc-water-turbulence">
            <feTurbulence type="turbulence" baseFrequency="0.015 0.02" numOctaves="3" seed="12" result="turb" />
            <feDisplacementMap in="SourceGraphic" in2="turb" scale="4.5" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
      </svg>

      {/* Ambient water caustics overlay across the ENTIRE continuous page */}
      <div className="bbc-ocean-caustics-layer"></div>

      {/* Floating rising ocean bubbles throughout the whole page */}
      <div className="bbc-bubbles-container">
        {bubbles.map(b => (
          <div
            key={b.id}
            className="bbc-bubble"
            style={{
              left: b.left,
              width: b.size,
              height: b.size,
              animationDelay: b.delay,
              animationDuration: b.duration
            }}
          />
        ))}
      </div>

      {/* --------------------------------------------------------------------
          BBC Navigation Header
          -------------------------------------------------------------------- */}
      <header className="bbc-nav">
        <div className="bbc-nav-left">
          <div className="bbc-compliance-badge">
            <span className="bbc-compliance-subtext">Ocean Data Integrity Initiative</span>
            <a href="#hero" className="bbc-brand-logo">
              <span className="bbc-brand-dot"></span>
              tidetrace
            </a>
          </div>
        </div>

        <nav className="bbc-nav-center">
          <a href="#challenge" className="bbc-nav-link">Telemetry</a>
          <a href="#quality-control" className="bbc-nav-link">Quality Control</a>
          <a href="#provenance" className="bbc-nav-link">Provenance</a>
          <a href="#database-core" className="bbc-nav-link">PostgreSQL Core</a>
        </nav>

        <div className="bbc-nav-right">
          <button className="bbc-sound-btn" onClick={toggleAudio} title="Toggle Ocean Audio Ambience">
            <span>{isAudioPlaying ? '🔊 Sound On' : '🔇 Ambient Sound'}</span>
          </button>
          <button className="bbc-launch-btn" onClick={() => onEnterConsole('dashboard')}>
            <span>Launch Console</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </header>

      {/* --------------------------------------------------------------------
          Floating Depth HUD (Right side)
          -------------------------------------------------------------------- */}
      <aside className="bbc-depth-hud">
        <span className="bbc-depth-label">Ocean Depth</span>
        <div className="bbc-depth-value">{scrollDepth.toLocaleString()}m</div>
        <div className="bbc-depth-zone">{getDepthZone(scrollDepth)}</div>
        <div className="bbc-depth-ruler">
          <div
            className="bbc-depth-indicator"
            style={{ top: `${Math.min((scrollDepth / 6400) * 100, 100)}%` }}
          ></div>
        </div>
      </aside>

      {/* --------------------------------------------------------------------
          Hero Section (#hero) — 100% EVEN SUNLIGHT ACROSS LEFT, CENTER & RIGHT
          -------------------------------------------------------------------- */}
      <section id="hero" className="bbc-hero">
        {/* Background Underwater Video Loop */}
        <video
          className="bbc-hero-video-bg"
          autoPlay
          loop
          muted
          playsInline
          poster="/landing/Hyundai_Hero_Desktop_1920x1080-v2-poster-00001.jpg"
        >
          <source src="/landing/hero_video.mp4" type="video/mp4" />
        </video>

        <div className="bbc-hero-overlay"></div>

        {/* FULL-WIDTH UNIFORM SUNLIGHT WASH (Spanning left, center and right evenly) */}
        <div className="bbc-even-sunlight-wash"></div>

        {/* 16 EVENLY DISTRIBUTED SUNBEAMS ACROSS 100% OF THE VIEWPORT WIDTH */}
        <div className="bbc-light-rays-wrap">
          <ul className="bbc-light-rays-list">
            <li></li><li></li><li></li><li></li>
            <li></li><li></li><li></li><li></li>
            <li></li><li></li><li></li><li></li>
            <li></li><li></li><li></li><li></li>
          </ul>
        </div>

        {/* Floating Marine Life around Coral Reef */}
        <img src="/landing/school01.webp" alt="Fish school" className="bbc-fish-school-1" />
        <img src="/landing/school-1-left.webp" alt="Fish school" className="bbc-fish-school-2" />
        <img src="/landing/fish-1.webp" alt="Swimming fish" className="bbc-fish-swim-1" />
        <img src="/landing/left-fish-3.webp" alt="Deep fish" className="bbc-fish-swim-2" />

        {/* BBC Typography & Strapline */}
        <div className="bbc-hero-content">
          <h1 className="bbc-hero-title">tidetrace</h1>
          <h2 className="bbc-hero-subhead">Collaborating for ocean data integrity</h2>

          <div className="bbc-hero-strapline">
            TideTrace (n): An immutable, provenance-aware oceanographic database management system engineering high-throughput sensor telemetry ingestion, automated multi-tier quality control pipelines, and deterministic historical replay across global marine research stations.
          </div>

          <a href="#challenge" className="bbc-scroll-prompt">
            <span>Scroll to dive into ocean data integrity</span>
            <div className="bbc-scroll-arrow"></div>
          </a>
        </div>

        {/* Ocean Seafloor Coral Reef WITH SMOOTH ORGANIC FEATHERED TRANSITION */}
        <div className="bbc-reef-wrapper">
          <img src="/landing/Reef-fish-2.webp" alt="Ocean floor reef" className="bbc-reef-image" />
          <div className="bbc-reef-feather"></div>
        </div>
      </section>

      {/* --------------------------------------------------------------------
          Chapter 1: Epipelagic Zone (0m — 200m)
          -------------------------------------------------------------------- */}
      <section id="challenge" className="bbc-chapter-section">
        {/* Authentic BBC Sea Creatures throughout Chapter 1 */}
        <img src="/landing/turtle.webp" alt="Swimming Sea Turtle" className="bbc-turtle-decor" />
        <img src="/landing/diver-swimming.webp" alt="Research Scuba Diver" className="bbc-diver-decor" />
        <img src="/landing/left-fish-4.webp" alt="Reef Fish" className="bbc-fish-chap1" />

        <div className="bbc-container">
          <div className="bbc-chapter-header">
            <div className="bbc-chapter-tag">Chapter 01 // Epipelagic Zone (0m — 200m)</div>
            <h2 className="bbc-chapter-title">The Invisible Threat in Ocean Science</h2>
            <p className="bbc-chapter-desc">
              Every hour, hundreds of automated buoys and acoustic profiling gliders record temperature, salinity, and tidal currents across the global seas. Yet raw observation data is routinely overwritten, modified, or silently corrected without cryptographic provenance.
            </p>
          </div>

          {/* Live System Stats Banner */}
          <div className="bbc-stats-banner">
            <div>
              <div className="bbc-stat-number">{dbStats ? dbStats.total_observations.toLocaleString() : '100,297'}</div>
              <div className="bbc-stat-label">Raw Observations Protected</div>
            </div>
            <div>
              <div className="bbc-stat-number">100%</div>
              <div className="bbc-stat-label">Append-Only Immutability</div>
            </div>
            <div>
              <div className="bbc-stat-number">{dbStats ? dbStats.table_count : '14'}</div>
              <div className="bbc-stat-label">Relational DBMS Tables</div>
            </div>
            <div>
              <div className="bbc-stat-number">&lt; 15ms</div>
              <div className="bbc-stat-label">B-Tree Indexed Lookup</div>
            </div>
          </div>

          <div className="bbc-feature-grid">
            <div className="bbc-card" onClick={() => onEnterConsole('ingestion')} style={{ cursor: 'pointer' }}>
              <div className="bbc-card-icon">🌊</div>
              <h3 className="bbc-card-title">Atomic Telemetry Ingestion</h3>
              <p className="bbc-card-text">
                Incoming sensor feeds are grouped into immutable Ingestion Batches with transaction isolation, ensuring incomplete transmissions never compromise historical baselines.
              </p>
            </div>
            <div className="bbc-card" onClick={() => onEnterConsole('observations')} style={{ cursor: 'pointer' }}>
              <div className="bbc-card-icon">📍</div>
              <h3 className="bbc-card-title">Deep-Sea Station Anchors</h3>
              <p className="bbc-card-text">
                Sensors, calibrations, and deployments maintain strict foreign-key integrity back to geographic marine stations, from the Pacific Abyss to Arctic Ice Shelves.
              </p>
            </div>
            <div className="bbc-card" onClick={() => onEnterConsole('database')} style={{ cursor: 'pointer' }}>
              <div className="bbc-card-icon">🛡️</div>
              <h3 className="bbc-card-title">Database CHECK Constraints</h3>
              <p className="bbc-card-text">
                Ocean physics are enforced directly inside the PostgreSQL catalog: sea temperatures cannot fall below -2.5°C, salinity is strictly bounded, and depth cannot be negative.
              </p>
            </div>
          </div>

          <div className="bbc-quote-callout">
            <div className="bbc-quote-text">
              "Without guaranteed provenance, an ocean anomaly cannot be scientifically distinguished from an uncalibrated thermistor or a corrupted network packet."
            </div>
            <div className="bbc-quote-author">— TideTrace Oceanographic Architecture Group</div>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------
          Chapter 2: Mesopelagic Twilight (200m — 1,000m)
          -------------------------------------------------------------------- */}
      <section id="quality-control" className="bbc-chapter-section">
        {/* Authentic BBC Sea Creatures throughout Chapter 2 */}
        <img src="/landing/StingRay.webp" alt="Giant Oceanic Manta Ray" className="bbc-stingray-decor" />
        <img src="/landing/school01.webp" alt="Deep Fish School" className="bbc-school-chap2" />
        <img src="/landing/right-fish-5.webp" alt="Twilight Pelagic Fish" className="bbc-fish-chap2" />

        <div className="bbc-container">
          <div className="bbc-chapter-header">
            <div className="bbc-chapter-tag">Chapter 02 // Mesopelagic Twilight (200m — 1,000m)</div>
            <h2 className="bbc-chapter-title">Versioned Multi-Tier QC Tests</h2>
            <p className="bbc-chapter-desc">
              TideTrace executes version-controlled quality pipelines across every single observation. Instead of stripping flagged readings, each record receives timestamped verdicts from physical tests.
            </p>
          </div>

          <div className="bbc-feature-grid">
            <div className="bbc-card" onClick={() => onEnterConsole('quality')} style={{ cursor: 'pointer' }}>
              <div className="bbc-card-icon">⚡</div>
              <h3 className="bbc-card-title">Physical Range Limits</h3>
              <p className="bbc-card-text">
                Verifies observation bounds against oceanographic thermodynamic limits. Readings exceeding normal marine bounds are flagged as <code>suspect</code> or <code>fail</code>.
              </p>
            </div>
            <div className="bbc-card" onClick={() => onEnterConsole('quality')} style={{ cursor: 'pointer' }}>
              <div className="bbc-card-icon">📈</div>
              <h3 className="bbc-card-title">Rate-of-Change & Spike Filter</h3>
              <p className="bbc-card-text">
                Calculates numerical second-derivatives between successive temporal readings to instantly detect sensor electrical noise or acoustic transducer spikes.
              </p>
            </div>
            <div className="bbc-card" onClick={() => onEnterConsole('quality')} style={{ cursor: 'pointer' }}>
              <div className="bbc-card-icon">📉</div>
              <h3 className="bbc-card-title">Flatline & Biofouling Detector</h3>
              <p className="bbc-card-text">
                Detects sensor freeze anomalies where marine organisms adhere to optical membranes, generating static identical outputs over extended sampling windows.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------
          Chapter 3: Bathypelagic Midnight (1,000m — 4,000m)
          -------------------------------------------------------------------- */}
      <section id="provenance" className="bbc-chapter-section">
        {/* Authentic BBC Sea Creatures throughout Chapter 3 */}
        <img src="/landing/shark.webp" alt="Oceanic Apex Shark" className="bbc-shark-decor" />
        <img src="/landing/left-fish-5.webp" alt="Midnight Pelagic Fish" className="bbc-fish-chap3" />

        <div className="bbc-container">
          <div className="bbc-chapter-header">
            <div className="bbc-chapter-tag">Chapter 03 // Bathypelagic Midnight (1,000m — 4,000m)</div>
            <h2 className="bbc-chapter-title">Deterministic Replay & Frozen Manifests</h2>
            <p className="bbc-chapter-desc">
              Scientific reproducibility requires that any analysis executed today produces the exact same statistical outputs ten years from now. TideTrace achieves this via frozen analysis manifests.
            </p>
          </div>

          <div className="bbc-feature-grid">
            <div className="bbc-card" onClick={() => onEnterConsole('revisions')} style={{ cursor: 'pointer' }}>
              <div className="bbc-card-icon">📝</div>
              <h3 className="bbc-card-title">Append-Only Curated Revisions</h3>
              <p className="bbc-card-text">
                When oceanographers calibrate a series, raw readings are never updated in place. A new revision row is appended with analyst attribution and mathematical justification.
              </p>
            </div>
            <div className="bbc-card" onClick={() => onEnterConsole('analyses')} style={{ cursor: 'pointer' }}>
              <div className="bbc-card-icon">🔒</div>
              <h3 className="bbc-card-title">Cryptographic Manifest Hashes</h3>
              <p className="bbc-card-text">
                Analyses lock their parameters, observation IDs, and QC rule version hashes into an immutable manifest, enabling deterministic bit-for-bit replay at any time.
              </p>
            </div>
            <div className="bbc-card" onClick={() => onEnterConsole('audit')} style={{ cursor: 'pointer' }}>
              <div className="bbc-card-icon">🔍</div>
              <h3 className="bbc-card-title">Structured Audit Trail</h3>
              <p className="bbc-card-text">
                Every login, ingestion batch, quality rule change, and data revision is recorded into an append-only audit table with IP address, user role, and before/after JSON diffs.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------
          Chapter 4: Benthic Abyss (4,000m — 6,400m)
          -------------------------------------------------------------------- */}
      <section id="database-core" className="bbc-chapter-section">
        {/* Authentic BBC Sea Creatures throughout Chapter 4 */}
        <img src="/landing/left-fish-1.webp" alt="Abyssal Benthic Fish" className="bbc-fish-chap4" />

        <div className="bbc-container">
          <div className="bbc-chapter-header">
            <div className="bbc-chapter-tag">Chapter 04 // Benthic Abyss (4,000m — 6,400m)</div>
            <h2 className="bbc-chapter-title">The PostgreSQL Relational Foundation</h2>
            <p className="bbc-chapter-desc">
              Inspect the physical database catalog running on port 5433 with ACID transactions, Alembic versioned schema migrations, and composite B-Tree indexes.
            </p>
          </div>

          <div className="bbc-stats-banner">
            <div>
              <div className="bbc-stat-number">{dbStats ? dbStats.database_size : '41 MB'}</div>
              <div className="bbc-stat-label">Active Database Disk Footprint</div>
            </div>
            <div>
              <div className="bbc-stat-number">13 MB</div>
              <div className="bbc-stat-label">Observation Table Size</div>
            </div>
            <div>
              <div className="bbc-stat-number">11 MB</div>
              <div className="bbc-stat-label">Composite B-Tree Indexes</div>
            </div>
            <div>
              <div className="bbc-stat-number">PostgreSQL 18.6</div>
              <div className="bbc-stat-label">Underlying Storage Engine</div>
            </div>
          </div>

          <div style={{ textAlign: 'center', marginTop: '40px' }}>
            <button
              className="bbc-launch-btn"
              style={{ fontSize: '14px', padding: '12px 28px', margin: '0 auto' }}
              onClick={() => onEnterConsole('database')}
            >
              <span>Inspect Database Schema & Tables</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------
          Footer Video Section & Big Launch CTA
          -------------------------------------------------------------------- */}
      <footer className="bbc-footer-section">
        <video
          className="bbc-footer-video-bg"
          autoPlay
          loop
          muted
          playsInline
        >
          <source src="/landing/footer_video.mp4" type="video/mp4" />
        </video>

        <div className="bbc-footer-content">
          <div className="bbc-chapter-tag" style={{ color: '#ffffff' }}>Experience The Platform</div>
          <h2 className="bbc-footer-title">Dive into the TideTrace Console</h2>
          <p className="bbc-footer-subtitle">
            Interact with live ingestion streams, run automated QC pipelines, execute deterministic historical replays, and inspect the PostgreSQL relational catalog.
          </p>

          <button className="bbc-big-cta-btn" onClick={() => onEnterConsole('dashboard')}>
            <span>Launch TideTrace Console</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <div className="bbc-footer-bar">
          <div>
            <strong>TideTrace</strong> — Ocean Data Provenance and Integrity Platform
          </div>
          <div>
            PostgreSQL 18.6 • FastAPI • SQLAlchemy 2.0 • React + Vite
          </div>
        </div>
      </footer>
    </div>
  );
};
