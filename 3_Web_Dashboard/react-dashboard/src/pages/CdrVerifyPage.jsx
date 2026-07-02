import { useEffect, useMemo, useState } from 'react';
import { Eye, ImageOff, Search, ShieldCheck } from 'lucide-react';
import PanelCard from '../components/common/PanelCard';
import { API_BASE } from '../api/gateway';

const PAGE_SIZE = 20;

const PALETTE = {
  navy: '#1e2a4a',
  beige: '#faf7f2',
  border: '#e8e0d0',
  muted: '#64748b',
  low: '#7ec8c8',
  medium: '#d4c5a9',
  high: '#e05c5c',
  policy: '#8a3ffc',
};

function riskMeta(prob) {
  if (prob == null) return { level: '-', verdict: '-', color: PALETTE.muted, bg: '#f8fafc' };
  if (prob >= 75) return { level: 'HIGH', verdict: '의심', color: PALETTE.high, bg: '#fff5f5' };
  if (prob >= 30) return { level: 'MEDIUM', verdict: '주의', color: '#8f7b58', bg: '#fbf7ef' };
  return { level: 'LOW', verdict: '정상', color: '#2b8c8c', bg: '#effafa' };
}

function cdrProcessStatus(log) {
  if (!log.processed_at) return { label: '처리 상태 확인 필요', color: '#8f7b58', bg: '#fbf7ef' };
  return { label: '무해화 완료', color: PALETTE.navy, bg: '#f4f6fb' };
}

function finalAnalysis(log) {
  if (!log.processed_at) return { label: '처리 확인 필요', color: '#8f7b58', bg: '#fbf7ef' };
  if (log.stego_probability >= 30) return { label: '무해화 성공', color: PALETTE.navy, bg: '#f4f6fb' };
  return { label: '정상 통과', color: '#2b8c8c', bg: '#effafa' };
}

function formatKb(value) {
  if (value == null || Number.isNaN(Number(value))) return '-';
  return `${Number(value).toFixed(1)} KB`;
}

function formatFileSize(value) {
  if (value == null || Number.isNaN(Number(value))) return '-';
  const bytes = Number(value);
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
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

function InfoRow({ label, children }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        minHeight: 28,
        flexWrap: 'wrap',
      }}
    >
      <div style={{ width: 112, flexShrink: 0, fontSize: 11, fontWeight: 800, color: PALETTE.muted }}>
        {label}
      </div>
      <div style={{ minWidth: 180, flex: '1 1 220px', color: '#111827', fontWeight: 650, wordBreak: 'break-word' }}>
        {children}
      </div>
    </div>
  );
}

