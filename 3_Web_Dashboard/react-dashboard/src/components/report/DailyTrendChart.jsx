import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getActionBucket, getEventDate, getVerdictBucket } from '../../utils/detectionStats';

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

export default function DailyTrendChart({ logs, mode = 'verdict' }) {
  const data = makeDailyRows(logs);

  if (data.length === 0) {
    return <div className="empty-state">선택한 기간에 탐지 기록이 없습니다</div>;
  }

  const bars = mode === 'action'
    ? [
        { key: 'bypass', name: '통과', fill: '#059669' },
        { key: 'sanitized', name: 'CDR 무해화', fill: '#5a7fa8' },
        { key: 'quarantine', name: '격리', fill: '#dc2626' },
        { key: 'policy', name: '정책 처리', fill: '#8a3ffc' },
      ]
    : [
        { key: 'clean', name: '정상', fill: '#059669' },
        { key: 'suspicious', name: '위협', fill: '#dc2626' },
        { key: 'unscanned', name: '미탐지', fill: '#d97706' },
      ];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0e8d8" />
        <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
        <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e8e0d0', fontSize: 11, borderRadius: 8 }} />
        <Legend formatter={(value) => <span style={{ fontSize: 11, color: '#64748b' }}>{value}</span>} />
        {bars.map(bar => (
          <Bar key={bar.key} dataKey={bar.key} name={bar.name} fill={bar.fill} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
