import PanelCard from '../components/common/PanelCard';
import { useState } from 'react';
import {
  formatFileSize,
  getActionBucket,
  getActionText,
  getEventDateTime,
  getVerdictBucket,
  getVerdictText,
} from '../utils/detectionStats';

function getParticipantText(log) {
  const sender = log.sender_email || '-';
  const recipient = log.recipient_email || '-';
  if (sender === '-' && recipient === '-') return '-';
  return `${sender} -> ${recipient}`;
}

const FILTERS = [
  { key: 'all', label: '전체' },
  { key: 'clean', label: '정상' },
  { key: 'suspicious', label: '위협' },
  { key: 'unscanned', label: '미탐지' },
  { key: 'policy', label: '정책' },
];

export default function DetectionHistoryPage({ logs }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const filtered = [...logs].reverse().filter(log => {
    const keyword = search.toLowerCase();
    const searchable = [
      log.original_name,
      log.mail_subject,
      log.sender_email,
      log.recipient_email,
      log.direction,
      log.action,
      log.verdict,
      log.attachment_mime_type,
    ].join(' ').toLowerCase();
    const matchSearch = searchable.includes(keyword);
    const verdictBucket = getVerdictBucket(log);
    const actionBucket = getActionBucket(log);
    const matchFilter = filter === 'all' || verdictBucket === filter || actionBucket === filter;
    return matchSearch && matchFilter;
  });

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="탐지 이력">
        <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="메일 제목, 송수신자, 파일명 검색..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              flex: '1 1 320px',
              padding: '7px 12px',
              border: '1px solid #e8e0d0',
              borderRadius: 6,
              fontSize: 12,
              color: '#1e2a4a',
              background: '#faf7f2',
              outline: 'none',
            }}
          />
          {FILTERS.map(item => (
            <button
              key={item.key}
              onClick={() => setFilter(item.key)}
              style={{
                padding: '7px 14px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                border: '1px solid #e8e0d0',
                background: filter === item.key ? '#1e2a4a' : '#faf7f2',
                color: filter === item.key ? '#ffffff' : '#64748b',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="log-table-wrap" style={{ maxHeight: 'calc(100vh - 220px)' }}>
          <table className="log-table">
            <thead>
              <tr>
                <th>파일 기준 시각</th>
                <th>방향</th>
                <th>메일 제목</th>
                <th>메일 경로</th>
                <th>파일명</th>
                <th>형식/크기</th>
                <th>위험도</th>
                <th>판정</th>
                <th>처리</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={9} className="empty-state">검색 결과가 없습니다</td></tr>
              ) : (
                filtered.map((log, i) => {
                  const verdictBucket = getVerdictBucket(log);
                  const isClean = verdictBucket === 'clean' || verdictBucket === 'unscanned';
                  const riskClass = (log.risk_level || 'unknown').toLowerCase();
                  return (
                    <tr key={`${getEventDateTime(log)}-${log.original_name}-${log.attachment_id || i}`} className={isClean ? '' : 'row-alert'}>
                      <td>{getEventDateTime(log).slice(0, 19).replace('T', ' ') || '-'}</td>
                      <td>{log.direction || '-'}</td>
                      <td style={{ minWidth: 180 }}>{log.mail_subject || '-'}</td>
                      <td style={{ minWidth: 220 }}>{getParticipantText(log)}</td>
                      <td className="cell-filename">{log.original_name || '-'}</td>
                      <td>{log.attachment_mime_type || '-'} / {formatFileSize(log.attachment_file_size)}</td>
                      <td>
                        <span className={`risk-badge risk-${riskClass}`}>
                          {log.risk_level || '-'}
                        </span>
                      </td>
                      <td>{getVerdictText(log)}</td>
                      <td>{getActionText(log)}</td>
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
