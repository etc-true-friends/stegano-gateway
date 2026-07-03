import {
  ALETHEIA_BG,
  ALETHEIA_COLORS,
  ENGINE_BG,
  ENGINE_COLORS,
  getActionLabel,
  getAletheiaResult,
  getEngineLabel,
  getRiskLabel,
  getVerdictLabel,
  isPolicyBlockedLog,
} from '../../utils/auditLabels';

const RISK_DOT = { HIGH: '●', MEDIUM: '●', LOW: '●' };

function EngineBadge({ log }) {
  const engine = getEngineLabel(log);
  if (engine === '-') return <span style={{ color: '#94a3b8' }}>-</span>;

  return (
    <span className="engine-badge" style={{
      color: ENGINE_COLORS[log.detection_engine] || ENGINE_COLORS[engine] || '#64748b',
      background: ENGINE_BG[log.detection_engine] || ENGINE_BG[engine] || '#f1f5f9',
    }}>
      {engine}
    </span>
  );
}

function AletheiaBadge({ log }) {
  const result = getAletheiaResult(log);
  if (result === '-') return <span style={{ color: '#94a3b8' }}>-</span>;

  return (
    <span className="aletheia-badge" style={{
      color: ALETHEIA_COLORS[result],
      background: ALETHEIA_BG[result],
    }}>
      {result}
    </span>
  );
}

export default function AuditLogTable({ logs }) {
  if (!logs.length) {
    return <div className="empty-state">로그 없음 · 파일 스캔 후 기록이 표시됩니다</div>;
  }

  const rows = [...logs].reverse().slice(0, 50);

  return (
    <div className="log-table-wrap">
      <table className="log-table">
        <thead>
          <tr>
            <th>시각</th>
            <th>파일명</th>
            <th>SRNet</th>
            <th>등급</th>
            <th>판정</th>
            <th>탐지 엔진</th>
            <th>Aletheia</th>
            <th>처리</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((log, i) => {
            const verdict = log.verdict || '-';
            const isClean = verdict === 'CLEAN';
            const isPolicy = isPolicyBlockedLog(log);
            return (
              <tr key={i} className={isClean ? '' : 'row-alert'}>
                <td>{(log.timestamp || '').slice(0, 19).replace('T', ' ')}</td>
                <td className="cell-filename">{log.original_name || '-'}</td>
                <td>{typeof log.stego_probability === 'number' ? `${log.stego_probability.toFixed(1)}%` : String(log.stego_probability || '-')}</td>
                <td>
                  <span className={`risk-badge risk-${(log.risk_level || 'LOW').toLowerCase()}`}>
                    {getRiskLabel(log.risk_level)}
                  </span>
                </td>
                <td>{RISK_DOT[log.risk_level] || '●'} {isPolicy ? '정책' : getVerdictLabel(verdict)}</td>
                <td><EngineBadge log={log} /></td>
                <td><AletheiaBadge log={log} /></td>
                <td>{getActionLabel(log.action)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
