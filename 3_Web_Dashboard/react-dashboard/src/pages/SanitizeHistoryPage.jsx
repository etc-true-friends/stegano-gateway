import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, FileWarning, Image, Search, ShieldCheck } from 'lucide-react';
import PanelCard from '../components/common/PanelCard';
import { fetchAuditLog, fetchCdrStatus } from '../api/gateway';
import { MOCK_CDR_HISTORY } from '../api/mockData';
import { formatKb, formatProb, probColor } from '../utils/cdrLabels';

const PAGE_SIZE = 10;

const PALETTE = {
  navy: '#1e2a4a',
  beige: '#faf7f2',
  border: '#e8e0d0',
  muted: '#64748b',
  high: '#e05c5c',
  medium: '#d4c5a9',
  low: '#7ec8c8',
  policy: '#8a3ffc',
};

function formatFileSize(value) {
  if (value == null || Number.isNaN(Number(value))) return '-';
  const bytes = Number(value);
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function formatTime(value) {
  return String(value || '').slice(0, 19).replace('T', ' ') || '-';
}

function isPolicySanitized(log) {
  return String(log.action || '').toUpperCase().includes('POLICY');
}

function Pill({ children, color = PALETTE.navy, bg = '#f8fafc' }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        minHeight: 24,
        padding: '3px 10px',
        borderRadius: 999,
        border: `1px solid ${color}22`,
        background: bg,
        color,
        fontSize: 11,
        fontWeight: 800,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </span>
  );
}

function MetaItem({ label, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
      <span style={{ fontSize: 10.5, color: PALETTE.muted, fontWeight: 800 }}>{label}</span>
      <span style={{ fontSize: 12.5, color: PALETTE.navy, fontWeight: 750, lineHeight: 1.5, wordBreak: 'break-word' }}>
        {children}
      </span>
    </div>
  );
}

function DeliveryFlow({ probability, riskLevel }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        rowGap: 8,
        flexWrap: 'wrap',
        padding: '12px 14px',
        borderRadius: 8,
        background: '#fbf7ef',
        border: `1px solid ${PALETTE.border}`,
      }}
    >
      <ShieldCheck size={19} color={PALETTE.navy} style={{ flexShrink: 0 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 9.5, color: PALETTE.muted, fontWeight: 800 }}>원본 탐지율</div>
          <div style={{ fontSize: 19, fontWeight: 900, color: probColor(probability) }}>{formatProb(probability)}</div>
        </div>
        <ArrowRight size={16} color={PALETTE.muted} />
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 9.5, color: PALETTE.muted, fontWeight: 800 }}>전달 결과</div>
          <div style={{ fontSize: 17, fontWeight: 900, color: PALETTE.navy }}>
            무해화본 전달
          </div>
        </div>
      </div>
      <Pill color={PALETTE.navy} bg="#f4f6fb">CDR 무해화 완료</Pill>
      {riskLevel && (
        <Pill color={PALETTE.navy} bg="#f4f6fb">
          종합 처리 등급 {riskLevel}
        </Pill>
      )}
      {riskLevel === 'HIGH' && Number(probability) < 75 && (
        <span style={{ color: PALETTE.muted, fontSize: 11, fontWeight: 650 }}>
          AI 탐지율 외 Aletheia/정책 기준이 반영될 수 있습니다.
        </span>
      )}
    </div>
  );
}

