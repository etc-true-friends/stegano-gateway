import { getActionLabel, getRiskLabel, getVerdictLabel } from '../../utils/auditLabels';

const RISK_DOT = { HIGH: '●', MEDIUM: '●', LOW: '●' };

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
            <th>위험도(%)</th>
            <th>등급</th>
            <th>판정</th>
            <th>처리</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((log, i) => {
            const verdict = log.verdict || '-';
            const isClean = verdict === 'CLEAN';
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
                <td>{RISK_DOT[log.risk_level] || '○'} {getVerdictLabel(verdict)}</td>
                <td>{getActionLabel(log.action)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
