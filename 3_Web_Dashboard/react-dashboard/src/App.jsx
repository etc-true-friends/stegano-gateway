import { useState } from 'react';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import DashboardPage from './pages/DashboardPage';
import AuditLogPage from './pages/AuditLogPage';
import DailyStatsPage from './pages/DailyStatsPage';
import FileTypeReportPage from './pages/FileTypeReportPage';
import ThresholdSettingsPage from './pages/ThresholdSettingsPage';
import QuarantinePage from './pages/QuarantinePage';
import CdrVerifyPage from './pages/CdrVerifyPage';
import { useAuditLog } from './hooks/useAuditLog';
import './App.css';

export default function App() {
    const [page, setPage] = useState('dashboard');
    const { audit, online, usingMock, refresh } = useAuditLog();

    return (
        <div className="app-shell">
            <Navbar online={online} usingMock={usingMock} onRefresh={refresh} />
            <div className="app-body">
                <Sidebar activePage={page} onNavigate={setPage} />

                <main className="main-content">
                    {page === 'dashboard' && <DashboardPage audit={audit} />}
                    {page === 'audit' && <AuditLogPage logs={audit.logs} />}
                    {page === 'cdr' && <CdrVerifyPage />}
                    {page === 'daily-stats' && <DailyStatsPage audit={audit} />}
                    {page === 'file-type' && <FileTypeReportPage audit={audit} />}
                    {page === 'threshold' && <ThresholdSettingsPage />}
                    {page === 'quarantine' && <QuarantinePage logs={audit.logs} />}
                </main>
            </div>
        </div>
    );
}