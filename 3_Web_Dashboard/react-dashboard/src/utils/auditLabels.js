export function normalizeAction(action) {
  return String(action || '').trim().toUpperCase();
}

export function isPolicyBlockedLog(log) {
  const action = normalizeAction(log?.action);
  return action.includes('POLICY') || action.includes('BLOCK');
}

export function isSuspiciousLog(log) {
  const action = normalizeAction(log?.action);
  return log?.verdict === 'SUSPICIOUS' || action.includes('QUARANTINE') || isPolicyBlockedLog(log);
}

export function isCdrLog(log) {
  const action = normalizeAction(log?.action);
  return !isPolicyBlockedLog(log)
    && (action.includes('QUARANTINE') || action.includes('SANITIZED') || action.includes('CDR'));
}

export function getRiskLabel(level) {
  return {
    HIGH: '높음',
    MEDIUM: '보통',
    LOW: '낮음',
  }[level] || '-';
}

export function getVerdictLabel(verdict) {
  if (verdict === 'CLEAN') return '정상';
  if (verdict === 'SUSPICIOUS') return '위험';
  return verdict || '-';
}

// 탐지 엔진 컬럼: 위험 판정에 기여한 엔진만 표시. 정상 로그는 빈값.
// 위험도 뱃지처럼 배경은 연하게, 글씨는 같은 계열 진한 색으로.
export const ENGINE_COLORS = {
  'SRNet Ensemble': '#3b82f6',
  'Aletheia SPA': '#8a3ffc',
  'Hybrid Detection': '#0f766e',
  'Policy Engine': '#e0894e',
};

export const ENGINE_BG = {
  'SRNet Ensemble': '#eff6ff',
  'Aletheia SPA': '#f4edff',
  'Hybrid Detection': '#ecfdf5',
  'Policy Engine': '#fdf3ea',
};

export function getEngineLabel(log) {
  return log?.detection_engine || '-';
}

export const ALETHEIA_COLORS = {
  CLEAN: '#059669',
  SUSPICIOUS: '#dc2626',
  SKIPPED: '#64748b',
  UNAVAILABLE: '#d97706',
};

export const ALETHEIA_BG = {
  CLEAN: '#f0fdf4',
  SUSPICIOUS: '#fef2f2',
  SKIPPED: '#f1f5f9',
  UNAVAILABLE: '#fffbeb',
};

export function getAletheiaResult(log) {
  const raw =
    log?.aletheia_result ??
    log?.aletheia_status ??
    log?.aletheia_verdict ??
    log?.spa_result ??
    log?.spa_status ??
    log?.aletheia?.result ??
    log?.aletheia?.status;
  const value = String(raw || '').trim().toUpperCase();
  if (['CLEAN', 'SUSPICIOUS', 'SKIPPED', 'UNAVAILABLE'].includes(value)) return value;
  if (value === 'PASS' || value === 'PASSED' || value === 'NORMAL') return 'CLEAN';
  if (value === 'FOUND' || value === 'DETECTED' || value === 'WARNING') return 'SUSPICIOUS';
  if (value === 'NOT_RUN' || value === 'NOT RUN' || value === 'BYPASSED') return 'SKIPPED';
  if (value === 'ERROR' || value === 'FAILED' || value === 'TIMEOUT') return 'UNAVAILABLE';
  return '-';
}

export function getAuditLogKey(log) {
  if (!log) return '';
  const stableId = log.audit_id || log.id || log.file_id || log.attachment_id;
  if (stableId) return String(stableId);
  return [
    log.timestamp,
    log.original_name,
    log.sender_email,
    log.recipient_email,
    log.action,
  ].map(value => String(value || '')).join('|');
}

export function findAuditLogByKey(logs, key) {
  return (logs || []).find(log => getAuditLogKey(log) === key);
}

export function getPolicyReason(log) {
  return log?.policy_reason
    || log?.policy_detection_reason
    || log?.policy_rule
    || log?.blocked_reason
    || log?.reason
    || (isPolicyBlockedLog(log) ? '정책 조건에 따라 차단 또는 대체 처리되었습니다.' : '-');
}

export function getCdrResult(log) {
  return log?.cdr_result
    || log?.cdr_status
    || log?.cdr_process_result
    || log?.sanitization_result
    || (isCdrLog(log) ? 'CDR 무해화 처리 완료' : '-');
}

export function getActionLabel(action) {
  const normalized = normalizeAction(action);
  if (normalized === 'BYPASS' || normalized === 'PASSED') return '통과';
  if (isPolicyBlockedLog({ action })) return '정책 격리/대체';
  if (normalized.includes('QUARANTINE') || normalized.includes('SANITIZED') || normalized.includes('CDR')) {
    return 'CDR 무해화';
  }
  return action || '-';
}
