import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

const RISK_COLORS = { 
  HIGH: '#e05c5c',
  MEDIUM: '#d4c5a9',
  LOW: '#7ec8c8'
};

const RISK_LABEL = {
  HIGH: '높음',
  MEDIUM: '보통',
  LOW: '낮음'
};

const VERDICT_COLORS = {
  '정상': '#7ec8c8',
  '의심': '#d4c5a9',
  '차단': '#e05c5c'
};

export default function RiskChart({ logs }) {
  const counts = logs.reduce((acc, log) => {
    const lvl = log.risk_level || 'LOW';
    acc[lvl] = (acc[lvl] || 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(counts).map(([name, value]) => ({ 
    name: RISK_LABEL[name] || name, 
    value,
    key: name
  }));

  // 바차트: 판정별 건수
  const verdictCounts = logs.reduce((acc, log) => {
    if (log.action === 'passed') acc['정상'] = (acc['정상'] || 0) + 1;
    else if (log.action === 'sanitized') acc['의심'] = (acc['의심'] || 0) + 1;
    else if (log.action === 'quarantined') acc['차단'] = (acc['차단'] || 0) + 1;
    return acc;
  }, {});

  const barData = ['정상', '의심', '차단'].map(k => ({
    name: k,
    count: verdictCounts[k] || 0
  }));

  if (logs.length === 0) {
    return <div className="empty-state">스캔 기록이 없습니다</div>;
  }

  return (
    <div className="chart-row">
      <div className="chart-half">
        <div className="chart-label">위험도 분포</div>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie 
              data={pieData} 
              dataKey="value" 
              nameKey="name" 
              cx="50%" cy="50%" 
              innerRadius={45}
              outerRadius={70}
            >
              {pieData.map((entry, i) => (
                <Cell key={i} fill={RISK_COLORS[entry.key] || '#5a7fa8'} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e8e0d0', color: '#334155', fontSize: 11, borderRadius: 8 }} />
            <Legend formatter={(value) => <span style={{ fontSize: 11, color: '#64748b' }}>{value}</span>} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-half">
        <div className="chart-label">판정별 처리 현황</div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={barData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0e8d8" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e8e0d0', color: '#334155', fontSize: 11, borderRadius: 8 }} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {barData.map((entry, i) => (
                <Cell key={i} fill={VERDICT_COLORS[entry.name] || '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}