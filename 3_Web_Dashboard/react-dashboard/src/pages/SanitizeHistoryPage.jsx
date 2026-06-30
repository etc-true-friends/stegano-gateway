import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import PanelCard from '../components/common/PanelCard';
import { fetchCdrStatus } from '../api/gateway';
import { MOCK_CDR_HISTORY } from '../api/mockData';
import { formatKb, formatProb, probColor } from '../utils/cdrLabels';

const PAGE_SIZE = 8;
const PALETTE = {
  navy: '#1e2a4a',
  beige: '#faf7f2',
  border: '#e8e0d0',
  muted: '#64748b',
};

function MetaItem({ label, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ fontSize: 10.5, color: PALETTE.muted, fontWeight: 600 }}>{label}</span>
      <span style={{ fontSize: 12.5, color: PALETTE.navy, fontWeight: 600, lineHeight: 1.5 }}>
        {children}
      </span>
    </div>
  );
}

function BeforeAfterRisk({ before, after }) {
  const reduced =
    before != null && after != null && before > 0
      ? Math.max(0, (1 - after / before) * 100)
      : null;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        rowGap: 8,
        flexWrap: 'wrap',
        padding: '12px 16px',
        borderRadius: 10,
        background: 'linear-gradient(90deg, #fef2f2 0%, #f0fdf4 100%)',
        border: `1px solid ${PALETTE.border}`,
      }}
    >
      <ShieldCheck size={20} color="#059669" style={{ flexShrink: 0 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 9.5, color: PALETTE.muted, fontWeight: 700 }}>무해화 전</div>
          <div style={{ fontSize: 19, fontWeight: 800, color: probColor(before) }}>
            {formatProb(before)}
          </div>
        </div>
        <ArrowRight size={16} color={PALETTE.muted} />
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 9.5, color: PALETTE.muted, fontWeight: 700 }}>무해화 후</div>
          <div style={{ fontSize: 19, fontWeight: 800, color: probColor(after) }}>
            {after == null ? '미검증' : formatProb(after)}
          </div>
        </div>
      </div>
      {reduced != null && (
        <span
          style={{
            marginLeft: 'auto',
            fontSize: 11,
            fontWeight: 700,
            color: '#059669',
            background: '#f0fdf4',
            border: '1px solid #05966933',
            borderRadius: 20,
            padding: '4px 12px',
          }}
        >
          위험도 {reduced.toFixed(1)}% 감소
        </span>
      )}
    </div>
  );
}

