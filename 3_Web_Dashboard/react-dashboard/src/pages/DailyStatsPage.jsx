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
      <PanelCard title="파일 기준 날짜 검색">
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

      <div className="daily-stats-grid" style={{ marginTop: 16 }}>
        <PanelCard title="일별 판정 분포">
          <DailyTrendChart logs={filteredLogs} mode="verdict" />
        </PanelCard>
        <PanelCard title="일별 처리 분포">
          <DailyTrendChart logs={filteredLogs} mode="action" />
        </PanelCard>
      </div>
    </div>
  );
}
