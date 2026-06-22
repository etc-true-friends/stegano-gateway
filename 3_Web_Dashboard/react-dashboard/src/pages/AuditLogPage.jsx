import PanelCard from '../components/common/PanelCard';
import { useState } from 'react';
import { getActionLabel, getRiskLabel, getVerdictLabel } from '../utils/auditLabels';

export default function AuditLogPage({ logs }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('전체');

  const filtered = [...logs].reverse().filter(log => {
    const matchSearch = (log.original_name || '').toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter === '전체' || log.verdict === filter;
    return matchSearch && matchFilter;
  });

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="감사 로그">
        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input
            type="text"
            placeholder="파일명 검색..."
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
          {['전체', 'CLEAN', 'SUSPICIOUS'].map(f => (
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
              {f === 'CLEAN' ? '정상' : f === 'SUSPICIOUS' ? '위험' : f}
            </button>
          ))}
        </div>

        <div className="log-table-wrap" style={{ maxHeight: 'calc(100vh - 220px)' }}>
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
              {filtered.length === 0 ? (
                <tr><td colSpan={6} className="empty-state">검색 결과가 없습니다</td></tr>
              ) : (
                filtered.map((log, i) => {
                  const verdict = log.verdict || '-';
                  const isClean = verdict === 'CLEAN';
                  return (
                    <tr key={i} className={isClean ? '' : 'row-alert'}>
                      <td>{(log.timestamp || '').slice(0, 19).replace('T', ' ')}</td>
                      <td className="cell-filename">{log.original_name || '-'}</td>
                      <td>{typeof log.stego_probability === 'number' ? `${log.stego_probability.toFixed(1)}%` : '-'}</td>
                      <td>
                        <span className={`risk-badge risk-${(log.risk_level || 'LOW').toLowerCase()}`}>
                          {getRiskLabel(log.risk_level)}
                        </span>
                      </td>
                      <td>
                        <span style={{
                          display: 'inline-block',
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          marginRight: 6,
                          background: log.risk_level === 'HIGH' ? '#e05c5c' : log.risk_level === 'MEDIUM' ? '#d4c5a9' : '#7ec8c8',
                        }}/>
                        {getVerdictLabel(verdict)}
                      </td>
                      <td>{getActionLabel(log.action)}</td>
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
