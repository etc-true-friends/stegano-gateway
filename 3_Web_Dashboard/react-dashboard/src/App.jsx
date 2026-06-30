import { useEffect, useState } from 'react';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import DashboardPage from './pages/DashboardPage';
import AuditLogPage from './pages/AuditLogPage';
import DetectionHistoryPage from './pages/DetectionHistoryPage';
import DailyStatsPage from './pages/DailyStatsPage';
import FileTypeReportPage from './pages/FileTypeReportPage';
import ThresholdSettingsPage from './pages/ThresholdSettingsPage';
import QuarantinePage from './pages/QuarantinePage';
import { useAuditLog } from './hooks/useAuditLog';
import './App.css';

const ROUTES = {
  dashboard: DashboardPage,
  audit: AuditLogPage,
  'detection-history': DetectionHistoryPage,
  'daily-stats': DailyStatsPage,
  'file-type': FileTypeReportPage,
  threshold: ThresholdSettingsPage,
  quarantine: QuarantinePage,
};

function getPageFromHash() {
  const page = window.location.hash.replace(/^#\/?/, '');
  return ROUTES[page] ? page : 'dashboard';
}

export default function App() {
  const [page, setPage] = useState(getPageFromHash);
  const { audit, online, usingMock, refresh } = useAuditLog();
  const PageComponent = ROUTES[page] || DashboardPage;

  useEffect(() => {
    const handleHashChange = () => setPage(getPageFromHash());
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigate = (nextPage) => {
    const safePage = ROUTES[nextPage] ? nextPage : 'dashboard';
    setPage(safePage);
    const nextHash = safePage === 'dashboard' ? '#/dashboard' : `#/${safePage}`;
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash;
    }
  };

  const pageProps = page === 'audit' || page === 'detection-history' || page === 'quarantine'
    ? { logs: audit.logs }
    : { audit };

  return (
    <div className="app-shell">
      <Navbar online={online} usingMock={usingMock} onRefresh={refresh} />
      <div className="app-body">
        <Sidebar activePage={page} onNavigate={navigate} />
        <main className="main-content">
          <PageComponent {...pageProps} />
        </main>
      </div>
    </div>
  );
}
