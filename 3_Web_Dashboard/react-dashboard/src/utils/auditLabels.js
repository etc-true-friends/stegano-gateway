export function normalizeAction(action) {
  return String(action || '').trim().toUpperCase();
}

export function isSuspiciousLog(log) {
  return log?.verdict === 'SUSPICIOUS' || normalizeAction(log?.action).includes('QUARANTINE');
}

export function isCdrLog(log) {
  const action = normalizeAction(log?.action);
  return action.includes('QUARANTINE') || action.includes('SANITIZED') || action.includes('CDR');
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
  if (normalized.includes('QUARANTINE') || normalized.includes('SANITIZED') || normalized.includes('CDR')) {
    return 'CDR 무해화';
  }
  return action || '-';
}
