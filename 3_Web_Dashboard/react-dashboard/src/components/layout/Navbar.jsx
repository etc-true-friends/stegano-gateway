import { Shield, RefreshCw, FlaskConical } from 'lucide-react';

export default function Navbar({ online, usingMock, onRefresh }) {
  return (
    <header className="navbar">
      <div className="navbar-brand">
        <Shield size={18} className="brand-icon" />
        <span className="brand-team">/etc/friends</span>
        <span className="brand-divider">·</span>
        <span className="brand-title">스테가노그래피 탐지 관제</span>
      </div>
      <div className="navbar-right">
        {usingMock && (
          <span className="mock-badge">
            <FlaskConical size={11} />
            DEMO DATA
          </span>
        )}
        <span className={`status-badge ${online ? 'online' : 'offline'}`}>
          ● {online ? 'API ONLINE' : 'API OFFLINE'}
        </span>
        <button className="icon-btn" onClick={onRefresh} title="새로고침">
          <RefreshCw size={14} />
        </button>
      </div>
    </header>
  );
}
