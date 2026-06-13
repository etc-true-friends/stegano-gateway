import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';

const CARDS = [
  { key: 'total', label: '총 스캔 수', dataKey: 'total' },
  { key: 'suspicious', label: '스테가노 탐지', dataKey: 'suspicious' },
  { key: 'cdr', label: 'CDR 무해화', dataKey: 'cdr' },
  { key: 'rate', label: '평균 위험도', dataKey: 'rate' },
];

function buildSparkData(logs) {
  const grouped = {};
  logs.forEach(log => {
    const date = (log.timestamp || '').slice(0, 10);
    if (!date) return;
    if (!grouped[date]) grouped[date] = { date, total: 0, suspicious: 0, cdr: 0, rateSum: 0 };
    grouped[date].total += 1;
    if (log.verdict === 'SUSPICIOUS' || log.action === 'quarantined' || log.action === 'sanitized') {
      grouped[date].suspicious += 1;
    }
    if (log.action === 'sanitized' || log.action === 'quarantined') {
      grouped[date].cdr += 1;
    }
    grouped[date].rateSum += (log.stego_probability || 0);
  });

  return Object.values(grouped)
    .sort((a, b) => a.date.localeCompare(b.date))
    .map(d => ({
      ...d,
      rate: d.total > 0 ? parseFloat((d.rateSum / d.total).toFixed(1)) : 0
    }));
}

export default function StatCards({ total, suspicious, logs = [] }) {
  const cdr = logs.filter(l => l.action === 'sanitized').length;
  const avgRisk = logs.length > 0
    ? `${(logs.reduce((sum, l) => sum + (l.stego_probability || 0), 0) / logs.length).toFixed(1)}%`
    : '0.0%';

  const sparkData = buildSparkData(logs);
  console.log('sparkData:', sparkData);
  const values = { total, suspicious, cdr, rate: avgRisk };

  return (
    <div className="stat-grid">
      {CARDS.map(c => (
        <div key={c.key} className="stat-card">
          <div className="stat-value" style={{ color: '#1e2a4a' }}>
            {values[c.key]}
          </div>
          <div className="stat-label">{c.label}</div>
          {sparkData.length >= 1 && (
            <div style={{ marginTop: 12 }}>
              <ResponsiveContainer width="100%" height={40}>
                <LineChart data={sparkData}>
                  <Line
                    type="monotone"
                    dataKey={c.dataKey}
                    stroke="#7ec8c8"
                    strokeWidth={1.5}
                    dot={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#fff',
                      border: '1px solid #e2e8f0',
                      fontSize: 10,
                      borderRadius: 4
                    }}
                    formatter={(val) => [val, c.label]}
                    labelFormatter={(label) => label}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}