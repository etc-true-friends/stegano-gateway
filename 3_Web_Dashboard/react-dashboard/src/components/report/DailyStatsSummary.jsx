import { getActionBucket, getVerdictBucket } from '../../utils/detectionStats';

const PALETTE = {
  navy: '#1e2a4a',
  low: '#7ec8c8',
  high: '#e05c5c',
  sanitized: '#1e2a4a',
};

const CARDS = [
  { key: 'total', label: '전체 파일', color: PALETTE.navy },
  { key: 'suspicious', label: '위협 판정', color: PALETTE.high },
  { key: 'clean', label: '정상 판정', color: PALETTE.low },
  { key: 'processed', label: '처리 완료', color: PALETTE.sanitized },
];

export default function DailyStatsSummary({ logs = [], rows }) {
  const values = rows
    ? rows.reduce((acc, row) => {
        acc.total += row.total_count || 0;
        acc.suspicious += row.suspicious_count || 0;
        acc.clean += row.clean_count || 0;
        acc.processed += (row.policy_count || 0) + (row.quarantine_count || 0) + (row.cdr_count || 0) + (row.bypass_count || 0);
        return acc;
      }, { total: 0, suspicious: 0, clean: 0, processed: 0 })
    : logs.reduce((acc, log) => {
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
        <div
          key={card.key}
          className="stat-card"
          style={{
            borderTop: `3px solid ${card.color}`,
            background: `linear-gradient(180deg, ${card.color}10 0%, #ffffff 42%)`,
          }}
        >
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
