import PanelCard from '../components/common/PanelCard';
import StatCards from '../components/dashboard/StatCards';
import RiskChart from '../components/dashboard/RiskChart';
import RecentEvents from '../components/dashboard/RecentEvents';
import ExtChart from '../components/dashboard/ExtChart';
import AuditLogTable from '../components/dashboard/AuditLogTable';

export default function DashboardPage({ audit }) {
  const { total_count: total, suspicious_count: suspicious, logs } = audit;

  return (
    <div className="dashboard-grid">
      <div className="grid-full">
        <PanelCard title="탐지 통계">
          <StatCards total={total} suspicious={suspicious} logs={logs} />
        </PanelCard>
      </div>

      <div className="grid-two-thirds">
        <PanelCard title="위험도 분포 현황">
          <RiskChart logs={logs} />
        </PanelCard>
      </div>
      <div className="grid-one-third">
        <PanelCard title="최근 이벤트 · 1시간">
          <RecentEvents logs={logs} />
        </PanelCard>
      </div>

      <div className="grid-full">
        <PanelCard title="확장자별 탐지 현황">
          <ExtChart logs={logs} />
        </PanelCard>
      </div>

      <div className="grid-full">
        <PanelCard title="최근 감사 로그">
          <AuditLogTable logs={logs} />
        </PanelCard>
      </div>
    </div>
  );
}
