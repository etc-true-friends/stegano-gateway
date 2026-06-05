const CARDS = [
  { key: 'total', label: 'TOTAL SCANNED', color: '#1e2a4a' },
  { key: 'clean', label: 'CLEAN', color: '#059669' },
  { key: 'suspicious', label: 'SUSPICIOUS', color: '#dc2626' },
  { key: 'rate', label: 'DETECTION RATE', color: '#4263eb' },
];

export default function StatCards({ total, suspicious }) {
  const clean = total - suspicious;
  const rate = total > 0 ? `${((suspicious / total) * 100).toFixed(1)}%` : '0.0%';

  const values = { total, clean, suspicious, rate };

  return (
    <div className="stat-grid">
      {CARDS.map(c => (
        <div key={c.key} className="stat-card">
          <div className="stat-value" style={{ color: c.color }}>
            {values[c.key]}
          </div>
          <div className="stat-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
