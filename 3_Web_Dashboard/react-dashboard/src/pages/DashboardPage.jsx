import PanelCard from '../components/common/PanelCard';
import StatCards from '../components/dashboard/StatCards';
import RiskChart from '../components/dashboard/RiskChart';
import RecentEvents from '../components/dashboard/RecentEvents';
import ExtChart from '../components/dashboard/ExtChart';

export default function DashboardPage({ audit }) {
  const { total_count: total, suspicious_count: suspicious, logs } = audit;

  return (
    <div className="dashboard-grid">
      {/* 상단: 통계 카드 */}
      <div className="grid-full">
        <PanelCard title="탐지 통계">
          <StatCards total={total} suspicious={suspicious} logs={logs} />
        </PanelCard>
      </div>

      {/* 중단: 차트 + 최근 이벤트 */}
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

      {/* 하단: 확장자별 탐지 현황 */}
      <div className="grid-full">
        <PanelCard title="확장자별 탐지 현황">
          <ExtChart logs={logs} />
        </PanelCard>
      </div>
    </div>
  );
}