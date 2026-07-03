import { useState } from 'react';
import { Eye } from 'lucide-react';
import PanelCard from '../components/common/PanelCard';
import {
  ALETHEIA_BG,
  ALETHEIA_COLORS,
  ENGINE_BG,
  ENGINE_COLORS,
  getActionLabel,
  getAletheiaResult,
  getAuditLogKey,
  getEngineLabel,
  getRiskLabel,
  getVerdictLabel,
  isPolicyBlockedLog,
} from '../utils/auditLabels';

function getParticipantText(log) {
  const sender = log.sender_email || '-';
  const recipient = log.recipient_email || '-';
  if (sender === '-' && recipient === '-') return '-';
  return `${sender} -> ${recipient}`;
}

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

export default function AuditLogPage({ logs = [], onNavigate }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('전체');

  const filtered = [...logs].reverse().filter(log => {
    const keyword = search.toLowerCase();
    const searchable = [
      log.original_name,
      log.sender_email,
      log.recipient_email,
      log.direction,
      log.action,
      log.detection_engine,
      getEngineLabel(log),
      getAletheiaResult(log),
    ].join(' ').toLowerCase();
    const matchSearch = searchable.includes(keyword);
    const matchFilter = filter === '전체'
      || log.verdict === filter
      || getAletheiaResult(log) === filter
      || (filter === 'POLICY' && isPolicyBlockedLog(log));
    return matchSearch && matchFilter;
  });

  const openDetail = (log) => {
    onNavigate?.('audit-detail', { logKey: getAuditLogKey(log) });
  };

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="감사 로그">
        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input
            type="text"
            placeholder="파일명, 발신자, 수신자, 탐지 엔진 검색..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              flex: 1,
              padding: '7px 12px',
              border: '1px solid #e8e0d0',
              borderRadius: 6,
              fontSize: 12,
              color: '#1e2a4a',
              background: '#faf7f2',
              outline: 'none',
            }}
          />
          {['전체', 'CLEAN', 'SUSPICIOUS', 'SKIPPED', 'UNAVAILABLE', 'POLICY'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '7px 14px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                border: '1px solid #e8e0d0',
                background: filter === f ? '#1e2a4a' : '#faf7f2',
                color: filter === f ? '#ffffff' : '#64748b',
              }}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="log-table-wrap" style={{ maxHeight: 'calc(100vh - 220px)' }}>
          <table className="log-table">
            <thead>
              <tr>
                <th>시각</th>
                <th>방향</th>
                <th>메일 경로</th>
                <th>파일명</th>
                <th>SRNet</th>
                <th>등급</th>
                <th>판정</th>
                <th>탐지 엔진</th>
                <th>Aletheia</th>
                <th>처리</th>
                <th>상세</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={11} className="empty-state">검색 결과가 없습니다</td></tr>
              ) : (
                filtered.map((log, i) => {
                  const verdict = log.verdict || '-';
                  const isClean = verdict === 'CLEAN';
                  const isPolicy = isPolicyBlockedLog(log);
                  return (
                    <tr key={`${getAuditLogKey(log)}-${i}`} className={isClean ? '' : 'row-alert'}>
                      <td>{(log.timestamp || '').slice(0, 19).replace('T', ' ')}</td>
                      <td>{log.direction || '-'}</td>
                      <td style={{ minWidth: 220 }}>{getParticipantText(log)}</td>
                      <td className="cell-filename">{log.original_name || '-'}</td>
                      <td>{typeof log.stego_probability === 'number' ? `${log.stego_probability.toFixed(1)}%` : '-'}</td>
                      <td>
                        <span className={`risk-badge risk-${(log.risk_level || 'LOW').toLowerCase()}`}>
                          {getRiskLabel(log.risk_level)}
                        </span>
                      </td>
                      <td>
                        <span className="verdict-dot" style={{
                          background: isPolicy ? '#8a3ffc' : log.risk_level === 'HIGH' ? '#e05c5c' : log.risk_level === 'MEDIUM' ? '#d4c5a9' : '#7ec8c8',
                        }}/>
                        {isPolicy ? '정책' : getVerdictLabel(verdict)}
                      </td>
                      <td><EngineBadge log={log} /></td>
                      <td><AletheiaBadge log={log} /></td>
                      <td>{getActionLabel(log.action)}</td>
                      <td>
                        <button className="table-icon-btn" onClick={() => openDetail(log)} title="상세 보기" aria-label="상세 보기">
                          <Eye size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </PanelCard>
    </div>
  );
}
