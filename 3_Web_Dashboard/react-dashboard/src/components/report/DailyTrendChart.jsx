import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function DailyTrendChart({ logs }) {
  const counts = {};
  logs.forEach(log => {
    const date = (log.timestamp || '').slice(0, 10);
    if (!date) return;
    if (!counts[date]) counts[date] = { date, total: 0, suspicious: 0 };
    counts[date].total += 1;
    if (log.verdict === 'SUSPICIOUS') counts[date].suspicious += 1;
  });

  const data = Object.values(counts).sort((a, b) => a.date.localeCompare(b.date));

  if (data.length === 0) {
    return <div className="empty-state">선택한 기간에 탐지 기록이 없습니다</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0e8d8" />
        <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
        <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e8e0d0', fontSize: 11, borderRadius: 8 }} />
        <Legend formatter={(value) => <span style={{ fontSize: 11, color: '#64748b' }}>{value}</span>} />
        <Bar dataKey="total" name="전체 스캔" fill="#5a7fa8" radius={[4, 4, 0, 0]} />
        <Bar dataKey="suspicious" name="의심 탐지" fill="#e05c5c" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
