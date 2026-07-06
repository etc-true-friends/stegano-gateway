import { useEffect, useMemo, useState } from 'react';
import {
    fetchThreatOverview,
    recordThreatOverviewView,
    heartbeatThreatOverview,
} from '../api/gateway';

const number = (value) => {
    const numeric = Number(value ?? 0);
    return Number.isNaN(numeric) ? 0 : numeric;
};

const percent = (value) => {
    if (value === null || value === undefined || value === '') return '-';

    const numeric = Number(value);

    if (Number.isNaN(numeric)) return '-';

    return `${numeric.toFixed(1).replace('.0', '')}%`;
};

const formatDateTime = (value) => {
    if (!value) return '-';

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value).replace('T', ' ').slice(0, 19);
    }

    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    const hh = String(date.getHours()).padStart(2, '0');
    const mi = String(date.getMinutes()).padStart(2, '0');
    const ss = String(date.getSeconds()).padStart(2, '0');

    return `${yyyy}-${mm}-${dd} ${hh}:${mi}:${ss}`;
};

const statusClass = (status) => {
    const normalized = String(status || '').toUpperCase();

    if (normalized === 'RUNNING' || normalized === 'HEALTHY') return 'running';
    if (normalized === 'DEGRADED') return 'degraded';
    if (normalized === 'DOWN' || normalized === 'STOPPED' || normalized === 'ERROR') return 'down';

    return 'unknown';
};

const riskClass = (risk) => {
    const normalized = String(risk || '').toUpperCase();

    if (normalized === 'HIGH') return 'high';
    if (normalized === 'MEDIUM') return 'medium';
    if (normalized === 'LOW') return 'low';

    return 'unknown';
};

const probabilityRiskClass = (value) => {
    const numeric = Number(value ?? 0);

    if (numeric >= 75) return 'high';
    if (numeric >= 30) return 'medium';
    return 'low';
};

const maxValue = (obj) => {
    const values = Object.values(obj || {}).map((value) => number(value));
    return Math.max(...values, 1);
};

const recordPageViewOncePerLoad = () => {
    if (typeof window === 'undefined') return true;

    if (window.__threatOverviewViewRecorded) {
        return false;
    }

    window.__threatOverviewViewRecorded = true;
    return true;
};

function SummaryCard({ label, value, subText, tone = 'default' }) {
    return (
        <div className={`summary-card ${tone}`}>
            <div className="summary-label">{label}</div>
            <div className="summary-value">{value}</div>
            {subText && <div className="summary-sub">{subText}</div>}
        </div>
    );
}

function BarRow({ label, value, max, tone = 'default' }) {
    const safeValue = number(value);
    const width = max > 0 ? Math.min((safeValue / max) * 100, 100) : 0;

    return (
        <div className="bar-row">
            <div className="bar-label">{label}</div>
            <div className="bar-track">
                <div className={`bar-fill ${tone}`} style={{ width: `${width}%` }} />
            </div>
            <div className="bar-value">{safeValue}</div>
        </div>
    );
}

function SmallMetric({ label, value, unit = '' }) {
    return (
        <div className="small-metric">
            <span>{label}</span>
            <strong>
                {value}
                {unit}
            </strong>
        </div>
    );
}

