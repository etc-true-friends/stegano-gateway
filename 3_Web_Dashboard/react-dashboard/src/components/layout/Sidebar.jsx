import { LayoutDashboard, Upload } from 'lucide-react';

const PIPELINE_STEPS = [
  { id: '01', label: 'POLICY CHECK', active: false },
  { id: '02', label: 'AI DETECTION', active: true },
  { id: '03', label: 'CDR SANITIZE', active: false },
  { id: '04', label: 'QUARANTINE', active: false },
  { id: '05', label: 'AUDIT LOG', active: false },
];

export default function Sidebar({ activePage, onNavigate, sysInfo }) {
  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        <button
          className={`nav-item ${activePage === 'dashboard' ? 'active' : ''}`}
          onClick={() => onNavigate('dashboard')}
        >
          <LayoutDashboard size={14} />
          DASHBOARD
        </button>
        <button
          className={`nav-item ${activePage === 'scan' ? 'active' : ''}`}
          onClick={() => onNavigate('scan')}
        >
          <Upload size={14} />
          FILE SCAN
        </button>
      </nav>

      <div className="sidebar-section">
        <div className="section-label">// PIPELINE</div>
        {PIPELINE_STEPS.map(s => (
          <div key={s.id} className={`pipeline-step ${s.active ? 'active' : ''}`}>
            {s.id} · {s.label}
          </div>
        ))}
      </div>

      {sysInfo && (
        <div className="sidebar-section">
          <div className="section-label">// SYSTEM</div>
          <div className="sys-info-row">
            <span className="info-key">MODEL</span>
            <span className="info-val">{sysInfo.ai_model || '-'}</span>
          </div>
          <div className="sys-info-row">
            <span className="info-key">DEVICE</span>
            <span className="info-val">{(sysInfo.device || '-').toUpperCase()}</span>
          </div>
          <div className="sys-info-row">
            <span className="info-key">VER</span>
            <span className="info-val">{sysInfo.version || '-'}</span>
          </div>
        </div>
      )}

      <div className="sidebar-section sidebar-footer">
        <div className="section-label">// TEAM</div>
        <div className="sys-info-row">
          <span className="info-val">/etc/friends</span>
        </div>
        <div className="sys-info-row">
          <span className="info-key">구름 정보보호 17기</span>
        </div>
      </div>
    </aside>
  );
}