function CdrHistoryCard({ log }) {
  return (
    <article
      style={{
        border: `1px solid ${PALETTE.border}`,
        borderRadius: 10,
        background: '#fff',
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 13,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <Image size={17} color={PALETTE.navy} />
        <span
          title={log.file_name}
          style={{
            flex: '1 1 220px',
            minWidth: 0,
            fontSize: 13.5,
            fontWeight: 850,
            color: PALETTE.navy,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {log.file_name || '-'}
        </span>
        <Pill color={PALETTE.navy} bg="#f4f6fb">이미지 CDR</Pill>
      </div>

      <DeliveryFlow probability={log.stego_probability} riskLevel={log.risk_level} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
        <MetaItem label="파일 크기 변화">
          {formatKb(log.original_kb)} <ArrowRight size={11} style={{ verticalAlign: 'middle' }} /> {formatKb(log.sanitized_kb)}
        </MetaItem>
        <MetaItem label="평균 픽셀 변화량">
          {log.avg_pixel_diff != null ? Number(log.avg_pixel_diff).toFixed(3) : '-'}
        </MetaItem>
        <MetaItem label="처리 시각">{formatTime(log.processed_at)}</MetaItem>
      </div>
    </article>
  );
}

function PolicyHistoryCard({ log }) {
  return (
    <article
      style={{
        border: `1px solid ${PALETTE.border}`,
        borderRadius: 10,
        background: '#fff',
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 13,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <FileWarning size={17} color={PALETTE.policy} />
        <span
          title={log.original_name}
          style={{
            flex: '1 1 220px',
            minWidth: 0,
            fontSize: 13.5,
            fontWeight: 850,
            color: PALETTE.navy,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {log.original_name || '-'}
        </span>
        <Pill color={PALETTE.policy} bg="#f5f0ff">정책 대체</Pill>
      </div>

      <div
        style={{
          padding: '12px 14px',
          borderRadius: 8,
          background: '#fff5f5',
          border: `1px solid ${PALETTE.high}22`,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <Pill color={PALETTE.high} bg="#fff5f5">위험 첨부 탐지</Pill>
        <ArrowRight size={15} color={PALETTE.muted} />
        <Pill color={PALETTE.policy} bg="#f5f0ff">안전 안내문으로 대체</Pill>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
        <MetaItem label="파일 크기">{formatFileSize(log.attachment_file_size)}</MetaItem>
        <MetaItem label="메일 방향">{log.direction || '-'}</MetaItem>
        <MetaItem label="처리 시각">{formatTime(log.timestamp)}</MetaItem>
      </div>

      {(log.sender_email || log.recipient_email) && (
        <div style={{ color: PALETTE.muted, fontSize: 11.5, fontWeight: 650 }}>
          {log.sender_email || '-'} <span style={{ color: PALETTE.border }}>→</span> {log.recipient_email || '-'}
        </div>
      )}
    </article>
  );
}

export default function SanitizeHistoryPage() {
  const [cdrLogs, setCdrLogs] = useState([]);
  const [policyLogs, setPolicyLogs] = useState([]);
  const [usingMock, setUsingMock] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const [cdrData, auditData] = await Promise.all([fetchCdrStatus(), fetchAuditLog()]);
      setCdrLogs(cdrData.logs || []);
      setPolicyLogs((auditData.logs || []).filter(isPolicySanitized));
      setUsingMock(false);
    } catch {
      setCdrLogs(MOCK_CDR_HISTORY.logs);
      setPolicyLogs([]);
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

  const mergedLogs = useMemo(() => {
    const cdrItems = cdrLogs.map(log => ({
      type: 'cdr',
      time: log.processed_at || log.timestamp || '',
      name: log.file_name || '',
      log,
    }));
    const policyItems = policyLogs.map(log => ({
      type: 'policy',
      time: log.timestamp || '',
      name: log.original_name || '',
      log,
    }));

    return [...cdrItems, ...policyItems].sort((a, b) => String(b.time).localeCompare(String(a.time)));
  }, [cdrLogs, policyLogs]);

  const filtered = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return mergedLogs;
    return mergedLogs.filter(item => String(item.name || '').toLowerCase().includes(keyword));
  }, [mergedLogs, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const validOriginalRisk = cdrLogs.filter(log => log.stego_probability != null);
  const avgOriginalRisk =
    validOriginalRisk.length === 0
      ? null
      : validOriginalRisk.reduce((acc, log) => acc + Number(log.stego_probability), 0) / validOriginalRisk.length;

  const validSizeChange = cdrLogs.filter(log => Number(log.original_kb) > 0 && Number(log.sanitized_kb) > 0);
  const avgSizeReduction =
    validSizeChange.length === 0
      ? null
      : (validSizeChange.reduce(
          (acc, log) => acc + Math.max(0, 1 - Number(log.sanitized_kb) / Number(log.original_kb)),
          0
        ) /
          validSizeChange.length) *
        100;

  const stats = [
    { label: '전체 처리 이력', value: `${mergedLogs.length}건`, color: PALETTE.navy },
    { label: '이미지 CDR', value: `${cdrLogs.length}건`, color: PALETTE.navy },
    { label: '정책 대체', value: `${policyLogs.length}건`, color: PALETTE.policy },
    {
      label: '평균 원본 탐지율',
      value: avgOriginalRisk == null ? '-' : formatProb(avgOriginalRisk),
      color: probColor(avgOriginalRisk),
    },
    {
      label: '평균 크기 감소',
      value: avgSizeReduction == null ? '-' : `${avgSizeReduction.toFixed(1)}%`,
      color: '#2b8c8c',
    },
  ];

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="무해화 이력">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, fontSize: 13, color: '#111827' }}>
          <p style={{ fontSize: 12, color: PALETTE.muted, lineHeight: 1.7, margin: 0 }}>
            CDR로 재구성된 이미지와 문서/첨부파일 정책 대체 처리 기록을 시간순으로 확인합니다.
            이미지 파일은 원본 탐지율과 CDR 무해화 전달 결과, 크기 변화를 기록하고 위험 첨부파일은 안전 대체 처리 결과를 남깁니다.
            {usingMock && <span style={{ color: '#8f7b58', fontWeight: 800 }}> 오프라인 예시 데이터 표시 중</span>}
          </p>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              rowGap: 8,
              flexWrap: 'wrap',
              padding: '10px 12px',
              borderRadius: 8,
              border: `1px solid ${PALETTE.border}`,
              background: PALETTE.beige,
              color: PALETTE.muted,
              fontSize: 11.5,
              fontWeight: 700,
              lineHeight: 1.6,
            }}
          >
            <span style={{ color: PALETTE.navy, fontWeight: 900 }}>등급 기준</span>
            <Pill color={PALETTE.high} bg="#fff5f5">HIGH 75% 이상</Pill>
            <Pill color="#8f7b58" bg="#fbf7ef">MEDIUM 30% 이상</Pill>
            <Pill color="#2b8c8c" bg="#effafa">LOW 30% 미만</Pill>
            <span>AI 탐지율 외 Aletheia 의심 또는 문서/첨부파일 정책 탐지도 종합 처리 등급에 반영됩니다.</span>
          </div>

          <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(5, minmax(0, 1fr))' }}>
            {stats.map(card => (
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

          <div style={{ position: 'relative', maxWidth: 420 }}>
            <Search
              size={15}
              color={PALETTE.muted}
              style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }}
            />
            <input
              type="text"
              placeholder="파일명 검색"
              value={search}
              onChange={event => setSearch(event.target.value)}
              style={{
                width: '100%',
                height: 36,
                padding: '0 12px 0 34px',
                border: `1px solid ${PALETTE.border}`,
                borderRadius: 6,
                fontSize: 12,
                color: PALETTE.navy,
                background: '#fff',
                outline: 'none',
                boxSizing: 'border-box',
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
                gridTemplateColumns: 'repeat(auto-fill, minmax(430px, 1fr))',
                gap: 14,
                alignItems: 'start',
              }}
            >
              {paged.map(item =>
                item.type === 'policy' ? (
                  <PolicyHistoryCard key={`policy-${item.log.file_id || item.name}-${item.time}`} log={item.log} />
                ) : (
                  <CdrHistoryCard key={`cdr-${item.log.file_id || item.name}-${item.time}`} log={item.log} />
                )
              )}
            </div>
          )}

          {filtered.length > PAGE_SIZE && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: 12,
                marginTop: 4,
                fontSize: 12,
              }}
            >
              <button
                type="button"
                onClick={() => setPage(prev => Math.max(1, prev - 1))}
                disabled={page === 1}
                style={{
                  padding: '7px 14px',
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: page === 1 ? 'not-allowed' : 'pointer',
                  border: `1px solid ${PALETTE.border}`,
                  background: page === 1 ? '#e5e7eb' : PALETTE.beige,
                  color: page === 1 ? '#9ca3af' : PALETTE.muted,
                }}
              >
                이전
              </button>
              <span style={{ color: PALETTE.muted, fontWeight: 700 }}>
                {page} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                disabled={page === totalPages}
                style={{
                  padding: '7px 14px',
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 700,
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
        </div>
      </PanelCard>
    </div>
  );
}
