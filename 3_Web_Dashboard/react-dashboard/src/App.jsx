import { useState } from 'react';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import DashboardPage from './pages/DashboardPage';
import ScanPage from './pages/ScanPage';
import { useAuditLog } from './hooks/useAuditLog';
import './App.css';

export default function App() {
  const [page, setPage] = useState('dashboard');
  const { audit, sysInfo, online, usingMock, refresh } = useAuditLog();

  return (
    <div className="app-shell">
      <Navbar online={online} usingMock={usingMock} onRefresh={refresh} />
      <div className="app-body">
        <Sidebar activePage={page} onNavigate={setPage} sysInfo={sysInfo} />
        <main className="main-content">
          {page === 'dashboard' && <DashboardPage audit={audit} />}
          {page === 'scan' && <ScanPage />}
        </main>
      </div>
    </div>
  );
}
