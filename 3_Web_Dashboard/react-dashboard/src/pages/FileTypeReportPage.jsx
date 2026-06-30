import PanelCard from '../components/common/PanelCard';
import DateRangeFilter from '../components/report/DateRangeFilter';
import ExtSummary from '../components/report/ExtSummary';
import ExtChart from '../components/dashboard/ExtChart';
import { useDateRangeFilter } from '../hooks/useDateRangeFilter';

export default function FileTypeReportPage({ audit }) {
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
          <ExtSummary logs={filteredLogs} />
        </PanelCard>
      </div>

      <div style={{ marginTop: 16 }}>
        <PanelCard title="파일 유형별 분석">
          <ExtChart logs={filteredLogs} />
        </PanelCard>
      </div>
    </div>
  );
}
