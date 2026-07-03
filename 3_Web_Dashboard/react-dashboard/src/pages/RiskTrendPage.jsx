import { useMemo, useState } from 'react';
import { Activity } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import PanelCard from '../components/common/PanelCard';
import DateRangeFilter from '../components/report/DateRangeFilter';
import { useDateRangeFilter } from '../hooks/useDateRangeFilter';
import { makeRiskTrendRows } from '../utils/reportStats';

const PERIODS = [
  { key: 'day', label: '일' },
  { key: 'week', label: '주' },
  { key: 'month', label: '월' },
];

const PALETTE = {
  navy: '#1e2a4a',
  border: '#e8e0d0',
  beige: '#faf7f2',
  muted: '#64748b',
  high: '#e05c5c',
  medium: '#d4c5a9',
  low: '#7ec8c8',
  policy: '#8a3ffc',
};

function MetricCard({ label, value, color = PALETTE.navy }) {
  return (
    <div
      className="stat-card"
      style={{
        borderTop: `3px solid ${color}`,
        background: `linear-gradient(180deg, ${color}10 0%, #ffffff 45%)`,
      }}
    >
      <div className="stat-label" style={{ color, marginBottom: 6 }}>{label}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
    </div>
  );
}

export default function RiskTrendPage({ audit }) {
  const { logs } = audit;
  const [period, setPeriod] = useState('day');
  const { startDate, setStartDate, endDate, setEndDate, activeRange, applyQuickRange, filteredLogs } = useDateRangeFilter(logs, '최근 30일');

  const rows = useMemo(
    () => makeRiskTrendRows(filteredLogs, period),
    [filteredLogs, period],
  );

  const summary = useMemo(() => {
    const totals = rows.reduce((acc, row) => {
      acc.total += row.total_count || 0;
      acc.suspicious += row.suspicious_count || 0;
      acc.high += row.high_count || 0;
      acc.scoreSum += Number(row.score || row.avg_score || 0);
      acc.maxScore = Math.max(acc.maxScore, Number(row.max_score || 0));
      return acc;
    }, { total: 0, suspicious: 0, high: 0, scoreSum: 0, maxScore: 0 });

    return {
      avgScore: rows.length ? totals.scoreSum / rows.length : 0,
      maxScore: totals.maxScore,
      suspicious: totals.suspicious,
      high: totals.high,
    };
  }, [rows]);

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="위험도 추이">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: PALETTE.muted, fontSize: 12, lineHeight: 1.7 }}>
            <Activity size={15} color={PALETTE.navy} />
            <span>SRNet 확률과 위험 등급을 0~100 점수로 환산해 기간별 평균 위험도 추이를 표시합니다.</span>
          </div>

          <DateRangeFilter
            startDate={startDate} setStartDate={setStartDate}
            endDate={endDate} setEndDate={setEndDate}
            activeRange={activeRange} applyQuickRange={applyQuickRange}
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ color: PALETTE.muted, fontSize: 11, fontWeight: 800 }}>집계 단위</span>
            {PERIODS.map(item => (
              <button
                key={item.key}
                type="button"
                onClick={() => setPeriod(item.key)}
                style={{
                  padding: '7px 14px',
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 800,
                  cursor: 'pointer',
                  border: `1px solid ${PALETTE.border}`,
                  background: period === item.key ? PALETTE.navy : PALETTE.beige,
                  color: period === item.key ? '#ffffff' : PALETTE.muted,
                }}
              >
                {item.label}
              </button>
            ))}
            <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: 11, fontWeight: 700 }}>
              감사 로그 집계
            </span>
          </div>
        </div>
      </PanelCard>

      <div className="stat-grid" style={{ marginTop: 16 }}>
        <MetricCard label="평균 위험도" value={`${summary.avgScore.toFixed(1)}%`} color={PALETTE.navy} />
        <MetricCard label="최고 위험도" value={`${summary.maxScore.toFixed(1)}%`} color={PALETTE.high} />
        <MetricCard label="위협 판정" value={`${summary.suspicious}건`} color={PALETTE.policy} />
        <MetricCard label="HIGH 등급" value={`${summary.high}건`} color={PALETTE.medium} />
      </div>

      <div style={{ marginTop: 16 }}>
        <PanelCard title="기간별 위험도(score) 라인 차트">
          {rows.length === 0 ? (
            <div className="empty-state">선택한 기간에 위험도 데이터가 없습니다</div>
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={rows} margin={{ top: 12, right: 20, left: -18, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0e8d8" />
                <XAxis dataKey="bucket" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    background: '#ffffff',
                    border: `1px solid ${PALETTE.border}`,
                    color: PALETTE.navy,
                    fontSize: 11,
                    borderRadius: 8,
                  }}
                  formatter={(value, name) => [
                    `${Number(value).toFixed(1)}%`,
                    name === 'score' ? '평균 위험도' : '최고 위험도',
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  name="평균 위험도"
                  stroke={PALETTE.high}
                  strokeWidth={3}
                  dot={{ r: 3, fill: PALETTE.high }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="max_score"
                  name="최고 위험도"
                  stroke={PALETTE.navy}
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </PanelCard>
      </div>

      <div style={{ marginTop: 16 }}>
        <PanelCard title="기간별 탐지 요약">
          <div className="log-table-wrap" style={{ maxHeight: 360 }}>
            <table className="log-table">
              <thead>
                <tr>
                  <th>기간</th>
                  <th>평균 위험도</th>
                  <th>최고 위험도</th>
                  <th>전체</th>
                  <th>위협</th>
                  <th>HIGH</th>
                  <th>CDR</th>
                  <th>정책</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(row => (
                  <tr key={row.bucket}>
                    <td>{row.bucket}</td>
                    <td>{Number(row.score || row.avg_score || 0).toFixed(1)}%</td>
                    <td>{Number(row.max_score || 0).toFixed(1)}%</td>
                    <td>{row.total_count || 0}</td>
                    <td>{row.suspicious_count || 0}</td>
                    <td>{row.high_count || 0}</td>
                    <td>{row.cdr_count || 0}</td>
                    <td>{row.policy_count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PanelCard>
      </div>
    </div>
  );
}
