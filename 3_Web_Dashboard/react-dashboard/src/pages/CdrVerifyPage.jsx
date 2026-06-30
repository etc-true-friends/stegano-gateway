import { useEffect, useMemo, useState } from 'react';
import PanelCard from '../components/common/PanelCard';
import { API_BASE } from '../api/gateway';

const PAGE_SIZE = 20;

function classify(prob) {
    if (prob == null) return '-';
    if (prob >= 75) return `HIGH | SUSPICIOUS | ${prob}%`;
    if (prob >= 30) return `MEDIUM | SUSPICIOUS | ${prob}%`;
    return `LOW | CLEAN | ${prob}%`;
}

function cdrProcessStatus(log) {
    if (!log.processed_at) return '처리 상태 확인 불가';
    return '무해화 완료';
}

function finalAnalysis(log) {
    if (!log.processed_at) return '처리 상태 확인 필요';

    if (log.stego_probability >= 30) {
        return 'CDR SUCCESS';
    }

    return 'CLEAN PASS';
}

export default function CdrVerifyPage() {
    const [logs, setLogs] = useState([]);
    const [searchText, setSearchText] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [decodeLoadingId, setDecodeLoadingId] = useState(null);
    const [decodeResults, setDecodeResults] = useState({});
    const [imageErrorIds, setImageErrorIds] = useState({});

    const loadLogs = async () => {
        try {
            const res = await fetch(`${API_BASE}/cdr/status`);
            const data = await res.json();
            setLogs(data.logs || []);
        } catch (err) {
            console.error('CDR 로그 조회 실패:', err);
            setLogs([]);
        }
    };

    const handleDecode = async (fileId) => {
        if (decodeResults[fileId] !== undefined) return;

        setDecodeLoadingId(fileId);

        try {
            const res = await fetch(`${API_BASE}/decode`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ file_id: fileId }),
            });

            const data = await res.json();
            console.log('decode result:', data);

            const decodedMessage =
                data.decoded_message ||
                data.message ||
                data.result ||
                'NOT FOUND';

            setDecodeResults((prev) => ({
                ...prev,
                [fileId]: decodedMessage,
            }));

            await loadLogs();
        } catch (err) {
            console.error('decode 실패:', err);

            setDecodeResults((prev) => ({
                ...prev,
                [fileId]: 'ERROR',
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

        return logs.filter((log) =>
            String(log.file_name || '')
                .toLowerCase()
                .includes(keyword)
        );
    }, [logs, searchText]);

    const totalPages = Math.max(1, Math.ceil(filteredLogs.length / PAGE_SIZE));

    const pagedLogs = useMemo(() => {
        const start = (currentPage - 1) * PAGE_SIZE;
        const end = start + PAGE_SIZE;
        return filteredLogs.slice(start, end);
    }, [filteredLogs, currentPage]);

    useEffect(() => {
        if (currentPage > totalPages) {
            setCurrentPage(totalPages);
        }
    }, [currentPage, totalPages]);

    const rowStyle = {
        display: 'flex',
        alignItems: 'flex-start',
        gap: 14,
        minHeight: 28,
    };

    const labelCellStyle = {
        width: 90,
        flexShrink: 0,
        fontWeight: 600,
        color: '#334155',
    };

    const valueCellStyle = {
        flex: 1,
        color: '#111827',
        wordBreak: 'break-all',
    };

    const decodeButtonStyle = (disabled) => ({
        padding: '7px 14px',
        borderRadius: 6,
        fontSize: 11,
        fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        border: '1px solid #e8e0d0',
        background: disabled ? '#1e2a4a' : '#faf7f2',
        color: disabled ? '#ffffff' : '#64748b',
        flexShrink: 0,
    });

    const pageButtonStyle = (disabled) => ({
        padding: '7px 14px',
        borderRadius: 6,
        fontSize: 11,
        fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        border: '1px solid #e8e0d0',
        background: disabled ? '#e5e7eb' : '#faf7f2',
        color: disabled ? '#9ca3af' : '#64748b',
    });

    return (
        <PanelCard title="CDR 검증 현황">
            <div
                style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 14,
                    fontSize: 13,
                    color: '#111827',
                    fontFamily: 'inherit',
                }}
            >
                <div
                    style={{
                        display: 'flex',
                        justifyContent: 'flex-start',
                        marginBottom: 6,
                    }}
                >
                    <input
                        type="text"
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        placeholder="파일명 검색"
                        style={{
                            width: 350,
                            height: 34,
                            padding: '0 12px',
                            borderRadius: 6,
                            border: '1px solid #d1d5db',
                            background: '#ffffff',
                            color: '#111827',
                            fontSize: 13,
                            fontFamily: 'inherit',
                            outline: 'none',
                        }}
                    />
                </div>

                {filteredLogs.length === 0 && (
                    <div className="empty-state">CDR 검증 로그가 없습니다.</div>
                )}

                {pagedLogs.map((log) => {
                    const isDecodeLoading = decodeLoadingId === log.file_id;
                    const decodedResult = decodeResults[log.file_id];
                    const isDecoded = decodedResult !== undefined;
                    const isDecodeDisabled = isDecodeLoading || isDecoded;
                    const hasImageError = imageErrorIds[log.file_id];

                    return (
                        <div
                            key={log.file_id}
                            style={{
                                border: '1px solid rgba(0,0,0,0.15)',
                                borderRadius: 10,
                                padding: 18,
                                background: '#ffffff',
                                color: '#111827',
                                fontSize: 13,
                                fontFamily: 'inherit',
                                lineHeight: 1.7,
                                display: 'flex',
                                justifyContent: 'space-between',
                                gap: 20,
                            }}
                        >
                            <div
                                style={{
                                    flex: 1,
                                    minWidth: 0,
                                }}
                            >
                                <div style={rowStyle}>
                                    <div style={labelCellStyle}>파일명</div>
                                    <div style={valueCellStyle}>{log.file_name}</div>
                                </div>

                                <div style={rowStyle}>
                                    <div style={labelCellStyle}>원본검사</div>
                                    <div style={valueCellStyle}>
                                        {classify(log.stego_probability)}
                                    </div>
                                </div>

                                <div
                                    style={{
                                        ...rowStyle,
                                        alignItems: 'center',
                                        marginTop: 4,
                                    }}
                                >
                                    <div style={labelCellStyle}>
                                        <button
                                            type="button"
                                            onClick={() => handleDecode(log.file_id)}
                                            disabled={isDecodeDisabled}
                                            style={decodeButtonStyle(isDecodeDisabled)}
                                        >
                                            {isDecodeLoading ? '진행중' : '디코더'}
                                        </button>
                                    </div>

                                    <div style={valueCellStyle}>
                                        {isDecoded && (
                                            <span
                                                style={{
                                                    color: '#111827',
                                                    fontWeight: 500,
                                                    fontSize: 13,
                                                    fontFamily: 'inherit',
                                                }}
                                            >
                                                {decodedResult}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <div style={{ height: 12 }} />

                                <div style={rowStyle}>
                                    <div style={labelCellStyle}>CDR 처리결과</div>
                                    <div style={valueCellStyle}>
                                        {cdrProcessStatus(log)}
                                    </div>
                                </div>

                                <div style={{ height: 12 }} />

                                <div style={rowStyle}>
                                    <div style={labelCellStyle}>최종분석</div>
                                    <div style={valueCellStyle}>
                                        {finalAnalysis(log)}
                                    </div>
                                </div>
                            </div>

                            <div
                                style={{
                                    width: 210,
                                    height: 175,
                                    flexShrink: 0,
                                    border: '1px solid #e5e7eb',
                                    borderRadius: 10,
                                    background: '#f8fafc',
                                    overflow: 'hidden',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                {hasImageError ? (
                                    <span
                                        style={{
                                            fontSize: 12,
                                            color: '#94a3b8',
                                        }}
                                    >
                                        이미지 없음
                                    </span>
                                ) : (
                                    <img
                                        src={`${API_BASE}/cdr/original/${log.file_id}`}
                                        alt={log.file_name}
                                        onError={() =>
                                            setImageErrorIds((prev) => ({
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
                            fontFamily: 'inherit',
                        }}
                    >
                        <button
                            type="button"
                            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                            disabled={currentPage === 1}
                            style={pageButtonStyle(currentPage === 1)}
                        >
                            이전
                        </button>

                        <span>
                            {currentPage} / {totalPages}
                        </span>

                        <button
                            type="button"
                            onClick={() =>
                                setCurrentPage((prev) => Math.min(prev + 1, totalPages))
                            }
                            disabled={currentPage === totalPages}
                            style={pageButtonStyle(currentPage === totalPages)}
                        >
                            다음
                        </button>
                    </div>
                )}
            </div>
        </PanelCard>
    );
}