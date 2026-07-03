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
  'Hybrid Detection': '#8a3ffc',
  'Policy Engine': '#e0894e',
};

export const ENGINE_BG = {
  'SRNet Ensemble': '#eff6ff',
  'Hybrid Detection': '#f4edff',
  'Policy Engine': '#fdf3ea',
};

export function getEngineLabel(log) {
  return log?.detection_engine || '-';
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
