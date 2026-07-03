import { useCallback, useEffect, useMemo, useState } from 'react';
import PanelCard from '../components/common/PanelCard';
import DateRangeFilter from '../components/report/DateRangeFilter';
import ExtSummary from '../components/report/ExtSummary';
import ExtChart from '../components/dashboard/ExtChart';
import { fetchFileTypeReport } from '../api/gateway';
import { useDateRangeFilter } from '../hooks/useDateRangeFilter';
import { makeFileTypeRows } from '../utils/reportStats';

export default function FileTypeReportPage({ audit }) {
  const { logs } = audit;
  const { startDate, setStartDate, endDate, setEndDate, activeRange, applyQuickRange, filteredLogs } = useDateRangeFilter(logs);
  const [remoteRows, setRemoteRows] = useState(null);
  const [usingFallback, setUsingFallback] = useState(false);

  const loadReport = useCallback(async () => {
    try {
      const data = await fetchFileTypeReport({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setRemoteRows(data.rows || []);
      setUsingFallback(false);
    } catch {
      setRemoteRows(null);
      setUsingFallback(true);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    const id = setTimeout(loadReport, 0);
    return () => clearTimeout(id);
  }, [loadReport]);

  const reportRows = useMemo(
    () => remoteRows || makeFileTypeRows(filteredLogs),
    [remoteRows, filteredLogs],
  );

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="기간 필터">
        <DateRangeFilter
          startDate={startDate} setStartDate={setStartDate}
          endDate={endDate} setEndDate={setEndDate}
          activeRange={activeRange} applyQuickRange={applyQuickRange}
        />
      </PanelCard>

      <div
        style={{
          marginTop: 12,
          color: '#94a3b8',
          fontSize: 11,
          fontWeight: 700,
          textAlign: 'right',
        }}
      >
        {usingFallback ? '로컬 로그 집계' : 'API 집계'} · 확장자/MIME별 탐지 건수 및 위험도 분포
      </div>

      <div style={{ marginTop: 16 }}>
        <PanelCard title="요약">
          <ExtSummary logs={filteredLogs} rows={reportRows} />
        </PanelCard>
      </div>

      <div style={{ marginTop: 16 }}>
        <PanelCard title="파일 유형별 분석">
          <ExtChart logs={filteredLogs} rows={reportRows} />
        </PanelCard>
      </div>

      <div style={{ marginTop: 16 }}>
        <PanelCard title="확장자/MIME 위험도 분포">
          <div className="log-table-wrap" style={{ maxHeight: 360 }}>
            <table className="log-table">
              <thead>
                <tr>
                  <th>확장자</th>
                  <th>MIME</th>
                  <th>전체</th>
                  <th>탐지</th>
                  <th>HIGH</th>
                  <th>MEDIUM</th>
                  <th>LOW</th>
                  <th>평균 위험도</th>
                </tr>
              </thead>
              <tbody>
                {reportRows.length === 0 ? (
                  <tr><td colSpan={8} className="empty-state">선택한 기간에 파일 유형 데이터가 없습니다</td></tr>
                ) : (
                  reportRows.map(row => (
                    <tr key={`${row.extension}-${row.mime_type}`}>
                      <td>{row.extension === 'unknown' ? '기타' : `.${row.extension}`}</td>
                      <td>{row.mime_type || 'unknown'}</td>
                      <td>{row.total_count || 0}</td>
                      <td>{row.suspicious_count || 0}</td>
                      <td>{row.high_count || 0}</td>
                      <td>{row.medium_count || 0}</td>
                      <td>{row.low_count || 0}</td>
                      <td>{Number(row.avg_risk_score || 0).toFixed(1)}%</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </PanelCard>
      </div>
    </div>
  );
}
