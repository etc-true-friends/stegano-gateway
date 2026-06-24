const CARDS = [
  { key: 'total', label: '전체 스캔', color: '#1e2a4a' },
  { key: 'suspicious', label: '의심 탐지', color: '#dc2626' },
];

export default function DailyStatsSummary({ logs }) {
  const total = logs.length;
  const suspicious = logs.filter(l => l.verdict === 'SUSPICIOUS').length;

  const values = { total, suspicious };

  return (
    <div className="stat-grid">
      {CARDS.map(c => (
        <div key={c.key} className="stat-card" style={{ borderTop: `3px solid ${c.color}` }}>
          <div className="stat-label" style={{ color: c.color, marginBottom: 6 }}>
            {c.label}
          </div>
          <div className="stat-value" style={{ color: c.color }}>
            {values[c.key]}건
          </div>
        </div>
      ))}
    </div>
  );
}
