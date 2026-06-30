import { getActionBucket, getVerdictBucket } from '../../utils/detectionStats';

const CARDS = [
  { key: 'total', label: '전체 파일', color: '#1e2a4a' },
  { key: 'suspicious', label: '위협 판정', color: '#dc2626' },
  { key: 'clean', label: '정상 판정', color: '#059669' },
  { key: 'processed', label: '처리 완료', color: '#5a7fa8' },
];

export default function DailyStatsSummary({ logs }) {
  const values = logs.reduce((acc, log) => {
    const verdict = getVerdictBucket(log);
    const action = getActionBucket(log);
    acc.total += 1;
    if (verdict === 'suspicious') acc.suspicious += 1;
    if (verdict === 'clean') acc.clean += 1;
    if (['policy', 'quarantine', 'sanitized', 'bypass'].includes(action)) acc.processed += 1;
    return acc;
  }, { total: 0, suspicious: 0, clean: 0, processed: 0 });

  return (
    <div className="stat-grid">
      {CARDS.map(card => (
        <div key={card.key} className="stat-card" style={{ borderTop: `3px solid ${card.color}` }}>
          <div className="stat-label" style={{ color: card.color, marginBottom: 6 }}>
            {card.label}
          </div>
          <div className="stat-value" style={{ color: card.color }}>
            {values[card.key]}건
          </div>
        </div>
      ))}
    </div>
  );
}
