import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function ExtChart({ logs = [], rows }) {
  const data = rows
    ? rows.map(row => ({
        ext: row.extension === 'unknown' ? '기타' : `.${row.extension}`,
        count: row.suspicious_count || 0,
        avgRisk: row.avg_risk_score || 0,
        mime: row.mime_type || 'unknown',
      })).filter(row => row.count > 0)
        .sort((a, b) => b.count - a.count)
    : Object.entries(logs.reduce((counts, log) => {
        if (log.verdict !== 'SUSPICIOUS') return counts;
        const name = log.original_name || '';
        const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : '기타';
        counts[ext] = (counts[ext] || 0) + 1;
        return counts;
      }, {}))
        .map(([ext, count]) => ({ ext: `.${ext}`, count }))
        .sort((a, b) => b.count - a.count);

  if (data.length === 0) {
    return <div className="empty-state">탐지된 파일이 없습니다</div>;
  }

  const COLORS = ['#e05c5c', '#d4c5a9', '#7ec8c8', '#1e2a4a', '#94a3b8'];

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0e8d8" />
        <XAxis dataKey="ext" tick={{ fill: '#94a3b8', fontSize: 11 }} />
        <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
        <Tooltip
          contentStyle={{ background: '#ffffff', border: '1px solid #e8e0d0', fontSize: 11, borderRadius: 8 }}
          formatter={(val, name, item) => {
            if (name === 'count' && item?.payload?.avgRisk != null) {
              return [`${val}건 · 평균 ${item.payload.avgRisk.toFixed ? item.payload.avgRisk.toFixed(1) : item.payload.avgRisk}%`, '탐지 건수'];
            }
            return [val, '탐지 건수'];
          }}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
