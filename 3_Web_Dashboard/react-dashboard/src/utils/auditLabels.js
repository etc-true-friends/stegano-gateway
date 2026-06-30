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

export function getActionLabel(action) {
  const normalized = normalizeAction(action);
  if (normalized === 'BYPASS' || normalized === 'PASSED') return '통과';
  if (isPolicyBlockedLog({ action })) return '정책 격리/대체';
  if (normalized.includes('QUARANTINE') || normalized.includes('SANITIZED') || normalized.includes('CDR')) {
    return 'CDR 무해화';
  }
  return action || '-';
}
