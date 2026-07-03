import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getActionBucket, getEventDate, getVerdictBucket } from '../../utils/detectionStats';
import { rowsToDailyTrendChart } from '../../utils/reportStats';

const PALETTE = {
  navy: '#1e2a4a',
  beige: '#d4c5a9',
  border: '#e8e0d0',
  muted: '#64748b',
  low: '#7ec8c8',
  high: '#e05c5c',
  policy: '#8a3ffc',
};

function makeDailyRows(logs) {
  const counts = {};

  logs.forEach(log => {
    const date = getEventDate(log);
    if (!date) return;
    if (!counts[date]) {
      counts[date] = {
        date,
        clean: 0,
        suspicious: 0,
        unscanned: 0,
        bypass: 0,
        sanitized: 0,
        quarantine: 0,
        policy: 0,
        mail: 0,
        other: 0,
      };
    }

    const row = counts[date];
    const verdict = getVerdictBucket(log);
    const action = getActionBucket(log);
    row[verdict] = (row[verdict] || 0) + 1;
    row[action] = (row[action] || 0) + 1;
  });

  return Object.values(counts).sort((a, b) => a.date.localeCompare(b.date));
}

export default function DailyTrendChart({ logs = [], rows, mode = 'verdict' }) {
  const data = rows ? rowsToDailyTrendChart(rows) : makeDailyRows(logs);

  if (data.length === 0) {
    return <div className="empty-state">선택한 기간에 탐지 기록이 없습니다</div>;
  }

  const bars = mode === 'action'
    ? [
        { key: 'sanitized', name: 'CDR 무해화', fill: PALETTE.navy },
        { key: 'policy', name: '정책 처리', fill: PALETTE.policy },
        { key: 'quarantine', name: '격리/대체', fill: PALETTE.high },
        { key: 'bypass', name: '정상 통과', fill: PALETTE.low },
        { key: 'mail', name: '메일 첨부', fill: PALETTE.beige },
        { key: 'other', name: '기타', fill: PALETTE.muted },
      ]
    : [
        { key: 'clean', name: '정상', fill: PALETTE.low },
        { key: 'suspicious', name: '위협', fill: PALETTE.high },
        { key: 'unscanned', name: '미검사', fill: PALETTE.beige },
      ];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0e8d8" />
        <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
        <Tooltip
          cursor={{ fill: 'rgba(30, 42, 74, 0.04)' }}
          contentStyle={{
            background: '#ffffff',
            border: `1px solid ${PALETTE.border}`,
            color: PALETTE.navy,
            fontSize: 11,
            borderRadius: 8,
          }}
        />
        <Legend
          wrapperStyle={{ paddingTop: 8 }}
          formatter={(value) => <span style={{ fontSize: 11, color: PALETTE.muted }}>{value}</span>}
        />
        {bars.map(bar => (
          <Bar key={bar.key} dataKey={bar.key} name={bar.name} fill={bar.fill} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
