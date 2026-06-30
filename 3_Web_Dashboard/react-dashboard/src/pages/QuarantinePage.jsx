import PanelCard from '../components/common/PanelCard';
import { getActionLabel, getRiskLabel, isPolicyBlockedLog, normalizeAction } from '../utils/auditLabels';

function isQuarantineLog(log) {
  const action = normalizeAction(log?.action);
  return isPolicyBlockedLog(log) || action.includes('QUARANTINE');
}

function getQuarantineType(log) {
  const action = normalizeAction(log?.action);
  if (isPolicyBlockedLog(log)) return '정책 격리/대체';
  if (action.includes('ARCHIVE')) return '압축파일 내부 격리';
  return '탐지 원본 격리';
}

function getReason(log) {
  if (isPolicyBlockedLog(log)) {
    return '위험 확장자, 위장 파일명, 매크로 문서 등 정책 위반 첨부파일입니다.';
  }
  if (normalizeAction(log?.action).includes('QUARANTINE')) {
    return '스테가노그래피 위험이 탐지되어 원본을 격리하고 CDR 무해화본을 사용합니다.';
  }
  return '-';
}

export default function QuarantinePage({ logs = [] }) {
  const rows = [...logs].filter(isQuarantineLog).reverse();
  const policyCount = rows.filter(isPolicyBlockedLog).length;
  const detectionCount = rows.length - policyCount;

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="격리/대체 현황">
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          gap: 12,
          marginBottom: 16,
        }}>
          <div className="stat-card" style={{ padding: 14 }}>
            <div className="stat-label" style={{ fontSize: 11 }}>전체 격리/대체</div>
            <div className="stat-value">{rows.length}</div>
          </div>
          <div className="stat-card" style={{ padding: 14 }}>
            <div className="stat-label" style={{ fontSize: 11 }}>정책 격리</div>
            <div className="stat-value" style={{ color: '#8a3ffc' }}>{policyCount}</div>
          </div>
          <div className="stat-card" style={{ padding: 14 }}>
            <div className="stat-label" style={{ fontSize: 11 }}>탐지 원본 격리</div>
            <div className="stat-value" style={{ color: '#e05c5c' }}>{detectionCount}</div>
          </div>
        </div>

        <p style={{ fontSize: 12, color: '#64748b', lineHeight: 1.7, marginBottom: 14 }}>
          원본이 격리되었거나 정책 대체가 적용된 첨부파일만 모아 보여줍니다.
        </p>

        <div className="log-table-wrap" style={{ maxHeight: 'calc(100vh - 280px)' }}>
          <table className="log-table">
            <thead>
              <tr>
                <th>시각</th>
                <th>파일명</th>
                <th>구분</th>
                <th>위험도</th>
                <th>탐지 확률</th>
                <th>처리</th>
                <th>사유</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td colSpan={7} className="empty-state">격리 또는 정책 대체 기록이 없습니다.</td></tr>
              ) : (
                rows.map((log, index) => (
                  <tr key={`${log.timestamp}-${index}`} className="row-alert">
                    <td>{(log.timestamp || '').slice(0, 19).replace('T', ' ')}</td>
                    <td className="cell-filename">{log.original_name || '-'}</td>
                    <td>{getQuarantineType(log)}</td>
                    <td>
                      <span className={`risk-badge risk-${(log.risk_level || 'LOW').toLowerCase()}`}>
                        {getRiskLabel(log.risk_level)}
                      </span>
                    </td>
                    <td>{typeof log.stego_probability === 'number' ? `${log.stego_probability.toFixed(1)}%` : '-'}</td>
                    <td>{getActionLabel(log.action)}</td>
                    <td style={{ minWidth: 260 }}>{getReason(log)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </PanelCard>
    </div>
  );
}
