import PanelCard from '../components/common/PanelCard';
import StatCards from '../components/dashboard/StatCards';
import RiskChart from '../components/dashboard/RiskChart';
import AuditLogTable from '../components/dashboard/AuditLogTable';
import RecentEvents from '../components/dashboard/RecentEvents';

export default function DashboardPage({ audit }) {
  const { total_count: total, suspicious_count: suspicious, logs } = audit;

  return (
    <div className="dashboard-grid">
      {/* 상단: 통계 카드 */}
      <div className="grid-full">
        <PanelCard title="STATISTICS">
          <StatCards total={total} suspicious={suspicious} />
        </PanelCard>
      </div>

      {/* 중단: 차트 + 최근 이벤트 */}
      <div className="grid-two-thirds">
        <PanelCard title="RISK DISTRIBUTION">
          <RiskChart logs={logs} />
        </PanelCard>
      </div>
      <div className="grid-one-third">
        <PanelCard title="RECENT EVENTS · 최근 1시간">
          <RecentEvents logs={logs} />
        </PanelCard>
      </div>

      {/* 하단: 감사 로그 */}
      <div className="grid-full">
        <PanelCard title="AUDIT LOG">
          <AuditLogTable logs={logs} />
        </PanelCard>
      </div>
    </div>
  );
}
