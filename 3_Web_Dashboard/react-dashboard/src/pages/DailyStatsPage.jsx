import PanelCard from '../components/common/PanelCard';
import DateRangeFilter from '../components/report/DateRangeFilter';
import DailyStatsSummary from '../components/report/DailyStatsSummary';
import DailyTrendChart from '../components/report/DailyTrendChart';
import { useDateRangeFilter } from '../hooks/useDateRangeFilter';

export default function DailyStatsPage({ audit }) {
  const { logs } = audit;
  const { startDate, setStartDate, endDate, setEndDate, activeRange, applyQuickRange, filteredLogs } = useDateRangeFilter(logs);

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="기간 필터">
        <DateRangeFilter
          startDate={startDate} setStartDate={setStartDate}
          endDate={endDate} setEndDate={setEndDate}
          activeRange={activeRange} applyQuickRange={applyQuickRange}
        />
      </PanelCard>

      <div style={{ marginTop: 16 }}>
        <PanelCard title="요약">
          <DailyStatsSummary logs={filteredLogs} />
        </PanelCard>
      </div>

      <div style={{ marginTop: 16 }}>
        <PanelCard title="일별 탐지 통계">
          <DailyTrendChart logs={filteredLogs} />
        </PanelCard>
      </div>
    </div>
  );
}
