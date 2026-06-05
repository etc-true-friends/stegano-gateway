const RISK_DOT = { HIGH: '🔴', MEDIUM: '🟡', LOW: '🟢' };

export default function RecentEvents({ logs }) {
  const recent = [...logs].reverse().slice(0, 7);

  if (!recent.length) {
    return <div className="empty-state">이벤트 없음</div>;
  }

  return (
    <ul className="event-list">
      {recent.map((log, i) => {
        const verdict = log.verdict || log.action || '-';
        const time = (log.timestamp || '').slice(11, 19);
        return (
          <li key={i} className={`event-item ${verdict !== 'CLEAN' ? 'event-alert' : ''}`}>
            <span className="event-time">{time}</span>
            <span className="event-icon">{RISK_DOT[log.risk_level] || '⚪'}</span>
            <span className="event-name">{log.original_name || '-'}</span>
            <span className={`event-verdict ${verdict !== 'CLEAN' ? 'verdict-suspicious' : 'verdict-clean'}`}>
              {verdict}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