export default function ThreatOverviewPage() {
    const [overview, setOverview] = useState(null);
    const [visitStats, setVisitStats] = useState({
        total_views: 0,
        current_visitors: 0,
    });
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');

    const loadOverview = async ({ showLoading = false } = {}) => {
        try {
            if (showLoading) {
                setLoading(true);
            }

            setErrorMessage('');

            const data = await fetchThreatOverview();
            setOverview(data);
        } catch (error) {
            console.error('위협 현황 조회 실패:', error);
            setErrorMessage('위협 현황 데이터를 불러오지 못했습니다. 백엔드 API와 VITE_API_BASE를 확인하세요.');
        } finally {
            if (showLoading) {
                setLoading(false);
            }
        }
    };

    const loadVisitStats = async (increaseView = false) => {
        try {
            const data = increaseView
                ? await recordThreatOverviewView()
                : await heartbeatThreatOverview();

            setVisitStats({
                total_views: number(data?.total_views),
                current_visitors: number(data?.current_visitors),
            });
        } catch (error) {
            console.error('방문자 통계 조회 실패:', error);
        }
    };

    const handleRefresh = async () => {
        try {
            setRefreshing(true);

            await Promise.all([
                loadOverview({ showLoading: false }),
                loadVisitStats(true),
            ]);
        } finally {
            setRefreshing(false);
        }
    };

    useEffect(() => {
        loadOverview({ showLoading: true });

        const shouldIncreaseView = recordPageViewOncePerLoad();
        loadVisitStats(shouldIncreaseView);

        const timer = setInterval(() => {
            loadVisitStats(false);
        }, 15000);

        return () => {
            clearInterval(timer);
        };
    }, []);

    const summary = overview?.summary || {};
    const mes = overview?.mes_process || {};
    const wms = overview?.wms_inventory || {};
    const erp = overview?.erp_metrics || {};
    const riskDistribution = overview?.risk_distribution || {};
    const directionDistribution = overview?.direction_distribution || {};
    const actionDistribution = overview?.action_distribution || {};
    const extensionDistribution = overview?.extension_distribution || {};
    const systemStatus = overview?.system_status || [];
    const recentEvents = overview?.recent_events || [];
    const recentCdr = overview?.recent_cdr || [];

    const operationImpact = useMemo(() => {
        return {
            mesImpact: number(mes.cdr_processed),
            wmsImpact: number(wms.quarantine_storage),
            erpImpact: number(summary.policy_blocked),
        };
    }, [mes.cdr_processed, wms.quarantine_storage, summary.policy_blocked]);

    const riskMax = maxValue(riskDistribution);
    const directionMax = maxValue(directionDistribution);
    const actionMax = maxValue(actionDistribution);
    const extensionMax = maxValue(extensionDistribution);

    if (loading) {
        return (
            <div className="threat-overview-page">
                <style>{styles}</style>
                <div className="loading-box">위협 현황 데이터를 불러오는 중입니다...</div>
            </div>
        );
    }

    if (errorMessage && !overview) {
        return (
            <div className="threat-overview-page">
                <style>{styles}</style>
                <div className="error-box">
                    <strong>조회 실패</strong>
                    <p>{errorMessage}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="threat-overview-page">
            <style>{styles}</style>

            <div className="overview-header">
                <div className="overview-title-area">
                    <h1>위협 현황</h1>
                    <span className="generated-text">
            Generated · {formatDateTime(overview?.generated_at)}
          </span>
                </div>

                <div className="header-actions">
                    <div className="visit-stats">
                        <div className="visit-stat">
                            <span>총 조회수</span>
                            <strong>{number(visitStats.total_views)}</strong>
                        </div>

                        <div className="visit-stat">
                            <span>현재 방문자</span>
                            <strong>{number(visitStats.current_visitors)}</strong>
                        </div>
                    </div>

                    <button
                        type="button"
                        className="refresh-button"
                        onClick={handleRefresh}
                        disabled={refreshing}
                    >
                        {refreshing ? '새로고침 중' : '새로고침'}
                    </button>
                </div>
            </div>

            {errorMessage && (
                <div className="inline-error">
                    {errorMessage}
                </div>
            )}

            <div className="summary-grid">
                <SummaryCard
                    label="전체 파일"
                    value={number(summary.total_files)}
                    subText={`스캔 ${number(summary.scanned_files)}건`}
                    tone="navy"
                />
                <SummaryCard
                    label="위협 탐지"
                    value={number(summary.suspicious_files)}
                    subText={`위협률 ${percent(summary.threat_rate)}`}
                    tone="red"
                />
                <SummaryCard
                    label="격리"
                    value={number(summary.quarantined)}
                    subText="Quarantine"
                    tone="orange"
                />
                <SummaryCard
                    label="정상 전달"
                    value={number(summary.delivered)}
                    subText={`전달률 ${percent(summary.delivery_rate)}`}
                    tone="green"
                />
            </div>

            <div className="overview-grid">
                <div className="left-column">
                    <div className="overview-card">
                        <div className="card-header">
                            <h3>MES 보안 처리 공정</h3>
                            <span>Process Flow</span>
                        </div>

                        <div className="process-grid">
                            <SmallMetric label="수신" value={number(mes.received)} />
                            <SmallMetric label="AI 검사" value={number(mes.ai_scanned)} />
                            <SmallMetric label="판정 완료" value={number(mes.judged)} />
                            <SmallMetric label="CDR 처리" value={number(mes.cdr_processed)} />
                            <SmallMetric label="격리" value={number(mes.quarantined)} />
                            <SmallMetric label="전달" value={number(mes.delivered)} />
                        </div>
                    </div>

                    <div className="overview-card operation-impact-card">
                        <div className="card-header">
                            <h3>MES/WMS/ERP 업무 영향도</h3>
                            <span>Business Impact</span>
                        </div>

                        <div className="impact-list">
                            <div className="impact-row">
                                <div>
                                    <strong>MES</strong>
                                    <p>AI 검사 및 CDR 공정 개입</p>
                                </div>
                                <span className="impact-count high">{operationImpact.mesImpact}건</span>
                            </div>

                            <div className="impact-row">
                                <div>
                                    <strong>WMS</strong>
                                    <p>격리 저장소 보류 파일</p>
                                </div>
                                <span className="impact-count medium">{operationImpact.wmsImpact}건</span>
                            </div>

                            <div className="impact-row">
                                <div>
                                    <strong>ERP</strong>
                                    <p>정책 위반 검토 필요</p>
                                </div>
                                <span className="impact-count low">{operationImpact.erpImpact}건</span>
                            </div>
                        </div>
                    </div>

                    <div className="overview-card">
                        <div className="card-header">
                            <h3>시스템 상태</h3>
                            <span>RUNNING · DEGRADED · DOWN</span>
                        </div>

                        <div className="status-list">
                            {systemStatus.map((item) => (
                                <div className="status-row" key={`${item.name}-${item.type}`}>
                                    <div>
                                        <strong>{item.name}</strong>
                                        <p>
                                            {item.type} · {item.detail}
                                        </p>
                                        {item.last_activity_label && (
                                            <p className="last-activity">
                                                {item.last_activity_label} · {formatDateTime(item.last_activity_at)}
                                            </p>
                                        )}
                                    </div>
                                    <span className={`status-badge ${statusClass(item.status)}`}>
                    {item.status || 'UNKNOWN'}
                  </span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="overview-card">
                        <div className="card-header">
                            <h3>최근 CDR 처리</h3>
                            <span>Sanitization</span>
                        </div>

                        <div className="cdr-list">
                            {recentCdr.length === 0 ? (
                                <div className="empty-text">CDR 처리 이력이 없습니다.</div>
                            ) : (
                                recentCdr.map((item, index) => (
                                    <div className="cdr-row" key={`${item.file_id}-${index}`}>
                                        <div>
                                            <strong>{item.file_name || '-'}</strong>
                                            <p>{formatDateTime(item.processed_at)}</p>
                                        </div>
                                        <div className="cdr-score">
                                            <span className={`cdr-prob ${probabilityRiskClass(item.stego_probability)}`}>
                                                원본 탐지율 {percent(item.stego_probability)}
                                            </span>

                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>

                <div className="right-column">
                    <div className="overview-card">
                        <div className="card-header">
                            <h3>ERP 운영 KPI</h3>
                            <span>Security Metrics</span>
                        </div>

                        <div className="kpi-grid">
                            <SmallMetric label="위협률" value={percent(erp.threat_rate)}/>
                            <SmallMetric label="정상률" value={percent(erp.clean_rate)}/>
                            <SmallMetric label="격리율" value={percent(erp.quarantine_rate)}/>
                            <SmallMetric label="정책 위반율" value={percent(erp.policy_violation_rate)}/>
                            <SmallMetric label="CDR 전환율" value={percent(erp.cdr_conversion_rate)}/>
                            <SmallMetric label="평균 위험 감소" value={percent(erp.avg_risk_reduction)}/>
                        </div>

                        <div className="risk-change">
                            <span>무해화 전/후 평균 위험도</span>
                            <strong>
                                {percent(erp.avg_before_risk)} → {percent(erp.avg_after_risk)}
                            </strong>
                        </div>
                    </div>

                    <div className="overview-card">
                        <div className="card-header">
                            <h3>위험도 분포</h3>
                            <span>Risk Level</span>
                        </div>

                        <div className="bar-list">
                            <BarRow label="HIGH" value={riskDistribution.HIGH} max={riskMax} tone="red"/>
                            <BarRow label="MEDIUM" value={riskDistribution.MEDIUM} max={riskMax} tone="orange"/>
                            <BarRow label="LOW" value={riskDistribution.LOW} max={riskMax} tone="green"/>
                            <BarRow label="UNKNOWN" value={riskDistribution.UNKNOWN} max={riskMax} tone="gray"/>
                        </div>
                    </div>

                    <div className="overview-card">
                        <div className="card-header">
                            <h3>반입/반출 분포</h3>
                            <span>WMS Flow</span>
                        </div>

                        <div className="bar-list">
                            <BarRow label="INBOUND" value={directionDistribution.INBOUND} max={directionMax}
                                    tone="navy"/>
                            <BarRow label="OUTBOUND" value={directionDistribution.OUTBOUND} max={directionMax}
                                    tone="navy"/>
                            <BarRow label="UNKNOWN" value={directionDistribution.UNKNOWN} max={directionMax}
                                    tone="gray"/>
                        </div>
                    </div>

                    <div className="overview-card">
                        <div className="card-header">
                            <h3>처리 액션 분포</h3>
                            <span>Action</span>
                        </div>

                        <div className="bar-list action-bar-list">
                            {Object.keys(actionDistribution).length === 0 ? (
                                <div className="empty-text">처리 액션 데이터가 없습니다.</div>
                            ) : (
                                Object.entries(actionDistribution).map(([label, value]) => (
                                    <BarRow key={label} label={label} value={value} max={actionMax} tone="navy"/>
                                ))
                            )}
                        </div>
                    </div>

                    <div className="overview-card">
                        <div className="card-header">
                            <h3>파일 확장자 분포</h3>
                            <span>File Type</span>
                        </div>

                        <div className="bar-list">
                            {Object.keys(extensionDistribution).length === 0 ? (
                                <div className="empty-text">파일 확장자 데이터가 없습니다.</div>
                            ) : (
                                Object.entries(extensionDistribution).slice(0, 6).map(([label, value]) => (
                                    <BarRow key={label} label={label.toUpperCase()} value={value} max={extensionMax}
                                            tone="orange"/>
                                ))
                            )}
                        </div>
                    </div>
                    <div className="overview-card recent-card">
                        <div className="card-header">
                            <h3>최근 위험 이벤트</h3>
                            <span>Latest Events</span>
                        </div>

                        <div className="event-table-wrap">
                            <table className="event-table">
                                <thead>
                                <tr>
                                    <th>시각</th>
                                    <th>파일명</th>
                                    <th>위험도</th>
                                    <th>처리</th>
                                </tr>
                                </thead>
                                <tbody>
                                {recentEvents.length === 0 ? (
                                    <tr>
                                        <td colSpan="4" className="empty-cell">
                                            최근 이벤트가 없습니다.
                                        </td>
                                    </tr>
                                ) : (
                                    recentEvents.map((event, index) => (
                                        <tr key={`${event.file_id || event.original_name}-${index}`}>
                                            <td>{formatDateTime(event.timestamp || event.mail_sent_at)}</td>
                                            <td className="file-name" title={event.original_name || '-'}>
                                                {event.original_name || '-'}
                                            </td>
                                            <td>
                          <span className={`risk-badge ${riskClass(event.risk_level)}`}>
                            {event.risk_level || 'UNKNOWN'}
                          </span>
                                            </td>
                                            <td>{event.action || '-'}</td>
                                        </tr>
                                    ))
                                )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

const styles = `
.threat-overview-page {
  min-height: 100vh;
  padding: 28px;
  background: #f4efe7;
  color: #0b1b44;
  box-sizing: border-box;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 22px;
}

.overview-title-area h1 {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.overview-title-area p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
}

.generated-text {
  display: inline-block;
  margin-top: 8px;
  color: #94a3b8;
  font-size: 12px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.visit-stats {
  display: flex;
  align-items: center;
  gap: 10px;
}

.visit-stat {
  min-width: 92px;
}

.visit-stat span {
  display: block;
  color: #64748b;
  font-size: 12px;
  margin-bottom: 4px;
}

.visit-stat strong {
  display: block;
  color: #0b1b44;
  font-size: 18px;
  font-weight: 600;
}

.refresh-button {
  height: 42px;
  padding: 0 16px;
  border: 1px solid #d8c7ae;
  border-radius: 12px;
  background: #0b1b44;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}

.refresh-button:hover {
  opacity: 0.9;
}

.refresh-button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.inline-error {
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid #fecaca;
  border-radius: 12px;
  background: #fff1f2;
  color: #b91c1c;
  font-size: 13px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.summary-card {
  padding: 18px;
  border: 1px solid #eadfcd;
  border-radius: 18px;
  background: #fffaf3;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.summary-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 600;
}

.summary-value {
  margin-top: 8px;
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.summary-sub {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.summary-card.navy .summary-value {
  color: #16244d;
}

.summary-card.red .summary-value {
  color: #e05c5c;
}

.summary-card.orange .summary-value {
  color: #8a6a2f;
}

.summary-card.green .summary-value {
  color: #008f72;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(420px, 0.85fr);
  gap: 22px;
  align-items: start;
}

.left-column,
.right-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-card {
  border: 1px solid #eadfcd;
  border-radius: 18px;
  background: #fffaf3;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.card-header {
  min-height: 52px;
  padding: 0 18px;
  border-bottom: 1px solid #eadfcd;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.card-header h3 {
  position: relative;
  margin: 0;
  padding-left: 12px;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.card-header h3::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  width: 4px;
  height: 16px;
  border-radius: 99px;
  background: #16244d;
}

.card-header span {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.process-grid,
.kpi-grid {
  padding: 18px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.small-metric {
  padding: 14px;
  border: 1px solid #eadfcd;
  border-radius: 14px;
  background: #fff;
}

.small-metric span {
  display: block;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.small-metric strong {
  display: block;
  margin-top: 8px;
  font-size: 22px;
  font-weight: 700;
  color: #0b1b44;
  letter-spacing: -0.02em;
}

.operation-impact-card {
  margin-top: 0;
}

.impact-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
}

.impact-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid #eadfcd;
  border-radius: 12px;
  background: #fffaf3;
}

.impact-row strong {
  color: #0b1b44;
  font-size: 15px;
  font-weight: 700;
}

.impact-row p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.impact-count {
  min-width: 58px;
  text-align: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.impact-count.high {
  color: #e05c5c;
  background: #fdf1ef;
}

.impact-count.medium {
  color: #8a6a2f;
  background: #f4ead7;
}

.impact-count.low {
  color: #1e2a4a;
  background: #e7eef0;
}

.status-list {
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid #f0e3d1;
}

.status-row:last-child {
  border-bottom: none;
}

.status-row strong {
  font-size: 14px;
  font-weight: 700;
}

.status-row p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
}

.status-row .last-activity {
  margin-top: 3px;
  color: #94a3b8;
  font-size: 11px;
}

.status-badge {
  min-width: 86px;
  padding: 6px 10px;
  border-radius: 999px;
  text-align: center;
  font-size: 11px;
  font-weight: 600;
}

.status-badge.running {
  color: #008f72;
  background: #dff5ed;
}

.status-badge.degraded {
  color: #b45309;
  background: #fef3c7;
}

.status-badge.down {
  color: #b91c1c;
  background: #fee2e2;
}

.status-badge.unknown {
  color: #475569;
  background: #e2e8f0;
}

.risk-change {
  margin: 0 18px 18px;
  padding: 14px 16px;
  border: 1px solid #eadfcd;
  border-radius: 14px;
  background: #fff;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
}

.risk-change span {
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
}

.risk-change strong {
  font-size: 15px;
  font-weight: 700;
}

.bar-list {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.action-bar-list .bar-row {
  grid-template-columns: 220px minmax(0, 1fr) 42px;
}

.bar-row {
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr) 42px;
  gap: 12px;
  align-items: center;
}

.bar-label {
  font-size: 13px;
  font-weight: 700;
}

.bar-track {
  height: 12px;
  border-radius: 999px;
  background: #eef2f7;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: #16244d;
}

.bar-fill.red {
  background: #e05c5c;
}

.bar-fill.orange {
  background: #d4c5a9;
}

.bar-fill.green {
  background: #7ec8c8;
}

.bar-fill.navy {
  background: #16244d;
}

.bar-fill.gray {
  background: #94a3b8;
}

.bar-value {
  text-align: right;
  font-size: 14px;
  font-weight: 700;
  color: #64748b;
}

.event-table-wrap {
  max-height: 660px;
  overflow: auto;
  padding: 20px;
}

.event-table {
  width: 100%;
  border-collapse: collapse;
  background: #fffaf3;
  font-size: 13px;
}

.event-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #fffaf3;
  color: #64748b;
  text-align: left;
  padding: 12px 14px;
  border-bottom: 1px solid #eadfcd;
  font-weight: 700;
}

.event-table td {
  padding: 13px 14px;
  border-bottom: 1px solid #f0e3d1;
  color: #0b1b44;
  vertical-align: middle;
}

.event-table tr:hover td {
  background: #f8f1e8;
}

.file-name {
  max-width: 170px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.risk-badge {
  display: inline-flex;
  min-width: 66px;
  justify-content: center;
  padding: 5px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.risk-badge.high {
  color: #e05c5c;
  background: #fdf1ef;
}

.risk-badge.medium {
  color: #8a6a2f;
  background: #f4ead7;
}

.risk-badge.low {
  color: #008f72;
  background: #dff5ed;
}

.risk-badge.unknown {
  color: #475569;
  background: #e2e8f0;
}

.cdr-list {
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cdr-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0e3d1;
}

.cdr-row:last-child {
  border-bottom: none;
}

.cdr-row strong {
  display: block;
  max-width: 360px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 700;
}

.cdr-row p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
}

.cdr-score {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 700;
}

.cdr-prob.high {
  color: #e05c5c;
}

.cdr-prob.medium {
  color: #8a6a2f;
}

.cdr-prob.low {
  color: #1e2a4a;
}


.empty-text,
.empty-cell {
  padding: 18px;
  color: #94a3b8;
  text-align: center;
  font-size: 13px;
}

.loading-box,
.error-box {
  max-width: 620px;
  margin: 80px auto;
  padding: 24px;
  border: 1px solid #eadfcd;
  border-radius: 18px;
  background: #fffaf3;
  color: #0b1b44;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.error-box strong {
  color: #dc2626;
  font-weight: 700;
}

.error-box p {
  margin: 8px 0 0;
  color: #64748b;
}

@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .overview-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .threat-overview-page {
    padding: 18px;
  }

  .overview-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    align-items: stretch;
    flex-direction: column;
  }

  .visit-stats {
    width: 100%;
  }

  .visit-stat {
    flex: 1;
  }

  .refresh-button {
    width: 100%;
  }

  .summary-grid,
  .process-grid,
  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .bar-row {
    grid-template-columns: 82px minmax(0, 1fr) 32px;
  }

  .event-table-wrap {
    padding: 12px;
  }

  .event-table th,
  .event-table td {
    padding: 10px 8px;
  }
}
`;
