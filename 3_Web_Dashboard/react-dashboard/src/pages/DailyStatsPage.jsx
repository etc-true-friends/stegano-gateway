import { useMemo } from 'react';
import PanelCard from '../components/common/PanelCard';
import DateRangeFilter from '../components/report/DateRangeFilter';
import DailyStatsSummary from '../components/report/DailyStatsSummary';
import DailyTrendChart from '../components/report/DailyTrendChart';
import { useDateRangeFilter } from '../hooks/useDateRangeFilter';
import { makeDailyDetectionRows } from '../utils/reportStats';

export default function DailyStatsPage({ audit }) {
  const { logs } = audit;
  const { startDate, setStartDate, endDate, setEndDate, activeRange, applyQuickRange, filteredLogs } = useDateRangeFilter(logs);

  const reportRows = useMemo(
    () => makeDailyDetectionRows(filteredLogs, 'day'),
    [filteredLogs],
  );

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="파일 기준 날짜 검색">
        <DateRangeFilter
          startDate={startDate} setStartDate={setStartDate}
          endDate={endDate} setEndDate={setEndDate}
          activeRange={activeRange} applyQuickRange={applyQuickRange}
        />
      </PanelCard>

      <div
        style={{
          marginTop: 12,
          padding: '10px 14px',
          border: '1px solid #e8e0d0',
          borderRadius: 8,
          background: '#faf7f2',
          color: '#64748b',
          fontSize: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        {[
          ['정상', '#7ec8c8'],
          ['위협', '#e05c5c'],
          ['미검사', '#d4c5a9'],
          ['CDR', '#1e2a4a'],
          ['정책', '#8a3ffc'],
        ].map(([label, color]) => (
          <span key={label} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 9, height: 9, borderRadius: 99, background: color }} />
            {label}
          </span>
        ))}
        <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: 11 }}>
          감사 로그 집계
        </span>
      </div>

      <div style={{ marginTop: 16 }}>
        <PanelCard title="요약">
          <DailyStatsSummary logs={filteredLogs} rows={reportRows} />
        </PanelCard>
      </div>

      <div className="daily-stats-grid" style={{ marginTop: 16 }}>
        <PanelCard title="일별 판정 분포">
          <DailyTrendChart logs={filteredLogs} rows={reportRows} mode="verdict" />
        </PanelCard>
        <PanelCard title="일별 처리 분포">
          <DailyTrendChart logs={filteredLogs} rows={reportRows} mode="action" />
        </PanelCard>
      </div>
    </div>
  );
}