function SanitizeCard({ log }) {
  const quarantined = String(log.action || '').toUpperCase().includes('QUARANTINE');

  return (
    <div
      style={{
        border: `1px solid ${PALETTE.border}`,
        borderRadius: 12,
        background: '#fff',
        padding: 18,
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      {/* 헤더: 파일명 + 격리 여부 + 처리 시각 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span
          style={{
            fontSize: 13.5,
            fontWeight: 700,
            color: PALETTE.navy,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: 240,
          }}
          title={log.file_name}
        >
          {log.file_name || '-'}
        </span>
        {quarantined && (
          <span
            style={{
              fontSize: 10.5,
              fontWeight: 700,
              color: '#8a3ffc',
              background: '#f5f0ff',
              borderRadius: 20,
              padding: '3px 10px',
            }}
          >
            원본 격리
          </span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: 11, color: PALETTE.muted }}>
          {(log.processed_at || '').slice(0, 19).replace('T', ' ') || '-'}
        </span>
      </div>

      {/* ⭐ 무해화 전/후 재탐지 위험도 */}
      <BeforeAfterRisk before={log.stego_probability} after={log.rescan_probability} />

      {/* 실측 메타데이터 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
          gap: 12,
          alignContent: 'start',
        }}
      >
        <MetaItem label="크기 변화">
          {formatKb(log.original_kb)} <ArrowRight size={11} style={{ verticalAlign: 'middle' }} />{' '}
          {formatKb(log.sanitized_kb)}
        </MetaItem>
        <MetaItem label="평균 픽셀 변화량">
          {log.avg_pixel_diff != null ? Number(log.avg_pixel_diff).toFixed(3) : '-'}
        </MetaItem>
      </div>
    </div>
  );
}

export default function SanitizeHistoryPage() {
  const [logs, setLogs] = useState([]);
  const [usingMock, setUsingMock] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await fetchCdrStatus();
      setLogs(data.logs || []);
      setUsingMock(false);
    } catch {
      setLogs(MOCK_CDR_HISTORY.logs);
      setUsingMock(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  useEffect(() => {
    setPage(1);
  }, [search]);

  const filtered = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return logs;
    return logs.filter(log => String(log.file_name || '').toLowerCase().includes(keyword));
  }, [logs, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const validRisk = logs.filter(l => l.stego_probability > 0 && l.rescan_probability != null);
  const avgReduction =
    validRisk.length === 0
      ? null
      : (validRisk.reduce((acc, l) => acc + Math.max(0, 1 - l.rescan_probability / l.stego_probability), 0) /
          validRisk.length) *
        100;
  const avgAfter =
    validRisk.length === 0
      ? null
      : validRisk.reduce((acc, l) => acc + l.rescan_probability, 0) / validRisk.length;

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="무해화 이력">
        <p style={{ fontSize: 12, color: PALETTE.muted, lineHeight: 1.7, marginBottom: 14 }}>
          위험으로 판정되어 CDR 무해화를 거친 파일의 실제 처리 내역입니다. 정화 전·후 재탐지
          위험도, 크기 변화, 평균 픽셀 변화량 등 측정값을 확인할 수 있습니다.
          {usingMock && <span style={{ color: '#d97706', fontWeight: 600 }}> (오프라인 · 예시 데이터)</span>}
        </p>

        {/* 요약 카드 — 일별 탐지 통계 요약과 동일한 스타일 */}
        <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 16 }}>
          {[
            { label: '전체 무해화', color: '#1e2a4a', value: `${logs.length}건` },
            {
              label: '평균 위험도 감소',
              color: '#059669',
              value: avgReduction == null ? '-' : `${avgReduction.toFixed(1)}%`,
            },
            {
              label: '평균 무해화 후 위험도',
              color: probColor(avgAfter),
              value: avgAfter == null ? '-' : formatProb(avgAfter),
            },
          ].map(card => (
            <div key={card.label} className="stat-card" style={{ borderTop: `3px solid ${card.color}` }}>
              <div className="stat-label" style={{ color: card.color, marginBottom: 6 }}>
                {card.label}
              </div>
              <div className="stat-value" style={{ color: card.color }}>
                {card.value}
              </div>
            </div>
          ))}
        </div>

        {/* 검색 */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input
            type="text"
            placeholder="파일명 검색..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              flex: '1 1 280px',
              padding: '7px 12px',
              border: `1px solid ${PALETTE.border}`,
              borderRadius: 6,
              fontSize: 12,
              color: PALETTE.navy,
              background: PALETTE.beige,
              outline: 'none',
            }}
          />
        </div>

        {loading ? (
          <div className="empty-state">불러오는 중...</div>
        ) : paged.length === 0 ? (
          <div className="empty-state">무해화 이력이 없습니다.</div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
              gap: 14,
              alignItems: 'start',
            }}
          >
            {paged.map(log => (
              <SanitizeCard key={log.file_id} log={log} />
            ))}
          </div>
        )}

        {filtered.length > PAGE_SIZE && (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 16, fontSize: 12 }}>
            <button
              type="button"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              style={{
                padding: '7px 14px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: page === 1 ? 'not-allowed' : 'pointer',
                border: `1px solid ${PALETTE.border}`,
                background: page === 1 ? '#e5e7eb' : PALETTE.beige,
                color: page === 1 ? '#9ca3af' : PALETTE.muted,
              }}
            >
              이전
            </button>
            <span style={{ color: PALETTE.muted }}>{page} / {totalPages}</span>
            <button
              type="button"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              style={{
                padding: '7px 14px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: page === totalPages ? 'not-allowed' : 'pointer',
                border: `1px solid ${PALETTE.border}`,
                background: page === totalPages ? '#e5e7eb' : PALETTE.beige,
                color: page === totalPages ? '#9ca3af' : PALETTE.muted,
              }}
            >
              다음
            </button>
          </div>
        )}
      </PanelCard>
    </div>
  );
}