export default function CdrVerifyPage() {
  const [logs, setLogs] = useState([]);
  const [policyLogs, setPolicyLogs] = useState([]);
  const [searchText, setSearchText] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [decodeLoadingId, setDecodeLoadingId] = useState(null);
  const [decodeResults, setDecodeResults] = useState({});
  const [imageErrorIds, setImageErrorIds] = useState({});
  const [imageDimensions, setImageDimensions] = useState({});

  const loadLogs = async () => {
    try {
      const [cdrRes, auditRes] = await Promise.all([
        fetch(`${API_BASE}/cdr/status`),
        fetch(`${API_BASE}/audit`),
      ]);
      const cdrData = await cdrRes.json();
      const auditData = await auditRes.json();
      setLogs(cdrData.logs || []);
      setPolicyLogs((auditData.logs || []).filter(isPolicySanitized).reverse());
    } catch (err) {
      console.error('CDR 로그 조회 실패:', err);
      setLogs([]);
      setPolicyLogs([]);
    }
  };

  const handleDecode = async fileId => {
    if (decodeResults[fileId] !== undefined) return;
    setDecodeLoadingId(fileId);

    try {
      const res = await fetch(`${API_BASE}/decode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id: fileId }),
      });
      const data = await res.json();
      const decodedMessage = data.decoded_message || data.message || data.result || '숨김 데이터 없음';

      setDecodeResults(prev => ({
        ...prev,
        [fileId]: decodedMessage,
      }));
      await loadLogs();
    } catch (err) {
      console.error('decode 실패:', err);
      setDecodeResults(prev => ({
        ...prev,
        [fileId]: '확인 실패',
      }));
    } finally {
      setDecodeLoadingId(null);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchText]);

  const filteredLogs = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();
    if (!keyword) return logs;
    return logs.filter(log => String(log.file_name || '').toLowerCase().includes(keyword));
  }, [logs, searchText]);

  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / PAGE_SIZE));

  const pagedLogs = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredLogs.slice(start, start + PAGE_SIZE);
  }, [filteredLogs, currentPage]);

  useEffect(() => {
    if (currentPage > totalPages) setCurrentPage(totalPages);
  }, [currentPage, totalPages]);

  const pageButtonStyle = disabled => ({
    padding: '7px 14px',
    borderRadius: 6,
    fontSize: 11,
    fontWeight: 700,
    cursor: disabled ? 'not-allowed' : 'pointer',
    border: `1px solid ${PALETTE.border}`,
    background: disabled ? '#e5e7eb' : PALETTE.beige,
    color: disabled ? '#9ca3af' : PALETTE.muted,
  });

  return (
    <PanelCard title="CDR 무해화 현황">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, fontSize: 13, color: '#111827' }}>
        <p style={{ margin: 0, color: PALETTE.muted, fontSize: 12, lineHeight: 1.7 }}>
          첨부 이미지의 CDR 무해화 처리 상태와 문서/첨부파일 정책 대체 내역을 함께 확인합니다.
          이미지 파일은 무해화 전후 정보와 숨김 데이터 확인 결과를, 위험 첨부파일은 안전 대체 상태를 표시합니다.
        </p>

        <div style={{ position: 'relative', maxWidth: 380 }}>
          <Search
            size={15}
            color={PALETTE.muted}
            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }}
          />
          <input
            type="text"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            placeholder="무해화 파일명 검색"
            style={{
              width: '100%',
              height: 36,
              padding: '0 12px 0 34px',
              borderRadius: 6,
              border: '1px solid #d1d5db',
              background: '#ffffff',
              color: '#111827',
              fontSize: 13,
              fontFamily: 'inherit',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {filteredLogs.length === 0 && <div className="empty-state">CDR 무해화 현황이 없습니다.</div>}

        {pagedLogs.map(log => {
          const risk = riskMeta(log.stego_probability);
          const process = cdrProcessStatus(log);
          const final = finalAnalysis(log);
          const isDecodeLoading = decodeLoadingId === log.file_id;
          const decodedResult = decodeResults[log.file_id];
          const isDecoded = decodedResult !== undefined;
          const isDecodeDisabled = isDecodeLoading || isDecoded;
          const hasImageError = imageErrorIds[log.file_id];

          return (
            <div
              key={log.file_id}
              style={{
                border: `1px solid ${PALETTE.border}`,
                borderRadius: 10,
                padding: 18,
                background: '#ffffff',
                color: '#111827',
                display: 'flex',
                flexWrap: 'wrap',
                gap: 22,
                alignItems: 'stretch',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 320, flex: '1 1 560px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  <div
                    title={log.file_name}
                    style={{
                      color: PALETTE.navy,
                      fontSize: 14,
                      fontWeight: 800,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: 420,
                    }}
                  >
                    {log.file_name || '-'}
                  </div>
                  <Pill color={process.color} bg={process.bg}>{process.label}</Pill>
                </div>

                <InfoRow label="원본 탐지 결과">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <Pill color={risk.color} bg={risk.bg}>{risk.level}</Pill>
                    <Pill color={risk.color} bg={risk.bg}>{risk.verdict}</Pill>
                    <span style={{ color: risk.color, fontWeight: 800 }}>
                      {log.stego_probability == null ? '-' : `${Number(log.stego_probability).toFixed(1)}%`}
                    </span>
                  </div>
                </InfoRow>

                <InfoRow label="무해화 처리 결과">
                  <Pill color={process.color} bg={process.bg}>{process.label}</Pill>
                </InfoRow>

                <InfoRow label="파일 크기 변화">
                  <span style={{ color: PALETTE.navy, fontWeight: 800 }}>
                    {formatKb(log.original_kb)} <span style={{ color: PALETTE.muted }}>→</span> {formatKb(log.sanitized_kb)}
                  </span>
                </InfoRow>

                <InfoRow label="이미지 해상도">
                  <span style={{ color: PALETTE.navy, fontWeight: 800 }}>
                    {imageDimensions[log.file_id]
                      ? `${imageDimensions[log.file_id].width} x ${imageDimensions[log.file_id].height}px`
                      : '-'}
                  </span>
                </InfoRow>

                <InfoRow label="최종 처리 결과">
                  <Pill color={final.color} bg={final.bg}>{final.label}</Pill>
                </InfoRow>

                <InfoRow label="숨김 데이터 확인">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, minHeight: 32 }}>
                    <button
                      type="button"
                      onClick={() => handleDecode(log.file_id)}
                      disabled={isDecodeDisabled}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '7px 12px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 800,
                        cursor: isDecodeDisabled ? 'not-allowed' : 'pointer',
                        border: `1px solid ${PALETTE.border}`,
                        background: isDecodeDisabled ? '#eef2f7' : PALETTE.beige,
                        color: isDecodeDisabled ? PALETTE.muted : PALETTE.navy,
                        flexShrink: 0,
                      }}
                    >
                      <Eye size={13} />
                      {isDecodeLoading ? '확인 중' : isDecoded ? '확인 완료' : '확인 실행'}
                    </button>

                    {isDecoded && (
                      <span style={{ color: PALETTE.navy, fontWeight: 650, fontSize: 12.5 }}>
                        {decodedResult}
                      </span>
                    )}
                  </div>
                </InfoRow>
              </div>

              <div
                style={{
                  width: 210,
                  height: 175,
                  flex: '0 0 210px',
                  border: `1px solid ${PALETTE.border}`,
                  borderRadius: 10,
                  background: '#f8fafc',
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {hasImageError ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#94a3b8' }}>
                    <ImageOff size={15} />
                    이미지 없음
                  </span>
                ) : (
                  <img
                    src={`${API_BASE}/cdr/original/${log.file_id}`}
                    alt={log.file_name}
                    onLoad={event => {
                      const { naturalWidth, naturalHeight } = event.currentTarget;
                      setImageDimensions(prev => ({
                        ...prev,
                        [log.file_id]: { width: naturalWidth, height: naturalHeight },
                      }));
                    }}
                    onError={() =>
                      setImageErrorIds(prev => ({
                        ...prev,
                        [log.file_id]: true,
                      }))
                    }
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'contain',
                      display: 'block',
                    }}
                  />
                )}
              </div>
            </div>
          );
        })}

        {filteredLogs.length > PAGE_SIZE && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 12,
              marginTop: 10,
              fontSize: 13,
            }}
          >
            <button
              type="button"
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              style={pageButtonStyle(currentPage === 1)}
            >
              이전
            </button>

            <span style={{ color: PALETTE.muted, fontWeight: 700 }}>
              {currentPage} / {totalPages}
            </span>

            <button
              type="button"
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
              style={pageButtonStyle(currentPage === totalPages)}
            >
              다음
            </button>
          </div>
        )}

        <div
          style={{
            marginTop: 4,
            paddingTop: 18,
            borderTop: `1px solid ${PALETTE.border}`,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <div style={{ color: PALETTE.navy, fontSize: 13, fontWeight: 900 }}>
              문서/첨부파일 정책 대체
            </div>
            <Pill color={PALETTE.policy} bg="#f5f0ff">{policyLogs.length}건</Pill>
          </div>

          {policyLogs.length === 0 ? (
            <div className="empty-state">정책 대체 처리 이력이 없습니다.</div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
                gap: 12,
              }}
            >
              {policyLogs.slice(0, 6).map(log => (
                <div
                  key={`${log.file_id || log.original_name}-${log.timestamp}`}
                  style={{
                    border: `1px solid ${PALETTE.border}`,
                    borderRadius: 10,
                    background: '#fff',
                    padding: 16,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                    <div
                      title={log.original_name}
                      style={{
                        flex: 1,
                        minWidth: 0,
                        color: PALETTE.navy,
                        fontSize: 13.5,
                        fontWeight: 850,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {log.original_name || '-'}
                    </div>
                    <Pill color={PALETTE.policy} bg="#f5f0ff">정책 대체</Pill>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    <InfoRow label="탐지 유형">
                      <Pill color={PALETTE.high} bg="#fff5f5">위험 첨부</Pill>
                    </InfoRow>
                    <InfoRow label="처리 결과">
                      <Pill color={PALETTE.policy} bg="#f5f0ff">안전 안내문 대체</Pill>
                    </InfoRow>
                    <InfoRow label="파일 크기">
                      <span>{formatFileSize(log.attachment_file_size)}</span>
                    </InfoRow>
                    <InfoRow label="메일 방향">
                      <span>{log.direction || '-'}</span>
                    </InfoRow>
                  </div>

                  {(log.sender_email || log.recipient_email) && (
                    <div style={{ color: PALETTE.muted, fontSize: 11.5, fontWeight: 650 }}>
                      {log.sender_email || '-'} <span style={{ color: PALETTE.border }}>→</span> {log.recipient_email || '-'}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </PanelCard>
  );
}
