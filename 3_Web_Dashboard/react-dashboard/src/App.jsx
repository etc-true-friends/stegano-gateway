import { useEffect, useState } from 'react';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import DashboardPage from './pages/DashboardPage';
import AuditLogPage from './pages/AuditLogPage';
import DetectionHistoryPage from './pages/DetectionHistoryPage';
import DailyStatsPage from './pages/DailyStatsPage';
import FileTypeReportPage from './pages/FileTypeReportPage';
import RiskTrendPage from './pages/RiskTrendPage';
import ThresholdSettingsPage from './pages/ThresholdSettingsPage';
import QuarantinePage from './pages/QuarantinePage';
import CdrVerifyPage from './pages/CdrVerifyPage';
import SanitizeHistoryPage from './pages/SanitizeHistoryPage';
import AuditLogDetailPage from './pages/AuditLogDetailPage';
import { useAuditLog } from './hooks/useAuditLog';
import './App.css';
import ThreatOverviewPage from './pages/ThreatOverviewPage';

const ROUTES = {
  dashboard: DashboardPage,
  'threat-overview': ThreatOverviewPage,
  audit: AuditLogPage,
  'audit-detail': AuditLogDetailPage,
  'detection-history': DetectionHistoryPage,
  'daily-stats': DailyStatsPage,
  'file-type': FileTypeReportPage,
  'risk-trend': RiskTrendPage,
  threshold: ThresholdSettingsPage,
  quarantine: QuarantinePage,
  cdr: CdrVerifyPage,
  'sanitize-history': SanitizeHistoryPage,
};

function getPageFromHash() {
  const page = window.location.hash.replace(/^#\/?/, '').split('?')[0];
  return ROUTES[page] ? page : 'dashboard';
}

function getParamsFromHash() {
  const query = window.location.hash.split('?')[1] || '';
  return Object.fromEntries(new URLSearchParams(query));
}

export default function App() {
  const [page, setPage] = useState(getPageFromHash);
  const [routeParams, setRouteParams] = useState(getParamsFromHash);
  const { audit, online, usingMock, refresh } = useAuditLog();
  const PageComponent = ROUTES[page] || DashboardPage;

  useEffect(() => {
    const handleHashChange = () => {
      setPage(getPageFromHash());
      setRouteParams(getParamsFromHash());
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigate = (nextPage, params = {}) => {
    const safePage = ROUTES[nextPage] ? nextPage : 'dashboard';
    setPage(safePage);
    setRouteParams(params);
    const query = new URLSearchParams(params).toString();
    const nextHash = `#/${safePage}${query ? `?${query}` : ''}`;
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash;
    }
  };

  const pageProps =
      page === 'audit' || page === 'detection-history' || page === 'quarantine'
          ? { logs: audit.logs, onNavigate: navigate }
          : page === 'audit-detail'
              ? { logs: audit.logs, routeParams, onNavigate: navigate }
          : page === 'cdr' || page === 'threshold' || page === 'sanitize-history' || page === 'threat-overview'
              ? {}
              : { audit };

  return (
    <div className="app-shell">
      <Navbar online={online} usingMock={usingMock} onRefresh={refresh} />
      <div className="app-body">
        <Sidebar activePage={page === 'audit-detail' ? 'audit' : page} onNavigate={navigate} />
        <main className="main-content">
          <PageComponent {...pageProps} />
        </main>
      </div>
    </div>
  );
}
