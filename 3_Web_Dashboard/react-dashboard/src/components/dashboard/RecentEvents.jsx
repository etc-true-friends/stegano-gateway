import { getVerdictLabel, isSuspiciousLog } from '../../utils/auditLabels';

export default function RecentEvents({ logs }) {
  const recent = [...logs].reverse().slice(0, 7);

  if (!recent.length) {
    return <div className="empty-state">이벤트 없음</div>;
  }

  return (
    <ul className="event-list">
      {recent.map((log, i) => {
        const time = (log.timestamp || '').slice(11, 19);
        const isAlert = isSuspiciousLog(log);
        return (
          <li key={i} className={`event-item ${isAlert ? 'event-alert' : ''}`}>
            <span className="event-time">{time}</span>
            <span style={{
              display: 'inline-block',
              width: 8, height: 8,
              borderRadius: '50%',
              background: log.risk_level === 'HIGH' ? '#e05c5c' : log.risk_level === 'MEDIUM' ? '#d4c5a9' : '#7ec8c8',
              flexShrink: 0,
            }}/>
            <span className="event-name">{log.original_name || '-'}</span>
            <span className={`event-verdict ${isAlert ? 'verdict-suspicious' : 'verdict-clean'}`}>
              {getVerdictLabel(log.verdict)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
