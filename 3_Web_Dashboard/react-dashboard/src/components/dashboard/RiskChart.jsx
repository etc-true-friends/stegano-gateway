import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { getRiskLabel, isCdrLog, isPolicyBlockedLog, isSuspiciousLog } from '../../utils/auditLabels';

const RISK_COLORS = {
  HIGH: '#e05c5c',
  MEDIUM: '#d4c5a9',
  LOW: '#7ec8c8',
};

const PROCESS_COLORS = {
  '정상': '#7ec8c8',
  '위험 탐지': '#e05c5c',
  'CDR 무해화': '#1e2a4a',
  '정책 차단/대체': '#8a3ffc',
};

export default function RiskChart({ logs }) {
  const counts = logs.reduce((acc, log) => {
    const lvl = log.risk_level || 'LOW';
    acc[lvl] = (acc[lvl] || 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(counts).map(([name, value]) => ({
    name: getRiskLabel(name),
    value,
    key: name,
  }));

  const processCounts = logs.reduce((acc, log) => {
    if (isPolicyBlockedLog(log)) acc['정책 차단/대체'] = (acc['정책 차단/대체'] || 0) + 1;
    if (isCdrLog(log)) acc['CDR 무해화'] = (acc['CDR 무해화'] || 0) + 1;
    if (isSuspiciousLog(log)) acc['위험 탐지'] = (acc['위험 탐지'] || 0) + 1;
    if (!isSuspiciousLog(log) && !isCdrLog(log) && !isPolicyBlockedLog(log)) {
      acc['정상'] = (acc['정상'] || 0) + 1;
    }
    return acc;
  }, {});

  const barData = ['정상', '위험 탐지', 'CDR 무해화', '정책 차단/대체'].map(k => ({
    name: k,
    count: processCounts[k] || 0,
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
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={0} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e8e0d0', color: '#334155', fontSize: 11, borderRadius: 8 }} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {barData.map((entry, i) => (
                <Cell key={i} fill={PROCESS_COLORS[entry.name] || '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
