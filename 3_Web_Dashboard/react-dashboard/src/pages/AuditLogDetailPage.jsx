import { ArrowLeft, FileSearch } from 'lucide-react';
import PanelCard from '../components/common/PanelCard';
import {
  ALETHEIA_BG,
  ALETHEIA_COLORS,
  ENGINE_BG,
  ENGINE_COLORS,
  findAuditLogByKey,
  getActionLabel,
  getAletheiaResult,
  getCdrResult,
  getEngineLabel,
  getPolicyReason,
  getRiskLabel,
  getVerdictLabel,
  isPolicyBlockedLog,
} from '../utils/auditLabels';

function valueOrDash(value) {
  return value == null || value === '' ? '-' : String(value);
}

function formatDateTime(value) {
  return valueOrDash(value).slice(0, 19).replace('T', ' ');
}

function formatProbability(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(1)}%` : '-';
}

function getParticipantText(log) {
  const sender = log.sender_email || '-';
  const recipient = log.recipient_email || '-';
  if (sender === '-' && recipient === '-') return '-';
  return `${sender} -> ${recipient}`;
}

function SummaryItem({ label, children }) {
  return (
    <div className="audit-detail-summary-item">
      <span>{label}</span>
      <strong>{children}</strong>
    </div>
  );
}

function DetailRow({ label, children }) {
  return (
    <div className="audit-detail-row">
      <dt>{label}</dt>
      <dd>{children || '-'}</dd>
    </div>
  );
}

function StatusBadge({ type, children }) {
  const colorMap = {
    engine: '#64748b',
    policy: '#8a3ffc',
  };
  const bgMap = {
    engine: '#f1f5f9',
    policy: '#f5f0ff',
  };

  return (
    <span className="audit-status-badge" style={{ color: colorMap[type], background: bgMap[type] }}>
      {children}
    </span>
  );
}

export default function AuditLogDetailPage({ logs = [], routeParams = {}, onNavigate }) {
  const log = findAuditLogByKey(logs, routeParams.logKey);

  if (!log) {
    return (
      <div className="page-content" style={{ maxWidth: '100%' }}>
        <PanelCard title="감사 로그 상세">
          <button className="back-btn" onClick={() => onNavigate?.('audit')}>
            <ArrowLeft size={14} />
            감사 로그로 돌아가기
          </button>
          <div className="empty-state">선택한 감사 로그를 찾을 수 없습니다</div>
        </PanelCard>
      </div>
    );
  }

  const engine = getEngineLabel(log);
  const aletheiaResult = getAletheiaResult(log);
  const isPolicy = isPolicyBlockedLog(log);

  return (
    <div className="page-content" style={{ maxWidth: '100%' }}>
      <PanelCard title="감사 로그 상세">
        <div className="audit-detail-header">
          <button className="back-btn" onClick={() => onNavigate?.('audit')}>
            <ArrowLeft size={14} />
            목록
          </button>
          <div className="audit-detail-title">
            <FileSearch size={18} />
            <div>
              <h2>{log.original_name || '이름 없는 파일'}</h2>
              <p>{formatDateTime(log.timestamp)} · {valueOrDash(log.direction)}</p>
            </div>
          </div>
        </div>

        <div className="audit-detail-summary">
          <SummaryItem label="SRNet 확률">{formatProbability(log.stego_probability)}</SummaryItem>
          <SummaryItem label="Aletheia 결과">
            {aletheiaResult === '-' ? '-' : (
              <span className="aletheia-badge" style={{
                color: ALETHEIA_COLORS[aletheiaResult],
                background: ALETHEIA_BG[aletheiaResult],
              }}>
                {aletheiaResult}
              </span>
            )}
          </SummaryItem>
          <SummaryItem label="위험 등급">
            <span className={`risk-badge risk-${(log.risk_level || 'unknown').toLowerCase()}`}>
              {getRiskLabel(log.risk_level)}
            </span>
          </SummaryItem>
          <SummaryItem label="처리 결과">{getActionLabel(log.action)}</SummaryItem>
        </div>

        <div className="audit-detail-grid">
          <section className="audit-detail-section">
            <h3>탐지 엔진</h3>
            <dl>
              <DetailRow label="엔진 구분">
                {engine === '-' ? '-' : (
                  <span className="engine-badge" style={{
                    color: ENGINE_COLORS[log.detection_engine] || ENGINE_COLORS[engine] || '#64748b',
                    background: ENGINE_BG[log.detection_engine] || ENGINE_BG[engine] || '#f1f5f9',
                  }}>
                    {engine}
                  </span>
                )}
              </DetailRow>
              <DetailRow label="SRNet Ensemble 확률">{formatProbability(log.stego_probability)}</DetailRow>
              <DetailRow label="Aletheia SPA 결과">{aletheiaResult}</DetailRow>
              <DetailRow label="최종 판정">{isPolicy ? '정책' : getVerdictLabel(log.verdict)}</DetailRow>
            </dl>
          </section>

          <section className="audit-detail-section">
            <h3>처리 상세</h3>
            <dl>
              <DetailRow label="정책 탐지 사유">
                {isPolicy ? <StatusBadge type="policy">{getPolicyReason(log)}</StatusBadge> : getPolicyReason(log)}
              </DetailRow>
              <DetailRow label="CDR 처리 결과">{getCdrResult(log)}</DetailRow>
              <DetailRow label="액션">{getActionLabel(log.action)}</DetailRow>
              <DetailRow label="파일 ID">{valueOrDash(log.file_id)}</DetailRow>
            </dl>
          </section>

          <section className="audit-detail-section audit-detail-section-wide">
            <h3>메일 및 파일 정보</h3>
            <dl>
              <DetailRow label="메일 경로">{getParticipantText(log)}</DetailRow>
              <DetailRow label="발신자">{valueOrDash(log.sender_email)}</DetailRow>
              <DetailRow label="수신자">{valueOrDash(log.recipient_email)}</DetailRow>
              <DetailRow label="원본 파일명">{valueOrDash(log.original_name)}</DetailRow>
            </dl>
          </section>
        </div>
      </PanelCard>
    </div>
  );
}
