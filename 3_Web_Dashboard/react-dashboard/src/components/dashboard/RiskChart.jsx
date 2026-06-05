import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

const RISK_COLORS = { HIGH: '#ef4444', MEDIUM: '#f59e0b', LOW: '#10b981' };

export default function RiskChart({ logs }) {
  const counts = logs.reduce((acc, log) => {
    const lvl = log.risk_level || 'LOW';
    acc[lvl] = (acc[lvl] || 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(counts).map(([name, value]) => ({ name, value }));
  const barData = ['HIGH', 'MEDIUM', 'LOW'].map(k => ({ name: k, count: counts[k] || 0 }));

  if (logs.length === 0) {
    return (
      <div className="empty-state">스캔 기록이 없습니다</div>
    );
  }

  return (
    <div className="chart-row">
      <div className="chart-half">
        <div className="chart-label">// 위험도 분포 (파이)</div>
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
              {pieData.map(entry => (
                <Cell key={entry.name} fill={RISK_COLORS[entry.name] || '#5a7fa8'} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', color: '#334155', fontSize: 11, borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-half">
        <div className="chart-label">// 위험도 분포 (바)</div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={barData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', color: '#334155', fontSize: 11, borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }} />
            <Bar dataKey="count" radius={[2, 2, 0, 0]}>
              {barData.map(entry => (
                <Cell key={entry.name} fill={RISK_COLORS[entry.name] || '#4a9eff'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
